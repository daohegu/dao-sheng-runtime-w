# V1 Spec — 集成 adapter 层（spec-adapters）

> **STEP 13 产出（2026-09-13）**。固化对象：host 集成层、Model 调用 adapter、Research adapter、seam 清单、进程边界硬要求。
>
> 源（随本副本发布的公开源文档，可公开核验，冲突时规格服从）：ADR 0001/0002、`docs/architecture/system-context.md` §1/§3、`container-model.md` §2/§3、`component-model.md` §1/§4/§5、`docs/domain/domain-invariants.md` INV-1/INV-7（及 §3）。
>
> 私有历史来源（历史证据标签，原始登记册与原文不随本副本发布，不构成公开用户必须服从的权威依据）：`docs/audit/` M-01…M-05 / M-1…M-6 / H-1…H-9 / D-05 / D-04 / R-09 / R-12 / K-01 / K-07 / K-08（K-\* / R-\* / M-\* / D-\* / H-\* 口径同 `docs/constitution/invariants.md` §3）；`RECONSTRUCTION.md` U-5（U-\* → `RECONSTRUCTION.md` Open Questions，同 `domain-invariants.md` §3 口径）；`CLAUDE.md` 规则 11（公开对应口径 = INV-15，`domain-invariants.md`）。
>
> 编号说明：上述私有历史编号的语义以本文件及其他公开正文行内自明，并可在公开文档中核验（同 `docs/constitution/invariants.md` 编号说明与 §3、`domain-model.md` / `ubiquitous-language.md` 编号说明口径）：M-01（V0 `hermes_import.py` 直依赖 host 会话 schema；导入会话 → [Experience 候选]）——`data-ownership.md` §2 Host 会话记录行、`container-model.md` §2/§4、`runtime-boundaries.md` §1/§2；M-02（subprocess 桥形态 = V0 `life/bridge.py`）——`container-model.md` §2、`bounded-contexts.md` §5 ADR ③；M-03（host 存储路径构造知识属 host 集成层，Core 不可知）——`container-model.md` §1/§2、`runtime-boundaries.md` §1；M-04（host 身份宣称文本只在 composition root 声明位，不进 Core 或投影文本）——`container-model.md` §4、`component-model.md` §4、ADR 0002 决定 4/5；M-05——仅出现于头部压缩范围「M-01…M-06」，本文件正文未使用；其公开行内语义 = doctrine 三处漂移（6 / 7 / 20 项并存，与 D-6 同族），见 `data-ownership.md` §2 Core Doctrine 行、`bounded-contexts.md` §5 ADR ④、`constitution/invariants.md` CINV-5，与本文件 adapter 对象无直接关系；编号保留、归属不裁定；M-1…M-3 / M-6（Model 泄漏族：默认值 / 端点 / 硬建 DuckDuckGoResearchProvider 移装配点；与 M-01…M-05 为两套独立编号族，头部「M-01…M-06」为压缩混写，「M-06」形态未见公开行内对应）——`bounded-contexts.md` §6 #1、`data-ownership.md` §2 Model 配置行、`component-model.md` §1/§4；H-1…H-9（9 处 Hermes 泄漏收敛位，如 H-2 `sync_hermes()` 在 Growth 核、H-4 host 名进 provenance 枚举）——`bounded-contexts.md` §6 #1、`system-context.md` 编号说明 / §3、ADR 0002 Context；D-05（症状级清洗在 R-12 根因修复前不得删除的硬性顺序）——INV-7、ADR 0002 决定 5；D-04（`ResearchService` 47 行 pass-through 壳不 KEEP，包 KEEP）——`component-model.md` §5、`spec-growth.md` §7；R-09（accept dependencies, don't create them）——`data-ownership.md` §2、`component-model.md` §1/§4；R-12（投影不回流；host 关系表述不进 Core 文本）——INV-7、`data-ownership.md` §2/§3、`container-model.md` §2/§4、`component-model.md` §4、ADR 0002 决定 4/5；K-01（Agent seam real）——`component-model.md` §2/§4；K-07（world seam 两 adapter 接近 real）——`component-model.md` §1/§4；K-08（观察 ≠ 判断；`ResearchResult` 必须携带 sources + confidence）——`component-model.md` §1/§5；U-5（Model 部署形态 UNKNOWN）——`domain-invariants.md` §3、`system-context.md` §1、`container-model.md` §1、`data-ownership.md` §2；规则 11（UNKNOWN 不得猜测）——`domain-invariants.md` INV-15。编号保留、归属不裁定、不编造映射、不声称已核验私有原文。旧版 `spec-index.md` §1 曾将 K-01/K-07/K-08 的公开核验位置记为 `component-model.md` §1/§2/§3，与本文件核验的落点（K-01——§2/§4、K-07——§1/§4、K-08——§1/§5；该文件 §3 = Memory Interface / R-05，未见 K-08 行内出现）不一致，本文件编号说明的核验位置亦超出旧索引为本文件列出的公开源列。`spec-index.md` 已于 2026-10-14 统一更新：其 §1 spec-adapters 行已按本文件核验落点修正（旧「§1/§2/§3」记载承认有误），并分列公开源文档与私有历史索引核验锚点（含 `data-ownership.md` §2、`bounded-contexts.md` §3/§6 #1 等）；该映射差异已解决。REVIEW：§2 源行将 ADR 0002 标注为「（Model 容器）」；ADR 0002 公开文本 = host 集成层确立，未对 Model 容器作决定；Model 容器的公开落点 = `container-model.md` §1/§2/§3、`system-context.md` §1 COGNITIVE MODELS 行；标签保留、归属不裁定。
>
> 与上述公开源文档冲突时以公开源文档为准（`spec-index.md` §1 口径，限随本副本实际发布的文档）；私有历史编号不作为公开读者必须服从的权威依据。公开文档之间的真实冲突不由本规格裁定：标记 REVIEW。REVIEW（后续公开 ADR）：ADR 0008（accepted 2026-09-24，Model Interface 与多 Backend Adapter seam；其约束来源行明确引用本文件 §2/§4）与 ADR 0010（accepted 2026-10-09，Host Adapter → Experience 候选供数语义契约）为晚于本规格（2026-09-13）且直接治理本文件对象的公开 ADR。ADR 0008 决定 4/7（ADR 0010 行内引用）确立 Model 调用 seam hypothetical → real（第二 wire 形态 llama.cpp 出现），与本文件 §4 seam 清单正文「Model 调用 = hypothetical」不一致；`spec-index.md` §1 未将 ADR 0008/0010 列入本文件公开源列。上述公开文档之间的真实分歧与索引映射差异：本文件不重写正文、不裁定，标记 REVIEW。REVIEW 状态分列（2026-10-14，与本文件「§4 当前状态补充」同步）：已关闭——「§4 hypothetical 与后续 accepted ADR 的 real 之间缺少当前状态解释」（原 §4 表格 = 2026-09-13 历史状态快照；当前 Model 调用 seam = real，有 ADR 0008、0009、0010 公开记录支持；U-5 部署值仍 UNKNOWN / `None`）；仍保留 REVIEW、不视为已解决——ADR 0008/0010 与本规格的历史管辖 / 来源关系（含 `spec-index.md` §1 未将其列入本文件公开源列、是否追溯改写旧规格），本文件不裁定。

## §1 host 集成层（唯一允许知道 "Hermes" 的层）

源：ADR 0002 决定 1–6、`container-model.md` §2、M-01/M-02/M-03/M-04。

- **定位**：进程内 adapter 层（非独立容器）——host 会话管理、经验回流导入、同步。**唯一允许知道 "Hermes" 的层**；"DaoSheng 与 host 的关系"只在 composition root 声明位（`spec-composition-root.md` §3；R-12/M-04 不进 Core 文本）。
- **Interface = 中性三方法**：`open_session` / `import_session` / `sync`——无 host 名（ADR 0002 决定 2）：
  - `open_session`：建立/打开 host 会话（V0 漂移形态收敛：M-02 `life/bridge.py` subprocess 桥 + M-01 `hermes_import.py` 842 行单一文件）；
  - `import_session`：经验回流"导入会话 → [Experience 候选]"（M-01；origin 中性标注在本层完成，`spec-memory.md` §1）；
  - `sync`：V0 `sync_hermes()` + `_state_db_path` 三位置 fallback + `source="hermes:"` 前缀（M-03）的收敛位——**`sync_hermes()` 移除非改名**（ADR 0002 决定 5：同步属本层，不属 Growth 核，`spec-growth.md` §6）。
- **去重 / 幂等 = 本层职责**（`spec-individual.md` §2.3）：经验回流 append-only 幂等重导入的去重发生在 host 集成层，不在 Core。
- **D-05 处置（硬性顺序）**：症状级清洗函数在 R-12 根因修复**之前不得删除**（INV-7）；根因修复（"DaoSheng 与 host 关系"表述退出 Core 文本）后随 R-12 删除。
- **Host 概念正式定义 = UNKNOWN**（`domain-invariants.md` §3）：结构已定（本层），概念定义不猜测（规则 11）。

## §2 Model 调用 adapter

源：ADR 0002（Model 容器）、`container-model.md` §2/§3、M-1…M-3、R-09、INV-1。

- **形态**：`chat` / `complete` 两级调用；HTTP 细节、超时、**默认值（M-1…M-3）全部隐藏**在 adapter 内（depth：调用方只知道两级调用 + 结果）。
- **默认值移 composition root**（R-09）：adapter 不自带部署默认值；配置声明在装配点（`spec-composition-root.md` §3）。
- **重连 = adapter 行为**（INV-1）：Model 重启对个体无影响（`spec-individual.md` §3）；重连 / 退避逻辑藏在本 adapter 内，不暴露给 Core。
- **部署形态 = UNKNOWN（U-5）**：本地模型服务的部署细节当前无已定值，不预设（L4 / 部署层决定）。

## §3 Research adapter

源：K-08、R-09、M-6、D-04。

- **形态**：`research → ResearchResult(sources, confidence)`。
- **观察 ≠ 判断（K-08 纪律）**：Research 产出是**观察**（带来源），不是个体的判断；`ResearchResult` **必须携带 `sources` + `confidence`** = invariant（缺任一即违规）。
- **V0 硬建 DuckDuckGo 客户端 → 移 composition root**（R-09 / M-6）：adapter 接受依赖不创建（accept don't create）；具体后端（DuckDuckGo 或其他）是装配决定，不是 Research 包内部决定。
- **包 KEEP，壳不 KEEP**（D-04）：Research 包保留（K-08 纪律需要一个落点）；V0 `ResearchService` 47 行 pass-through 壳删除（deletion test，`spec-growth.md` §7）。

## §4 Seam 清单（个体级 deletion test）

源：`component-model.md` §4/§5。

| Seam | 状态 | 依据 |
|---|---|---|
| Agent（Model 调用） | **real**，当前 5 个 adapter 形态 | K-01 |
| World（外部服务） | **real**（接近） | K-07 |
| Memory Provider | hypothetical（单 adapter：embedded SQLite） | ADR 0001；第二个真实 Provider 出现即 real（Re-evaluation Trigger） |
| host 集成 | hypothetical | 本文件 §1 |
| Model 调用 | hypothetical | 本文件 §2（与 Agent 行区分：Agent = 个体行动面，Model 调用 = 部署面） |
| Research | hypothetical | 本文件 §3 |

- "one adapter = hypothetical seam, two = real"：hypothetical 不意味着不建 seam——seam 已按 §1–§3 的形态固化；它只意味着**当前不预设第二个 adapter**。
- **个体级 deletion test**：host 名字从 Core 枚举 / 文本中删除后，复杂度不会在 N 个调用点重现（收敛在 §1 一层）——这是 `spec-individual.md` §5 投影纪律与 provenance 中性化（`spec-memory.md` §1）的合并判据（H-1…H-9 的收敛位）。

### §4 当前状态补充（2026-10-14 追加；不改写上方表格与本文件任何历史正文）

- 上表「Model 调用 = hypothetical」为 **2026-09-13（STEP 13 产出日）的历史状态快照**，原文保留以保存历史记录，不回改。
- **当前 Model 调用 seam 状态 = real**。依据：ADR 0008（accepted 2026-09-24）决定 4「Model 调用 seam 状态：hypothetical → real」；ADR 0009（accepted 2026-10-08）§触发判定「0009 引用并延伸 0008（0008 的 Model Interface / seam real / Registry / U-5 决定全部继续有效）」及其内部一致性检查「seam real……全部保留；0009 = seam 之下延伸」延续确认；ADR 0010（accepted 2026-10-09）约束来源行以「ADR 0008 决定 4 / 7（seam hypothetical → real……）」为在先例。两份后续 accepted ADR 均未回改 0008（规则 7）。
- 此处 `real` 沿用公开文档既有定义：本文件 §4「one adapter = hypothetical seam, two = real」——第二 Backend Adapter / wire 协议形态出现（llama.cpp server wire ≠ Ollama native `/api/*`，ADR 0008 Context diff 3）后，Model 调用 seam 升格为 real；real seam 的契约 = Model Interface（ADR 0008 决定 4）。
- **seam = real ≠ 具体部署值已确定**：U-5 的具体模型、模型路径、endpoint、部署参数（timeout / retry 等）及部署选择继续维持原有 UNKNOWN / `None` 边界——`ModelConfig` 声明位保持全 `None`（ADR 0008 决定 7 与 §Consequences「未决（显式保留）」；ADR 0009 决定 4 与内部一致性检查 U-5 行）；本文件 §2「部署形态 = UNKNOWN（U-5）」与 §6 未定项表保持原样，不为任何槽位填入默认值（规则 11）。
- 本节仅为当前状态说明，使 §4 历史快照与后续 accepted ADR 的当前状态可被读者对齐；不声称重新裁决历史来源之间的管辖 / 技术关系，不回改 ADR 0008 / 0009 / 0010 及本文件 §1–§6 历史正文。本文件头部 REVIEW（ADR 0008/0010 vs §4）已于 2026-10-14 按本节口径作 closed / retained 状态同步（非裁定）：「缺少当前状态解释」一项已关闭；历史管辖 / 来源关系疑点仍保留 REVIEW、不视为已解决；其余 REVIEW 状态不变。

## §5 进程边界硬要求

源：`container-model.md` §2/§3。

- **Hermes Desktop 进程不直接触碰 Core 持久文件**（个体持久文件清单，`spec-individual.md` §4）：一切交互经 host 集成 adapter 层（本文件 §1）。
- 四个容器（`container-model.md` §2）：DaoSheng Runtime（Core 进程，拥有个体持久文件）/ Hermes Desktop（host 进程，host 文件）/ Cognitive Models（本地模型服务）/ External World 服务——本文件 §1/§2/§3 分别是后三个的 adapter 落点。

## §6 未定项

| 未定项 | 状态 |
|---|---|
| Host 概念正式定义 | UNKNOWN（`domain-invariants.md` §3），不猜测 |
| Model 部署形态（U-5） | 当前无已定值，不预设（L4 / 部署层） |
| Research 后端选择 | 装配决定（`spec-composition-root.md` §4）；具体后端未定，不预设 |
