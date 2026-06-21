# 数据库性能规范

本文是 Hify 使用 PostgreSQL、SQLAlchemy、Alembic 和 pgvector 时的强制数据库规范。AI 创建或修改表、查询、索引和 Migration 时必须逐条执行。

## 1. 建表前必须提交的信息

创建表或新增索引前，必须先明确以下内容，禁止直接从 ORM Model 开始：

```text
Owner module:
Write patterns:
Read query shapes:
Sort and pagination:
Expected rows after 12 months:
Expected writes per second at peak:
Retention period:
Large-table class:
Indexes and the query served by each index:
```

估算行数使用：

```text
12-month rows = active teams
              * records per team per day
              * retention days
              * fan-out per business action
```

例如一次 Run 平均写 20 个 Step、100 个持久化 Event，必须按 120 行而不是 1 个 Run 估算。

没有查询形态和行数估算时，AI 禁止创建二级索引或分区表。

## 2. 通用字段约定

### 2.1 标准业务表模板

团队级业务表默认使用：

```sql
CREATE TABLE agents_agents (
    id uuid PRIMARY KEY,
    team_id uuid NOT NULL,
    name text NOT NULL,
    status varchar(32) NOT NULL,
    version bigint NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamptz NULL,
    CONSTRAINT ck_agents_agents__status
        CHECK (status IN ('draft', 'published', 'archived')),
    CONSTRAINT ck_agents_agents__name_not_blank
        CHECK (length(btrim(name)) > 0)
);
```

规则：

- `id` 使用 PostgreSQL `uuid`，由应用生成 UUIDv7；禁止使用随机 UUIDv4、`serial` 或业务字符串作为主键。
- 所有团队数据必须有 `team_id uuid NOT NULL`。
- 时间统一使用 `timestamptz` 和 UTC，禁止使用无时区 `timestamp`。
- `created_at` 只在插入时设置；`updated_at` 每次实际修改时由应用显式更新。
- `version bigint` 用于乐观锁，从 0 开始；存在并发修改的 Aggregate 必须使用。
- `deleted_at` 只在产品需要恢复、审计或保留引用时添加，禁止所有表默认软删除。
- ID 和时间字段在 API/Contract 中不得使用字符串替代类型。

Python 3.12 统一使用 `uuid6` 包的 `uuid6.uuid7()`，并在 `hify.shared.domain.ids.new_uuid()` 中封装。业务代码只能调用 `new_uuid()`，禁止直接调用 UUID 库。数据库只保存 UUID，不依赖非标准 PostgreSQL UUID 扩展生成 ID。

SQLAlchemy 2 Model 使用以下字段方式：

```python
from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.shared.domain.ids import new_uuid


class AgentModel(Base):
    __tablename__ = "agents_agents"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
```

禁止依赖 SQLAlchemy `onupdate` 自动维护 `updated_at`，因为 Core/Bulk SQL 可能绕过它；Repository 的每个 Update 必须显式设置 `updated_at` 并校验 `version`。

### 2.2 字段类型

| 数据 | 类型 | 规则 |
|---|---|---|
| 名称、Prompt、正文 | `text` | 只有业务长度约束时才用 `varchar(n)` |
| 状态、类型 | `varchar(32)` + `CHECK` | 禁止 PostgreSQL Enum，避免困难迁移 |
| 布尔值 | `boolean NOT NULL` | 必须有明确默认值 |
| Token、计数 | `bigint NOT NULL` | 禁止可能溢出的 `integer` |
| 金额、成本 | `numeric(20, 8)` | 禁止浮点数保存金额 |
| 时间点 | `timestamptz` | 必须为 UTC |
| 短期时长 | `integer` 毫秒 | 字段名带 `_ms` |
| 长期时长 | `bigint` 毫秒 | 字段名带 `_ms` |
| IP 地址 | `inet` | 禁止普通字符串 |
| 动态元数据 | `jsonb` | 只存非核心、低频查询属性 |
| 密钥密文 | `bytea` 或加密 `text` | 必须同时保存 `key_version` |
| Embedding | `vector(n)` | 每个索引表固定维度和距离算法 |

禁止把需要筛选、排序、唯一约束或频繁更新的核心字段藏在 JSONB 中。JSONB 字段必须有大小上限；单行 JSONB 预计超过 64 KiB 时改存 S3 或拆表。

### 2.3 空值和默认值

- 业务必填字段必须 `NOT NULL`，禁止用应用校验代替数据库约束。
- 集合 JSONB 使用 `NOT NULL DEFAULT '{}'::jsonb` 或 `'[]'::jsonb`，不得同时混用 NULL 和空集合语义。
- 字符串缺失使用 NULL，禁止使用空字符串表示未知；需要非空时增加 `CHECK (length(btrim(value)) > 0)`。
- 默认值必须是确定的业务默认；禁止为了绕过 Migration 给必填业务字段设置虚假默认。

### 2.4 外部引用和约束

- 同模块 Aggregate 内部可以使用数据库外键，引用列必须单独或作为组合索引左前缀。
- 跨模块只保存 UUID，禁止跨模块外键和 ORM Relationship。
- `ON DELETE CASCADE` 只允许 Aggregate 内部子表且最大级联量可控；可能删除超过 10,000 行时改为后台批量删除。
- 唯一性必须由数据库 Unique Constraint/Index 保证，禁止“先查询再插入”。
- 团队级唯一性必须包含 `team_id`。

### 2.5 通用字段命名

```text
主键                 id
团队                 team_id
用户                 user_id / created_by / updated_by
外部系统 ID          external_id
幂等键               idempotency_key
状态                 status
乐观锁               version
创建/更新时间        created_at / updated_at
软删除               deleted_at
租约                 lease_owner / lease_expires_at
错误                  error_code / error_message
模型用量             input_tokens / output_tokens
毫秒时长             duration_ms / latency_ms
```

布尔字段使用 `is_`、`has_` 或 `can_` 前缀。数组或集合字段使用复数名。禁止不明确的 `data`、`info`、`value` 和 `type` 字段名。

## 3. 索引设计原则

### 3.1 每个索引必须服务具体查询

新增索引必须同时给出目标 SQL 形态：

```text
Query:
WHERE columns:
ORDER BY:
Expected selectivity:
Expected rows:
Index:
Why existing indexes do not cover it:
```

禁止“这个字段可能会查”作为建索引理由。高写入表原则上不超过 5 个二级索引；超过时必须用 `EXPLAIN (ANALYZE, BUFFERS)` 或生产查询统计证明必要。

### 3.2 组合索引列顺序

组合 B-tree 索引按以下顺序：

```text
租户隔离列
-> 等值过滤列
-> 范围过滤或排序列
-> 唯一稳定排序列
```

团队列表查询的标准模式：

```sql
SELECT id, name, status, created_at
FROM agents_agents
WHERE team_id = :team_id
  AND status = :status
  AND deleted_at IS NULL
  AND (created_at, id) < (:cursor_created_at, :cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT :limit_plus_one;
```

对应索引：

```sql
CREATE INDEX ix_agents_agents__team_status_created_id_active
ON agents_agents (team_id, status, created_at DESC, id DESC)
WHERE deleted_at IS NULL;
```

规则：

- 团队数据索引通常以 `team_id` 开头。
- 等值列在范围列之前。
- 索引排序方向必须匹配主要 `ORDER BY`。
- 所有分页排序最后必须追加唯一 `id`，保证稳定顺序。
- 已有 `(team_id, status, created_at)` 时，禁止再建可被其左前缀覆盖的 `(team_id)`，除非索引尺寸或执行计划证明有必要。

### 3.3 禁止的索引

默认禁止：

- 单独为低基数字段创建索引，例如 `status`、`is_active`、`deleted_at`。
- 为每个外部 UUID 创建与现有组合索引重复的索引。
- 为频繁更新但从不筛选/排序的 `updated_at` 创建索引。
- 同时存在相同列集合、只有名称不同的索引。
- 在写入路径上保留从未使用的实验索引。
- 对 `text` 使用 B-tree 支持 `%keyword%` 查询；B-tree 不能解决前导通配符。

### 3.4 Partial Index

状态或软删除数据只占少数时优先 Partial Index：

```sql
CREATE INDEX pix_jobs_jobs__pending_available
ON jobs_jobs (available_at, id)
WHERE status IN ('pending', 'retry');
```

Soft Delete 唯一名称：

```sql
CREATE UNIQUE INDEX uq_agents_agents__team_name_active
ON agents_agents (team_id, lower(name))
WHERE deleted_at IS NULL;
```

查询条件必须与 Partial Index Predicate 语义一致，否则 PostgreSQL 可能无法使用索引。

### 3.5 Covering Index

只有高频只读查询且 `EXPLAIN` 显示大量 Heap Fetch 时才使用 `INCLUDE`：

```sql
CREATE INDEX ix_usage_records__team_created
ON usage_records (team_id, created_at DESC, id DESC)
INCLUDE (provider, model, input_tokens, output_tokens);
```

禁止 INCLUDE Prompt、正文、JSONB、Embedding 或其他宽字段。每次更新 INCLUDE 字段也需要更新索引。

### 3.6 JSONB、文本搜索和大小写

- JSONB `@>`、`?` 等查询经过验证后使用 GIN；禁止默认给每个 JSONB 加 GIN。
- 前缀查询使用可索引范围或 `text_pattern_ops`。
- 包含搜索使用 `pg_trgm` GIN/GiST，必须限制最小关键词长度。
- 自然语言搜索使用 PostgreSQL Full Text Search，不使用大表 `ILIKE '%keyword%'`。
- 大小写不敏感唯一性使用 `lower(column)` Functional Unique Index；应用查询必须使用相同表达式。

### 3.7 pgvector 索引

每个向量表必须固定：Embedding Model、维度和距离算法。禁止在同一个 ANN 索引中混合不同维度或不同距离语义。

Cosine HNSW 初始模板：

```sql
CREATE INDEX hnsw_knowledge_chunks__embedding_cosine
ON knowledge_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX ix_knowledge_chunks__team_kb_document
ON knowledge_chunks (team_id, knowledge_base_id, document_id);
```

规则：

- 向量索引负责相似度，B-tree 负责 `team_id`、知识库、文档、状态和元数据过滤。
- 默认 Top-K 不超过 20，ANN Candidate 不超过 1,000。
- 查询必须限制 Team 和 Knowledge Base，禁止跨租户全局向量搜索。
- `ef_search` 按召回率测试设置，不在代码中无限提高。
- 更换 Embedding 维度时创建新列/表和新索引，后台重建后切换，禁止原地混写。

### 3.8 索引命名

```text
普通索引       ix_<table>__<purpose>
唯一索引       uq_<table>__<purpose>
Partial        pix_<table>__<purpose>
GIN            gin_<table>__<purpose>
BRIN           brin_<table>__<purpose>
HNSW           hnsw_<table>__<purpose>
Check          ck_<table>__<rule>
Foreign key    fk_<table>__<referenced_table>
```

PostgreSQL 标识符上限为 63 Bytes。名称过长时缩短 Purpose，不使用随机 Hash，保证可读和稳定。

### 3.9 生产索引 Migration

- 新建空表时，索引和表可以在同一事务创建。
- 已有表超过 100,000 行时，普通二级索引必须使用 `CREATE INDEX CONCURRENTLY`。
- `CONCURRENTLY` 必须放在 Alembic `autocommit_block()`，禁止位于普通事务。
- 生产删除索引使用 `DROP INDEX CONCURRENTLY`。
- 创建 Unique Constraint 时先处理重复数据，再并发创建 Unique Index；禁止让 Migration 长时间锁表。
- 每次索引 Migration 必须有 Downgrade 或明确说明不可逆原因。

## 4. 大表预判

### 4.1 分类标准

| 类别 | 12 个月预测 | 设计要求 |
|---|---:|---|
| Small | < 100 万行且 < 5 GiB | 普通表和 B-tree |
| Medium | 100 万-1,000 万行或 5-50 GiB | 严格索引、保留策略、批量操作 |
| Large | > 1,000 万行或 > 50 GiB | 分区评估、归档、专门容量测试 |
| Hot | 峰值持续 > 100 writes/s | 减少索引、批量写入、避免热点行 |

满足任意一项即进入更高类别。数据尺寸必须包含表、TOAST 和所有索引，不只计算 Heap。

### 4.2 Hify 预判表

| 表类型 | 预判 | 一期策略 |
|---|---|---|
| Agent、Provider、Workflow 配置 | Small | 普通表 |
| Conversation Messages | Medium | Keyset、按团队索引、长期保留 |
| Run Steps | Medium | 批量写、按 Run/时间索引 |
| Run Events | Large 候选 | 合并 Chunk、30 天保留、暂不分区 |
| Usage Raw Records | Large 候选 | 90 天保留，按日/月聚合 |
| Audit Records | Large 候选 | 12 个月保留，只追加 |
| Outbox | Hot | Partial Index、处理后 7 天删除 |
| Jobs | Medium/Hot | Pending Partial Index、90 天保留 |
| Knowledge Chunks | Medium/Large | HNSW + 过滤索引、随文档删除 |

### 4.3 一期大表处理

一期必须先通过减少写入和保留策略控制规模：

- Run 流式 Token 按 100-250 ms 或 20-50 Chunk 合并后写入，禁止每 Token 一行。
- Run Events 保留 30 天；最终 Message、Run、Step 和 Usage 聚合长期保留。
- 已处理 Outbox 保留 7 天。
- Job 详细记录保留 90 天，业务结果由所有者表长期保存。
- Usage Raw 保留 90 天，生成日聚合和月聚合。
- 大 Prompt、模型原始响应、文档正文和二进制文件优先存 S3，数据库保存地址、Hash 和必要检索字段。

清理任务每批删除 5,000-10,000 行并提交，批次间短暂 Sleep。禁止单事务删除百万行。

### 4.4 分区触发条件

任意条件持续出现时评估分区：

- 表超过 1,000 万行或总尺寸超过 50 GiB。
- 每月新增超过 100 万行且需要按时间批量清理。
- 单次 Retention 删除超过 100 万行。
- Vacuum、索引维护或删除持续影响在线查询。
- 所有核心查询都天然包含时间范围。

默认使用按 `created_at` 的月度 Range Partition。禁止一期按 `team_id` Hash 分区，因为团队大小不均、跨团队运维和分区数量更复杂。

分区前必须确认：

- 所有查询包含分区裁剪条件。
- Primary/Unique Constraint 包含分区键，或唯一性由应用和其他表重新建模。
- 不依赖指向分区子表的跨模块外键。
- 已定义未来分区自动创建、旧分区归档和删除任务。

### 4.5 BRIN 使用

仅当表按时间物理追加、行数达到千万级且查询主要为大时间范围时，使用 `BRIN(created_at)`。BRIN 不替代最近记录 Keyset 分页需要的 B-tree。

## 5. 分页查询规范

### 5.1 默认使用 Keyset Pagination

所有可能超过 10,000 行的列表 API 必须使用 Keyset/Cursor Pagination。禁止对用户可翻页列表使用深 OFFSET。

标准降序 SQL：

```sql
SELECT id, status, created_at
FROM runs_runs
WHERE team_id = :team_id
  AND status = :status
  AND (created_at, id) < (:cursor_created_at, :cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT :page_size_plus_one;
```

无 Status Filter 时必须构造另一条不含 `status` 条件的固定 SQL，并使用 `(team_id, created_at DESC, id DESC)` 索引。禁止使用 `OR :param IS NULL` 拼成万能查询，因为它可能降低索引使用率。

首页没有 Cursor 时省略 Tuple 条件。请求 `limit + 1` 行判断 `has_more`，返回前移除最后一行。

### 5.2 Cursor 格式

Cursor 是不透明、版本化、签名的 Base64URL：

```json
{
  "v": 1,
  "created_at": "2026-06-21T08:30:00.123456Z",
  "id": "019...",
  "filter_hash": "sha256...",
  "snapshot_at": "2026-06-21T08:31:00Z"
}
```

规则：

- 使用服务端 HMAC 签名，拒绝被修改、版本未知或 Filter Hash 不匹配的 Cursor。
- Cursor 必须包含全部排序列和唯一 Tie-breaker。
- 默认 `page_size=20`，最大 `page_size=100`。
- Cursor 不包含数据库内部页码或 OFFSET。
- 需要稳定快照时，第一页生成 `snapshot_at`，后续增加 `created_at <= snapshot_at`。

### 5.3 排序字段

- 优先使用不可变、非空的 `created_at, id`。
- 使用可变字段如 `updated_at`、`status` 排序时，翻页期间可能出现重复或遗漏；必须接受该语义或使用 Snapshot/只读投影。
- Nullable 排序字段默认禁止用于 Cursor；确有需要时 Cursor 必须包含 NULL Flag 并显式使用 `NULLS FIRST/LAST`。
- 用户自定义排序只能从白名单选择，禁止直接拼接请求字段到 SQL。

### 5.4 JOIN 和一对多

分页必须先确定主表 ID，再 JOIN：

```sql
WITH page AS (
    SELECT id, created_at
    FROM conversations_conversations
    WHERE team_id = :team_id
      AND (created_at, id) < (:created_at, :id)
    ORDER BY created_at DESC, id DESC
    LIMIT :limit_plus_one
)
SELECT p.id, p.created_at, c.title
FROM page p
JOIN conversations_conversations c ON c.id = p.id
ORDER BY p.created_at DESC, p.id DESC;
```

禁止先 JOIN 一对多表再 LIMIT，这会导致主记录数量不稳定和重复。关联计数使用预聚合列、LATERAL 子查询或单独批量查询，不使用 N+1。

### 5.5 COUNT

- 列表 API 默认返回 `has_more`，不返回每次实时 `COUNT(*)`。
- 小表或严格需要时允许精确 COUNT，但必须有匹配过滤索引并独立测量。
- 大表总量使用异步聚合表或缓存统计；后台管理可使用 PostgreSQL Estimate，并明确标记为估算。
- 禁止为了显示页码在每次请求扫描大表。

### 5.6 OFFSET 允许范围

OFFSET 只允许：

- Small 配置表。
- 后台一次性管理界面。
- `OFFSET <= 1,000` 且已有稳定 `ORDER BY`。

超过 1,000 必须改为 Cursor。禁止没有 `ORDER BY` 的 LIMIT/OFFSET。

### 5.7 向量检索不是分页

ANN 检索只返回有限 Top-K，不提供“下一页相似结果”Cursor。需要浏览知识库 Chunk 时使用普通 `created_at/id` 或 `document_id/position/id` Keyset，不复用向量距离翻页。

## 6. 查询和写入规范

### 6.1 禁止 N+1

Repository 返回列表时，关联数据必须通过以下方式之一加载：

- 同模块内受控 JOIN/`selectinload`。
- 一次批量 `WHERE id = ANY(:ids)`。
- 跨模块批量 Contract。
- 本地读模型。

禁止在循环中逐行调用 Repository 或跨模块 Contract。

### 6.2 事务范围

- 事务只包含数据库读写，禁止在事务内调用 LLM、MCP、HTTP、S3 或 Celery。
- 先提交业务事务和 Outbox，再异步执行外部副作用。
- 行锁必须有稳定索引条件，禁止无界 `SELECT ... FOR UPDATE`。
- Job Claim 使用 `FOR UPDATE SKIP LOCKED` 或原子 `UPDATE ... RETURNING`。
- 批量插入使用 SQLAlchemy Bulk/Core 或 PostgreSQL Multi-values，禁止逐行 Commit。

### 6.3 查询列

- 禁止大表 `SELECT *`。
- 列表查询只选择响应需要的窄字段。
- Prompt、正文、JSONB、Embedding 等宽字段只在详情或执行路径读取。
- ORM Relationship 默认不得 Lazy Load；必须显式加载。

## 7. 性能验证

### 7.1 新查询

针对预计超过 100,000 行的表，新查询必须提供：

```sql
EXPLAIN (ANALYZE, BUFFERS, WAL)
<query with representative parameters>;
```

验收要求：

- 返回少量数据时不得出现无理由的全表扫描。
- `actual rows` 与估算相差超过 10 倍时执行 `ANALYZE` 并检查统计信息。
- 分页查询扫描行数不应随页码线性增长。
- 不允许明显 Sort Spill 到磁盘。
- 写查询必须检查 WAL 和受影响索引数量。

生产环境禁止直接对写查询执行 `EXPLAIN ANALYZE`；使用预生产数据或事务内可回滚测试。

### 7.2 必备指标

- Query P50/P95/P99 和调用次数。
- 慢查询及 `pg_stat_statements`。
- 活跃/等待连接和 Pool Wait。
- 锁等待、Deadlock 和长事务。
- 表/索引大小、Bloat、Dead Tuple 和 Vacuum 延迟。
- Index Scan/Seq Scan、未使用索引和重复索引。
- Buffer Cache Hit、磁盘 IOPS 和 Temporary Bytes。
- pgvector 检索延迟、候选数和召回率基准。

### 7.3 告警阈值

```text
数据库 CPU > 70% 持续 10 分钟
连接使用 > 70%
Pool Wait P95 > 50 ms
核心 OLTP Query P95 > 100 ms
Vector Search P95 > 200 ms
锁等待 P95 > 50 ms
长事务 > 30 秒
Deadlock > 0
非预期表 Seq Scan 持续增长
```

## 8. AI 建表检查清单

AI 创建或修改数据库对象时必须依次确认：

1. 表归属哪个模块，表名是否包含模块前缀？
2. 是否列出写入、读取、排序和分页 Query Shape？
3. 是否按 12 个月估算行数、尺寸、峰值写入和保留期？
4. 是否选择 UUIDv7、`timestamptz`、NOT NULL 和正确数值类型？
5. 是否避免把核心查询字段放入 JSONB？
6. 每个索引是否对应明确查询，组合列顺序是否正确？
7. 是否存在重复、左前缀冗余或低基数单列索引？
8. 团队查询和唯一约束是否包含 `team_id`？
9. 分页是否使用稳定 Keyset 和唯一 Tie-breaker？
10. 大表是否定义批量写、Retention、清理和分区触发条件？
11. 是否避免跨模块 FK、Relationship、JOIN 和共享 Session？
12. Migration 对大表是否使用 Concurrent Index 和兼容发布顺序？
13. 是否补充 Repository 集成测试和代表性 EXPLAIN？
14. 是否运行 Migration Upgrade/Downgrade 和数据库测试？

任意一项无法回答时，AI 必须先补充设计，禁止以“后续优化”代替索引、分页和数据量设计。
