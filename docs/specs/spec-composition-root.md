# V1 Spec — Composition Root（spec-composition-root）

> **STEP 13 产出（2026-09-13）**。固化对象：装配点职责、"道"文本运行时单一来源注入、Model 配置声明、host 关系声明位。
>
> 公开源文档（随本副本发布，可公开核验，冲突时规格服从）：`docs/architecture/component-model.md` §1、ADR 0002/0004/0005、`docs/constitution/constitution.md` §2/§6、`docs/constitution/principles.md`、ADR 0001（原头部标注「U-5 关联」，该关联不可核验，见下方 REVIEW）。
>
> 私有历史来源（历史证据标签，原始登记册与原文不随本副本发布，不构成公开用户必须服从的权威依据）：`docs/audit/` R-09 / M-04 / M-05 / M-6 / M-1…M-3 / R-12 / D-6 / D-05 / K-11（K-\* / R-\* / M-\* / D-\* 口径同 `docs/constitution/invariants.md` §3）；U-5（U-\* → `RECONSTRUCTION.md` Open Questions，同 `domain-invariants.md` §3 口径）；Q1、规则 11（Q\* / 规则编号为私有历史追认 / 工程规则编号，公开对应口径见下方编号说明）。
>
> 编号说明：上述私有历史编号的语义以本文件及其他公开正文行内自明，并可在公开文档中核验（同 `docs/constitution/invariants.md` 编号说明与 §3、`domain-model.md` / `ubiquitous-language.md` / `bounded-contexts.md` 编号说明口径）：R-09（accept dependencies, don't create them）——`data-ownership.md` §2、`component-model.md` §1/§4；M-04（host 身份宣称文本只在 composition root 声明位，不进 Core 文本）——`data-ownership.md` §2、ADR 0002 决定 4、`component-model.md` §5；M-05 / D-6（doctrine 三处 6 / 7 / 20 双维护漂移）——`data-ownership.md` §2、`constitution.md` §6、`constitution/invariants.md` CINV-5、`bounded-contexts.md` §5 ADR ④；M-1…M-3 / M-6（Model 泄漏族：默认值 / 端点 / 硬建后端移装配点；与 M-01…M-05 host 族为两套独立编号族）——`data-ownership.md` §2、`bounded-contexts.md` §6 #1、`component-model.md` §1/§4；R-12（投影不回流；host 关系表述不进 Core 文本）——`domain-invariants.md` INV-7、`data-ownership.md` §2/§3、ADR 0002 决定 4/5；D-05（症状级清洗在 R-12 根因修复前不得删除的硬性顺序）——INV-7、ADR 0002 决定 5；K-11（V0 `protected_fields` 历史形态）——`constitution.md` §1/§3、`data-ownership.md` §1/§3、`constitution/invariants.md` CINV-2/CINV-3；U-5（Model 部署形态 UNKNOWN，不预设）——`data-ownership.md` §2、`domain-invariants.md` §3、`ubiquitous-language.md` 部署关系条目；Q1（六条 = 成文子集追认）——`constitution.md` §1、`constitution/invariants.md` CINV-1、`bounded-contexts.md` §5 ADR ④；规则 11（UNKNOWN 不得猜测）——`domain-invariants.md` INV-15。编号保留、归属不裁定、不编造映射、不声称已核验私有原文。
>
> REVIEW：原头部将 ADR 0001 标注「（U-5 关联）」。ADR 0001 公开全文（Memory 持久化：embedded SQLite / WAL / FTS5）未提及 U-5；U-5 的公开行内语义可在 `data-ownership.md` §2、`domain-invariants.md` §3、`ubiquitous-language.md` 等处核验，但「ADR 0001 ↔ U-5」关联在公开文档中不可核验——标签保留、关联不裁定。已解决（2026-10-14）：此前记录的映射差异——`spec-index.md` §1 未将 ADR 0002 列入本文件公开源列，而本文件正文 §3 实际引用 ADR 0002 决定 4——已由索引更新解决：当前索引 §1 已将 ADR 0002 纳入本文件公开源列（ADR 0002/0004/0005）。
>
> 与上述公开源文档冲突时以公开源文档为准（`spec-index.md` §1 口径，限随本副本实际发布的文档）；私有历史编号不作为公开读者必须服从的权威依据。公开文档之间的真实冲突不由本规格裁定：标记 REVIEW。

## §1 装配点职责

源：`component-model.md` §1、R-09、ADR 0004 决定 1。

- **无调用方的装配点**：composition root 是 V1 唯一的装配位——把 Individual 及其全部依赖（Growth / Memory Provider / Capability Manager / Faculties 状态 / host 集成 adapter / Model adapter / Research adapter）在此处构造并注入。
- **依赖装配（R-09：accept don't create）**：Individual 及其内部组件全部**构造注入**（`spec-individual.md` §6）；任何组件不自建依赖。
- **不设独立 life 层**（ADR 0004 决定 1）：回合机制归 Individual；host 会话归 host 集成 adapter 层（`spec-adapters.md` §1）——装配点不为此引入中间层。
- L4 运营策略的具体参数（调度频率、上限值等）的默认值在此声明（`principles.md` 四层模型 L4）——属运营策略，不是 Domain 决定。

## §2 "道"文本运行时单一来源注入

源：ADR 0005、M-05、D-6、CINV-1/CINV-2、Q1。

- **设计层成文单一来源 = `docs/constitution/principles.md`**（`constitution.md` §6）。运行时**不得**再有任何第二成文来源。
- **注入形态**：从 `principles.md` 注入**只读来源**，经 typed 投影形态进入运行时（V0 `doctrine.py` frozen dataclass 形态为参考——仅参考，非 KEEP 依据）；运行时唯一副本。
- **投影纪律**（M-05 / D-6：V0 doctrine 6 / decision 7 / reflection 20 三处漂移）：投影可裁剪、可改写措辞，**不得另立来源**（`spec-individual.md` §5.2）。
- **变更边界**：Core Doctrine `immutable`（K-11；V1 不得弱化）；变更**仅设计层**（CINV-2 / `constitution.md` §3）——运行时任何路径不得改写（CINV-2）。
- **边界提醒**：六条 = 当前**成文子集**（Q1），可增补非全部（CINV-1）；"道"的具体内容 = **UNKNOWN**（CINV-1 / `domain-invariants.md` §3）——本规格只固化注入纪律，不定义"道"内容。

## §3 Model 配置声明 与 host 关系声明位

源：R-09、M-1…M-6、M-04、ADR 0002 决定 4。

- **Model 配置声明**：Model 调用 adapter 的默认值（M-1…M-3：端点 / 超时 / 重试参数）与后端选择（Research 后端 M-6）在此声明——adapter 不自带默认值（`spec-adapters.md` §2/§3）。部署形态 = UNKNOWN（U-5），声明的具体值由部署层在实现阶段给出，不预设。
- **host 身份宣称文本（M-04）= 声明位**：V0 中身份宣称文本出现在 `context_for_turn` / `app.py`（M-04）；V1 中"DaoSheng 与 host 的关系"的表述**只出现在本装配点的声明位**（ADR 0002 决定 4；R-12），不进入 Core 生成的任何文本（`spec-individual.md` §5.1）。
- **D-05 顺序约束**：R-12 根因修复（本节声明位建立）完成之前，症状级清洗函数不得删除（INV-7 硬性顺序，`spec-adapters.md` §1）。

## §4 未定项

| 未定项 | 状态 |
|---|---|
| Model 部署形态与具体配置值（U-5） | 当前无已定值，不预设（L4 / 部署层） |
| Research 后端具体选择 | 装配决定；未定，不预设（`spec-adapters.md` §3） |
| "道"具体内容 | UNKNOWN（CINV-1），不猜测（规则 11） |
