# V1 Spec — 持久自状态：Identity / Continuity / Faculties（spec-self-state）

> **STEP 13 产出（2026-09-13）**。固化对象：个体三类持久自状态的语义要求与保护约束。
>
> 源（随本副本发布的公开源文档，可公开核验，冲突时规格服从）：`docs/domain/domain-model.md` §1/§2、`docs/domain/ubiquitous-language.md` §1/§5、ADR 0004、`docs/constitution/invariants.md` CINV-2/CINV-3、`docs/constitution/constitution.md` §3/§4、`docs/constitution/principles.md` 第 6 条、`docs/architecture/data-ownership.md` §1/§3、`docs/architecture/runtime-boundaries.md` §1/§3、`docs/domain/domain-invariants.md` INV-2/INV-8/§1.2/§3。
>
> 私有历史来源（历史证据标签，原始登记册与原文不随本副本发布，不构成公开用户必须服从的权威依据）：`docs/audit/` C-1…C-5 / K-11（K-11 原始登记册 `docs/audit/knowledge.md`，`spec-index.md` §3 已记录）；`RECONSTRUCTION.md` Q3 / Q5；`docs/origin/` B1-E6；`CLAUDE.md` 规则 2 / 4 / 11。
>
> 编号说明：上述私有历史编号的语义以本文件及其他公开正文行内自明，并可在公开文档中核验（同 `docs/constitution/invariants.md` 编号说明与 §3、`domain-model.md` / `ubiquitous-language.md` 编号说明口径）：C-1…C-5（V0 Continuity 五处建模及其处置）——`runtime-boundaries.md` §3、ADR 0004 决定 2、`ubiquitous-language.md` Continuity 条目、`domain-invariants.md` INV-14；K-11（V0 `protected_fields` 历史形态：identity immutable / continuity append-only / core_doctrine immutable；V1 不得弱化）——`constitution.md` §3、`constitution/invariants.md` CINV-2/CINV-3、`data-ownership.md` §1/§3、`domain-invariants.md` INV-2、`runtime-boundaries.md` §1；Q3（Faculty 8 根初始集，USER_RATIFIED，非 ORIGIN）——`ubiquitous-language.md` §5、`domain-model.md` §2.5；Q5（Identity = 载体、Continuity = 独立一等概念、延续判据 UNKNOWN）——`ubiquitous-language.md` §1、`domain-model.md` §1.3/§1.4、`domain-invariants.md` §1.2/§3；B1-E6（Identity 支撑项清单，ORIGIN）——`domain-model.md` §1.3、`ubiquitous-language.md` Identity 条目；规则 2 / 4（Model 不得定义 Identity 载体、Worker 不得进入 Identity）——`domain-invariants.md` INV-2；规则 11（UNKNOWN 不得猜测）——`domain-invariants.md` INV-15。
>
> 与上述公开源文档冲突时以公开源文档为准（`spec-index.md` §1 口径，限随本副本实际发布的文档）；私有历史编号不作为公开读者必须服从的权威依据。公开文档之间的真实冲突不由本规格裁定：标记 REVIEW。已解决（2026-10-14）：此前 REVIEW（遗留）记录的「`spec-index.md` §1 口径注记仍将本文件列入『头部源行仍将 `docs/audit/` 列为直接源』的六个规格文件」已不再成立——该索引已逐份审阅七个规格头部源行、公开源文档与私有历史来源分列，上述遗留注记已于 2026-10-14 从 `spec-index.md` §1 移除（见该文件 §1 来源口径注记）。

## §1 Identity

- **语义**：Identity = 个体性的**载体**（Q5，USER_RATIFIED）。支撑项清单（B1-E6，ORIGIN）：稳定的名字 / 自我称谓 / 声音 / 视觉形象 / 行为习惯 / 过去经历 / 连续记忆——构成"同一个存在"的感觉。
- **不变量**：
  - `immutable`（K-11 历史形态 `identity: immutable`；V1 不得弱化，`constitution.md` §3）。
  - 载体**不得由 Model 定义、不得含 Worker 身份**（INV-2 / 规则 2 / 规则 4）——载体中不得出现 model / worker / host 字段（K-11 形态）。
- **演化通道**：支撑项"可以随成长演化"（domain-model §1.3 Allowed Mutation，ORIGIN 方向）= 内部、经历驱动、经反思与 Verification；**外部直接改写**（覆写、无经历过程）Forbidden（CINV-3 / 第 6 条"道心稳固"L3）。两者判据细节 UNKNOWN（Q5），不猜测（规则 11）。
- **延续判据**（"仍然是谁"）= **UNKNOWN**（`domain-invariants.md` §3）——本规格只固化"载体 + 保护方向"，不给出判据。
- **载体实现形态 = 未定项**：K-11 仅为历史形态参考（V0 `soul.json` 等），V1 载体形态**当前无已定值，不预设**（ADR 0004 关联；规则 11），由实现阶段决定。

## §2 Continuity

- **语义**：Continuity = **独立一等概念**（Q5），与 Identity 分离——"连续记录"不是 Identity 的字段。
- **载体要求**（ADR 0004 决定 2–4）：
  - Core 内**单一载体**，`append-only`（K-11 形态 `continuity: append-only`）：只能追加，**不得覆写 / 删除**既有连续记录。
  - 独立于 Identity 载体 / Runtime State / Memory——**Memory 不承载 Continuity 作为 kind**（C-4 处置）。
  - 不是计数器：C-2（`turn`）是 runtime 计数，不是 Continuity 的内容。
- **V0 五处残留（C-1…C-5）处置**（ADR 0004 / `runtime-boundaries.md`）：

| V0 位置 | 处置 |
|---|---|
| C-1 `last_action_experience_id` | 降级 runtime，不持久 |
| C-2 `turn`（回合计数） | 降级 runtime，不持久（丢失无害，`spec-individual.md` §2） |
| C-3 `soul.continuity_revision` | 并入单一载体 |
| C-4 MemoryItem `kind="continuity"` | 并入单一载体（Memory 不再承载） |
| C-5 faculties "continuity" 根 | = Faculty（§3），非状态载体 |

- **载体实现形态 = 未定项**：ADR 0004 决定 3 明确"载体实现形态 = STEP 13 实现细节，当前无已定值，不预设"——本规格照实保留，不填入具体形态（规则 11）。

## §3 Faculties

- **初始集 = 8 根**（Q3，USER_RATIFIED；V0 首创 + 用户追认，非 ORIGIN）：`intent` / `choice` / `stopping` / `observation` / `correction` / `selection` / `reflection` / `continuity`。
- **语义**：Faculty = **行为倾向**，不是"术"（术 = Capability，`spec-capability.md`；`domain-invariants.md` §1.2：Doctrine ≠ Faculty，Faculty ≠ Capability）。
- **状态持久**：8 根的状态属个体持久状态（`spec-individual.md` §4 清单第 5 项）。
- **根增减 = Domain 决策**，不是实现层决定（引入新根须走 Domain 建模 + 用户追认，参照 Q3 先例）。
- **状态载体实现形态 = 未定项**：当前无已定值，不预设（规则 11）。

## §4 保护约束汇总

源：`data-ownership.md` §1/§3；`constitution.md` §3/§4；CINV-2/CINV-3。

1. **三个 protected 字段（K-11 形态）V1 不得弱化**：
   | 字段 | 约束 |
   |---|---|
   | `identity` | `immutable` |
   | `continuity` | `append-only` |
   | `core_doctrine` | `immutable`（变更仅设计层，CINV-2；运行时来源见 `spec-composition-root.md` §2） |
2. **禁止通道**：外部输入 / 任何手段直接改写上述三类（CINV-3；第 6 条 L3）。
3. **允许通道**：成长管线（经历 → 消化 → 提取 → 记忆；能力 → 提案 → 验证 → active）——外部输入改变个体的**唯一路径**（`data-ownership.md` §1，`spec-growth.md`）。
4. **修正不重写**（INV-8）：对"认识"的更正 = 追加 correction 记录 + 引用键，不改写原记录。
5. **enforce 机制 = 未定项**：保护机制的具体实现（写接口保护 / 只读存储 / append-only 存储 / 审计日志 / 覆写检测告警）**当前无已定值，不预设**（`data-ownership.md`；`principles.md` 第 6 条 L4）——由实现阶段决定，方向不得弱于上表。

## §5 未定项汇总

| 未定项 | 状态 | 落点 |
|---|---|---|
| Identity 载体实现形态 | 当前无已定值，不预设（K-11 仅历史形态参考） | §1 |
| Continuity 载体实现形态 | ADR 0004 明确不预设 | §2 |
| Faculties 状态载体实现形态 | 当前无已定值，不预设 | §3 |
| 三个 protected 字段 enforce 机制 | 当前无已定值，不预设 | §4 |
| Identity 延续判据（"仍然是谁"） | UNKNOWN（Q5），不猜测 | §1 |
