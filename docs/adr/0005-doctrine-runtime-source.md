# ADR 0005 — "道"文本的运行时单一来源

- **Status**: accepted（2026-09-13，STEP 12）
- **约束来源**: M-05（原则文本三处：`doctrine.py` 6 条 + `decision.py` 7 条 + `reflection.py` 20 条；来源 D-6 / A-3）；CINV-2（运行时不自改）/ CINV-3 / CINV-5；`docs/constitution/principles.md`（设计层成文单一来源，STEP 10 已建立；六条文本与 V0 `doctrine.py` 逐字一致）；Q1 用户追认（6 条 = "道"原则的**当前成文子集**，可增补、非"道"全部）

## Context

V0 的原则 / 约束文本分散**三处、三套条数、三种用途**：`core/doctrine.py`（6 条"道生根本约束"，frozen dataclass，形态最接近 Domain 概念）/ `decision.py`（7 条行动原则 + 执行要求，内嵌 `prepare_action` 投影拼装，A-3）/ `growth/reflection.py`（20 条"重要原则"，内嵌 reflection prompt）——同一 Domain 概念（"道"的行为约束面）没有单一来源，三处各自演化，改一处不保其余两处一致（M-05）。设计层：`docs/constitution/principles.md` 已是**设计层单一来源**（STEP 10）；剩余的是**运行时**单一来源的结构决定（本 ADR，`principles.md` 头注"运行时单一来源 = ADR ④ 待 STEP 12"的落点）。

## Decision

1. **Core Doctrine（"道"原则成文文本）的运行时单一来源 = 由 composition root 从设计层单一来源 `docs/constitution/principles.md` 注入的运行时只读来源**（typed 投影形态，V0 `doctrine.py` frozen dataclass 为形态参考）。这是 Runtime 内"道"文本的**唯一运行时副本**。
2. **一切运行时投影引用该单一来源**：decision / reflection 的投影拼装引用之，可裁剪 / 改写措辞（投影 ≠ 原文），但**不得另立**（M-05 三处三套条数的漂移教训：6 / 7 / 20 项并存）。
3. **变更路径**：Core Doctrine 只能由**设计层**变更（设计层文档变更 = 设计层行为，不经运行时写路径）；个体不得运行时自增 / 自修 / 自豁免（CINV-2：否则"道心稳固"可被自身行为绕过）。
4. **`protected_fields` 不是原则文本**：`identity: immutable` / `continuity: append-only` / `core_doctrine: immutable` 是**保护性约束**（K-11 历史形态，V1 不得弱化），留在 Identity 载体的机制里，不与原则文本混在同一来源（M-05 保留条件 3）。
5. **内容边界**：六条 = 当前成文子集（Q1 追认，可增补）；"道"的具体内容仍 UNKNOWN（CINV-1）——本 ADR 决定**结构的单一来源**，不裁决内容；V0 的 7 条 / 20 条内容不默认进入 V1（设计层取舍，非数据迁移，联动 ADR 0007）。

## Consequences

- **正面**：三处三套条数收敛为"一个设计层来源 + 一个运行时只读投影"；漂移教训（M-05）结构性消除；运行时不自改（CINV-2）有了单一 enforce 点；`data-ownership.md` 的 `core_doctrine: immutable` 保护有落点。
- **代价 / 限制**：设计层文档 → 运行时投影的映射（如何加载、何时读取）= STEP 13 实现细节；投影拼装处保留措辞裁剪权（不同场景不同投影），但条数与语义锚定单一来源。
- **显式保留**："道"的具体内容（六条之外的原则清单）= UNKNOWN；增补走设计层（用户），个体不得自增（CINV-2）。
