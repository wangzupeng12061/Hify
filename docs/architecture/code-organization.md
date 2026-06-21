# Hify 代码组织规范

本文是 Hify 后端代码的强制架构规范。文中的“必须”“禁止”和“只能”均为可执行约束，AI 和人工开发者不得自行放宽。

## 1. 总体原则

Hify 使用领域模块化单体。所有后端模块运行在同一代码库中，但每个模块拥有独立的领域模型、应用用例、持久化实现和公开契约。

必须遵守以下规则：

1. 业务代码按领域模块组织，禁止按全局 `controllers/services/models` 组织。
2. 模块内部固定分为 `api`、`application`、`domain`、`infrastructure`、`contracts` 五层。
3. 模块外部只能导入该模块的 `contracts`，禁止导入其他内部目录。
4. `domain` 不得依赖 Web 框架、ORM、队列、LangGraph、模型 SDK 或其他业务模块。
5. FastAPI、SQLAlchemy、Celery、Redis、LangGraph、模型 SDK 和 MCP SDK 都是边界实现，不得进入领域模型。
6. 每个数据对象只有一个归属模块。其他模块只能保存其 ID 或本地快照，不能直接修改该对象。
7. 一期允许多个部署进程共享代码，不允许为了“以后可能拆服务”提前创建网络微服务。

## 2. 仓库结构

后端必须使用以下结构：

```text
backend/
├── pyproject.toml
├── alembic.ini
├── migrations/
│   └── versions/
├── src/hify/
│   ├── bootstrap/
│   │   ├── api.py
│   │   ├── celery.py
│   │   ├── container.py
│   │   ├── settings.py
│   │   └── orchestrators/
│   ├── modules/
│   │   ├── identity/
│   │   ├── providers/
│   │   ├── agents/
│   │   ├── conversations/
│   │   ├── runs/
│   │   ├── knowledge/
│   │   ├── workflows/
│   │   ├── tools/
│   │   ├── mcp/
│   │   └── usage/
│   └── shared/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
├── scripts/
│   └── check_architecture.py
└── tests/
    ├── architecture/
    ├── integration/
    └── e2e/
```

`bootstrap` 是唯一允许同时导入多个模块实现层的位置。它只负责组装依赖、注册路由、启动进程和跨模块用例编排，不包含业务规则。

## 3. 模块所有权

| 模块 | 唯一拥有的数据和行为 |
|---|---|
| `identity` | 用户、团队、成员关系、角色、权限 |
| `providers` | 模型提供商、模型定义、加密凭证、模型调用适配 |
| `agents` | Agent 配置、Prompt、工具绑定、知识库绑定、发布版本 |
| `conversations` | 会话、消息、消息反馈 |
| `runs` | Agent 执行、步骤、流式事件、取消、运行状态 |
| `knowledge` | 知识库、文档、分块、Embedding、检索 |
| `workflows` | 工作流定义、节点、边、版本、静态校验 |
| `tools` | 内置工具和 HTTP 工具的定义、授权、调用 |
| `mcp` | MCP Server 连接、能力发现、MCP 工具适配 |
| `usage` | Token 用量、额度、成本、审计记录 |

归属判断规则：创建、修改和删除某类数据的模块即为所有者。非所有者禁止直接写入该模块的数据表。

## 4. 标准模块模板

每个模块必须从下面的结构开始：

```text
modules/<module>/
├── __init__.py
├── api/
│   ├── router.py
│   ├── schemas.py
│   └── dependencies.py
├── application/
│   ├── commands/
│   ├── queries/
│   ├── dto.py
│   ├── ports.py
│   └── event_handlers.py
├── domain/
│   ├── entities.py
│   ├── value_objects.py
│   ├── services.py
│   ├── events.py
│   ├── errors.py
│   └── repositories.py
├── infrastructure/
│   ├── database/
│   │   ├── models.py
│   │   └── repositories.py
│   ├── adapters/
│   └── tasks.py
├── contracts/
│   ├── services.py
│   ├── dto.py
│   └── events.py
└── wiring.py
```

空目录不必提前创建。首次出现对应职责时，必须放入上述固定位置，禁止增加 `utils.py`、`helpers.py` 或全局 `services.py` 作为逃生目录。

## 5. 各层职责

### 5.1 Domain

允许：

- Entity、Aggregate、Value Object 和领域服务。
- 纯业务规则、状态转换和不变量校验。
- 领域事件、领域异常和 Repository Protocol。
- Python 标准库以及 `hify.shared.domain`。

禁止：

- 导入 FastAPI、Pydantic、SQLAlchemy、Celery、Redis、LangGraph、LangChain 或供应商 SDK。
- 导入任何其他业务模块，包括其他模块的 `contracts`。
- 执行 SQL、HTTP、模型调用、队列投递或读取环境变量。
- 返回 ORM Model、Pydantic API Schema 或第三方 SDK 对象。

实体方法必须表达业务动作，例如 `agent.publish()`，禁止由应用层直接修改 `agent.status`。

### 5.2 Application

允许：

- 实现一个明确的 Command 或 Query 用例。
- 加载 Aggregate、调用领域行为、提交 Unit of Work。
- 通过本模块 `ports.py` 调用数据库以外的外部能力。
- 通过其他模块的 `contracts` 进行跨模块调用。
- 将领域对象转换为 Application DTO。

禁止：

- 导入 FastAPI Router、HTTP Request/Response 或 API Schema。
- 导入 SQLAlchemy Model、Session 或执行原始 SQL。
- 直接调用 OpenAI、LangGraph、MCP、Redis、S3 等 SDK。
- 包含 HTML、HTTP 状态码或前端展示逻辑。

每个写用例必须使用独立文件：

```text
application/commands/create_agent.py
application/commands/publish_agent.py
application/queries/get_agent.py
```

文件中使用 `<Verb><Noun>Command`、`<Verb><Noun>Handler` 或 `<Verb><Noun>Query`、`<Verb><Noun>Handler` 命名。一个文件只能定义一个公开用例。

### 5.3 API

允许：

- 定义 FastAPI Router、Pydantic 请求和响应 Schema。
- 解析 HTTP 输入、获取当前用户、调用 Application Handler。
- 将已知应用异常映射为 HTTP 状态码。
- 将运行事件编码为 SSE。

禁止：

- 访问数据库或 Redis。
- 包含业务判断、额度计算、权限规则或事务控制。
- 调用其他模块的 Router、Repository 或 Infrastructure。
- 将 SQLAlchemy Model 直接序列化为响应。

Router 函数只执行四步：解析输入、构造 Command/Query、调用 Handler、转换响应。

### 5.4 Infrastructure

允许：

- 实现 Repository、Unit of Work 和 Application Port。
- 定义 SQLAlchemy Model、数据库查询和 Alembic 迁移。
- 封装模型供应商、pgvector、Redis、S3、MCP、LangGraph 和 Celery。
- 将第三方异常转换为 Hify 定义的应用异常。

禁止：

- 定义业务规则。
- 被其他模块直接导入。
- 从第三方 SDK 对象直接返回到 API 或 Domain。
- 绕过 Aggregate 直接实现业务状态转换。

`wiring.py` 负责创建该模块的 Repository、Adapter 和 Handler。除 `bootstrap` 外，其他位置禁止导入 `wiring.py`。

### 5.5 Contracts

`contracts` 是模块唯一公开入口，只允许包含：

- 跨模块服务的 `Protocol`。
- 不可变输入输出 DTO。
- 已版本化的集成事件。
- 对外稳定的错误类型。

禁止：

- 导出 Entity、ORM Model、Repository、Handler 或第三方类型。
- 导入本模块的 `api`、`application`、`domain`、`infrastructure`。
- 在 DTO 中使用数据库 Session、Lazy Relationship 或 LangGraph State。

契约 DTO 使用 `@dataclass(frozen=True, slots=True)`，不得复用 API Pydantic Schema。

## 6. 层间依赖矩阵

`允许` 表示可以直接 import，`禁止` 表示架构测试必须报错。

| 来源 | shared | 本模块 contracts | 本模块 domain | 本模块 application | 本模块 infrastructure | 本模块 api | 其他模块 contracts | 其他模块内部 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `domain` | 允许 | 禁止 | 允许 | 禁止 | 禁止 | 禁止 | 禁止 | 禁止 |
| `application` | 允许 | 允许 | 允许 | 允许 | 禁止 | 禁止 | 允许 | 禁止 |
| `api` | 允许 | 允许 | 允许异常类型 | 允许 | 禁止 | 允许 | 禁止 | 禁止 |
| `infrastructure` | 允许 | 允许 | 允许 | 允许端口 | 允许 | 禁止 | 允许 | 禁止 |
| `contracts` | 标准库优先 | 允许 | 禁止 | 禁止 | 禁止 | 禁止 | 禁止 | 禁止 |
| `wiring` | 允许 | 允许 | 允许 | 允许 | 允许 | 允许 | 允许 | 禁止 |

## 7. 跨模块调用规则

### 7.1 同步读取

需要立即返回结果时，调用方 Application 只能依赖被调用模块在 `contracts/services.py` 中定义的 Protocol。

```python
# modules/providers/contracts/services.py
class ModelCatalog(Protocol):
    async def get_model(self, model_id: UUID) -> ModelInfo: ...

# modules/agents/application/commands/create_agent.py
class CreateAgentHandler:
    def __init__(self, model_catalog: ModelCatalog) -> None:
        self._model_catalog = model_catalog
```

具体实现由 `bootstrap/container.py` 注入。调用方禁止实例化被调用模块的 Handler 或 Repository。

### 7.2 同步写入

默认禁止一个模块在自身事务中同步修改另一个模块。

确实需要同步写入时必须满足全部条件：

1. 被调用模块公开幂等 Command Contract。
2. 调用发生在调用方事务提交之后。
3. 请求携带全局唯一 `idempotency_key`。
4. 失败可以重试或由补偿动作恢复。

需要两个模块在同一数据库事务内写入，说明数据归属划分错误；必须重新确定 Aggregate 所有者，禁止共享 SQLAlchemy Session 解决。

### 7.3 异步事件

无需立即返回的跨模块副作用必须使用集成事件。事件定义在发布模块的 `contracts/events.py`：

```python
@dataclass(frozen=True, slots=True)
class AgentPublishedV1:
    event_id: UUID
    occurred_at: datetime
    agent_id: UUID
    version: int
    team_id: UUID
```

规则：

- 事件名必须带版本后缀，例如 `AgentPublishedV1`。
- 事件只能包含标量、枚举、时间、ID 和可序列化集合。
- 禁止包含 Entity、ORM Model 或隐式数据库引用。
- 发布必须与本地写事务使用 Transactional Outbox。
- 消费者必须按 `event_id` 幂等处理。
- 修改字段语义必须新增 `V2`，禁止原地破坏兼容性。

### 7.4 跨模块流程

同时协调三个及以上模块的用户用例放在 `bootstrap/orchestrators/<use_case>.py`。Orchestrator 只能调用模块 Contracts，禁止访问 Repository、ORM Model 或领域对象。

Orchestrator 不提供跨模块原子事务。每一步必须幂等，并明确失败后的重试或补偿行为。

## 8. 数据库边界

1. 每张表由一个模块拥有，表名使用模块前缀，例如 `agents_agents`、`runs_steps`。
2. Repository 只能查询和写入本模块拥有的表。
3. 禁止跨模块 ORM Relationship。
4. 跨模块引用只保存 UUID，例如 `model_id`，不得加载其他模块 ORM 对象。
5. 禁止跨模块数据库外键。存在性和权限通过 Contract 校验。
6. 禁止跨模块 SQL JOIN。列表展示需要组合数据时，由 Query Handler 批量调用 Contract，或维护事件驱动的本地读模型。
7. Migration 文件名必须以模块名开头，例如 `agents_20260621_add_version.py`。

## 9. AI Runtime 特别规则

### 9.1 Runs 是执行编排所有者

`runs` 负责一次执行的生命周期。它可以通过 Contracts 读取 Agent 快照、模型配置、检索结果和工具定义，但禁止访问这些模块的数据库表。

交互式执行禁止作为普通 Celery Task 实现。FastAPI 调用 `RunExecutor` 并消费统一 `RunEvent`；Celery 只处理文档解析、Embedding、清理和统计等后台任务。

### 9.2 LangGraph 隔离

LangGraph 只能出现在：

```text
modules/runs/infrastructure/adapters/langgraph/
```

工作流模块保存 Hify 自己的版本化 JSON Definition。`runs` 将 Definition 编译为 LangGraph，禁止把 LangGraph State、Checkpoint 或 Node 类型作为公开契约或数据库主模型。

### 9.3 模型提供商隔离

供应商 SDK 只能出现在：

```text
modules/providers/infrastructure/adapters/<provider>/
```

统一输出 Hify 定义的文本片段、工具调用、用量和错误。Agent 和 Run 代码禁止直接导入 OpenAI、Anthropic 等 SDK。

### 9.4 MCP 隔离

MCP SDK 只能出现在 `modules/mcp/infrastructure`。`tools` 和 `runs` 通过 `McpToolExecutor` Contract 调用，不得持有 MCP Session 或 SDK 类型。

### 9.5 RAG 隔离

pgvector 查询只能出现在 `knowledge/infrastructure`。其他模块通过 `KnowledgeRetriever` Contract 获取不可变的 `RetrievedChunk` DTO。

## 10. Shared 使用规则

`shared` 只能包含真正无业务含义的基础设施：

- ID、时间、分页、基础 Domain Event。
- Unit of Work 和 Event Bus 抽象。
- 数据库 Session 工厂、日志、Tracing 和加密原语。

禁止放入：

- `AgentUtils`、`KnowledgeHelper` 等业务代码。
- 被两个模块使用但实际属于其中一个模块的 DTO。
- 通用 Repository 基类中的业务查询。

一个类型进入 `shared` 前必须至少被三个模块使用，并且名称不包含任何模块业务术语；否则保留在所有者模块。

## 11. 测试要求

每个用例必须对应以下测试：

| 层 | 测试类型 | 外部依赖 |
|---|---|---|
| Domain | 单元测试 | 全部禁止 |
| Application | 单元测试 | 使用 Fake Contract、Fake Repository |
| Infrastructure | 集成测试 | 使用真实 PostgreSQL/Redis 或官方测试容器 |
| API | 契约测试 | 替换 Application Handler |
| 跨模块 | 集成测试 | 只通过 Contracts 调用 |

架构测试必须扫描 AST 并拒绝：

1. 跨模块导入非 `contracts` 路径。
2. Domain 导入框架或其他业务模块。
3. API 导入 Infrastructure。
4. Application 导入 ORM、FastAPI 或供应商 SDK。
5. LangGraph、模型 SDK、MCP SDK、pgvector 出现在规定目录之外。

CI 必须执行：

```bash
uv run python scripts/check_architecture.py
uv run pytest tests/architecture
uv run pytest
```

## 12. AI 修改代码检查清单

AI 在创建或修改代码前必须逐项判断：

1. 该数据和行为的唯一所有者模块是什么？
2. 代码属于 API、Application、Domain、Infrastructure 还是 Contracts？
3. 是否导入了其他模块？如果是，路径是否严格止于 `contracts`？
4. 是否把框架或第三方 SDK 类型泄漏到了 Domain、Contracts 或 API 响应？
5. 是否直接查询或写入了其他模块的数据表？
6. 跨模块副作用是否应该改成 Outbox 事件？
7. 新的公开事件是否带版本并支持幂等？
8. 新用例是否使用独立 Command/Query 文件？
9. 是否补充了对应层级的测试？
10. 架构检查和完整测试是否通过？

任意一项不满足时，AI 必须先调整设计，不能通过新增 `utils.py`、共享 Session、循环导入、运行时 import 或忽略类型检查绕过规则。
