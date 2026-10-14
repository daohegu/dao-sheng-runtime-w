# V1 Spec — Memory 与 Memory Provider（spec-memory）

> **STEP 13 产出（2026-09-13）**。固化对象：Memory Ontology（语义）、Memory Interface（6 方法契约）、Memory Provider 要求、修正语义、Insight 归位。
>
> 源（随本副本发布的公开源文档，可公开核验，冲突时规格服从）：`docs/domain/` Memory 条目（双轨 / 三维语义层 / 修正引用键——`domain-model.md` §2.3、`ubiquitous-language.md` §2）、ADR 0001 / 0006 / 0007、`docs/research/memory-architecture.md`、`docs/architecture/component-model.md` §3、`docs/domain/bounded-contexts.md` §4 / §6 #1、`docs/domain/domain-invariants.md` INV-3 / INV-8 / INV-10（及 §1.1 #1、§3）、`docs/architecture/container-model.md` §5、`docs/constitution/principles.md` 第 4 条 L3。
>
> 私有历史来源（历史证据标签，原始登记册与原文不随本副本发布，不构成公开用户必须服从的权威依据）：`docs/audit/` H-4 / R-05 / R-10；`RECONSTRUCTION.md` Q2（Q\* = 用户 2026-09-13 追认问答，同 `principles.md` 附录口径）/ U-2（U-\* → `RECONSTRUCTION.md` Open Questions，同 `domain-invariants.md` §3 口径）；A-1（私有历史索引，原始登记册不随本副本发布，同 `domain-model.md` 编号说明口径）；`docs/origin/` B1-E4；`CLAUDE.md` 规则 5 / 7 / 9。
>
> 编号说明：上述私有历史编号的语义以本文件及其他公开正文行内自明，并可在公开文档中核验（同 `docs/constitution/invariants.md` 编号说明与 §3、`domain-model.md` / `ubiquitous-language.md` 编号说明口径）：H-4（host 名进 provenance 枚举 = Validated Evidence；中性化方向）——`bounded-contexts.md` §4 / §6 #1、`ubiquitous-language.md` Memory 条目、`domain-model.md` §2.3、ADR 0007 约束来源 / 决定 2 / Consequences；Q2（三维语义层 + 修正引用键 = USER_RATIFIED 追认；"不要为了完整而编造"）——`ubiquitous-language.md` Memory 条目、`domain-model.md` §2.3、`bounded-contexts.md` §4、`domain-invariants.md` §1.1 #1 / §3、ADR 0001 约束来源；R-05（V0 5 方法 Protocol vs 11 方法 SQLite，seam 表达不完整 → 6 方法 Domain 契约）——`component-model.md` §3、`bounded-contexts.md` §4、`research/memory-architecture.md` §3.2；A-1（growth 直接构造 MemoryItem 写 memory = 违规形态；修复方向）——ADR 0006 约束来源 / 决定 2、`component-model.md` §1 Growth 行；B1-E4（双轨 / 管线，ORIGIN）——`domain-model.md` §2.3、`ubiquitous-language.md` Memory 条目、`domain-invariants.md` INV-6 / §1.1 #1；规则 5 / 7 / 9（Provider 不得定义 Ontology / 历史经历记录不得重写 / 引入须 Research Evidence）——`domain-invariants.md` INV-3 / INV-8、`bounded-contexts.md` §4、`research/memory-architecture.md` 头部 / §1；R-10（分支 1：H-4 推断行可删除；分支 2：迁移逻辑归迁移工具）——ADR 0007 约束来源 / 决定 2 / Consequences、`bounded-contexts.md` §5、`domain-invariants.md` §3；U-2（V0 数据文件不得直接 rm）——ADR 0007 Consequences。
>
> 与上述公开源文档冲突时以公开源文档为准（`spec-index.md` §1 口径，限随本副本实际发布的文档）；私有历史编号不作为公开读者必须服从的权威依据。公开文档之间的真实冲突不由本规格裁定：标记 REVIEW。REVIEW（已解决，2026-10-14）：`spec-index.md` §1 口径注记原先将本文件列入「头部源行仍将 `docs/audit/` 列为直接源」的六个规格文件；本文件已按该口径处理（公开源文档与私有历史来源分列），索引已于 2026-10-14 同步更新——`spec-index.md` §1 现将本文件的公开源文档与私有历史索引分列，该遗留注记已按该口径移除，本项关闭。

## §1 Memory Ontology（属个体，不属 Provider）

- **双轨**（B1-E4，ORIGIN）：Experience（经历）与 Memory（记忆）是两条轨道；经历经成长管线（`spec-growth.md`）进入记忆。
- **三维语义层**（Q2 追认，Domain 概念）：每条记忆显式携带
  | 维度 | 取值 |
  |---|---|
  | `memory_origin` | `canonical` / `derived` / `external` / `echo` |
  | `memory_status` | `observed` / `reported` / `verified` |
  | `memory_confidence` | `confirmed` / `supported` / `uncertain` |
- **修正引用键**（Q2 追认）：记忆可携带指向 correction 记录的引用键（`register_reference` / `resolve_reference` 的语义基础，§2）。
- **provenance 中性化**（H-4）：来源枚举值**不得包含 host 名**——"Hermes" 等 host 名字不进 Core 枚举（个体级 deletion test，`spec-adapters.md` §4）。V0 的 `provenance=="hermes_desktop"` 向后兼容推断行（H-4）在"不迁移默认"下可删除（ADR 0007 Consequences，R-10 分支 1）；若将来迁移，该逻辑归一次性迁移工具（ADR 0007 决定 2）。
- **Ontology 与存储分离**（ADR 0001 决定 4；INV-3）：Ontology 属个体（语义 Owner = 个体），schema 属 Provider（实现 Owner = 部署层）；**Ontology 必须能完整映射到任一 Provider**——Provider 不得定义 Ontology（规则 5）。
- **消化 / 遗忘机制 = UNKNOWN**（`domain-invariants.md` §3；B1-E4 只说"遗忘是结构性组成"，Q2"不要为了完整而编造"）——本规格不定义遗忘机制。

## §2 Memory Interface — 6 方法契约

源：`component-model.md` §3（R-05 答案）。Interface = 调用方必须知道的一切（方法、不变量、约束）。

| 方法 | 契约 |
|---|---|
| `remember` | 写入一条记忆。三维语义层字段（origin / status / confidence）**显式传入**。返回 reference。 |
| `recall(query: RecallQuery) → [Memory]` | `RecallQuery` = 结构化过滤（三维语义层维度）+ 可选关键词 / 子串。排序判据**隐藏**在 Interface 内。结果上限 ≤32 项（形态）。 |
| `get(reference) → Memory` | 按 reference 精确取一条。 |
| `correct_memory(target, correction)` | **追加**修正记录；原记忆的内容与身份**不变**（INV-8：修正的是"认识"，不是"发生过什么"）。返回 correction 的 reference。 |
| `register_reference(...)` | 显式引用注册——修正引用键属 Ontology（Q2 追认），引用关系显式建立，不靠隐式匹配。 |
| `resolve_reference(ref) → [Memory]` | 按显式 reference 解析相关记忆；**显式 reference 优先**（V0 行为形态保留）。 |

**为什么是 6**：不是 V0 `protocol.py` 5 方法（浅，R-05）与 `sqlite.py` 11 方法（实现方法表）的合并，是 **Domain 契约的表达**；派生读折叠进查询参数 = depth——`recent_by_origin` = `recall` 的 origin 过滤形态；`find_by_reference` / `get_corrections` = 派生读，不单列方法（`component-model.md` §3）。

**检索实现细节**（ADR 0001 决定 3；属 Provider 实现，不进 Ontology）：中文 ≥3 字符查询走 FTS5 trigram，<3 字符走 LIKE（unicode61 tokenizer 不适用中文，research E4）；向量检索**延期**——引入须独立 Research Evidence（规则 9）。

## §3 Memory Provider 要求

源：ADR 0001 + `docs/research/memory-architecture.md`（Confidence MEDIUM，网络不可达）。

1. **形态**：单文件嵌入式 SQLite（WAL 模式）；Provider = **embedded**（进程内 adapter，非独立容器——`container-model.md` §5 不采用独立 Memory server）。
2. **recall 能力**：结构化过滤（三维语义层）+ 全文检索（FTS5 trigram，最小查询长度 3）。
3. **Provider 选择须 Research Evidence**（规则 9）；当前证据 = `docs/research/memory-architecture.md`（本地验证 E1–E7；官方来源不可达，Confidence MEDIUM）。
4. **Re-evaluation Trigger（5 条）**：网络恢复（官方证据补验）/ 需要中文 2 字符或语义召回 / 多进程多 host 并发写 / 记忆规模 >10^6 / 出现第二个真实 Provider——任一触发即复审 ADR 0001（`research/memory-architecture.md` §7）。
5. **数据迁移**：V0 SQLite 记忆默认**不迁移**（ADR 0007）；V0 数据文件原地保留（不得直接 rm，U-2 精神）。

## §4 修正语义（INV-8）

- Correction = **追加记录 + 引用键**，不重写原记录（规则 7 / INV-8）。
- 历史不重写：修正的对象是"认识"（Understanding / Insight / 记忆记录），不是"发生过什么"（`principles.md` 第 4 条 L3）。
- V0 浅证据形态（`growth/pipeline.py` 的 `correct_memory` TypeError 兜底、`life/runtime.py` `_append_memory_block` 的 `reference_keys` 散落）在 V1 **全部消灭**——修正只经 §2 `correct_memory` / `register_reference`（`component-model.md` §3）。

## §5 Insight = Memory 的一种（ADR 0006）

- **单一权威表征**：Insight 的权威表征 = Memory Ontology 记忆项（三维语义层 + 修正引用键）——不单立实体、不单立存储。
- `growth/insight.py` 独立文件存储**删除**（deletion test 通过，ADR 0006 决定 1）。
- `verify_insight` 输出经 Memory Interface 归位：insight → Memory（`remember` / `correct_memory` 形态）；continuity 记录 → Continuity 载体（`spec-self-state.md` §2）——growth 不再直接构造 MemoryItem（A-1 修复，`spec-growth.md` §2）。
- Insight 可检验、可修正、可淘汰（INV-10）：检验结果经 `correct_memory` / 引用键表达，不删除原 Insight 记录。

## §6 未定项

| 未定项 | 状态 |
|---|---|
| 消化 / 遗忘机制与判据 | UNKNOWN（`domain-invariants.md` §3），不编造 |
| 向量检索 | 延期；引入须独立 Research Evidence（规则 9） |
| 三维枚举值的扩展 | 设计层决定（Ontology 变更），Provider 不得自扩 |
