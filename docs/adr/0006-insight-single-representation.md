# ADR 0006 — Insight 单一表征

- **Status**: accepted（2026-09-13，STEP 12）
- **约束来源**: R-03（D-4：Insight 双表征——`growth/insight.py` dataclass 文件存储 与 `MemoryItem kind="insight"` 并存，无权威方）；R-08（A-1：`verify_insight` 在 growth 内直接构造 MemoryItem 写 memory）；ADR 0004（决定 2：Memory 不承载 Continuity 作为 kind，C-4 归 Continuity 载体）；K-02 / Q2 追认（三维语义层 + 修正引用键 = DaoSheng Memory Ontology 基础）

## Context

V0 的 Insight 有**双表征**（R-03 / D-4）：同一概念两套身份、两处存储、两套生命周期，无权威方。Insight 的读写方 = growth 管线（digest / extract / reflect）与 `verify_insight` 验证路径；后者的输出含两类——insight 本体与 `kind="continuity"` 项（C-4）。ADR 0004 已裁定 C-4 归属（Continuity 单一载体，不进 Memory）——R-03 的判据（"Insight 的读写方是谁、`verify_insight` 产生的 `kind='continuity'` 项归属哪一侧"）由此补齐，可裁决。

## Decision

1. **Insight 是 Memory 的一种**：单一权威表征 = DaoSheng Memory Ontology 内的记忆项（三维语义层字段 `memory_origin` / `memory_status` / `memory_confidence` + 修正引用键适用，K-02 / Q2）；V0 `kind="insight"` 为形态参考。**`growth/insight.py` 的独立文件存储删除**（deletion test：删除后 Insight 的复杂度不消失，只是归位到 Memory——双表征的无权威方问题随之一并消除）。
2. **growth 侧只保留领域操作**（"验证 insight"动作，R-08）：`verify_insight` 的输出经 **Memory Interface** 归位——**insight → Memory**（`remember` / `correct_memory` 形态）；**continuity 记录 → Continuity 载体**（ADR 0004）。growth 内部不再直接构造 MemoryItem 写库（A-1 修复）。
3. **候选取舍**（R-03 二选一）：选"Insight 是 Memory 的一种"，拒"Insight 独立、Memory 只存 projection"——
   - (a) Insight 的读写方是 growth 管线，管线对 Memory 的唯一写路径 = Memory Interface（R-08 纪律）；单一表征使验证路径无需绕过 Interface；
   - (b) 双表征 / 多处投影在 V0 已产生三处漂移教训（M-05 原则文本 6/7/20 条、R-04 能力两套 ID、R-03 本身）——"projection 与原文漂移"的权威问题靠 projection 解决不了；
   - (c) C-4 经 ADR 0004 归位后，`verify_insight` 两类输出各有一个家（Memory / Continuity 载体），不再需要第二套表征承载任何一侧。

## Consequences

- **正面**：两套身份 → 一套（R-03 修复）；insight 验证路径经 Interface，可测（the interface is the test surface，K-10 方向）；`verify_insight` 输出归位清晰，联动 ADR 0004 无悬置。
- **代价 / 限制**：Insight 的生命周期（验证 / 修正）随 Memory Ontology 机制——修正 = 追加 correction 记录，原记录内容与身份不变（INV-8）；若将来 Insight 需要 Memory 之外的独立生命周期（如独立的"信念修正"状态机），复审本 ADR。
- **联动**：ADR 0004（C-4）；R-08（A-1）；K-02（语义层字段）；`component-model.md` §3（Memory Interface 6 方法是归位路径）。
