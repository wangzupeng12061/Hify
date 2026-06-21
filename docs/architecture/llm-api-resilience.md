# 外部 LLM API 调用与容错规范

本文定义 Hify 调用 OpenAI、Anthropic Claude、Google Gemini 和 Ollama 时的强制技术方案，覆盖线程与并发、容错、超时和重试。实现必须同时遵守 `code-organization.md`。

## 1. 目标与基本决策

外部 LLM 调用是高延迟、不稳定、受限流约束且可能产生重复费用的远程 I/O。Hify 必须遵守以下决策：

1. 交互式 Agent 调用在 FastAPI 进程内使用异步 SDK 和 SSE 流式返回，禁止交给 Celery。
2. 文档处理、Embedding、批量生成和统计任务进入独立 Celery 队列。
3. 每个供应商 SDK 只负责协议适配；超时、重试、熔断、限流和回退由 Hify 统一实现。
4. SDK 自带重试必须关闭，避免“SDK 重试 x Hify 重试”造成指数级请求和不可预测延迟。
5. 一旦向用户发送首个模型内容 Token，本次调用禁止自动重试或切换模型。
6. 所有调用都受总时间预算控制；重试和回退不能延长总预算。

## 2. 代码位置

```text
backend/src/hify/modules/providers/
├── contracts/
│   ├── dto.py                    # ModelRequest、ModelChunk、ModelUsage
│   ├── errors.py                 # 统一供应商错误
│   └── services.py               # ModelGateway Protocol
├── application/
│   ├── routing.py                # 主模型与显式回退链选择
│   └── policies.py               # Policy DTO，不依赖 SDK
├── infrastructure/
│   ├── adapters/
│   │   ├── openai/
│   │   ├── anthropic/
│   │   ├── gemini/
│   │   └── ollama/
│   └── resilience/
│       ├── bulkhead.py            # 并发隔离
│       ├── circuit_breaker.py     # 熔断器
│       ├── client_registry.py     # SDK Client 生命周期
│       ├── rate_limiter.py        # Redis 分布式配额
│       ├── retry.py               # 统一重试算法
│       └── timeout.py             # Deadline 与分阶段超时
└── wiring.py
```

`runs` 模块只依赖 `providers.contracts.ModelGateway`，禁止导入任何供应商 SDK 或 resilience 实现。

## 3. 统一调用契约

所有适配器必须转换为相同的输入、事件和异常：

```python
class ModelGateway(Protocol):
    def stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]: ...


@dataclass(frozen=True, slots=True)
class CallContext:
    run_id: UUID
    attempt_id: UUID
    team_id: UUID
    user_id: UUID
    deadline: float       # time.monotonic() absolute deadline
    cancellation: CancellationToken
```

`ModelChunk` 只能是 Hify 定义的文本、推理、工具调用、用量、结束或错误事件，禁止包含 SDK Response、LangGraph Event 或 HTTPX Response。

## 4. 线程与并发管理

### 4.1 FastAPI 交互式调用

- Router 和调用链必须使用 `async def`。
- OpenAI、Anthropic、Gemini 和 Ollama 必须使用各自的异步 Client。
- 禁止为每个请求创建线程或 SDK Client。
- 禁止在 Event Loop 中调用同步 SDK、`requests`、同步文件 I/O 或 CPU 密集代码。
- 每个 API 容器使用一个 Event Loop 和一个 Uvicorn Worker；初始运行 2 个 API 容器。
- 增加吞吐优先水平扩容容器，不通过持续增加线程数扩容。

如果某个依赖只有同步接口，必须临时使用 `anyio.to_thread.run_sync`，并使用独立 `CapacityLimiter(8)`。禁止使用无限制的默认线程池。该适配器必须标记技术债务并优先替换为异步实现。

### 4.2 Client 生命周期与连接池

`ProviderClientRegistry` 在进程启动时创建，在进程关闭时逐个 `aclose()`：

- Key：`(provider, credential_id, base_url)`，禁止把明文密钥放入 Key 或日志。
- 同一 Key 的请求复用一个 Client 和 HTTP 连接池。
- LRU 最大 128 个 Client，空闲 15 分钟淘汰并关闭。
- 每个云供应商 Client：`max_connections=20`、`max_keepalive_connections=10`、`keepalive_expiry=30s`。
- 每个 Ollama Host：`max_connections=4`、`max_keepalive_connections=2`。
- 凭证更新时立即使对应 Client 失效，不等待 TTL。

这些值是初始默认值，必须通过配置覆盖。调整依据是 `llm_in_flight`、连接池等待和供应商限流指标，而不是注册用户数。

### 4.3 Bulkhead 并发隔离

每个 API Worker 必须设置独立 `asyncio.Semaphore`，防止一个供应商耗尽全部连接：

| 维度 | 初始上限 |
|---|---:|
| 单用户交互式 Run | 2 |
| 单团队交互式 Run | 20 |
| 单云供应商凭证/Worker | 16 |
| 单 Ollama Host/Worker | 2 |

获取 Semaphore 最多等待 2 秒，超时返回 `PROVIDER_BUSY`，不得继续堆积等待。Ollama 的上限最终必须与实际 GPU/模型并发能力一致。

本地 Semaphore 保护进程资源；Redis Token Bucket 负责跨实例 RPM/TPM 配额。Redis Key 必须包含 `provider + credential_id + model`，令牌扣减使用 Lua 保证原子性。配额未知时采用保守配置，禁止解释为无限。

### 4.4 后台任务

Celery 必须使用不同队列隔离负载：

```text
ingestion     文档解析，CPU/IO 混合
embedding     Embedding API 调用
llm_batch     非交互式模型生成
maintenance   清理和统计
```

- `llm_batch` 初始 `concurrency=4`、`worker_prefetch_multiplier=1`。
- CPU 密集的解析任务使用 Prefork 进程，不在线程池运行。
- 每个 Celery 子进程拥有自己的同步 Client，禁止跨进程共享连接对象。
- 任务只有在幂等时才允许 `acks_late=True`。
- 交互式聊天、工具调用循环和 SSE 禁止进入 Celery。

## 5. 超时方案

### 5.1 分层超时

一次调用必须同时设置以下超时，不能只设置单个总 Timeout：

| 超时 | 云模型默认值 | Ollama 默认值 | 含义 |
|---|---:|---:|---|
| Pool acquire | 2s | 2s | 等待连接池连接 |
| Connect | 5s | 2s | 建立 TCP/TLS 连接 |
| Write | 15s | 15s | 上传请求体 |
| First token | 45s | 120s | 请求发出到首个内容事件 |
| Stream idle | 60s | 120s | 相邻上游数据事件最大间隔 |
| Standard attempt | 120s | 300s | 单次普通模型尝试 |
| Reasoning attempt | 300s | 600s | 单次长推理模型尝试 |
| Agent run | 600s | 600s | 整个 Agent Run，包括工具调用 |

Embedding 单次 Attempt 默认 30 秒，模型列表和健康检查默认 10 秒。

### 5.2 Deadline 传播

`runs` 在开始时计算绝对 `deadline = monotonic() + run_timeout`，通过 `CallContext` 传到所有模型、RAG 和工具调用。每个下游 Timeout 必须取配置值与剩余时间的较小值。

开始一次重试前必须满足：

```text
remaining_budget >= retry_delay + minimum_attempt_budget
```

`minimum_attempt_budget` 初始为 10 秒。不满足时直接返回总 Deadline 超时，禁止再发请求。

### 5.3 流式连接

- HTTP Read Timeout 表示相邻网络数据间隔，不等于整个生成时间。
- 应用层单独计时 First Token 和 Stream Idle。
- Hify SSE 每 15 秒发送一次注释 Heartbeat，避免代理关闭空闲连接。
- Heartbeat 不重置上游 LLM 的 Stream Idle Timeout。
- 浏览器断开、用户点击停止或 Run 超时后，必须取消上游 Task、关闭 Response 并释放 Semaphore。

## 6. 重试方案

### 6.1 重试层级

只允许 `providers/infrastructure/resilience/retry.py` 执行重试。适配器必须关闭 SDK 默认重试：OpenAI/Anthropic 设置 `max_retries=0`；其他 SDK 若无法关闭，Hify 外层尝试次数必须扣除 SDK 内部尝试，并在指标中明确记录。

交互式调用对同一模型最多 3 次 Attempt（首次 + 2 次重试），整条回退链最多 4 次；后台任务对同一模型最多 5 次，整条回退链最多 6 次。模型回退不得突破总 Attempt 上限。

### 6.2 可重试错误

| 错误 | 交互式策略 |
|---|---|
| DNS、连接拒绝、Connect Timeout | 首 Token 前重试 |
| Read Timeout、连接中断 | 仅首 Token 前重试 |
| HTTP 408 | 重试 |
| HTTP 429 | 遵守 `Retry-After` 后重试 |
| HTTP 500/502/503/504 | 重试 |
| 供应商明确标记的临时过载 | 重试 |
| OpenAI HTTP 409 | 由 OpenAI Adapter 标记为可重试 |

禁止重试：400、401、403、404、422、内容安全拒绝、上下文超长、无效工具 Schema、无效模型名和额度永久耗尽。

### 6.3 退避算法

使用 Full Jitter：

```python
upper = min(cap, base * (2 ** retry_index))
delay = random.uniform(0, upper)
```

- 交互式：`base=0.5s`、`cap=8s`。
- 后台任务：`base=1s`、`cap=60s`。
- 有合法 `Retry-After` 时使用其值，但不得超过剩余 Deadline。
- 禁止固定间隔重试，禁止无 Jitter 的指数退避。

### 6.4 流式重试边界

适配器在产生首个内容、推理或工具调用增量后设置 `content_emitted=True`。此后任何错误都转换为 `ProviderStreamInterruptedError`：

- 不自动重试。
- 不自动切换模型。
- 保留已经输出的内容并把 Run 标记为 `interrupted`。
- UI 提供“重新生成”，由用户创建新的 Attempt。

原因是供应商 API 通常不能从确定 Token 位置恢复；自动重试会重复内容、重复费用，并可能产生不同工具调用。

### 6.5 幂等与副作用

- 每个 Run、模型 Attempt 和工具调用分别拥有 `run_id`、`attempt_id`、`tool_call_id`。
- 持久化流式事件使用 `(run_id, sequence)` 唯一约束。
- 模型生成可能已在供应商完成但响应丢失，因此重试只能做到业务去重，不能保证不产生重复模型费用。
- 工具执行不是模型重试的一部分。具有外部副作用的工具必须使用 `tool_call_id` 作为幂等键。
- 禁止因为模型重试重新执行已成功的工具。

## 7. 容错方案

### 7.1 统一错误分类

所有 Adapter 必须映射到以下错误，API 禁止暴露供应商异常文本：

```text
ProviderAuthenticationError     永久错误
ProviderPermissionError         永久错误
ProviderBadRequestError         永久错误
ProviderContextLimitError       永久错误
ProviderContentPolicyError      永久错误
ProviderRateLimitError          临时错误，携带 retry_after
ProviderTimeoutError            临时错误，携带 timeout_stage
ProviderUnavailableError        临时错误
ProviderStreamInterruptedError  已输出内容，不重试
ProviderCancelledError          用户或系统取消
```

完整供应商错误只进入受限日志，并移除 API Key、Prompt 和响应正文。

### 7.2 熔断器

熔断状态保存在 Redis，Key 为 `(provider, credential_id, base_url, model)`，保证多 API 实例共享状态：

- 滑动窗口：最近 30 秒，至少 10 次请求。
- Open 条件：连接错误、Timeout 和 5xx 的比例达到 50%。
- Open 时长：30 秒。
- Half-open：只允许 2 个探测请求。
- 两个探测都成功则 Close；任一失败重新 Open 60 秒。
- 连续 Open 时长按 30、60、120 秒增长，上限 5 分钟。

401、403、400、内容拒绝、上下文超长和用户取消不计入熔断。429 单独进入限流指标，不触发供应商故障熔断。

Redis 不可用时熔断器降级为进程内状态；调用链不能因为熔断存储故障而全部失败。

### 7.3 显式模型回退

回退链属于已发布 Agent Version，不允许平台静默选择任意模型。每个候选模型必须声明能力：

```text
text, vision, tools, structured_output, context_window, data_region
```

只有能力满足当前请求、数据策略允许且尚未输出首 Token 时才能回退。默认策略：

1. 在主模型执行统一重试。
2. 主模型熔断或重试耗尽后，选择下一个兼容候选。
3. 整条回退链共用原始 Run Deadline 和最大 Attempt 数。
4. 日志和 UI 记录实际供应商、模型及回退原因。

禁止默认 Hedged Request（同时请求多个模型），因为它会成倍增加费用并使取消和计费复杂化。

### 7.4 降级行为

| 场景 | 行为 |
|---|---|
| 所有模型不可用 | 返回可重试错误，保留 Run 和诊断 ID |
| 工具调用模型不可用 | 只回退到支持工具调用的候选 |
| RAG 可用但生成不可用 | 不向用户暴露原始检索片段，返回模型不可用 |
| Redis 限流器不可用 | 每凭证采用进程内保守上限，禁止无限放行 |
| Ollama 不可用 | 可按 Agent 明确配置回退到云模型，默认不跨数据边界 |
| 流中断 | 保留部分输出，Run 标记 `interrupted` |

## 8. 取消与资源回收

取消来源包括浏览器断开、用户停止、Run Deadline、服务关闭和管理员取消。取消信号必须从 `runs` 传播到 Provider Adapter：

1. 设置 `CancellationToken`。
2. 取消正在等待的重试 Sleep。
3. 取消 HTTP Stream Task 并关闭 Response。
4. 释放本地和 Redis 并发租约。
5. 持久化 `cancelled` 事件，不记为供应商失败。
6. 记录已经确认的 Token Usage；未知用量标记为 `estimated`，禁止记为零。

## 9. 配置模型

所有默认值通过类型化配置提供，不允许散落在 Adapter 中：

```text
LLM_CONNECT_TIMEOUT_SECONDS=5
LLM_POOL_TIMEOUT_SECONDS=2
LLM_WRITE_TIMEOUT_SECONDS=15
LLM_FIRST_TOKEN_TIMEOUT_SECONDS=45
LLM_STREAM_IDLE_TIMEOUT_SECONDS=60
LLM_ATTEMPT_TIMEOUT_SECONDS=120
LLM_REASONING_ATTEMPT_TIMEOUT_SECONDS=300
LLM_RUN_TIMEOUT_SECONDS=600
LLM_INTERACTIVE_MAX_ATTEMPTS_PER_MODEL=3
LLM_INTERACTIVE_MAX_TOTAL_ATTEMPTS=4
LLM_BACKGROUND_MAX_ATTEMPTS_PER_MODEL=5
LLM_BACKGROUND_MAX_TOTAL_ATTEMPTS=6
LLM_RETRY_BASE_SECONDS=0.5
LLM_RETRY_CAP_SECONDS=8
LLM_SSE_HEARTBEAT_SECONDS=15
```

供应商、模型或 Agent Version 可以收紧这些值；放宽 Run 总 Deadline 必须由管理员显式配置。

## 10. 可观测性与告警

每次 Attempt 必须记录：

```text
run_id, attempt_id, team_id, provider, model, credential_id_hash,
status, error_type, retry_index, fallback_from, timeout_stage,
queue_wait_ms, connect_ms, time_to_first_token_ms, duration_ms,
input_tokens, output_tokens, estimated_cost, provider_request_id
```

禁止默认记录 API Key、完整 Prompt、完整响应和工具敏感参数。

必须提供以下指标：

- `llm_requests_total{provider,model,status}`
- `llm_in_flight{provider}`
- `llm_time_to_first_token_seconds`
- `llm_request_duration_seconds`
- `llm_retries_total{provider,reason}`
- `llm_timeouts_total{provider,stage}`
- `llm_rate_limits_total{provider}`
- `llm_stream_interruptions_total{provider}`
- `llm_circuit_state{provider,model}`
- `llm_fallbacks_total{from_provider,to_provider}`

初始告警条件：5 分钟 5xx/Timeout 比例超过 10%、P95 First Token 超过 20 秒、429 比例超过 5%、任一熔断器持续 Open 超过 2 分钟。

## 11. 实施顺序

1. 定义统一 DTO、错误和 `ModelGateway`。
2. 实现 Async Client Registry、连接池和取消传播。
3. 实现 Deadline、分阶段 Timeout 和统一 Retry。
4. 实现本地 Bulkhead 与 Redis RPM/TPM 限流。
5. 接入四个供应商 Adapter，并关闭 SDK 内部重试。
6. 实现 Redis 熔断器和显式回退链。
7. 接入结构化日志、Metrics 和 Trace。
8. 增加故障注入测试后再开放生产流量。

## 12. 必测场景

- DNS 失败、连接拒绝、Connect Timeout。
- 首 Token 前发生 429、500、503 和 Read Timeout。
- 输出 Token 后连接中断，确认没有自动重试。
- `Retry-After` 超过剩余 Deadline。
- 用户取消时正在请求、等待 Semaphore 和等待退避。
- 单个供应商慢请求耗尽自身 Bulkhead，但其他供应商仍可调用。
- 熔断器 Open、Half-open 成功和 Half-open 失败。
- Redis 不可用时采用保守本地限流。
- 主模型失败后仅回退到能力兼容模型。
- 工具成功后模型重试不会重复执行工具。
- SDK Client 凭证更新、LRU 淘汰和进程关闭时正确释放连接。

故障测试应使用 HTTP Stub 注入延迟、分块中断和指定状态码，不依赖真实供应商产生故障。

## 13. 官方参考

- [OpenAI Python SDK：Retries 与 Timeouts](https://github.com/openai/openai-python#retries)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Google Gen AI Python SDK](https://github.com/googleapis/python-genai)
- [Ollama Python：Custom Client 与 Async Client](https://github.com/ollama/ollama-python#custom-client)
- [HTTPX Timeouts](https://www.python-httpx.org/advanced/timeouts/)
- [HTTPX Resource Limits](https://www.python-httpx.org/advanced/resource-limits/)
- [FastAPI Concurrency and async/await](https://fastapi.tiangolo.com/async/)
