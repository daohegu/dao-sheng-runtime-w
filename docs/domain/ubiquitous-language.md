# Ubiquitous Language — DaoSheng V1 Domain Model

> **STEP 09 产出（2026-09-13）**。本文件是 DaoSheng V1 的统一语言表：22 个任务术语 + 1 个 Domain 增补术语（Faculty，Q3）+ STEP 05/06 恢复的辅助术语。
>
> **配套文档**：`domain-model.md`（核心概念六属性）/ `bounded-contexts.md`（四个边界）/ `domain-invariants.md`（区分与不变量）。
>
> **组织原则（用户 2026-09-13 确立，本模型的最高组织原则）**：
> Domain Model 的目标不是"把所有 UNKNOWN 消灭"，而是把**已经知道的 / 不知道的 / 历史上曾经实现过的 / 当前用户明确追认的**严格分开。DaoSheng V1 宁可保留 UNKNOWN，也不要为了形成完整模型而制造未经依据的本体定义。
>
> **权威顺序**（V1 重构治理规则）：Original Intent > Historical Decision > Validated Evidence > Implementation > Current Guess。
>
> **编号说明**：本文引用的内部编号（规则编号、材料 1/2/3、B1-E\*/B2-E\*/B3-E\*、Hermes 原则 P\*、Q\*、U-\*、K-\*/M-\*/R-\*/D-\*/C-\*/H-\*、带圈编号 ADR）为 DaoSheng V1 私有重构历史索引，其原始登记册与原文不随本副本发布，各处引用语义以行内自明为准（同 `domain-model.md` 编号说明口径）。

## 证据分类（四类信息分离的落位标签）

每个术语的定义都标注其证据分类。一个术语可同时具有多个分类的条目——这正是"严格分开"的落点。

| 标签 | 含义 | 落位 |
|---|---|---|
| `ORIGIN` | Original Intent；材料 1/2/3 原文恢复 | 材料 1/2/3 恢复记录（B1-E* / B2-E* / B3-E*；原文不随本副本发布） |
| `HISTORICAL_DECISION` | 历史材料中记录的决策（Hermes 生态） | Hermes 原则记录（P1–P23；原始登记册不随本副本发布） |
| `USER_RATIFIED` | 当前用户明确追认（2026-09-13，本 Step grilling 两轮 12 题裁定） | V1 重构历史决定记录（不随本副本发布） |
| `IMPLEMENTATION` | 历史上曾经实现过的（V0 代码投影；权威顺序最低级） | V0 审计记录（K-* / R-* / M-* / D-* / C-* / H-* 编号；不随本副本发布） |
| `LATER_INTERPRETATION` | 历史解释层（原始材料之后的派生解释，如规则 3 的 Host 定位） | 派生解释记录（原协议层记录，不随本副本发布） |
| `UNKNOWN` | 不知道；显式标注，不猜测（规则 11） | 各文档 UNKNOWN 清单 |

---

## §1 存在层

### DaoSheng（道生）

- **定义**：个体名，与项目名同词。"以道为最高设计边界、从最小完整幼体开始、在现实世界中不断经历/记忆/学习/行动/反思、逐渐形成自己能力与个体性的 AI"（非"已经成熟的超级 Agent"）。
- **证据分类**：`ORIGIN`（B1-E1，材料 1 §14）。

### Individual（个体）

- **定义**：有经历、有能力、有记忆、有连续性、有原则、能够独立行动的 AI 个体。
- **正名**：**Individual（个体）**（`USER_RATIFIED` 2026-09-13，Q4）。
- **词汇注记**："AI 个体 / 智能个体 / 数字个体"三词并存于材料 1 原文，关系 UNKNOWN——记录为 `ORIGIN` 词汇，不断言等价。
- **证据分类**：`ORIGIN`（B1-E1）+ `USER_RATIFIED`（正名）+ `UNKNOWN`（三词关系）。

### Identity（身份）

- **定义**：个体性的**载体**（`USER_RATIFIED` Q5）。`ORIGIN` 给出"同一个存在"的感觉的支撑项清单（B1-E6）：稳定的名字 / 自我称谓 / 声音 / 视觉形象 / 行为习惯 / 过去经历 / 连续记忆——清单照录为证据，不作等价或穷尽断言。
- **判据**：什么构成"仍然是谁"（身份延续判据）：`UNKNOWN`，保留不猜。
- **结构约束**：载体不得由 Model 定义（规则 2）、不得包含 Worker 身份（规则 4）；V0 `soul.py` 载体无 model/worker/host 字段，为符合约束的载体形态（`IMPLEMENTATION`，K-11）。
- **证据分类**：`ORIGIN`（支撑项清单，B1-E6）+ `USER_RATIFIED`（载体定位）+ `UNKNOWN`（延续判据）。

### Continuity（连续性）

- **定义**：个体**跨时间的持续属性**，即"同一个存在"在时间上成立的条件（`USER_RATIFIED` Q5，独立一等概念，不是 Identity 的属性字段）。与 Memory 双轨（连续记忆 = 支撑项之一）定义关联。
- **实现残留**：V0 五处建模（C-1…C-5：`state.last_action_experience_id` / `state.turn` / `soul.continuity_revision` / MemoryItem `kind="continuity"` / faculties "continuity" 根）= `IMPLEMENTATION` 残留，不构成 Domain 定义（规则 1）；收敛方向 = 单一载体，**具体归属待 ADR**（life 层归属 ADR 联动）。
- **证据分类**：`USER_RATIFIED`（概念独立性）+ `IMPLEMENTATION`（五处残留记录）+ `UNKNOWN`（单一载体归属）。

### Doctrine（教义 / 原则）

- **定义**："道"原则的**当前成文子集**；"道" ≠ 这 6 条；可增补（`USER_RATIFIED` Q1）。
- **"道"定位**（`ORIGIN`，B1-E9）：最高层的范围与约束——如何成长 / 哪些行为不应发生 / 何时行动 / 如何面对失败与力量 / 与环境的关系；不是人设 / Prompt / 宗教装饰；**具体内容 UNKNOWN**。
- **当前成文内容**：V0 doctrine 6 条（不妄动 / 知止 / 顺势 / 反思 / 海纳百川 / 道心稳固，`core/doctrine.py`）= `IMPLEMENTATION`（V0 首创）+ `USER_RATIFIED`（2026-09-13 追认为初始成文内容）。decision.py 7 条 / reflection.py 20 条 = 实现投影（双维护，D-6），**非追认对象**。
- **内容追认已完成（本 Step）；单一来源放哪 = 架构决定**（ADR ④ 顺延）。
- **证据分类**：`ORIGIN`（"道"定位）+ `IMPLEMENTATION` + `USER_RATIFIED`（6 条）+ `UNKNOWN`（"道"具体内容）+ 待 ADR（单一来源位置）。

## §2 记忆与认知层

### Experience（经历）

- **定义**：发生于个体经历中的事情全体（`USER_RATIFIED` Q9），包括外部事件与内部过程；不被 Observation / Action 穷尽。
- **ORIGIN 支撑**：初步循环（B1-E12）核心 = "经历事情"，不是"回答问题"。
- **关联**：全量经历 = 其存储形态，与长期记忆双轨分开（B1-E4）；"聊天记录不等于记忆"。
- **证据分类**：`ORIGIN`（B1-E12）+ `USER_RATIFIED`（定义措辞）。

### Understanding（理解）

- **定义**：个体从经历中形成的内部理解（`USER_RATIFIED` Q7；`ORIGIN`：B1-E12 初步循环"内部理解"环节——是理解，不是"回答"）。
- **形成路径**：Research = Understanding 的形成路径之一（`USER_RATIFIED` Q11，不占独立术语）；"观察 ≠ 判断"纪律随迁（K-08）。
- **证据分类**：`ORIGIN`（B1-E12）+ `USER_RATIFIED`。

### Memory（记忆）

- **双轨**（`ORIGIN`，B1-E4）：全量经历 = 历史档案（"保存全部"）；长期记忆 = 记性（"记住什么"）；"聊天记录不等于记忆"；管线：经历 → 消化 → 提取 → 记忆 → 复用；遗忘是结构性组成（**机制与判据 UNKNOWN**）。
- **DaoSheng Memory Ontology 基础**（`USER_RATIFIED` Q2）：V0 MemoryItem 三维语义层追认为基础——`memory_origin`（canonical/derived/external/echo）× `memory_status`（observed/reported/verified）× `memory_confidence`（confirmed/supported/uncertain）+ 修正引用键；provenance 枚举已中性化（host 名 `hermes_desktop` 推断行剔除，H-4）。
- **边界**：Memory Provider（Hindsight 等）不得定义 DaoSheng Memory Ontology（规则 5）。
- **证据分类**：`ORIGIN`（双轨/管线）+ `USER_RATIFIED`（三维语义层）+ `UNKNOWN`（消化/遗忘机制与判据）。

### Insight（洞见）

- **定义**：从经历中提取的规律性认识，可被 Verification 检验、被 Correction 修正（`IMPLEMENTATION` V0 首创 + `USER_RATIFIED` 2026-09-13，Q7）。
- **边界（用户明确）**：Insight ≠ Truth（是当前认识，不是绝对事实）；Insight ≠ Identity；Insight ≠ Doctrine。
- **表征**：单一表征形式（一类 Memory vs 独立实体）= 架构决定（R-03，待 ADR / 架构 Step）。
- **证据分类**：`IMPLEMENTATION` + `USER_RATIFIED` + `UNKNOWN`（表征形式）。

## §3 成长与行动层

### Growth（成长）

- **判据**（`ORIGIN`，B1-E5）："成长不只是增加知识，而是过去的经历能够改变未来的行为"；判据："经历最终能够改变这个个体"；Memory / Reflection 不是终点。
- **成长链**（`ORIGIN`，B1-E8）：学习知识 → 形成经验 → 掌握技能 → 形成习惯 → 形成个性 → 形成自我理解。
- **子方面**（`USER_RATIFIED` Q11，不占独立术语）：习惯 / 个性 / 自我理解 = Growth 的子方面；反思 = Growth / 初步循环中的过程，由 Faculty 的 reflection 根支撑。
- **证据分类**：`ORIGIN` + `USER_RATIFIED`（子方面归位）。

### Capability（能力）

- **定义**：个体后天修成的"术"（`ORIGIN`，B1-E7）；Skill 作为手段"规定能力与使用方式"（B1-E3）。
- **生命周期**：四目录形态 proposed / working / active / retired = `IMPLEMENTATION`（V0 首创，K-04/K-06）；**正式生命周期状态机 = 待 ADR 追认**（ADR ② 顺延）；纪律：未经验证的能力绝不能进入 active（K-04，与 Verification 原则联动）。
- **证据分类**：`ORIGIN`（"术"定位）+ `IMPLEMENTATION`（四目录）+ 待 ADR（生命周期追认）。

### Action（行动）

- **定义**：个体**作用于世界的输出环节**（`USER_RATIFIED` Q9）；`ORIGIN` 支撑：B1-E12 初步循环"行动/模仿/尝试"（内部 → 世界）。
- **关联**：行动本身也是经历（B1-E5）；反馈 = Action 后的世界回应（子环节，`USER_RATIFIED` Q9/Q11，不升格为独立术语）。
- **证据分类**：`ORIGIN`（B1-E12）+ `USER_RATIFIED`（定义措辞）。

### Observation（观察）

- **定义**：个体**从世界接收输入的环节**（`USER_RATIFIED` Q9）；`ORIGIN` 支撑：B1-E12 初步循环"感知/摄取"（世界 → 内部）。
- **注**：V0 `observe()` 语义掏空、真实回合在 `act()`（R-01）= 实现层入口分裂（`IMPLEMENTATION`），不影响 Domain 定义。
- **证据分类**：`ORIGIN`（B1-E12）+ `USER_RATIFIED`（定义措辞）。

### Correction（修正）

- **定义**：个体对自身已有行为、理解、Insight、记忆记录等进行**重新审视、修正或撤销**（`USER_RATIFIED` Q10）。不限定任何实现机制。
- **Domain / Implementation 分界（用户明确）**：其中可以包含对 Memory Record 的更正；**"记忆是否可更正"属于 Domain（可以）**；具体如何保留旧版本、追踪修订历史属于 Implementation。
- **与 Verification 的区别（用户措辞）**：Correction = 我发现自己原来有问题，因此修正自己（事后、自我驱动）。
- **证据分类**：`USER_RATIFIED`（定义）；`ORIGIN` 原始支撑：B1-E12"反思 → 改变行为"。

### Verification（验证）

- **定义**：个体在**接受某项能力、认识、记忆或结论为可信之前**，对其依据与可靠性进行检验的过程（`USER_RATIFIED` Q10，提升为 Domain 原则）。
- **适用范围**：Capability、Insight、Memory 都可以存在 Verification。
- **Domain / Implementation 分界（用户明确）**："active" / "可信记忆"等具体状态与流程属于 Implementation，不写死进 Domain Definition。
- **与 Correction 的区别（用户措辞）**：Verification = 在接受某项东西之前，我要求它具有足够依据（事前、依据驱动）。
- **历史形态**（`IMPLEMENTATION`）：V0 三处——Verifier 执行前闸门（K-05）/ `verify_insight` / MemoryItem 修正字段；legacy `verify()` 与新架构不一致（D-03）。
- **证据分类**：`USER_RATIFIED`（Domain 原则）+ `IMPLEMENTATION`（历史形态记录）。

## §4 外部手段层（External Means）

> 本层所有术语的共同定位（`ORIGIN`，B1-E13）："这些都不是'DaoSheng 本身'，只是 DaoSheng 可以拥有和使用的东西"（"它们不再定义 DaoSheng，只是成为未来可以使用的实现手段"）。各自拥有独立的外部语义，**统一领域边界/分类，不是单一模型**（Q12）。

### Model（模型）

- **定义**：实现手段，负责理解 / 判断 / 调度 / 交互（`ORIGIN`，B1-E3）；"Agent 的能力不应全部来自模型参数"（B1-E3）。
- **约束**：Model 不得定义 DaoSheng、不得定义 Identity（规则 2）。**LLM ≡ Model**（任务文本 "LLM" 与项目术语 Model 为同一区分，见 `domain-invariants.md` §1）。
- **部署关系**：V0 默认 gpt-oss:20b（Worker A）与材料 2 A1（Qwen3.5-9B）并存，关系 UNKNOWN（U-5）。
- **证据分类**：`ORIGIN`（分工）+ `UNKNOWN`（部署关系）。

### Skill（技能）

- **定义**：手段，规定能力与使用方式（`ORIGIN`，B1-E3）；DaoSheng 化解读："个体后天修成的'术'"（B1-E7）→ 对应 Domain 概念 **Capability**。
- **区分**：Skill != DaoSheng（B1-E13）；Skill（手段）≠ Capability（个体之"术"，Domain 概念）。
- **证据分类**：`ORIGIN`。

### Helper（助手）

- **定义**：手段，确定性的具体执行（`ORIGIN`，B1-E3）。
- **历史决策**（`HISTORICAL_DECISION`）：Hermes P4 定义；P10 好 Helper 的七特征；P11 复杂度封装。
- **证据分类**：`ORIGIN` + `HISTORICAL_DECISION`。

### Tool（工具）

- **定义**：**UNKNOWN**（`USER_RATIFIED` Q6 决定保持 UNKNOWN）。材料 1/2/3 未作为独立概念讨论（仅泛指"工具"）。
- **约束**：引入 Domain 须 ADR（规则 8）；不得由 V0 / Hermes 实现反向定义（规则 1）。
- **定位参考**（`HISTORICAL_DECISION`，仅定位非定义）：Hermes P20 "MCP = 工具层的控制桥梁"；P21 "Skill 解决怎么思考，MCP 解决怎么执行"。
- **证据分类**：`UNKNOWN`（独立概念定义）+ `HISTORICAL_DECISION`（定位参考）。

### MCP（Model Context Protocol）

- **定义**：手段，负责连接外部工具与环境（`ORIGIN`，B1-E3）。
- **历史决策**（`HISTORICAL_DECISION`）：P20 工具层控制桥梁；P21 "Skill 解决怎么思考，MCP 解决怎么执行"。
- **区分**：MCP != DaoSheng（B1-E13）。
- **证据分类**：`ORIGIN` + `HISTORICAL_DECISION`。

### Worker（工作者）

- **定义**：**UNKNOWN**（`USER_RATIFIED` Q6 决定保持 UNKNOWN）。材料 1/2/3 未出现此概念；唯一约束 = 规则 4"Worker 不得成为 Identity"（LATER_INTERPRETATION，原始来源 UNKNOWN）。
- **历史记录**（`IMPLEMENTATION`，非定义）：V0 Worker A = Ollama gpt-oss:20b、Worker B = 本地 Qwen3.5-9B（llama.cpp）= 两个模型后端节点（审计 M-2/M-3）。
- **Owner**：部署层。
- **证据分类**：`UNKNOWN`（领域定义）+ `IMPLEMENTATION`（V0 证据记录）。

### Hermes

- **定义**：历史本地 Agent 系统（`ORIGIN`，材料 2：本地 Hermes Agent + llama.cpp + 即时通讯渠道 — 历史事实；具体机器、实例昵称、渠道名与 Model 量化细节不在本副本公开范围）。DaoSheng 的灵感来源之一。
- **约束**：Hermes 不得定义 DaoSheng（规则 3）。
- **Host 定位**：重构路线中定位为 "Host"（`LATER_INTERPRETATION`，材料 3 07/11，B3-E6/E8）；**正式定义 UNKNOWN**；V0 代码中不存在独立 host 集成层（M-01…M-04，审计）；落地须 ADR（ADR ① 顺延）。
- **证据分类**：`ORIGIN`（历史系统）+ `LATER_INTERPRETATION`（Host 定位）+ `UNKNOWN`（Host 正式定义）。

## §5 Domain 增补术语（22 项之外，grilling 裁定新增）

### Faculty（才能根）

- **定义**：个体先天的行为倾向（`IMPLEMENTATION` V0 首创 + `USER_RATIFIED` 2026-09-13，Q3 纳入 Domain 概念）。
- **初始集**（`USER_RATIFIED`，8 根）：intent / choice / stopping / observation / correction / selection / reflection / continuity——标注"V0 首创 + 用户追认，非 ORIGIN"。
- **关联**：与 Doctrine 语义联动（stopping ↔ 知止）；根的增减 = Domain 决策（单一来源方向 R-06）；continuity 根的归属随 Continuity 归属 ADR 联动。
- **证据分类**：`IMPLEMENTATION` + `USER_RATIFIED`。

## §6 辅助术语（STEP 05/06 恢复，出处材料 1/2/3 恢复记录）

| 术语 | 定义 | 出处 |
|---|---|---|
| 幼体 | "完整但未成熟"：基本结构完整，能力尚未展开；非"什么都不会的弱模型" | B1-E8（§7） |
| 最小完整体 | 发展方法：先创造最小完整体，不先堆功能/知识/人格/工具；"道生一……"仅作从少到多的发展方式，不作工程架构解释 | B1-E10（§9） |
| 初步循环 | 世界 → 感知/摄取 → 内部理解 → 行动/模仿/尝试 → 反馈 → 记忆 → 反思 → 改变行为 → 再次进入世界；核心 = "经历事情"，不是"回答问题" | B1-E12（§11） |
| 道 | 见 Doctrine 条目（"道"定位部分）；具体内容 UNKNOWN | B1-E9（§8） |
| 道士（文化原型） | "理想化的完整个体"（隐世/下山/观察/学习/修行/多种术/行为原则/随经历成长）；只是"文化原型"，不是定义；明确排除宗教义 | B1-E7（§6） |
| 双轨 | 全量经历（历史档案）vs 长期记忆（记性）；见 Memory 条目 | B1-E4（§3） |
| Hindsight | Memory Provider 历史实例（本地长期记忆服务器；retain/recall；部署手册 v1.0，2026-07-25）；不得定义 DaoSheng Memory Ontology（规则 5） | B2-E12（材料 2 篇四） |
| Hermes 实例命名 | Hermes Agent 曾以稳定实例名运行（具体实例昵称不在本副本公开范围）；历史先例：稳定名字/声音/视觉形象/自我概念；不得反推 DaoSheng 定义（规则 3） | B2-E16（材料 2 篇五） |
| Memory Provider | 提供记忆实现的组件（Hindsight 为历史实例）；独立于 DaoSheng Memory Ontology（规则 5） | B1-E4、B1-E13 |

## §7 术语扩展规则（Q11）

- 当前统一语言 = 22 个任务术语 + Faculty（§5）+ 辅助术语（§6）。
- 22 术语之外的子词当前**全部**作为父概念的子方面、环节或形成路径记录，不占独立词条：
  - 习惯 / 个性 / 自我理解 → Growth 的子方面
  - 反思 → Growth / 初步循环中的过程，同时由 Faculty 的 reflection 根支撑
  - 反馈 → Action 后的世界回应
  - Research → Understanding 的形成路径之一
- **未来只有在建模、推理或实现中证明其必须拥有独立语义边界时，才重新进入术语扩展**（用户 2026-09-13 原话）。

## §8 术语索引（速查）

| # | 术语 | 层 | 证据分类概要 |
|---|---|---|---|
| 1 | DaoSheng | 存在 | ORIGIN |
| 2 | Individual | 存在 | ORIGIN + 追认（正名）+ UNKNOWN（三词关系） |
| 3 | Identity | 存在 | ORIGIN（支撑项）+ 追认（载体定位）+ UNKNOWN（判据） |
| 4 | Continuity | 存在 | 追认（独立概念）+ IMPLEMENTATION（五处残留）+ UNKNOWN（归属） |
| 5 | Doctrine | 存在 | ORIGIN（道定位）+ 追认（6 条）+ UNKNOWN（道内容）+ 待 ADR（单一来源） |
| 6 | Experience | 认知 | ORIGIN + 追认 |
| 7 | Understanding | 认知 | ORIGIN + 追认 |
| 8 | Memory | 认知 | ORIGIN（双轨）+ 追认（三维语义）+ UNKNOWN（消化/遗忘） |
| 9 | Insight | 认知 | IMPLEMENTATION + 追认 + UNKNOWN（表征） |
| 10 | Growth | 行动/成长 | ORIGIN + 追认（子方面） |
| 11 | Capability | 行动/成长 | ORIGIN（术）+ IMPLEMENTATION（四目录）+ 待 ADR |
| 12 | Action | 行动/成长 | ORIGIN + 追认 |
| 13 | Observation | 行动/成长 | ORIGIN + 追认 |
| 14 | Correction | 行动/成长 | 追认（不限实现机制） |
| 15 | Verification | 行动/成长 | 追认（Domain 原则）+ IMPLEMENTATION（历史形态） |
| 16 | Hermes | 外部手段 | ORIGIN（历史）+ LATER_INTERPRETATION（Host）+ UNKNOWN（正式定义） |
| 17 | Model | 外部手段 | ORIGIN（分工）+ UNKNOWN（部署关系） |
| 18 | Worker | 外部手段 | UNKNOWN（定义）+ IMPLEMENTATION（V0 记录） |
| 19 | Skill | 外部手段 | ORIGIN |
| 20 | Helper | 外部手段 | ORIGIN + HISTORICAL_DECISION |
| 21 | Tool | 外部手段 | UNKNOWN（独立概念）+ HISTORICAL_DECISION（定位） |
| 22 | MCP | 外部手段 | ORIGIN + HISTORICAL_DECISION |
| 23 | Faculty | 增补 | IMPLEMENTATION + 追认 |
