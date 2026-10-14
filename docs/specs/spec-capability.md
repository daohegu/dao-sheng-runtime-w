# V1 Spec — Capability System（spec-capability）

> **STEP 13 产出（2026-09-13）**。固化对象：能力生命周期状态机、Verifier 闸门、Capability Manager 四方法、四目录 adapter 形态、Growth 与 Capability 边界。
>
> 源（随本副本发布的公开源文档，可公开核验，冲突时规格服从）：ADR 0003、`docs/domain/` Capability 条目（`domain-model.md` §3.2、`ubiquitous-language.md` Capability 条目）、`docs/architecture/component-model.md` §1、`docs/architecture/data-ownership.md` §1/§2、`docs/domain/bounded-contexts.md` §5 ADR ②、`docs/domain/domain-invariants.md` INV-11。
>
> 私有历史来源（历史证据标签，原始登记册与原文不随本副本发布，不构成公开用户必须服从的权威依据）：`docs/audit/` K-04 / K-05 / K-06 / A-7 / D-03 / R-04（K-\* / R-\* / D-\* 口径同 `docs/constitution/invariants.md` §3；A-7 同 `domain-model.md` 编号说明口径）；`docs/origin/` B1-E7；`CLAUDE.md` 规则 7 / 规则 12。
>
> 编号说明：上述私有历史编号的语义以本文件及其他公开正文行内自明，并可在公开文档中核验（同 `docs/constitution/invariants.md` 编号说明与 §3、`domain-model.md` / `ubiquitous-language.md` 编号说明口径）：K-04（Manager 生命周期；「未验证的能力绝不能进入 active」；active 完全隔离；四目录 V0 历史形态——公开行内该形态归 K-04/K-06 合称）——ADR 0003 约束来源 / Context、`component-model.md` §1 Capability 行、`data-ownership.md` §2 Capability 行、`domain-model.md` §3.2、`domain-invariants.md` INV-11、`bounded-contexts.md` §5 ADR ②；K-05（Verifier 执行前闸门）——ADR 0003 约束来源 / 决定 1、`component-model.md` §1 Capability 行、`data-ownership.md` §2 Capability 行、`domain-model.md` §3.6；K-06（四目录生命周期含保留条件；四目录 = 状态机的一个合法 adapter 形态、不是定义本身）——ADR 0003 Context / 决定 1 / 决定 3、`component-model.md` §1 Capability 行、`data-ownership.md` §2 Capability 行、`bounded-contexts.md` §5 ADR ②、`domain-model.md` §3.2；A-7（直接构造 `root/"active"/name` 路径的反例形态）——`component-model.md` §1 Capability 行（V0 反例 A-7）；同一禁令在 ADR 0003 决定 3 标注为 R-07（标签差异，归属不裁定）；D-03（V0 legacy `verify()` 旁路不得当作生命周期）——`domain-model.md` §3.2 / §3.6、`bounded-contexts.md` §5 ADR ②；R-04（capabilities/ 包唯一权威，growth 侧只留 proposal 记录于 Memory）——`data-ownership.md` §2 Capability 行、ADR 0003 Context / 决定 2 / 决定 4；B1-E7（Capability = 个体后天修成的「术」，ORIGIN 证据标签）——`domain-model.md` §3.2、`ubiquitous-language.md` Capability 条目；规则 7（历史经历记录不得被后续解释重写；公开对应口径 = Historical Experience 冻结）——`domain-invariants.md` INV-8、`bounded-contexts.md` §6 #4、`spec-index.md` §4 #3；规则 12（V0 形态逐条过 deletion test，不默认继承）——`component-model.md` 头部行内口径。编号保留、归属不裁定、不编造映射、不声称已核验私有原文。
>
> 与上述公开源文档冲突时以公开源文档为准（`spec-index.md` §1 口径，限随本副本实际发布的文档）；私有历史编号不作为公开读者必须服从的权威依据。公开文档之间的真实冲突不由本规格裁定：标记 REVIEW。已解决（2026-10-14）：`spec-index.md` §1 口径注记此前曾将本文件列入「头部源行仍将 `docs/audit/` 列为直接源」的六个规格文件；该注记已不再成立并于 2026-10-14 索引统一更新时移除，本文件头部将 `docs/audit/` 列于私有历史来源而非直接源，与索引当前口径一致。

## §1 状态机（Core Domain 概念）

源：ADR 0003 决定 1。

```
proposed → working → active → retired
```

- 状态机 = **Core Domain 概念**，不是目录结构的副产品（K-04 反例的纠正：V0 用目录当生命周期，V1 用状态机当生命周期）。
- **active 的唯一可达路径 = Verifier 执行前闸门**（K-05 / INV-11）：能力进入 `active` 之前必须通过 Verifier 验证；**不存在绕过闸门的第二条路径**（无旁路、无手动提升、无 legacy 通道）。
- `retired` = 终态保留：**保留不删除**（K-06 方向）——退役能力的记录仍在，历史不被抹除（规则 7 精神）。

## §2 Capability Manager — 唯一权威生命周期

源：ADR 0003 决定 2/3。

Manager 四方法 + 执行前闸门：

| 方法 | 语义 |
|---|---|
| `propose` | 登记 `proposed`（提案来源：Growth 能力提案，经 Memory 记录，§5） |
| `advance` | 状态推进（`working` → `active` 必经 Verifier 闸门，§1） |
| `retire` | 置 `retired`，保留不删除 |
| `execute` | 执行能力；**执行前闸门**——执行同样受 Verifier 约束（INV-11） |

- Manager 是能力生命周期的**唯一权威**：其他组件不得直接改动能力状态（`spec-growth.md` §5：Growth 无直接文件操作）。
- 方法签名与内部结构 = 实现阶段决定；本规格固化的是"四方法 + 闸门"这一契约形态。

## §3 四目录 = 状态机的一个合法 adapter 形态

源：K-04/K-06、ADR 0003 决定 3。

- V0 的 `capabilities/` 四目录（proposed / working / active / retired）**保留为状态机的一个合法 adapter 形态**——目录名与状态名对齐；但**生命周期语义在状态机，不在目录**（目录只是 adapter 的一种物理表达）。
- adapter 含义：未来状态机可以有其他物理形态（第二物理形态触发 Re-evaluation，§6）。
- **A-7 反例禁止**：任何组件不得直接构造 `root/"active"/name` 这类路径来"提升"能力——路径操作不是生命周期操作；提升只经 Manager `advance` + 闸门。

## §4 legacy `verify()` 旁路处置

源：D-03、ADR 0003。

- V0 legacy `verify()` 旁路（不经状态机的独立验证通道）**不作生命周期**：V1 中验证只有 §1/§2 的 Verifier 闸门一处形态；legacy 旁路形态在 V1 不存在（不 KEEP，规则 12）。

## §5 Growth 与 Capability 的边界

源：R-04、ADR 0003 决定 4。

- **Growth 只提 proposal**：能力提案记录在 Memory（`spec-memory.md`），由 Manager `propose` 接管；Growth 不触碰 `capabilities/` 目录、不构造路径（A-7 反例）。
- 成长路径完整形态（`data-ownership.md` §1）：能力 → 提案 → 验证 → active——这是外部输入改变个体**能力**的唯一通道（`spec-growth.md` §2 双通道）。

## §6 Re-evaluation Trigger

源：ADR 0003。

- 出现**第二物理形态**（非目录形态的载体）或**状态集扩展**（如 `suspended`）→ 复审 ADR 0003。
- 状态集扩展 = Domain 决策（新状态涉及生命周期语义，非实现细节），不得由实现层自行引入。

## §7 未定项

| 未定项 | 状态 |
|---|---|
| 各状态的具体判据（如 `working` 的进入/停留条件细节） | ADR 0003 固化状态机骨架；细节属实现阶段，不得新增状态（§6） |
| Manager 方法签名 | 实现阶段决定；契约 = 四方法 + 闸门（§2） |
