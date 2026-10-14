# Bounded Contexts — DaoSheng V1 四个边界

> **STEP 09 产出（2026-09-13）**。本文件建立 DaoSheng V1 Domain Model 的边界结构：**一个核心上下文 + 三个外部边界**（外部手段层 / Host / Memory Provider），以及上下文间纪律。
>
> **术语说明**："边界 / bounded context" = 领域建模意义上的统一语言与归属范围；**seam** 是边界在实现层的落位（接口位置），具体 seam 设计属架构 Step，本文件不决定。
>
> **组织原则（用户 2026-09-13 确立）**：把**已经知道的 / 不知道的 / 历史上曾经实现过的 / 当前用户明确追认的**严格分开。宁可保留 UNKNOWN，也不制造未经依据的本体定义。
>
> **编号说明**：正文出现的内部编号（规则 1–5 / 7 / 8 / 9 / 11、材料 2/3、B1-E\*/B2-E\*/B3-E\*、Hermes 原则 P\*、Q\*、K-\*、M-\*、R-\*、D-\*、C-\*、H-\*、ADR ①–④）为 DaoSheng V1 私有重构历史索引，其原始登记册与原文不随本副本发布，各处引用语义以行内自明为准（同 `domain-model.md` / `ubiquitous-language.md` 编号说明口径）。

---

## §1 总览 — 边界地图

| # | 边界 | 性质 | Owner | 状态 |
|---|---|---|---|---|
| 1 | **核心上下文（DaoSheng 个体）** | Domain 核心：Individual 及其 Identity / Continuity / Doctrine / Experience / Understanding / Memory（Ontology）/ Insight / Growth / Capability / Action / Observation / Correction / Verification / Faculty | 个体自身 | 本 Step 确立（定义见 `domain-model.md`） |
| 2 | **外部手段层（External Means）** | 统一领域边界/分类（Q12）：Model / Skill / Helper / Tool / MCP / Worker；各自拥有独立外部语义，**不是单一模型** | 部署层 | 本 Step 确立（§2） |
| 3 | **Host（未来）** | 核心与外部手段 / 历史系统之间的集成层 | 未定（ADR ①） | 仅定位（`LATER_INTERPRETATION`），正式定义 UNKNOWN（§3） |
| 4 | **Memory Provider** | 记忆管线的外部实现上下文（retain / recall） | 部署层 | 边界确立；Ontology 归属核心（§4） |

**总原则**：外部上下文经 **seam** 与核心关联，**不合并**——核心定义语义，外部提供手段 / 实现；外部语义不得渗入核心定义（§6）。

---

## §2 外部手段层（统一分类，不是单一模型）

- **共同定位**（`ORIGIN`，B1-E13）："这些都不是'DaoSheng 本身'，只是 DaoSheng 可以拥有和使用的东西"（"它们不再定义 DaoSheng，只是成为未来可以使用的实现手段"）。
- **Q12 裁定**（`USER_RATIFIED` 2026-09-13）：外部手段层是**统一的领域边界 / 分类**；每个手段拥有**独立的外部语义**；手段层整体**不是单一模型**——不为它制造统一的"手段本体"。
- **成员与语义来源**（定义详情见 `ubiquitous-language.md` §4）：

  | 成员 | 外部语义 | 来源 |
  |---|---|---|
  | Model | 理解 / 判断 / 调度 / 交互；LLM ≡ Model | B1-E3 |
  | Skill | 规定能力与使用方式；手段层 Skill **instantiates** Domain 概念 Capability | B1-E3；B1-E7（"术"解读） |
  | Helper | 确定性的具体执行 | B1-E3；P4 / P10 / P11（`HISTORICAL_DECISION`） |
  | Tool | 定义 **UNKNOWN**（Q6 保持 UNKNOWN）；引入须 ADR（规则 8） | —；定位参考 P20 / P21 |
  | MCP | 连接外部工具与环境；"Skill 解决怎么思考，MCP 解决怎么执行"（P21 定位） | B1-E3；P20 / P21 |
  | Worker | 定义 **UNKNOWN**（Q6 保持 UNKNOWN）；V0 Worker A / B 节点 = 历史记录，非定义 | —；IMPLEMENTATION 记录 |

- **Hermes 不属手段层**：历史系统（`ORIGIN`，材料 2），其 "Host" 定位指向未来的独立上下文（§3），不是第 7 个手段。
- **与核心的关系**：个体"可以拥有和使用"手段（B1-E13）；手段可替换、个体不变；任何手段不得定义个体（规则 2 / 3 / 4，`domain-invariants.md` §1 / §2）。

## §3 Host（未来独立上下文）

- **定位**：核心上下文与外部手段 / 历史系统之间的集成层。定位来源 = `LATER_INTERPRETATION`（材料 3 07/11 "Host" 定位，B3-E6 / E8）；**正式定义 UNKNOWN，不猜测（规则 11）**。
- **Hermes（历史系统）≠ Host（未来上下文）**：Hermes 是冻结的 Historical Experience（规则 7；原始材料只读，原文不随本副本发布）；未来 host 集成层的建立是架构决定，不是 Hermes 机制的移植（规则 3）。
- **V0 证据**（`IMPLEMENTATION`，STEP 08 审计）：V0 代码中**不存在独立 host 集成层**——`growth/hermes_import.py`（M-01，842 行，依赖 Hermes `messages` 表 schema）/ `life/bridge.py`（M-02，Hermes Desktop subprocess）/ `sync_hermes()` + `_state_db_path` 三位置 fallback + `source="hermes:"` 前缀（M-03）/ host 身份宣称注入（M-04，prompt 注入的 host 身份宣称，原文不在本副本公开范围）分散于 `growth/` / `life/` / `app.py`。审计统一观察：**V0 缺的不是这几段代码的改写，而是一个 host 集成层的存在**（私有重构历史审计，原文不随本副本发布；收敛方向见 ADR 0002）。
- **ADR 之前不把 host 定义写入 Domain**（Q8：Architecture ADR 不在 Domain Model 中提前解决）。
- **未决**：ADR ① host 集成层建立（M-01…M-04），含 Host 正式定义与"DaoSheng 与 host 的关系"表述 → §5。

## §4 Memory Provider（外部实现上下文）

- **性质**：为记忆管线提供 retain / recall 实现的外部实现组件。历史实例：Hindsight（本地长期记忆服务器，部署手册 v1.0，B2-E12；`HISTORICAL_DECISION` / `IMPLEMENTATION`，**不是 V1 承诺**）。
- **边界（规则 5）**：Memory Provider **不得定义 DaoSheng Memory Ontology**。Ontology Owner = 个体（核心上下文）；Provider Owner = 部署层。
- **seam 方向**（Domain 层语义，不是接口细节）：
  - **核心定义语义**：双轨（全量经历 / 长期记忆，B1-E4）、管线（经历 → 消化 → 提取 → 记忆 → 复用）、三维语义层 `memory_origin × memory_status × memory_confidence` + 修正引用键（Q2 追认；provenance 枚举中性化，host 名剔除，H-4）。
  - **Provider 提供实现**：带上述语义的记录的保存与召回。接口形式 = Implementation——V0 MemoryStore Protocol 5 方法 vs SQLiteMemory 11 方法（R-05，seam 表达不完整）是实现层问题，不影响本边界的存在与方向。
- **V1 的 Provider 选择**属外部技术选择，须 Research Evidence（规则 9），归架构 Step。
- **区分**：Memory Provider != DaoSheng Memory Ontology（任务六条区分之首，`domain-invariants.md` §1.1）。

## §5 未决边界项（待 ADR / 架构 Step，本 Step 不决定）

| # | 未决项 | 来源 | 落位 |
|---|---|---|---|
| **ADR ①** | host 集成层建立（M-01…M-04）；含 Host 正式定义、"DaoSheng 与 host 的关系"表述 | §3 V0 证据（STEP 08 审计统一观察） | ADR（`docs/adr/`） |
| **ADR ②** | Capability 四目录（proposed / working / active / retired）生命周期追认：正式生命周期状态机 | K-04 / K-06 / D-03 | ADR |
| **ADR ③** | life 层整体归属（Core vs host adapter 层）；联动 **Continuity 单一载体归属**（V0 五处 C-1…C-5 收敛为单一载体，位置未定） | R-11 / M-02 / M-03 | ADR |
| **ADR ④** | "道"原则文本单一来源位置（doctrine 6 + decision 7 + reflection 20 三处 → 单一来源）；**内容追认已在本 Step 完成（Q1），剩余为结构决定** | M-05 / D-6 | ADR |
| **R-03** | Insight 单一表征形式（一类 Memory vs 独立实体） | 私有重构历史审计 R-03 | 架构 Step |
| — | V1 是否迁移 V0 既有数据（soul.json / SQLite 记忆 / capabilities 四目录） | 私有重构历史审计 R-10（H-4 分支） | 架构 Step / 用户决策 |

> 本表是**未决项记录**，不是决定队列——本 Step 不创建任何 ADR（Q8），各项进入 Domain 须经 ADR（规则 8）或 USER_RATIFIED。

## §6 上下文间纪律（边界纪律）

1. **外部语义不得渗入核心定义**——V0 的违反 = Validated Evidence：9 处 Hermes 泄漏 H-1…H-9（如 H-2 `sync_hermes()` 在 Growth 核、H-4 host 名进 provenance 枚举）、6 处 Model 泄漏 M-1…M-6（默认值 / 端点 / 身份宣称）；V1 修复方向 R-10（prompt 中性化）/ M-01…M-04（host 层）/ H-4（provenance 中性化）（私有重构历史审计，原文不随本副本发布）。
2. **任何手段不得定义个体**（规则 2 / 3 / 4 + B1-E13）：Model / Skill / Helper / Tool / MCP / Worker / Hermes 都不是"DaoSheng 本身"；任务六条区分见 `domain-invariants.md` §1.1。
3. **记忆语义归核心，实现归 Provider**（规则 5）：Provider 不得把自身 schema / 枚举带入 Ontology。
4. **Historical Experience 冻结**（规则 7）：原始材料只读（原文不随本副本发布），不得被后续解释重写；Hermes 历史系统记录不可变，未来 Host 不是对它的改写。
5. **Implementation 不得反向定义 Domain**（规则 1）：V0 的 Continuity 五处建模、四目录形态、三维语义层等均为"历史形态"记录（`IMPLEMENTATION` 标签），不是 Domain 定义；追认须经 USER_RATIFIED（本 Step Q1–Q12 已完成的部分）或 ADR（§5 未决项）。
6. **UNKNOWN 不猜测**（规则 11）：未决边界项停留在 §5，不以 GUESS 填充。
