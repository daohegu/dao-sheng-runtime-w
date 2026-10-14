# V1 Spec — Growth 与成长管线（spec-growth）

> **STEP 13 产出（2026-09-13）**。固化对象：成长判据、成长管线（双通道的允许通道）、Memory 操作纪律、能力提案、Insight 验证归位、经验回流导入。
>
> 源（随本副本发布的公开源文档，可公开核验，冲突时规格服从）：`docs/domain/` Growth 条目（INV-4 / INV-6——`domain-invariants.md` §2、`ubiquitous-language.md` §2/§3）、ADR 0002 / 0003 / 0006、`docs/architecture/component-model.md` §1/§5、`docs/architecture/data-ownership.md` §1/§2、`docs/domain/bounded-contexts.md` §3/§5、`docs/constitution/principles.md` 第 4 条。
>
> 私有历史来源（历史证据标签，原始登记册与原文不随本副本发布，不构成公开用户必须服从的权威依据）：`docs/audit/` R-01…R-04 / R-08（子标签 A-1 / A-5 / A-6）/ M-01 / D-04 / D-06 / K-08 / A-1（K-\* / R-\* / M-\* / D-\* 口径同 `docs/constitution/invariants.md` §3）；A-7（私有历史索引，原始登记册不随本副本发布，同 `domain-model.md` 编号说明口径）；`docs/origin/` B1-E5 / B1-E8。
>
> 编号说明：上述私有历史编号的语义以本文件及其他公开正文行内自明，并可在公开文档中核验（同 `docs/constitution/invariants.md` 编号说明与 §3、`domain-model.md` / `ubiquitous-language.md` 编号说明口径）：R-01（`observe` / `act` / `complete_turn` 三入口收敛一处）——ADR 0004 决定 1、`ubiquitous-language.md` Observation 条目；R-02——未找到公开行内对应，保留为纯历史标签（同 `spec-index.md` §1 口径）；R-03（Insight 单一表征形式 = UNKNOWN，收敛方向见架构 Step）——`bounded-contexts.md` §5、`domain-invariants.md` §3；R-04（growth 侧直写 capabilities/ = 漂移形态；capabilities/ 包唯一权威，growth 侧只留 proposal 记录于 Memory）——`data-ownership.md` §2 Capability 行、ADR 0003 决定 2/4；M-01（V0 host 导入直依赖 host 会话 schema；host 集成层收敛方向）——`bounded-contexts.md` §3、`data-ownership.md` §2 Host 会话记录行、ADR 0002；D-04（`ResearchService` 47 行 pass-through 壳不 KEEP，包 KEEP）——`component-model.md` §5、`spec-adapters.md` §3；D-06（五个薄 pass-through 不 KEEP）——`component-model.md` §5；已解决（2026-10-14）：`spec-index.md` §1 旧表曾将 D-06 误映射至 `constitution/invariants.md` CINV-5，该索引已按本文件现状修正（D-06 = 五个薄 pass-through，公开核验锚点 `component-model.md` §5，见表后注记 1）。REVIEW：CINV-5 原文使用的编号是 D-6（doctrine 双维护漂移，与 `bounded-contexts.md` §5 的 M-05 / D-6 同族），不假定 D-06 与 D-6 为同一编号，归属不裁定；A-1（growth 直接构造 MemoryItem 写 memory = 违规形态；修复方向）——ADR 0006 约束来源 / 决定 2、`component-model.md` §1 Growth 行、`spec-memory.md` §5；R-08 A-1 / A-5 / A-6（不直接构造记忆对象 / 无跨类私有调用 / 阶段协作只在各自 Interface 内）——`component-model.md` §1 Growth 行、ADR 0004 决定 1（A-5）；A-7（直接构造 `capabilities/` 目录路径的反例形态）——`component-model.md` §1 Capability 行、`spec-capability.md` §3/§5；K-08（观察 ≠ 判断；`ResearchResult` 必须携带 sources + confidence）——`component-model.md` §1/§5、`spec-adapters.md` §3；B1-E5（成长判据，ORIGIN）——`domain-invariants.md` INV-4、`ubiquitous-language.md` Growth 条目；B1-E8——REVIEW：本文件 §1 将管线「经历 → 消化 → 提取 → 记忆 → 复用」标注为 B1-E8，而公开行内语义中该管线记录为 B1-E4 / INV-6（`ubiquitous-language.md` §2 Memory 条目、`domain-invariants.md` INV-6），B1-E8 对应另一条成长链（「学习知识 → 形成经验 → 掌握技能 → 形成习惯 → 形成个性 → 形成自我理解」，`ubiquitous-language.md` §3 Growth 条目）；编号保留、归属不裁定、不编造映射、不声称已核验私有原文。
>
> 与上述公开源文档冲突时以公开源文档为准（`spec-index.md` §1 口径，限随本副本实际发布的文档）；私有历史编号不作为公开读者必须服从的权威依据。公开文档之间的真实冲突不由本规格裁定：标记 REVIEW。已解决（2026-10-14）：`spec-index.md` §1 曾记录的 REVIEW（遗留）——「六个规格文件头部源行仍将 `docs/audit/` 列为直接源，留待后续审阅统一处理」——已不再成立，由该索引于 2026-10-14 移除；本文件头部已按该口径将公开源文档与私有历史来源分列。

## §1 成长判据

- **INV-4（ORIGIN，B1-E5）**："成长不只是增加知识，而是**过去的经历能够改变未来的行为**"。
- **Memory / Reflection 不是终点**：反思产出 = 行为变化，不是反思报告（`principles.md` 第 4 条）。
- 成长链（B1-E8，ORIGIN）：经历 → 消化 → 提取 → 记忆 → 复用——本规格 §2 固化的是这条链的**接口纪律**，不是算法。（REVIEW：公开行内语义中该管线记录为 B1-E4 / INV-6——`ubiquitous-language.md` §2 Memory 条目、`domain-invariants.md` INV-6；B1-E8 对应另一条成长链——`ubiquitous-language.md` §3 Growth 条目。编号保留、归属不裁定，见头部编号说明。）

## §2 成长管线 = 双通道的允许通道

源：`data-ownership.md` §1。

- 外部输入改变个体的**唯一路径**是成长管线：
  - 知识路径：经历 → 消化 → 提取 → 记忆；
  - 能力路径：能力 → 提案 → 验证 → active（`spec-capability.md`）。
- 管线之外的通道（直接改写 Identity / Continuity / Core Doctrine）= 禁止（`spec-self-state.md` §4）。
- **一切 Memory 操作经 Memory Interface**（R-08 A-1 / ADR 0006 决定 2）：growth 内部不直接构造 MemoryItem、不直接触达存储——V0 的 A-1 违规形态（growth 直接构造记忆对象）在 V1 全部消灭（`spec-memory.md` §2）。
- **不得跨类调用私有方法**（R-08 A-5 / A-6）：管线内部阶段（digest / extract / reflect）之间的协作只在各自 Interface 内进行。

## §3 管线内部阶段

源：`component-model.md` §1 Growth 行。

- 输入：Experience 候选（来自经验回流，§5）。
- 内部阶段：digest（消化）/ extract（提取）/ reflect（反思）——**机制细节**（触发、形式、频率、算法）属 L4 运营策略与实现，当前无已定值，不预设（`principles.md` 第 4 条 L4；消化 / 遗忘机制 UNKNOWN）。
- 输出：Memory 写入（经 Interface）/ Insight 验证结果（§4）/ 能力提案（§5 边界，`spec-capability.md`）/ 反思结果输出（行为倾向更新，`spec-self-state.md` §3）。
- **reflection 调度归 Individual**（`spec-individual.md` §1）：本规格只定义"反思产出什么、归位到哪里"，不定义"何时调度"。

## §4 verify_insight 输出归位（ADR 0006）

- `verify_insight` 是 growth 保留的**领域操作**（检验 = Verification 在 Insight 上的应用，INV-10）。
- 输出归位：
  - insight 相关 → Memory（经 `remember` / `correct_memory` 形态，`spec-memory.md` §2/§5）；
  - continuity 记录 → Continuity 单一载体（append-only，`spec-self-state.md` §2）。
- growth 不再持有 Insight 独立存储（`growth/insight.py` 删除，ADR 0006 决定 1）。

## §5 能力提案（Growth 与 Capability 的边界）

- **Growth 只提 proposal**（R-04 / ADR 0003 决定 4）：能力提案**记录在 Memory**，由 Capability Manager 接管后续生命周期（`propose` / `advance` / `retire` / `execute`，`spec-capability.md`）。
- Growth **无直接文件操作**：不触碰 `capabilities/` 四目录、不构造目录路径（A-7 反例形态，`spec-capability.md` §4）。

## §6 经验回流导入

源：ADR 0002（host 集成层）、`spec-adapters.md` §1。

- 形态："导入会话 → [Experience 候选]"——host 会话记录经 host 集成 adapter 层导入，转为 Experience 候选进入管线。
- origin 的**中性标注在本层完成**（provenance 中性化，`spec-memory.md` §1）：进入 Core 的候选不携带 host 名字。
- 导入 = append-only **幂等**（`spec-individual.md` §2）；去重是 host 集成层职责。
- `sync_hermes()` 从 Growth 核 Interface **移除而非改名**（ADR 0002 决定 5）：同步是 host 集成层的事，不是成长核的事。

## §7 Deletion test 排除项（growth 侧）

源：`component-model.md` §5。

- **D-06 五个薄 pass-through 不保留**（deletion test：删除后内联到调用方）：`remember_user_preference` / `remember_user_habit` / `research_once` / `propose_capability` / `recall_experience_packages`——它们是"接口几乎和实现一样复杂"的浅模块，V1 不单设。
- **D-04**：`ResearchService` 47 行壳不 KEEP——包（Research，`spec-adapters.md` §3）KEEP（K-08 纪律需要它），壳不 KEEP。

## §8 未定项

| 未定项 | 状态 |
|---|---|
| 消化 / 提取 / 反思的机制、触发、频率、形式 | 当前无已定值，不预设（L4 + 实现；消化遗忘 = UNKNOWN） |
| 经验候选的结构化形态 | 实现阶段决定；约束 = 不携带 host 名（§6） |
