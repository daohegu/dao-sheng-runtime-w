# V1 Spec — 规格总纲（spec-index）

> **STEP 13 产出（2026-09-13）**。本目录是《总路线》08"把已经决定的东西变成规格"的产出：把已决定的 Domain / Constitution / Research / ADR / Architecture 固化为"V1 系统应当是什么"的规格视图，供 STEP 14（《总路线》09 Tickets）分解为可执行任务。
>
> **规格不是新的权威层**。规格只固化、汇总、组织已有决定；不重新决定、不新增 Domain 概念、不新增 ADR。规格条目与**随本副本发布的公开源文档**（ADR、`docs/domain/`、`docs/architecture/`、`docs/constitution/`、`docs/research/`）冲突时，规格服从——规格是固化，不是重新决定。私有历史编号及其原始登记册（`docs/audit/`、`docs/origin/`、`CLAUDE.md`、`RECONSTRUCTION.md`）不随本副本发布，属历史证据标签，**不构成公开用户必须服从的权威依据**（口径见 §1 编号说明；同 `docs/constitution/invariants.md` §3 口径）。权威顺序的公开记录是 INV-16（`docs/domain/domain-invariants.md` §2：Original Intent > Historical Decision > Validated Evidence > Implementation > Current Guess）——它是证据类型排序，不是"规格服从私有源文档"的规则；在公开副本中可公开核验的层级是 Validated Evidence（即 §1 所列公开源文档）。公开文档之间的真实冲突不由本索引裁定：标记 **REVIEW**，按现存公开裁决依据处理（`docs/constitution/invariants.md` §3：按权威顺序 INV-16 裁决，修订低权威侧或后写入侧并记录；规则 8：修订若涉及架构方向进 ADR）。REVIEW（未确认）：invariants.md §3 公开明文覆盖的是 CINV-\* 与 INV-\* 之间的冲突；公开副本中没有任何文档把「ADR 流程」规定为一切公开文档之间冲突的普适裁决流程——规则 8（ADR 闸门）的公开行内语义 = 重大架构变化 / 新概念引入须先立 ADR（可在 `constitution.md` §3/§5、`docs/adr/0009`、`docs/adr/0010` 行内核验），不是文档间冲突的普适裁决流程。本索引不将该泛化当作已有规则，也不另建裁决规则。规格中每条规范性陈述都必须能溯源到 §1 所列公开源文档之一；无法溯源的内容不写入规格。

## §1 源文档映射

> **来源口径（2026-10-13 统一）**：下表区分两类来源，保留全部历史编号与溯源，仅调整权威口径。**公开源文档** = 随本副本发布、可公开核验的文档，是冲突时规格服从的依据。**私有历史索引** = K-\* / R-\* / M-\* / D-\* / H-\* / C-\* / A-\* / U-\* / Q\* / B1-E\* / 规则编号等编号及其原始登记册（`docs/audit/`、`docs/origin/`、`CLAUDE.md`、`RECONSTRUCTION.md`），保留为历史来源说明 / 历史证据标签，原始登记册与原文不随本副本发布，各处引用语义以行内自明为准（同 `docs/constitution/invariants.md` 编号说明与 §3、`domain-model.md` / `ubiquitous-language.md` / `bounded-contexts.md` 编号说明口径），**不构成公开用户必须服从的权威依据**。
>
> 本口径同时解决 `spec-individual.md` 头部记录的 REVIEW：本文件不再将 `docs/audit/` 列为任何规格的直接源。七个规格头部源行已逐份审阅并按本口径处理（公开源文档与私有历史来源分列，`docs/audit/`、`docs/origin/`、`RECONSTRUCTION.md`、`CLAUDE.md` 明确标注为私有历史来源而非直接源）；本表原先记录的 REVIEW（遗留）——「六个规格文件头部源行仍将 `docs/audit/` 列为直接源，留待后续审阅统一处理」——已不再成立，于 2026-10-14 移除；它们"冲突时以源文档（`spec-index.md`）为准" defer 至本索引口径，本索引限定为公开源文档。下表已按已审阅的规格头部同步更新（2026-10-14）；未解决的映射疑点、历史归属不确定性与公开技术分歧保留于表后「映射 REVIEW 保留」注记，不视为已解决。

| 规格文件 | 公开源文档（随本副本发布，可核验） | 私有历史索引（历史来源说明，原始登记册不随本副本发布） |
|---|---|---|
| `spec-individual.md` | `docs/architecture/component-model.md` §1/§2、`runtime-boundaries.md`、`container-model.md` §2/§3、ADR 0002/0004、`docs/domain/domain-invariants.md` INV-5/7/13、`docs/architecture/data-ownership.md` | R-01/R-08/R-09/R-12 / K-01/K-10 / M-04/M-05 / D-05/D-6 / C-1/C-2——语义的公开口径可在 `spec-individual.md` 编号说明、ADR 0002 决定 4/5、ADR 0004 决定 1、`component-model.md` §1/§2（K-01/K-10）、`data-ownership.md` §2、INV-7（D-05）、`runtime-boundaries.md` §3（C-1/C-2）核验 |
| `spec-self-state.md` | `docs/domain/domain-model.md` §1/§2、`ubiquitous-language.md` §1/§5、ADR 0004、`docs/constitution/invariants.md` CINV-2/CINV-3、`docs/constitution/constitution.md` §3/§4、`docs/constitution/principles.md` 第 6 条、`docs/architecture/data-ownership.md` §1/§3、`docs/architecture/runtime-boundaries.md` §1/§3、`docs/domain/domain-invariants.md` INV-2/INV-8（及 §1.2、§3） | C-1…C-5 / K-11 / Q3 / Q5 / B1-E6 / 规则 2/4/11——语义的公开口径可在 `runtime-boundaries.md` §3、ADR 0004、`domain-invariants.md` INV-2、`constitution/invariants.md` CINV-2/CINV-3、`data-ownership.md` §1/§3、`ubiquitous-language.md` Identity / Faculty 条目核验 |
| `spec-memory.md` | `docs/domain/` Memory 条目（双轨 / 三维语义层 / 修正引用键——`domain-model.md` §2.3、`ubiquitous-language.md` §2）、ADR 0001/0006/0007、`docs/research/memory-architecture.md`、`component-model.md` §3、`docs/domain/bounded-contexts.md` §4/§6 #1、`docs/domain/domain-invariants.md` INV-3/8/10（及 §1.1 #1、§3）、`docs/architecture/container-model.md` §5、`docs/constitution/principles.md` 第 4 条 L3 | H-4 / Q2 / R-05 / R-10 / A-1 / U-2 / B1-E4 / 规则 5/7/9——语义的公开口径可在 `bounded-contexts.md` §4/§6 #1、`component-model.md` §3、ADR 0001 决定 4、ADR 0006 决定 2、ADR 0007 决定 2 / Consequences（R-10/U-2）、`domain-invariants.md` §1.1 #1 核验 |
| `spec-growth.md` | `docs/domain/` Growth 条目（INV-4/INV-6——`domain-invariants.md` §2、`ubiquitous-language.md` §2/§3）、ADR 0002/0003/0006、`component-model.md` §1/§5、`docs/architecture/data-ownership.md` §1/§2、`docs/domain/bounded-contexts.md` §3/§5、`docs/constitution/principles.md` 第 4 条 | R-01…R-04 / R-08（子标签 A-1/A-5/A-6）/ M-01 / D-04 / D-06 / K-08 / A-1 / A-7 / B1-E5 / B1-E8——语义的公开口径可在 ADR 0004 决定 1（R-01）、`bounded-contexts.md` §3/§5（M-01/R-03）、`component-model.md` §5（D-04；D-06 = 五个薄 pass-through）、`data-ownership.md` §2（R-04）、ADR 0006（A-1）、`component-model.md` §1（K-08/A-7/R-08）、`domain-invariants.md` INV-4（B1-E5）核验；**R-02 未找到公开行内对应，保留为纯历史标签**；D-06 与 D-6、B1-E8 归属见表后注记 |
| `spec-capability.md` | ADR 0003、`docs/domain/` Capability 条目（`domain-model.md` §3.2、`ubiquitous-language.md` Capability 条目）、`component-model.md` §1、`docs/architecture/data-ownership.md` §1/§2、`docs/domain/bounded-contexts.md` §5 ADR ②、`docs/domain/domain-invariants.md` INV-11 | K-04/K-05/K-06/A-7/D-03/R-04 / B1-E7 / 规则 7/12——语义的公开口径可在 `component-model.md` §1（K-04/K-05/K-06/A-7）、`data-ownership.md` §2（K-04/K-05/K-06/R-04）、`bounded-contexts.md` §5 ADR ②（K-04/K-06/D-03）、`domain-model.md` §3.2（B1-E7）核验；A-7 同一禁令在 ADR 0003 决定 3 标注为 R-07（标签差异，归属不裁定，见表后注记） |
| `spec-adapters.md` | ADR 0001/0002、`docs/architecture/system-context.md` §1/§3、`container-model.md` §2/§3、`component-model.md` §1/§4/§5、`docs/domain/domain-invariants.md` INV-1/INV-7（及 §3） | M-01…M-05（Host 审计族）/ M-1…M-6（Model 泄漏族；两套独立编号族，见表后注记）/ H-1…H-9 / D-05 / D-04 / R-09 / R-12 / K-01 / K-07 / K-08 / U-5 / 规则 11——语义的公开口径可在 `bounded-contexts.md` §3/§6 #1、`system-context.md` 编号说明 / §1（U-5）、`data-ownership.md` §2（R-09/M-01/M-1…M-6）、INV-7（D-05/R-12）、`component-model.md` §5（D-04）、K-01——`component-model.md` §2/§4、K-07——§1/§4、K-08——§1/§5 核验（该文件 §3 = Memory Interface / R-05，未见 K-08 行内出现；旧索引「§1/§2/§3」记载有误，已按核验修正） |
| `spec-composition-root.md` | `component-model.md` §1、ADR 0002/0004/0005、`docs/constitution/constitution.md` §2/§6、`docs/constitution/principles.md`、ADR 0001（头部标注「U-5 关联」在公开内容不可核验，REVIEW 保留，见表后注记） | R-09 / M-04 / M-05 / D-6 / M-1…M-3 / M-6 / R-12 / D-05 / K-11 / U-5 / Q1 / 规则 11——语义的公开口径可在 `data-ownership.md` §2（R-09 accept don't create、M-04 host 身份宣称、M-05/D-6 doctrine 三处漂移、U-5 Model 部署关系 UNKNOWN、M-1…M-6 Model 泄漏族）、`constitution.md` §6 + `constitution/invariants.md` CINV-5 + `bounded-contexts.md` §5 ADR ④（M-05/D-6）、ADR 0002 决定 4/5（R-12/D-05）、`constitution.md` §1/§3 + CINV-2/CINV-3（K-11）、CINV-1（Q1）、INV-15（规则 11）、`bounded-contexts.md` §6 #1（M-1…M-6）核验 |

> **映射 REVIEW 保留（2026-10-14 审阅；本索引不裁定、不编造映射、不视为已解决）**：
> 1. **D-06 vs D-6**：旧表将 D-06 映射至 `constitution/invariants.md` CINV-5（doctrine 三处漂移，「D-06 方向」）——该映射有误，已按 `spec-growth.md` 现状修正：D-06 = 五个薄 pass-through（`remember_user_preference` / `remember_user_habit` / `research_once` / `propose_capability` / `recall_experience_packages`），公开核验锚点 = `component-model.md` §5。CINV-5 原文使用的编号是 **D-6**（doctrine 6 / 7 / 20 双维护漂移，与 `bounded-contexts.md` §5 ADR ④、`data-ownership.md` §2 Core Doctrine 行的 M-05 / D-6 同族）。大小写 / 前导零 / 文本相似不构成同一性证据，不假定 D-06 与 D-6 为同一编号；D-6 的原始历史归属不裁定。
> 2. **B1-E8 归属**：`spec-growth.md` §1 将管线「经历 → 消化 → 提取 → 记忆 → 复用」标注为 B1-E8，而公开行内该管线记录为 **B1-E4** / INV-6（`ubiquitous-language.md` §2 Memory 条目、`domain-invariants.md` INV-6）；B1-E8 对应另一条成长链（「学习知识 → 形成经验 → 掌握技能 → 形成习惯 → 形成个性 → 形成自我理解」，`ubiquitous-language.md` §3 Growth 条目）。编号保留、不擅自映射为 B1-E4、归属不裁定。
> 3. **A-7 vs R-07**：同一禁令（直接构造 `root/"active"/name` 拼路径）在 `spec-capability.md` 与 `component-model.md` §1 标注为 A-7，在 ADR 0003 决定 3 标注为 **R-07**。标签差异记录在案，历史归属不裁定。
> 4. **M-01…M-05 vs M-1…M-6**：两套独立编号族——M-01…M-05 = Host 集成审计族（`data-ownership.md` §2 Host 会话记录行、`bounded-contexts.md` §6 #1），M-1…M-6 = Model 泄漏族（默认值 / 端点 / 身份宣称 / 硬建后端，`data-ownership.md` §2 Model 配置行、`bounded-contexts.md` §6 #1），不得混为同一系列。「M-01…M-06」为压缩混写；**「M-06」形态未见公开行内对应**，不自行与 Model 泄漏族的 M-6 合并；M-05 仅出现于 `spec-adapters.md` 头部压缩范围、正文未使用，其公开行内语义属 doctrine 漂移族（与 D-6 同族），与该文件 adapter 对象无直接关系——编号保留、归属不裁定。
> 5. **ADR 0008 / ADR 0010 vs `spec-adapters.md`**（2026-10-14 部分关闭）：两份 ADR 晚于该规格（2026-09-13）且直接治理其对象；ADR 0008 决定 4/7 确立 Model 调用 seam hypothetical → real，与该文件 §4 正文不一致。**已关闭**：「旧 §4 的 hypothetical 与后续 accepted ADR 的 real 之间缺少当前状态解释」——`spec-adapters.md` 已于 2026-10-14 在 §4 之后追加「§4 当前状态补充」：原 §4 表格保留为 2026-09-13 历史状态快照，当前 Model 调用 seam 状态 = real（ADR 0008 决定 4，ADR 0009 / 0010 相关记录延续确认；U-5 具体部署值仍 UNKNOWN / `None`），当前 seam 状态可查阅该节。**仍保留、不视为已解决**：本索引仍不将 ADR 0008/0009/0010 加入该规格公开源列，不宣称这些 ADR 追溯性改写旧规格；历史管辖 / 来源关系争议仍按 `spec-adapters.md` 已有 REVIEW 记录保留，本索引不裁定。
> 6. **ADR 0001 ↔ U-5**：`spec-composition-root.md` 头部将 ADR 0001 标注「U-5 关联」；ADR 0001 公开全文未提及 U-5，该关联在公开文档中不可核验——ADR 0001 保留于公开源列（其 Memory 持久化决定是该规格的公开依据），「ADR 0001 ↔ U-5」关联 REVIEW 保留、关联不裁定。
> 7. **R-02**：未找到公开行内对应，保留为纯历史标签（见 `spec-growth.md` 行）。
> 8. **`spec-adapters.md` §2「ADR 0002（Model 容器）」标签**：ADR 0002 公开文本 = host 集成层确立，未对 Model 容器作决定；该标签差异为 `spec-adapters.md` 内部 REVIEW，本索引不裁定。

## §2 规格清单

| 文件 | 固化对象 | 一句话 |
|---|---|---|
| `spec-individual.md` | Individual 顶层聚合 | 单一回合入口 `act(...)` + `persist()`，回合原子性，重启语义，依赖构造注入 |
| `spec-self-state.md` | Identity / Continuity / Faculties | 三类持久自状态：immutable / append-only 单一载体 / 8 根初始集 |
| `spec-memory.md` | Memory 与 Memory Provider | 三维语义层 Ontology + 6 方法 Interface + embedded SQLite 要求 + 修正不重写 |
| `spec-growth.md` | Growth 与成长管线 | 经历→消化→提取→记忆→复用；一切 Memory 操作经 Interface；能力只提 proposal |
| `spec-capability.md` | Capability System | 状态机 proposed → working → active → retired；Verifier 闸门 = active 唯一可达路径 |
| `spec-adapters.md` | 集成 adapter 层 | host 集成 / Model 调用 / Research 三个 adapter + seam 清单 + 进程边界硬要求 |
| `spec-composition-root.md` | Composition root | 依赖装配、"道"文本运行时单一来源注入、Model 配置声明、host 关系声明位 |

## §3 全局未定项（规格不预设）

以下两项在源文档中已明确"当前无已定值，不预设"，规格**照实保留为未定项**，由实现阶段（STEP 14 及以后）决定；任何规格文档不得为其填入具体值（规则 11 / INV-15）：

| 未定项 | 源出处 | 规格落点 |
|---|---|---|
| Continuity 单一载体的**实现形态** | ADR 0004 决定 3 | `spec-self-state.md` §2 |
| Identity / Faculties 载体实现形态（K-11 仅为历史形态参考） | ADR 0004 决定 3；K-11 为私有历史编号（原始登记册 `docs/audit/knowledge.md` 不随本副本发布），其公开行内语义可在 `docs/domain/domain-invariants.md` INV-2、`docs/constitution/invariants.md` CINV-2/CINV-3、`docs/architecture/data-ownership.md` §1/§3 核验 | `spec-self-state.md` §1/§3 |
| 三个 protected 字段的 **enforce 机制** | `docs/architecture/data-ownership.md` | `spec-self-state.md` §4 |

域内 UNKNOWN（`docs/domain/domain-invariants.md` §3，11 项）在 STEP 12 后的状态：

| UNKNOWN | 状态（2026-09-13） |
|---|---|
| Insight 单一表征形式 | **已解决** → ADR 0006（Insight = Memory 的一种） |
| Continuity 单一载体归属 | **已解决** → ADR 0004（Core 内单一载体；载体形态 = 上表未定项） |
| Capability 正式生命周期状态机 | **已解决** → ADR 0003 |
| Host 正式定义 | 结构已定（ADR 0002 host 集成层）；**Host 概念正式定义仍 UNKNOWN** |
| V1 是否迁移 V0 数据 | 默认值已定（ADR 0007：不迁移）；**最终状态仍 UNKNOWN**（用户决策） |
| Identity 延续判据 / "道"具体内容 / 消化遗忘机制 / Worker 定义 / Tool 定义 / 三词关系 | 保持 UNKNOWN，不猜测（规则 11） |

## §4 规格纪律

规格文档**不得**：

1. 重新决定已定内容（发现与公开源文档冲突 → 回公开源文档裁决，规格服从；公开文档之间的真实冲突 → 标记 **REVIEW**，按 `docs/constitution/invariants.md` §3 现存裁决依据处理——INV-16 证据序；修订涉及架构方向时进 ADR（规则 8）——本索引不代裁定；该依据向一切公开文档间冲突的泛化未确认，见前言 REVIEW（未确认）注记）。
2. 新增 Domain 概念或修改 `docs/domain/`（规则 1 / INV-14 方向；CINV-5）。
3. 修改 V0 代码、已完成 Step 的记录（执行历史不追溯）。`docs/origin/` 与规则 7 原文为私有历史材料，不随本副本发布；本纪律的公开对应口径 = Historical Experience 冻结：历史经历记录不得被后续解释重写（`docs/domain/domain-invariants.md` INV-8；`docs/domain/bounded-contexts.md` §3/§6 #4），本副本内公开 Historical Experience 记录同样只读。
4. 为 §3 未定项预设具体值（规则 11）。
5. 把 V0 实现形态当 V1 依据（V0 形态仅作历史证据标签引用，K-* / M-* / R-* / D-* / H-* 编号——口径见 §1 编号说明与 `docs/constitution/invariants.md` §3）。

规格文档**应当**：

1. 每条规范性陈述携带源引用：优先公开源引用（ADR / INV / CINV / 公开文档章节）；私有历史编号（K / R / M / D / H / B1-E / Q 等）可保留为历史证据标签，但其语义须行内自明或可在公开文档中核验，不得替代公开溯源。
2. 把"必须 / 不得"与"当前无已定值"严格分开表述。
3. 以可分解性为目标组织内容（STEP 14 Tickets 的输入）。

## §5 下一步

STEP 14（《总路线》09 Tickets）：把本目录规格分解为可执行任务。分解时以 §2 七个对象为分解轴；§3 未定项在对应 Ticket 内作为"实现阶段决定项"显式列出，不得隐式带过。
