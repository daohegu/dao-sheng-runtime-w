# V1 Architecture — Component Model

> STEP 12 产出（2026-09-13）。词汇 = `/codebase-design`：module / interface（调用方必须知道的一切：签名 + invariants + 顺序约束 + 错误模式 + 配置 + 性能特征）/ implementation / **depth = interface 处的 leverage**（调用方每学一单位 interface 能行使多少行为）/ seam（Interface 所在的位置）/ adapter（在 seam 上满足 Interface 的具体物）/ leverage / locality；deletion test；the interface is the test surface；one adapter = hypothetical seam，two = real。
>
> 本文档是 **Core 容器内**的模块级设计。V0 代码是深度判定的形态参考（Implementation，最低权威，规则 1）：形态逐条过 deletion test，不默认继承（规则 12）。

---

## 1. 模块总览

| Module | Interface（调用方必须知道） | 深度判定 | seam |
|---|---|---|---|
| **Individual**（顶层聚合） | `act(...)` 单一回合入口 + `persist()` | **深**：依赖编排、回合机制（R-01 单一入口：V0 observe/act/complete_turn 三处 → 一处）、digest 管线调度、投影拼装、reflection 调度、faculty 更新全部隐藏——调用方只知道"一个回合" | 顶层无 seam（本身 = 整个个体的聚合）；测试经其 Interface（the interface is the test surface） |
| **Identity** | 只读投影：个体性载体（名字 / 自我称谓 / 声音等）+ protected_fields 约束（K-11 形态：无 model/worker/host 字段） | **深（immutable）**：加载、校验、保护约束隐藏；调用方只读 | 非 seam（不可替换） |
| **Continuity** | 读 + 追加（ADR 0004：Core 内单一载体，append-only） | **深**：载体细节隐藏；调用方只知道"读个体连续性 / 追加一条连续性记录"；**不得覆写 / 删除**（第 6 条 / K-11） | 非 seam |
| **Memory**（Ontology + Provider seam） | **6 方法**（§3，R-05 答案）：`remember / recall / get / correct_memory / register_reference / resolve_reference` + 参数化查询 | **深**：recall 排序判据、correction 语义（INV-8）、reference 解析、三维语义层读写全部隐藏；调用方不知道 SQLite / FTS5 / 任何存储细节 | **Memory Provider seam**（hypothetical，单 adapter = embedded SQLite，ADR 0001） |
| **Growth**（经历管线） | Experience 候选输入 + 管线内部阶段（digest / extract / reflect）+ 反思结果输出 | **深**：阶段编排、提取判据、验证闸门（INV-11 方向）隐藏；**一切 Memory 操作经 Memory Interface**（R-08 A-1：verify_insight 不直写 MemoryItem）；无跨类私有调用（R-08 A-5/A-6） | 非 seam（个体内部）；Insight 记录在 Memory（ADR 0006） |
| **Capability System** | `propose / advance / retire / execute`（Manager）+ 执行前闸门 | **深**：状态机（ADR 0003）、验证（K-05 Verifier）、active 完全隔离（K-04）、目录形态（K-06）全部隐藏；调用方不知道四目录与路径（V0 反例 A-7：runner 直接构造 `root/"active"/name`） | 非 seam（Core 内 Domain 概念）；四目录 = 状态机的一个合法 adapter 形态（K-06） |
| **Host 集成 adapter 层**（ADR 0002） | `open_session / import_session / sync`（中性概念：回合 / 会话 / 经验回流）+ host 声明（composition root） | **深**：Hermes 内部 schema、`profiles/` 路径、Desktop subprocess、身份投影过滤（R-12）全部隐藏；**唯一允许知道 "Hermes" 的层** | **host 集成 seam**（hypothetical，单 adapter） |
| **Model 调用 adapter** | 认知模型调用（chat / complete 形态） | 薄但够深：模型 HTTP 细节、默认模型值（M-1…M-3）全部隐藏；默认值移 composition root（R-09："accept dependencies, don't create them"） | **model 调用 seam**（hypothetical，单 adapter） |
| **Research / world 观察** | `research → ResearchResult(sources, confidence)` / `observe → FileObservation` | **深**：provider 切换、来源标注、观察 ≠ 判断纪律（K-08）隐藏；**ResearchResult 必须携带 sources + confidence**（K-08 invariant） | **research seam**（hypothetical）/ **world seam**（V0 两 adapter，接近 real，K-07） |
| **Composition root** | —（无调用方的装配点） | host 声明、依赖装配（R-09）、"道"文本运行时单一来源注入（ADR 0005）、默认值（模型 / endpoint，L4） | — |

## 2. Agent seam（V0 唯一 real seam，KEEP K-01）

- V0 四核三接口骨架 + Agent seam：v0.1 = development.py + subprocess.py（生产）+ FakeAgent（测试）；v0.1.1 增 hermes / pi / world_observer——**历史合计 5 生产 adapter = real seam**（K-01）。
- V1 保留 Agent seam 的位置与 Interface 形态（调用方只知道"agent 调用"中性概念）。**god object（1171 行聚合）不在 KEEP 内**（K-01 明示排除）——V1 的 Individual 模块必须深、且经其自身 Interface 可测试。
- V0 test surface 被删（`v0-drift.md` §2.7）是教训；v0.1 tests = KEEP 证明（K-10，证明非逐字代码）：V1 的测试全部经 Interface，不测实现内部细节。

## 3. Memory Interface（R-05 答案——方法集与深度）

V0 两形态：`protocol.py` 5 方法（滞后，R-05 已证其浅：调用方必须知道 implementation）vs `sqlite.py` 11 方法（实现全量，另含 `recent_by_origin` / `find_by_reference` / `resolve_reference` / `register_reference` / `get_corrections` / `correct_memory`）。V1 Interface = **6 方法 + 参数化查询**——不是两者的合并，是 Domain 契约的表达：

| 方法 | 契约（调用方必须知道） | 实现隐藏 |
|---|---|---|
| `remember(...)` | 写入一条记忆（三维语义层字段显式：origin / status / confidence）；返回 reference | 表结构、FTS 索引、id 生成 |
| `recall(query: RecallQuery) → [Memory]` | `RecallQuery` = 结构化过滤（origin / status / confidence）+ 可选关键词 / 子串。**CJK ≥3 字符走 FTS5 trigram、<3 字符走 LIKE——这是实现细节，调用方不需要知道通道**（ADR 0001 决定 3）；**排序判据隐藏于实现**（V0 分层排序思想可参考，Implementation 参考非权威） | trigram / LIKE 通道选择、排序、≤32 项上限形态（V0 有界 LIKE，E6 expression depth） |
| `get(reference) → Memory` | 按 reference 取单条 | — |
| `correct_memory(target, correction)` | **追加修正记录；原记忆内容与身份不变**（INV-8）；返回 correction reference | correction 存储形态、引用链 |
| `register_reference(...)` | 显式引用注册（修正引用键属 Ontology，Q2 追认） | 存储形态 |
| `resolve_reference(ref) → [Memory]` | 引用解析（显式 reference 优先 = V0 行为形态） | 解析算法 |

**为什么是 6，不是 5 或 11**：

- V0 protocol 5 方法**浅**（R-05）：缺口靠 duck-check / getattr 兜底（`growth/pipeline.py` `correct_memory` TypeError 兜底；`life/runtime.py` `_append_memory_block` `reference_keys`——V1 全部消灭，调用方不再需要知道实现有没有某方法）。
- V0 sqlite 11 方法**不是 Interface，是实现的方法表**：`recent_by_origin` = `recall` 的 origin 过滤形态；`find_by_reference` = `resolve_reference` 的派生读；`get_corrections` = `recall` / `resolve_reference` 的派生读。派生读并入查询参数 = depth（leverage）：调用方学 6 个契约，获得完整 Ontology 读写。
- **深度判定**：每个方法携带 invariant（INV-8 修正不重写 / INV-3 Ontology 分离 / 三维语义层字段语义 / 显式 reference 优先）——**the interface is the test surface**：V1 的 Memory 测试经这 6 个方法验证 Ontology 契约（三维过滤正确性、correction 追加语义、reference 链），不测 SQLite 细节。
- **seam 状态**：单 adapter（embedded SQLite）= **hypothetical seam**（ADR 0001；research §7 触发 5）。第二个 Provider 实现出现时此 seam 变 real，6 方法 Interface 即其契约——**Interface 不随 adapter 变化**（Ontology 与存储分离是 seam 的语义要求：Ontology 必须能完整映射到任一 Provider）。

## 4. seam 清单与状态

| seam | 位置 | adapter（当前） | 状态 |
|---|---|---|---|
| **Agent seam** | Individual 的认知调用 | V0 历史合计 5 生产（development / subprocess / hermes / pi / world_observer）+ 1 测试（FakeAgent）（K-01） | **real**（V0 已证实，V1 保留） |
| **world seam** | world 观察 | V0 两 adapter（K-07） | **real**（接近 real 判据，V1 保留） |
| **Memory Provider seam** | Memory 模块 | embedded SQLite（ADR 0001） | hypothetical（单 adapter，保留不过度设计） |
| **host 集成 seam** | host 集成层（ADR 0002） | Hermes host adapter | hypothetical（单 adapter） |
| **model 调用 seam** | model adapter | 1（V0 部署形态 Ollama /v1；部署值 = L4，UNKNOWN U-5） | hypothetical（单 adapter） |
| **research seam** | Research 模块 | 1（V0 默认硬建 DuckDuckGo——V1 移 composition root，R-09 / M-6 方向） | hypothetical（单 adapter） |

## 5. 不得成为模块的东西（deletion test 结论）

- **D-06 五个薄 pass-through**（`remember_user_preference` / `remember_user_habit` / `research_once` / `propose_capability` / `recall_experience_packages`）：删除后复杂度消失 = pass-through（`delete.md`）——V1 内联到调用方，不留壳。
- **ResearchService 47 行壳**（D-04）：包 KEEP（研究观察 ≠ 判断的纪律，K-08），壳不 KEEP。
- **god object 聚合**（1171 行）：不是深度模块，是聚合体（K-01 排除）——V1 的 Individual 以 Interface 契约为深，不以行数为深（depth ≠ 行比）。
- **host 身份宣称文本**（M-04：H-6 / H-7）：不是模块也不是数据——属 composition root 声明，且**不得**进入 Core 或投影文本（R-12：进投影即回流污染）。
- **V0 备份文件 / egg-info**（D-01 / D-02）：不属模块范畴（归档移出 / 删除，D-01 不得直接 rm——U-2 未读，唯一演化历史残留，规则 7 精神）。
