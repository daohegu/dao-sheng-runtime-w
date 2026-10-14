# ADR 0003 — Capability 生命周期状态机与四目录权威

- **Status**: accepted（2026-09-13，STEP 12）
- **约束来源**: 材料 1 §4/§6（Skill = "个体后天修成的'术'"；能力有生命周期、可修成、可退休）；K-04（Manager 生命周期，"未验证的能力绝不能进入 active"）/ K-05（Verifier 执行前闸门）/ K-06（四目录生命周期，含保留条件）；R-04（Capability 双表征，来源 D-05）；`docs/domain/bounded-contexts.md` §5（ADR ②）

## Context

V0 的 Capability 有**双表征**（R-04 / D-05）：同时是 growth 侧 `MemoryItem kind="capability" provenance="growth" lifecycle="candidate"`（uuid5 命名空间）与 `capabilities/` 包四目录生命周期（K-06，uuid4）——两套 ID 体系、两套状态机，无权威方。V0 的 `capabilities/` 包是设计质量最高的子系统（K-04：proposal → 验证 → 晋升 active 单向闸门、active 完全隔离；K-05：唯一把"未经验证不得执行"落成机制处；K-06：目录即状态，可审计可回看）——但双表征使其权威分裂（K-04 保留条件 3：D-5 须收敛）。

## Decision

1. **能力生命周期状态机是 Core 的 Domain 概念，状态集 = proposed → working → active → retired**。**active 的唯一可达路径 = Verifier 执行前闸门**（K-05）：未验证的能力绝不能进入 active（K-04）。retired 保留不删除。
2. **`capabilities/` 包（Manager）是唯一权威生命周期**；growth 侧只保留 **proposal 记录**——"曾提出过这个能力"是经历 / 记忆，属 Memory（R-04）；"能力的状态机"属 Manager。V0 uuid5 侧 MemoryItem 不再承载 lifecycle 语义。
3. **四目录 = 状态机的一个合法 adapter 形态，不是定义本身**（K-06 保留条件 2）：状态集与迁移规则归状态机；目录名 / 目录契约经 Manager Interface 表达（R-07：Runner 不得直接构造 `root/"active"/name` 拼路径）。
4. **Growth 与 Capability System 边界**（R-04）：Growth 提案、Manager 管理；growth 侧对 capabilities/ 无任何直接文件操作。

## Consequences

- **正面**：双表征收敛为单一权威（R-04 修复）；闸门语义（K-05）与物理隔离（K-06）保留；"术" = 有生命周期的领域对象，目录即状态、可审计、可回看。
- **代价 / 限制**：状态机迁移的 enforce 机制 = STEP 13 实现细节；proposal 记录在 Memory 侧的形态与三维语义层（K-02）联动，具体形态是实现细节，本 ADR 不预设。
- **Re-evaluation Trigger**：出现第二个能力生命周期物理形态（非目录）、或状态集需扩展（如 suspended 状态）时，复审本 ADR。
