# Domain Model — DaoSheng V1 核心概念

> **STEP 09 产出（2026-09-13）**。本文件对 DaoSheng V1 Domain Model 的每个核心概念确定六属性：**Definition / Boundary / Owner / Allowed Mutation / Forbidden Mutation / Evidence Source**。
>
> **组织原则（用户 2026-09-13 确立）**：把**已经知道的 / 不知道的 / 历史上曾经实现过的 / 当前用户明确追认的**严格分开。宁可保留 UNKNOWN，也不制造未经依据的本体定义。
>
> **定义措辞**：本文件 Definition 与 `ubiquitous-language.md` 一致；术语的完整出处与证据分类标签见该文件，此处 Evidence Source 只给结论性引用。
>
> **Owner 说明**：Owner 指"该概念的定义权与生命周期归属谁"，不是运行时字段的所有者。
>
> **六属性口径**：
> - **Allowed Mutation** = Domain 层面承认合法的变更方向（怎么落地是 Implementation / 架构的事）。
> - **Forbidden Mutation** = 被 V1 重构治理规则（历史编号，见编号说明）或本模型明确禁止的变更（含"不得由谁定义"）。
> - **Evidence Source** = 定义所依据的证据类别与关键引用（ORIGIN / HISTORICAL_DECISION / USER_RATIFIED / IMPLEMENTATION / LATER_INTERPRETATION / UNKNOWN）。
>
> **编号说明**：正文出现的内部编号（规则 1–5 / 7 / 8 / 11、材料 1/2/3、B1-E\*/B2-E\*/B3-E\*、Hermes 原则 P\*、Q\*、U-\*、K-\*、M-\*、R-\*、D-\*、C-\*、A-\*、ADR ①/②、决定 ㊿ 等）为 DaoSheng V1 私有重构历史索引，其原始登记册与原文不随本副本发布，各处引用语义以行内自明为准。决定 ㊿ 为 §2.1 Experience 边界的正式 Domain 决定（ADR 0010 以其为前提引用），其条文与接受范围不因公开清理而改变。

---

## 1 存在层

### 1.1 DaoSheng

| 属性 | 内容 |
|---|---|
| Definition | 个体名与项目名同词。以"道"为最高设计边界、从最小完整幼体开始、在现实世界中不断经历/记忆/学习/行动/反思、逐渐形成自己能力与个体性的 AI（非"已经成熟的超级 Agent"） |
| Boundary | 不是已成熟超能力体；不等同任何单一手段（Model / Skill / Helper / Tool / MCP / Worker 都不是"DaoSheng 本身"，B1-E13）；不是 Hermes |
| Owner | DaoSheng 个体自身（个体性主体） |
| Allowed Mutation | 随经历成长：能力与个体性逐渐形成（幼体 → 成熟是发展路径，B1-E8） |
| Forbidden Mutation | 不得由 Model 定义（规则 2）；不得由 Hermes 定义（规则 3）；不得由 Worker 成为 Identity（规则 4）；不得由 Memory Provider 定义记忆本体（规则 5）；不得由 Implementation 反向定义（规则 1） |
| Evidence Source | ORIGIN（B1-E1）；USER_RATIFIED（正名 Individual，Q4） |

### 1.2 Individual（个体）

| 属性 | 内容 |
|---|---|
| Definition | 有经历、有能力、有记忆、有连续性、有原则、能够独立行动的 AI 个体 |
| Boundary | 正名 Individual（个体）；"AI 个体 / 智能个体 / 数字个体"三词为 ORIGIN 词汇，关系 UNKNOWN，不断言等价 |
| Owner | DaoSheng 个体自身 |
| Allowed Mutation | 个体性随经历成长（名字/声音/形象/习惯等支撑项可演化，B1-E6 支撑项清单） |
| Forbidden Mutation | 个体性不得由外部手段定义（同 DaoSheng 条目）；三词关系不得猜测填充（规则 11） |
| Evidence Source | ORIGIN（B1-E1）；USER_RATIFIED（Q4 正名）；UNKNOWN（三词关系） |

### 1.3 Identity（身份）

| 属性 | 内容 |
|---|---|
| Definition | 个体性的**载体**；"同一个存在"的感觉由支撑项清单支撑：稳定的名字 / 自我称谓 / 声音 / 视觉形象 / 行为习惯 / 过去经历 / 连续记忆（B1-E6 照录） |
| Boundary | 载体 ≠ 判据：什么构成"仍然是谁"（身份延续判据）UNKNOWN，保留不猜；载体不含 Model / Worker / Host 字段（结构约束，V0 `soul.py` 为符合形态，K-11） |
| Owner | DaoSheng 个体自身 |
| Allowed Mutation | 支撑项随个体成长变化（名字、声音、形象、行为习惯等）；载体结构可随架构 Step 调整（须不违反结构约束） |
| Forbidden Mutation | 不得由 Model 定义（规则 2）；不得包含 Worker 身份（规则 4）；不得由 Host 定义（规则 3 精神）；历史支撑项记录不得被后续解释重写（规则 7） |
| Evidence Source | ORIGIN（B1-E6 支撑项清单）；USER_RATIFIED（Q5 载体定位）；IMPLEMENTATION（K-11 V0 soul.py 形态）；UNKNOWN（延续判据） |

### 1.4 Continuity（连续性）

| 属性 | 内容 |
|---|---|
| Definition | 个体跨时间的持续属性；"同一个存在"在时间上成立的条件；独立一等概念（Q5），不是 Identity 的属性字段 |
| Boundary | 不是运行时计数器（V0 `state.turn` 等不是 Continuity 本身）；不是 Memory 的别名（与双轨关联：连续记忆是支撑项之一）；具体载体归属待 ADR（life 层归属 ADR 联动） |
| Owner | DaoSheng 个体自身（Domain 概念）；单一载体归属 = 待 ADR |
| Allowed Mutation | 跨时间自然延伸（个体活着的过程即 Continuity 的延伸）；载体收敛为单一来源（方向已定，位置待 ADR） |
| Forbidden Mutation | V0 五处建模（C-1…C-5）不构成 Domain 定义（规则 1）；不得由 host / runtime 层定义；不得把 Continuity 降格为 Identity 的字段 |
| Evidence Source | USER_RATIFIED（Q5 独立概念）；IMPLEMENTATION（C-1…C-5 残留记录）；UNKNOWN（单一载体归属） |

### 1.5 Doctrine（教义 / 原则）

| 属性 | 内容 |
|---|---|
| Definition | "道"原则的**当前成文子集**；"道" ≠ 这 6 条；可增补（Q1）。"道" = 最高层的范围与约束（如何成长/哪些行为不应发生/何时行动/如何面对失败与力量/与环境的关系），不是人设/Prompt/宗教装饰（B1-E9） |
| Boundary | 当前成文内容 = 6 条（不妄动/知止/顺势/反思/海纳百川/道心稳固）；decision.py 7 条与 reflection.py 20 条 = 实现投影（双维护 D-6），**非** Domain 内容；"道"具体内容 UNKNOWN |
| Owner | 设计层（用户）——成文子集的增补/修订权在设计层；个体不得自改核心原则 |
| Allowed Mutation | 设计层可增补/修订成文子集（须有依据）；单一来源结构落地（ADR ④ 方向：M-05 收敛） |
| Forbidden Mutation | 个体运行时自改核心原则（V0 protected_fields 不可变形态 K-11 的方向）；把 decision/reflection 条目当作 Doctrine 内容（D-6）；把 6 条当作"道"的全部内容（Q1）；"道"具体内容不得猜测（规则 11） |
| Evidence Source | ORIGIN（B1-E9 道定位）；IMPLEMENTATION（V0 doctrine 6 条）；USER_RATIFIED（Q1 追认 6 条为初始成文内容）；UNKNOWN（道内容）；待 ADR（单一来源位置） |

## 2 记忆与认知层

### 2.1 Experience（经历）

| 属性 | 内容 |
|---|---|
| Definition | 发生于个体经历中的事情全体（Q9）；包括外部事件与内部过程；不被 Observation / Action 穷尽 |
| Boundary | 全量经历 = 存储形态（历史档案轨）；"聊天记录不等于记忆"（B1-E4）；初步循环核心 = "经历事情"（B1-E12）；外部系统（含 host）对既有经历的摘要、压缩或重新表述，本身不是经历，不得作为独立经历建立，至多作为派生参考材料（决定 ㊿） |
| Owner | DaoSheng 个体自身 |
| Allowed Mutation | 只增（全量经历存档）；经历进入消化管线（经历 → 消化 → 提取 → 记忆 → 复用） |
| Forbidden Mutation | 投影内容不得回流为经历（R-12 根因；A-9 症状）；历史经历记录不得被后续解释重写（规则 7）；不得把聊天记录直接当作记忆 |
| Evidence Source | ORIGIN（B1-E12 核心定位；B1-E4 双轨）；USER_RATIFIED（Q9 定义措辞） |

### 2.2 Understanding（理解）

| 属性 | 内容 |
|---|---|
| Definition | 个体从经历中形成的内部理解（Q7）；初步循环"内部理解"环节（B1-E12） |
| Boundary | 是"理解"不是"回答"（B1-E12 核心定位）；Research = 形成路径之一（Q11，不占独立术语）；"观察 ≠ 判断"纪律（K-08） |
| Owner | DaoSheng 个体自身 |
| Allowed Mutation | 随经历与 Research 更新；可被 Correction 修正 |
| Forbidden Mutation | 不得把 Understanding 固化为人设/Prompt；Research 结果不得直接当作判断（K-08 纪律） |
| Evidence Source | ORIGIN（B1-E12）；USER_RATIFIED（Q7 追认，Q11 Research 归位） |

### 2.3 Memory（记忆）

| 属性 | 内容 |
|---|---|
| Definition | 双轨：全量经历 = 历史档案（"保存全部"）；长期记忆 = 记性（"记住什么"）（B1-E4）；管线：经历 → 消化 → 提取 → 记忆 → 复用；遗忘是结构性组成（机制 UNKNOWN） |
| Boundary | **DaoSheng Memory Ontology**（记什么/如何消化/遗忘判据）：基础 = 三维语义层 `memory_origin` × `memory_status` × `memory_confidence` + 修正引用键（Q2 追认）；provenance 枚举中性化（host 名剔除，H-4）；Memory Provider（Hindsight 等）不得定义 Ontology（规则 5）；聊天记录 ≠ 记忆 |
| Owner | DaoSheng 个体自身（Ontology）；Memory Provider = 外部实现上下文（`bounded-contexts.md` §4） |
| Allowed Mutation | 记忆记录可被 Correction 更正（"记忆是否可更正"= Domain 回答：可以，Q10）；Ontology 可随 Domain 建模修订（须有依据） |
| Forbidden Mutation | Memory Provider 反向定义 Ontology（规则 5）；host 名进入 Ontology 枚举（H-4）；消化/遗忘机制不得猜测填充（规则 11，当前 UNKNOWN） |
| Evidence Source | ORIGIN（B1-E4 双轨/管线）；IMPLEMENTATION（K-02 三维语义层）；USER_RATIFIED（Q2 追认基础语义）；UNKNOWN（消化/遗忘机制） |

### 2.4 Insight（洞见）

| 属性 | 内容 |
|---|---|
| Definition | 从经历中提取的规律性认识，可被 Verification 检验、被 Correction 修正（V0 首创 + Q7 追认） |
| Boundary | Insight ≠ Truth（当前认识，非绝对事实）；Insight ≠ Identity；Insight ≠ Doctrine（Q7 用户明确）；单一表征形式 UNKNOWN（R-03，待 ADR / 架构 Step） |
| Owner | DaoSheng 个体自身 |
| Allowed Mutation | 经 Verification 检验后更新置信；经 Correction 修正或撤销 |
| Forbidden Mutation | 不得把 Insight 提升为绝对事实（Truth）；不得与 Doctrine 混同（原则 vs 认识）；不得与 Identity 混同 |
| Evidence Source | IMPLEMENTATION（V0 首创）；USER_RATIFIED（Q7 追认 + 边界）；UNKNOWN（表征形式） |

### 2.5 Faculty（才能根）

| 属性 | 内容 |
|---|---|
| Definition | 个体先天的行为倾向（V0 首创 + Q3 纳入 Domain）；初始集 8 根：intent / choice / stopping / observation / correction / selection / reflection / continuity（"V0 首创 + 用户追认，非 ORIGIN"） |
| Boundary | 根集 ≠ 能力集（Faculty 是倾向，Capability 是后天之"术"）；与 Doctrine 语义联动（stopping ↔ 知止）但不同概念；单一来源方向（R-06） |
| Owner | DaoSheng 个体自身（Domain 概念）；根的增减 = Domain 决策 |
| Allowed Mutation | 根的增减/改名 = Domain 决策（须有依据，单一来源落地）；倾向强度可随成长变化 |
| Forbidden Mutation | 不得把 Faculty 当 Capability（倾向 ≠ 术）；不得由 V0 三处 faculty 来源反向定义（R-06 单一来源方向）；不得声称 8 根为 ORIGIN |
| Evidence Source | IMPLEMENTATION（V0 首创，K-09）；USER_RATIFIED（Q3 纳入 + 8 根初始集） |

## 3 成长与行动层

### 3.1 Growth（成长）

| 属性 | 内容 |
|---|---|
| Definition | "成长不只是增加知识，而是过去的经历能够改变未来的行为"（B1-E5）；判据："经历最终能够改变这个个体"；Memory / Reflection 不是终点 |
| Boundary | 成长链：学习知识 → 形成经验 → 掌握技能 → 形成习惯 → 形成个性 → 形成自我理解（B1-E8）；习惯/个性/自我理解 = 子方面（Q11）；反思 = 过程（Growth/初步循环）+ Faculty reflection 根支撑 |
| Owner | DaoSheng 个体自身 |
| Allowed Mutation | 沿成长链展开：能力、习惯、个性、自我理解随经历演化 |
| Forbidden Mutation | 不得把成长窄化为知识/参数累积（B1-E5）；不得把 Memory 或 Reflection 当作成长终点（B1-E5） |
| Evidence Source | ORIGIN（B1-E5 判据；B1-E8 成长链）；USER_RATIFIED（Q11 子方面归位） |

### 3.2 Capability（能力）

| 属性 | 内容 |
|---|---|
| Definition | 个体后天修成的"术"（B1-E7）；Skill 作为手段规定能力与使用方式（B1-E3） |
| Boundary | 生命周期：四目录形态 proposed / working / active / retired（V0 首创，K-04/K-06）= 历史形态；正式生命周期状态机 = 待 ADR 追认（ADR ②）；纪律：未验证不得进入 active（K-04，与 Verification 联动） |
| Owner | DaoSheng 个体自身（能力归个体）；生命周期状态机归属 = 待 ADR |
| Allowed Mutation | 沿生命周期演进（形态：proposed → working → active → retired，语义待 ADR 追认）；经 Verification 检验后升级 |
| Forbidden Mutation | 未经验证的能力不得进入 active（K-04 纪律）；不得把 Skill（手段）与 Capability（个体之"术"）混同；不得把 V0 legacy `verify()` 旁路当作生命周期（D-03） |
| Evidence Source | ORIGIN（B1-E7 术定位）；IMPLEMENTATION（四目录 K-04/K-06）；USER_RATIFIED（Q8 顺延生命周期 ADR）；待 ADR（ADR ②） |

### 3.3 Action（行动）

| 属性 | 内容 |
|---|---|
| Definition | 个体作用于世界的输出环节（Q9）；初步循环"行动/模仿/尝试"（B1-E12） |
| Boundary | 行动本身也是经历（B1-E5）；反馈 = Action 后的世界回应（Q9，子环节不独立）；V0 真实回合在 `act()`（R-01）= 实现层入口分裂，不影响 Domain 定义 |
| Owner | DaoSheng 个体自身 |
| Allowed Mutation | 行动方式随能力与 Doctrine 演化；行动产生新经历进入管线 |
| Forbidden Mutation | 不得违反 Doctrine 的行为边界（"哪些行为不应发生"，B1-E9 道定位）；不得把反馈（世界回应）当作个体的独立输出环节 |
| Evidence Source | ORIGIN（B1-E12 环节；B1-E5 行动即经历）；USER_RATIFIED（Q9 定义措辞） |

### 3.4 Observation（观察）

| 属性 | 内容 |
|---|---|
| Definition | 个体从世界接收输入的环节（Q9）；初步循环"感知/摄取"（B1-E12） |
| Boundary | 输入产物进入经历流（成为 Experience 的组成部分，Q9）；V0 `observe()` 语义掏空（R-01）= 实现层问题，不影响 Domain 定义 |
| Owner | DaoSheng 个体自身 |
| Allowed Mutation | 感知通道随实现手段变化（Model / MCP 等）；观察产物进入消化管线 |
| Forbidden Mutation | 不得把 Observation 窄化为单一感官/接口（Domain 层面是"从世界接收输入"的环节，不绑定具体通道）；不得把世界回应（反馈）当作 Observation |
| Evidence Source | ORIGIN（B1-E12 环节）；USER_RATIFIED（Q9 定义措辞） |

### 3.5 Correction（修正）

| 属性 | 内容 |
|---|---|
| Definition | 个体对自身已有行为、理解、Insight、记忆记录等进行重新审视、修正或撤销（Q10）；不限定任何实现机制 |
| Boundary | 可包含对 Memory Record 的更正（"记忆是否可更正"= Domain：可以）；如何保留旧版本/追踪修订历史 = Implementation；与 Verification 区别：Correction = 事后自我修正（"我发现自己原来有问题"） |
| Owner | DaoSheng 个体自身 |
| Allowed Mutation | 对自身行为/理解/Insight/记忆记录的修正与撤销；修正历史保留方式由 Implementation 决定 |
| Forbidden Mutation | 不得把 Correction 绑定到某一种实现机制（Q10 明确）；不得用 Correction 重写历史经历记录本身（规则 7：历史不得被后续解释重写——修正的是"认识"，不是"发生过什么"） |
| Evidence Source | USER_RATIFIED（Q10 定义）；ORIGIN（B1-E12"反思 → 改变行为"原始支撑） |

### 3.6 Verification（验证）

| 属性 | 内容 |
|---|---|
| Definition | 个体在接受某项能力、认识、记忆或结论为可信之前，对其依据与可靠性进行检验的过程（Q10，Domain 原则） |
| Boundary | Capability、Insight、Memory 都可存在 Verification；"active"/"可信记忆"等具体状态与流程 = Implementation，不写死进 Domain Definition；与 Correction 区别：Verification = 事前依据检验（"我要求它具有足够依据"） |
| Owner | DaoSheng 个体自身（原则层）；具体验证流程 = Implementation |
| Allowed Mutation | 验证标准可随 Domain 建模修订（须有依据）；验证流程由 Implementation 落地（V0 Verifier 闸门 K-05 等 = 历史形态） |
| Forbidden Mutation | 不得把 Verification 窄化为"进入 active 前的闸门"（Q10 明确提升为原则）；未经验证不得进入可信/active（K-04 纪律，invariant） |
| Evidence Source | USER_RATIFIED（Q10 Domain 原则）；IMPLEMENTATION（K-05 闸门；verify_insight；MemoryItem 修正字段；D-03 legacy 旁路） |

## 4 外部手段层（External Means）

> 本层共同 Boundary（B1-E13）：都不是"DaoSheng 本身"，只是 DaoSheng 可以拥有和使用的东西；各自独立外部语义（`bounded-contexts.md` §2）。

### 4.1 Model（模型）

| 属性 | 内容 |
|---|---|
| Definition | 实现手段：理解 / 判断 / 调度 / 交互（B1-E3）；"Agent 的能力不应全部来自模型参数" |
| Boundary | LLM ≡ Model（同一区分）；不得定义 DaoSheng / Identity（规则 2）；部署关系 UNKNOWN（V0 gpt-oss:20b vs 材料 2 A1 Qwen3.5-9B，U-5） |
| Owner | 部署层（不是 DaoSheng 个体） |
| Allowed Mutation | 模型可替换（手段可换，个体不变——B1-E13 精神）；部署配置由架构 Step 决定 |
| Forbidden Mutation | 不得由 Model 定义 DaoSheng（规则 2）；不得由 Model 定义 Identity（规则 2）；不得把模型参数等同于个体能力（B1-E3） |
| Evidence Source | ORIGIN（B1-E3 分工）；UNKNOWN（部署关系 U-5） |

### 4.2 Skill（技能）

| 属性 | 内容 |
|---|---|
| Definition | 手段：规定能力与使用方式（B1-E3）；DaoSheng 化解读 = 个体后天修成的"术"（B1-E7，对应 Domain 概念 Capability） |
| Boundary | Skill（手段）≠ Capability（个体之"术"，Domain 概念）；Skill != DaoSheng（B1-E13） |
| Owner | 部署层 / 个体拥有（个体"可以拥有和使用"，B1-E13） |
| Allowed Mutation | Skill 可增删（个体后天修"术"的过程）；使用方式可修订 |
| Forbidden Mutation | 不得把 Skill 当 DaoSheng 本身（B1-E13）；不得把 Skill 与 Capability 混同（手段 vs 个体属性） |
| Evidence Source | ORIGIN（B1-E3 分工；B1-E7 术解读） |

### 4.3 Helper（助手）

| 属性 | 内容 |
|---|---|
| Definition | 手段：确定性的具体执行（B1-E3） |
| Boundary | Hermes 历史决策：P4 定义、P10 七特征、P11 复杂度封装（`HISTORICAL_DECISION`）；Helper != DaoSheng（B1-E13） |
| Owner | 部署层 |
| Allowed Mutation | Helper 可增删替换；执行细节可调整 |
| Forbidden Mutation | 不得把 Helper 当 DaoSheng 本身（B1-E13）；不得把 Hermes 的 Helper 特征当作 DaoSheng 定义（规则 3） |
| Evidence Source | ORIGIN（B1-E3 分工）；HISTORICAL_DECISION（P4/P10/P11） |

### 4.4 Tool（工具）

| 属性 | 内容 |
|---|---|
| Definition | **UNKNOWN**（Q6 决定保持 UNKNOWN）；材料 1/2/3 未作为独立概念讨论（仅泛指"工具"） |
| Boundary | 引入 Domain 须 ADR（规则 8）；定位参考（非定义）：Hermes P20 "MCP = 工具层控制桥梁"、P21 "Skill 怎么思考，MCP 怎么执行" |
| Owner | 部署层（当前，待定义） |
| Allowed Mutation | 定义确定前：无 Domain 层面变更（UNKNOWN 不猜测，规则 11） |
| Forbidden Mutation | 不得由 V0 / Hermes 实现反向定义 Tool（规则 1/3）；不得把泛指"工具"提升为独立 Domain 概念（无依据） |
| Evidence Source | UNKNOWN（独立概念定义）；HISTORICAL_DECISION（P20/P21 定位参考）；USER_RATIFIED（Q6 保持 UNKNOWN） |

### 4.5 MCP（Model Context Protocol）

| 属性 | 内容 |
|---|---|
| Definition | 手段：连接外部工具与环境（B1-E3）；Hermes P20 工具层控制桥梁（`HISTORICAL_DECISION`） |
| Boundary | MCP != DaoSheng（B1-E13）；P21 "Skill 解决怎么思考，MCP 解决怎么执行"（定位） |
| Owner | 部署层 |
| Allowed Mutation | MCP 服务端/工具可增删；连接方式可调整 |
| Forbidden Mutation | 不得把 MCP 当 DaoSheng 本身（B1-E13）；不得由 MCP 定义个体的能力或身份 |
| Evidence Source | ORIGIN（B1-E3 分工）；HISTORICAL_DECISION（P20/P21） |

### 4.6 Worker（工作者）

| 属性 | 内容 |
|---|---|
| Definition | **UNKNOWN**（Q6 决定保持 UNKNOWN）；材料 1/2/3 未出现此概念；唯一约束 = 规则 4"Worker 不得成为 Identity"（LATER_INTERPRETATION，原始来源 UNKNOWN） |
| Boundary | 历史记录（非定义）：V0 Worker A = Ollama gpt-oss:20b、Worker B = 本地 Qwen3.5-9B（llama.cpp）= 两个模型后端节点（审计 M-2/M-3） |
| Owner | 部署层 |
| Allowed Mutation | 定义确定前：无 Domain 层面变更（UNKNOWN 不猜测，规则 11） |
| Forbidden Mutation | Worker 不得成为 Identity（规则 4）；不得由 V0 的 Worker A/B 节点反向定义 Worker 的 Domain 含义（规则 1）；引入 Domain 须 ADR（规则 8） |
| Evidence Source | UNKNOWN（领域定义）；IMPLEMENTATION（V0 Worker A/B 记录）；USER_RATIFIED（Q6 保持 UNKNOWN） |

### 4.7 Hermes

| 属性 | 内容 |
|---|---|
| Definition | 历史本地 Agent 系统（材料 2：本地 Hermes Agent + llama.cpp + 即时通讯渠道 — 历史事实；具体机器、实例昵称、渠道名与 Model 量化细节不在本副本公开范围）；DaoSheng 的灵感来源之一 |
| Boundary | Hermes != DaoSheng（规则 3）；Host 定位 = LATER_INTERPRETATION（材料 3 07/11，B3-E6/E8）；**Host 正式定义 UNKNOWN**；V0 无独立 host 集成层（M-01…M-04） |
| Owner | 历史层（origin 历史材料记录，原文不随本副本发布）；未来 Host = 独立上下文（`bounded-contexts.md` §3），定义待 ADR |
| Allowed Mutation | 历史系统不可变（Historical Experience 冻结，规则 7）；未来 Host 集成层建立 = ADR ① |
| Forbidden Mutation | Hermes 不得定义 DaoSheng（规则 3）；不得把 Hermes 的机制（Helper 特征 / MCP 用法等）提升为 DaoSheng 本体；Host 正式定义不得猜测（规则 11） |
| Evidence Source | ORIGIN（材料 2 历史系统）；LATER_INTERPRETATION（Host 定位）；UNKNOWN（Host 正式定义）；待 ADR（ADR ① host 集成层） |

---

## 5 跨概念关系（最小集）

| 关系 | 说明 | 证据 |
|---|---|---|
| Individual **has** Identity / Continuity / Doctrine | 个体拥有身份载体、连续性、原则 | B1-E1/E5/E6；Q5 |
| Identity **supported by** 支撑项清单（含连续记忆） | 载体由支撑项支撑，非由字段穷尽 | B1-E6 |
| Continuity **related to** Memory 双轨 | 连续记忆 = 支撑项之一 | B1-E4/E6；Q5 |
| Experience **produces** Understanding / Insight / Memory | 经历是认知来源 | B1-E4/E12；Q7 |
| Observation / Action **part of** Experience | 二者可成为经历的组成部分，但不穷尽经历 | Q9 |
| Understanding / Insight **verified by** Verification | 接受为可信前检验依据 | Q10 |
| Insight / Understanding / Memory **corrected by** Correction | 事后自我修正 | Q10 |
| Capability **verified by** Verification | 未验证不得 active | K-04；Q10 |
| Skill **instantiates** Capability（手段层） | Skill 是 Capability 的实现手段 | B1-E3/E7 |
| Growth **measured by** "经历改变行为" | 成长判据 | B1-E5 |
| Faculty **supports** 行为倾向（含 reflection / stopping） | 与 Doctrine 联动 | Q3；B1-E9 |
| External Means（Model/Skill/Helper/Tool/MCP/Worker） **used by** Individual | 手段可拥有可使用，不定义个体 | B1-E13；规则 1-5 |

## 6 本文件刻意不回答的（UNKNOWN 汇总，指针）

- Identity 延续判据（"仍然是谁"）→ `domain-invariants.md` §3
- "道"具体内容 → `domain-invariants.md` §3
- Memory 消化/遗忘机制与判据 → `domain-invariants.md` §3
- Insight 单一表征形式（R-03）→ `domain-invariants.md` §3
- Capability 生命周期状态机（ADR ②）→ `bounded-contexts.md` §5
- Continuity 单一载体归属（life 层 ADR）→ `bounded-contexts.md` §5
- Worker / Tool 领域定义 → `domain-invariants.md` §3
- Host 正式定义（ADR ①）→ `bounded-contexts.md` §3/§5
- "AI 个体 / 智能个体 / 数字个体"三词关系 → `ubiquitous-language.md` §1
