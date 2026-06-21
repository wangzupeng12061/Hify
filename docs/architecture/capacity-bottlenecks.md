# Hify 一期性能瓶颈分析

本文基于 `deployment.md` 和 `llm-api-resilience.md` 的一期架构评估性能风险。排序依据是“对核心对话链路的影响范围 x 一期发生概率”，不是组件理论上限。

## 1. 结论

一期容量目标按以下负载验收：

```text
注册用户：50-100
同时活跃用户：20
同时交互式 Agent Run：20
同时 SSE 连接：100
单用户同时 Run：2
单团队同时 Run：20
文档处理并发：4
```

达到几千注册用户本身不会触发重构；并发 Run、LLM 配额、数据库写入、队列等待和知识库 Chunk 数才是扩容依据。

## 2. 严重程度排序

| 排名 | 瓶颈 | 严重程度 | 一期结论 |
|---:|---|---|---|
| 1 | 外部 LLM 延迟、限流和配额 | 极高 | 必须处理 |
| 2 | FastAPI Event Loop 与进程内 Agent Runtime | 极高 | 必须处理 |
| 3 | PostgreSQL 写放大、事务和连接池 | 高 | 必须处理 |
| 4 | 单 Celery Worker 的队头阻塞 | 高 | 必须处理基础保护，暂不拆集群 |
| 5 | Redis 混合承载 Broker 与运行控制 | 高 | 必须处理内存安全并监控 |
| 6 | pgvector 检索与业务查询争用数据库 | 中高 | 必须建索引和监控，暂不拆向量库 |
| 7 | Ollama GPU/内存和推理队列 | 中高 | 使用 Ollama 时必须处理 |
| 8 | 单 Egress Proxy 的连接与带宽 | 中 | 必须正确配置，只监控不扩容 |
| 9 | SSE 长连接、代理缓冲和断线 | 中 | 必须处理配置，暂不拆 SSE Gateway |
| 10 | SDK Client Registry 抖动和连接重建 | 中低 | 只监控 |
| 11 | Next.js Web 和对象存储 | 低 | 一期无需专项优化 |

## 3. 瓶颈详情

### 3.1 外部 LLM 延迟、限流和配额

**为什么排第一**

一次 Agent Run 可能包含多次模型调用和工具循环。即使 Hify 本身只耗时几十毫秒，模型首 Token、429、5xx 或重试也会把总延迟放大到几十秒甚至数分钟。增加 API 副本不能提高供应商凭证的 RPM/TPM。

**触发条件**

- `llm_in_flight` 达到配置上限的 80%，持续 5 分钟。
- 429 比例超过 5%，或重试请求超过总 Attempt 的 10%。
- P95 First Token 超过 20 秒，或 P95 单次生成超过 90 秒。
- 单个 Run 平均模型 Attempt 超过 3 次。
- Agent 工作流并行节点导致同一时刻模型调用数明显高于 Run 数。

**一期是否处理：必须。**

一期必须实现异步 Client 复用、用户/团队/凭证 Bulkhead、Redis RPM/TPM 限流、统一超时和重试、熔断以及显式回退。禁止把增加线程数当作解决方案。必须限制每个 Agent Version 的最大模型步骤数和最大 Token 预算。

一期不需要多区域模型网关，也不默认同时请求多个模型。

### 3.2 FastAPI Event Loop 与进程内 Agent Runtime

**为什么排第二**

两个 API 副本同时承担管理 API、SSE 长连接、RAG、Agent Loop 和工具调用。任何同步 SDK、同步文件操作、CPU 解析或无界任务创建都会阻塞一个副本的唯一 Event Loop，使该副本上所有请求一起变慢。

**触发条件**

- Event Loop Lag P95 超过 100 ms，持续 5 分钟。
- API CPU 超过 70% 或内存超过 75%，持续 10 分钟。
- 单副本活跃 Run 超过 12，或活跃 SSE 超过 100。
- `asyncio` Task 数持续增长，Run 结束后未回落。
- 普通管理 API P95 超过 300 ms，但数据库查询本身正常。
- Thread Pool 8 个槽位持续占满。

**一期是否处理：必须。**

一期必须保证整个交互链路异步，阻塞依赖放到有界线程池，文档和 CPU 工作进入 Celery。每个 Run 必须有 Deadline、取消传播、步骤数上限，并在结束时释放 Task、HTTP Response、Semaphore 和数据库 Session。

一期不拆独立 Runtime。达到 40 个以上持续并发 Run，或管理 API 与 SSE 明显相互影响时，再拆 `runs` Runtime 和 Event Gateway。

### 3.3 PostgreSQL 写放大、事务和连接池

**为什么排第三**

PostgreSQL 同时保存业务数据、消息、Run、Step、流式事件、Job、Outbox 和向量。若每个 Token 都单独写入，会把一次回答变成数百次事务；两个 API 副本和 Worker 的理论连接预算可达到 45 个，也可能在故障重试时快速耗尽。

**触发条件**

- 数据库 CPU 或磁盘 Utilization 超过 70%，持续 10 分钟。
- 活跃连接超过数据库上限的 70%。
- 获取 SQLAlchemy 连接 P95 超过 50 ms，或出现 Pool Timeout。
- 核心 OLTP 查询 P95 超过 100 ms。
- 锁等待 P95 超过 50 ms，或出现 Deadlock。
- Run 事件写入次数接近输出 Token 数。
- `runs_events`、`messages` 或 `outbox` 表增长超过预估且 Vacuum 跟不上。

**一期是否处理：必须。**

必须按 100-250 ms 或 20-50 个 Chunk 批量持久化流式文本，只对 Run 状态、工具边界和完成事件立即提交。为团队隔离、Run 查询、消息时间线、Job 状态、Outbox 状态建立组合索引。长模型请求期间禁止持有数据库事务或连接。

一期保持 PostgreSQL 单主，不上读副本；设置连接预算告警、慢查询日志和 Run/Event 保留策略。

### 3.4 单 Celery Worker 的队头阻塞

**为什么排第四**

一个 Prefork Concurrency 4 的 Worker 同时消费文档解析、Embedding、批量生成、集成事件和维护任务。大 PDF、OCR 或慢 Embedding 会占满四个进程，使 Outbox 和小任务即使在不同队列也得不到执行槽。

**触发条件**

- 任一队列最老任务等待超过 60 秒。
- Worker Busy Slots 超过 80%，持续 10 分钟。
- `ingestion` 队列长度超过 20，或单团队待处理文档超过 10。
- 单文档解析超过 2 分钟或内存超过 1 GiB。
- `events` Outbox 或 `maintenance` Job 因文档任务持续延迟。

**一期是否处理：必须做基础保护。**

一期保留一个 Worker Deployment，但必须设置 `events` 最高队列优先级、单任务 Soft/Hard Time Limit、文件大小/页数限制、单团队并发和幂等 Job 租约。通过 Redis Semaphore 把 `ingestion + embedding` 并发限制为 3，为 `events/maintenance/llm_batch` 保留第 4 个 Worker 槽位。

连续一周每天出现队列等待超过 60 秒时，拆分 `worker-ingestion` 与 `worker-llm`，不需要修改领域代码。

### 3.5 Redis 混合承载 Broker 与运行控制

**为什么排第五**

Redis 同时承担 Celery Broker、限流、并发租约、熔断和缓存。任务突发或缓存失控可能挤占 Broker 内存，使限流状态和后台任务同时异常。

**触发条件**

- Redis 内存超过 70%。
- 出现任意非预期 Eviction。
- Command P95 超过 5 ms，或连接使用率超过 70%。
- Celery 队列持续增长，Redis 网络带宽或 CPU 超过 70%。
- Rate Limit Lua 执行超过 10 ms。

**一期是否处理：必须。**

一期不使用 Redis 保存可重建的大对象或通用页面缓存。所有限流、租约和熔断 Key 必须有 TTL，Broker 任务的事实状态保存 PostgreSQL。设置内存告警和 `noeviction`，避免静默丢弃 Celery 消息；容量不足时让写入显式失败并由 Job Reconciler 恢复。

一期可共用一个托管 Redis。出现内存竞争、Broker 延迟或需要不同持久化策略时，优先拆成 `redis-broker` 和 `redis-runtime`。

### 3.6 pgvector 检索与业务查询争用

**为什么排第六**

向量检索、批量写入 Embedding 和普通 OLTP 共用 PostgreSQL CPU、缓存和 I/O。无 ANN 索引、过滤字段缺索引或一次返回过多 Chunk 会拖慢所有业务请求。

**触发条件**

- 知识库 Chunk 总数超过 50 万时仍在使用全表精确扫描。
- 检索 P95 超过 200 ms。
- 单次检索候选超过 1000 或最终返回超过 20 个 Chunk。
- Embedding 批量写入时普通 API P95 上升超过 30%。
- 向量索引不能放入有效缓存，数据库 I/O 持续超过 70%。

**一期是否处理：必须做索引和边界控制。**

一期使用 pgvector HNSW/合适的 ANN 索引，为 `team_id + knowledge_base_id` 等过滤字段建立 B-tree 索引，限制 Top-K 和上下文总 Token。Embedding 分批写入，不在交互式请求内建索引。

一期不拆专用向量数据库。只有在索引调优后检索仍持续超过 200 ms，或向量负载明显拖慢 OLTP，才评估拆分。

### 3.7 Ollama GPU、显存和推理队列

**为什么排第七**

Ollama 的吞吐主要由模型大小、上下文长度、量化方式和 GPU 显存决定。超过显存会导致模型换入换出或退回 CPU，TTFT 会突然恶化。

**触发条件**

- Ollama 同时请求超过 2。
- GPU Utilization 持续超过 90%，显存超过 90%。
- Ollama Pool Wait 超过 2 秒。
- P95 First Token 超过 30 秒，或出现频繁模型装卸。
- 上下文长度增长后 Tokens/s 明显下降。

**一期是否处理：使用 Ollama 时必须。**

一期必须限制 Host 并发、限制上下文和最大输出 Token、固定允许模型列表，并监控 TTFT、Tokens/s、GPU 和模型加载时间。Ollama 不属于 API 自动扩容范围。

一期不建设 GPU 调度集群。需要超过单机能力时，增加独立 Host 并在模型路由层选择实例。

### 3.8 单 Egress Proxy

**为什么排第八**

所有 LLM、MCP 和 HTTP Tool 流量通过一个 0.5 vCPU Proxy。错误的响应缓冲、连接数或 DNS 配置会增加 TTFT；Proxy 退出会阻断全部外部能力。

**触发条件**

- 活跃连接超过配置上限的 70%。
- Proxy CPU 超过 60% 或内存超过 70%。
- Proxy 引入的 P95 延迟超过 100 ms。
- 连接建立失败超过 1%，或出现响应缓冲导致非流式返回。

**一期是否处理：必须正确配置，只监控不扩容。**

必须关闭流式响应缓冲，连接上限至少 200，复用 Keep-Alive，并对响应体和重定向设限。只运行一个副本可以接受，但必须有自动重启和健康检查；禁止故障时绕过 Proxy。

### 3.9 SSE 长连接和代理行为

**为什么排第九**

SSE 本身消耗很低，但 Idle Timeout、代理缓冲、浏览器重复连接或断线未取消上游任务会产生“看似卡住”和资源泄漏。

**触发条件**

- 活跃 SSE 数超过 100/副本。
- SSE 断线率超过 2%，或重复 Claim Run 增加。
- API 已收到模型 Chunk，但浏览器延迟超过 1 秒才显示。
- 浏览器断开后上游 LLM 仍持续生成超过 5 秒。

**一期是否处理：必须处理配置。**

必须关闭代理缓冲、发送 15 秒 Heartbeat、限制单用户连接数、传播取消并清理 Task。当前 100 个连接目标不需要独立 SSE Gateway。

### 3.10 SDK Client Registry 抖动

**为什么排第十**

Client Registry 最多缓存 128 个 `(provider, credential, base_url)`。大量团队自带 Key 或频繁更新凭证会触发 LRU 淘汰，导致 TLS 连接不断重建并增加 TTFT。

**触发条件**

- Client Registry 命中率低于 90%。
- 每分钟 Eviction 超过 10。
- TLS Connect P95 超过 500 ms。
- 活跃 Credential Key 接近或超过 128。

**一期是否处理：只监控。**

保持 LRU 和 15 分钟 Idle TTL，记录命中、创建和淘汰指标。只有实际抖动后才调整容量或共享底层 Transport。

### 3.11 Next.js 和对象存储

**触发条件**

- Web CPU 持续超过 70%，SSR P95 超过 500 ms。
- Presigned 上传失败超过 1%，或对象存储区域与 Worker 跨区导致下载明显变慢。

**一期是否处理：无需专项优化。**

文件直传 S3 已避免 API 带宽瓶颈。Web 不执行业务和模型逻辑，1-2 个副本足够。只需保证服务、数据库和对象存储位于同一区域，并设置上传大小限制。

## 4. 一期必须完成的性能措施

上线前必须具备：

1. LLM 并发、RPM/TPM、超时、重试和熔断控制。
2. 全异步交互式调用，Event Loop Lag 指标和 Task 清理。
3. 流式事件批量写入，而不是每 Token 一次事务。
4. PostgreSQL 核心组合索引、连接池预算和慢查询日志。
5. Celery 文件限制、任务 Time Limit、团队配额和 Job Reconciler。
6. Redis TTL、内存/延迟告警和禁止非预期 Eviction。
7. pgvector ANN 索引、过滤索引、Top-K 和上下文 Token 上限。
8. Egress/SSE 不缓冲流式响应并正确传播取消。

一期明确不做：

- 独立 Agent Runtime。
- 独立向量数据库。
- Redis 集群或默认拆成两个实例。
- Kafka/NATS。
- PostgreSQL 读副本或分库。
- Kubernetes 和 GPU 调度平台。

## 5. 上线容量测试

使用 Stub LLM 注入固定 TTFT、分块速度、429、5xx 和断流，不使用真实供应商作为主要压测目标。

### 场景 A：交互式稳定性

```text
20 个并发 Run，持续 30 分钟
每个 Run 3 次模型步骤
TTFT 2 秒，每 100 ms 一个 Chunk
同时保持 100 个 SSE 连接
```

通过标准：

- 控制面 API P95 小于 300 ms。
- Event Loop Lag P95 小于 100 ms。
- 无数据库 Pool Timeout。
- 无泄漏 Task、连接或 Semaphore Lease。
- Run 完成后进程内存回落到稳态范围。

### 场景 B：慢供应商与限流

注入 20% 的 429、10% 的 503 和 10 秒 TTFT，验证 Attempt 上限、Deadline、熔断、回退和 UI 错误。请求数不得超过配置的理论最大 Attempt 数。

### 场景 C：文档突发

同时提交 20 个最大允许大小的文档，验证队列等待、内存限制、交互式 API 延迟和 Job Reconciler。文档处理不得使控制面 API P95 增加超过 30%。

### 场景 D：依赖故障

依次中断 Redis、Worker、单个 API、Egress Proxy 和单个 LLM，验证降级行为与资源释放，禁止出现无限重试和重复工具副作用。
