# ADR 0004 — life 层归属与 Continuity 单一载体

- **Status**: accepted（2026-09-13，STEP 12）
- **约束来源**: R-11（审计判断："回合机制属 Core、host 会话属 adapter"，待 ADR 确认，规则 8）；M-02 / M-03；C-1…C-5（`docs/audit/v0-drift.md` §2.6，Continuity 的 V0 五处建模）；K-11（`continuity_revision` 字段；`protected_fields` 历史形态）；Q5 用户追认（Continuity = 独立一等概念，**非** Identity 字段）；第 6 条道心稳固 / CINV-3（Continuity = append-only）

## Context

V0 的 `life/` 层混合两种机制：① **回合机制**（`complete_turn`、turn 计数、记忆块拼装——Core 语义）；② **host 会话**（`bridge.py` subprocess 起 Hermes Desktop、`_state_db_path` 拼 host 存储路径、`source="hermes:{session_id}"` 前缀——host 集成）。审计（R-11）判断归属为"回合机制属 Core、host 会话属 adapter"，待 ADR 确认。另一侧：Continuity（Q5 已定为独立一等概念）在 V0 有**五处建模**（C-1…C-5）——两处（C-1/C-2）是运行时机制状态被错位持久化，一处（C-3）错位在 Identity 载体，一处（C-4）作为 Memory kind 承载——Continuity 没有单一住所。

## Decision

1. **life 层归属**：V1 **不设独立 "life 层"**——
   - ① 回合机制并入 **Core**：Individual 的单一回合入口（R-01：`observe`/`act`/`complete_turn` 三处收敛一处）；持久化进入该入口的 Interface（R-08 A-5 修复：life 侧不得跨类调私有 `_persist()`）；
   - ② host 会话（进程调用、会话导入、存储路径、source 前缀）并入 **host 集成 adapter 层**（ADR 0002）；
   - `LifeRuntime` 全部依赖构造注入，装配归 composition root（R-11：恢复 test surface 的前提——依赖注入不解决，任何 seam 都无法 Fake）。
2. **Continuity = Core 内单一载体，append-only**（独立于 Identity 载体、Runtime State 与 Memory）：
   - C-1（`last_action_experience_id`）/ C-2（`turn`）= **运行时机制状态，不是 Continuity**——降级进程内存，不持久（`runtime-boundaries.md` §3）；
   - C-3（`soul.continuity_revision`）/ C-4（MemoryItem `kind="continuity"`）= Continuity 语义——**并入单一载体**；Memory 不承载 Continuity 作为 kind，`verify_insight` 的 continuity 输出写入 Continuity 载体（联动 ADR 0006：输出经 Interface 归位）；
   - C-5（faculties "continuity" 根）= **Faculty**（8 根之一，K-09，Q3 追认初始集）——"维持连续性的能力根"，不是状态载体；保留于 faculties 初始集。
3. **载体实现形态**（文件形态 / 结构）= STEP 13 实现细节，当前无已定值，不预设。
4. **保护**：`continuity: append-only`（第 6 条 / CINV-3 / K-11 历史形态），V1 不得弱化——仅个体内部机制可追加；覆写 / 删除禁止；host / model / 外部输入直写禁止（`data-ownership.md` §2）。

## Consequences

- **正面**：五处漂移 → 一个载体（locality）；C-1/C-2 错位（V0 把运行时机制状态写进持久层）纠正——判据："个体仍然是谁 / 经历过什么" = persistent，"当前进程正在做什么" = runtime（`runtime-boundaries.md` §1）；回合机制可测（依赖注入，不自建）。
- **代价 / 限制**：C-5 与 Continuity 载体的耦合机制（faculty 根如何影响连续性状态）本步不设——Domain 描述需要时由 Domain 文档处理；载体实现形态待 STEP 13。
- **联动**：ADR 0002（② 的落点）；ADR 0006（`verify_insight` 输出归位：insight → Memory，continuity 记录 → Continuity 载体）。
