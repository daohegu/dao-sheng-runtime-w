# Domain Invariants — DaoSheng V1 区分与不变量

> **STEP 09 产出（2026-09-13）**。本文件记录 DaoSheng V1 Domain Model 的两类约束：§1 **术语级区分**（含 STEP 09 任务明确要求的六条区分）与 §2 **不变量**（跨时间必须成立的行为 / 结构约束，违反 = 领域级错误）。§3 汇总域内 UNKNOWN。
>
> **区分 vs 不变量**：区分 = 两个概念不是同一个东西（术语边界）；不变量 = 必须始终成立的约束。证据标签口径同 `ubiquitous-language.md`（ORIGIN / HISTORICAL_DECISION / USER_RATIFIED / IMPLEMENTATION / LATER_INTERPRETATION / UNKNOWN）。

---

## §1 术语级区分

### §1.1 任务要求的六条区分（STEP 09 任务逐条明确）

| # | 区分 | 含义 | 证据 |
|---|---|---|---|
| 1 | **Memory Provider != DaoSheng Memory Ontology** | Memory Provider = 外部实现组件（记忆的保存 / 召回，历史实例 Hindsight）；Ontology = 记忆语义体系（双轨 / 管线 / 三维语义层 `memory_origin × memory_status × memory_confidence` + 修正引用键，Q2 追认）。实现不得定义语义（规则 5） | 规则 5；B1-E4；Q2；`bounded-contexts.md` §4 |
| 2 | **LLM != DaoSheng** | **LLM ≡ Model**：任务文本 "LLM" 与项目术语 Model 是同一区分，不是两个概念。Model = 实现手段（理解 / 判断 / 调度 / 交互），"Agent 的能力不应全部来自模型参数"；个体不是模型 | 规则 2；B1-E3 / B1-E13 |
| 3 | **Hermes != DaoSheng** | Hermes = 历史本地 Agent 系统，DaoSheng 的灵感来源之一；其 "Host" 定位（`LATER_INTERPRETATION`）是未来集成上下文，不改变本区分（规则 3） | 规则 3；材料 2；B3-E6 / E8 |
| 4 | **Worker != DaoSheng** | Worker 领域定义 UNKNOWN（Q6 保持），但边界约束有效：Worker 不得成为 Identity、不得定义 DaoSheng（规则 4） | 规则 4；Q6 |
| 5 | **Skill != DaoSheng** | Skill = 规定能力与使用方式的手段，"只是 DaoSheng 可以拥有和使用的东西"，不是个体本身（B1-E13）；且 **Skill（手段）≠ Capability（个体之"术"，Domain 概念）** | B1-E3 / B1-E13；B1-E7 |
| 6 | **MCP != DaoSheng** | MCP = 连接外部工具与环境的手段（B1-E3）；定位参考："Skill 解决怎么思考，MCP 解决怎么执行"（P21） | B1-E3 / B1-E13；P20 / P21 |

### §1.2 其他术语级区分

- **Skill（手段）≠ Capability（个体之"术"）**：Skill 是手段层对能力与使用方式的规定（B1-E3），Capability 是 Domain 属性（B1-E7）；Skill instantiates Capability。同类地，**Faculty ≠ Capability**（先天倾向 vs 后天之"术"，Q3）。
- **Insight ≠ Truth / ≠ Identity / ≠ Doctrine**（Q7）：Insight 是当前认识，可被 Verification 检验、被 Correction 修正或淘汰；不是绝对事实，不是身份载体，不是行为原则。
- **聊天记录 ≠ 记忆**（B1-E4）；**全量经历（历史档案）≠ 长期记忆（记性）**："保存全部"与"记住什么"分开（B1-E4 双轨）。
- **"道" ≠ Doctrine 6 条**（Q1）：6 条是"道"原则的**当前成文子集**，可增补；"道"具体内容本身 UNKNOWN。
- **Experience ≠ Observation ∪ Action**（Q9）：Experience 是发生于个体经历中的事情全体，不被两个环节穷尽；**反馈 = Action 后的世界回应**（子环节），不是个体的独立输出环节，也不是 Observation（Q11）。
- **Correction vs Verification**（Q10）：Correction = **事后、自我驱动**（"我发现自己原来有问题，因此修正自己"）；Verification = **事前、依据驱动**（"在接受为可信之前，我要求它具有足够依据"）。二者方向相反，都是 Domain 原则。
- **Identity = 载体 ≠ 判据**（Q5）：Identity 是个体性的载体；"仍然是谁"的延续判据 UNKNOWN。且 **Continuity = 独立一等概念**（个体跨时间持续的条件），不是 Identity 的属性字段。
- **"AI 个体 / 智能个体 / 数字个体"三词**（Q4）：raw/ 原文并存、关系 UNKNOWN，不断言等价；当前正式名称 = **Individual（个体）**。
- **Helper ≠ Tool**：Helper 有历史决策定义（P4"提前写成固定脚本或固定执行器"、P10 七特征）；Tool 独立概念定义 UNKNOWN（Q6）——两者不是同义词，泛指"工具"也不等于 MCP 连接的外部工具。
- **Hermes（历史系统）≠ Host（未来上下文）**：前者是冻结的 Historical Experience（规则 7），后者是待 ADR 的未来集成上下文（`bounded-contexts.md` §3）。
- **Doctrine（成文子集）≠ Faculty（先天倾向）**：语义联动（stopping ↔ 知止）但概念不同——行为原则 vs 行为倾向（Q3；B1-E9）。

## §2 不变量

编号 INV-*，供后续 Step 引用。

### A 存在层

- **INV-1**：任何手段不得定义 DaoSheng 个体——Model / Skill / Helper / Tool / MCP / Worker / Hermes 都不是"DaoSheng 本身"，只是个体可以拥有和使用的东西（B1-E13；规则 2 / 3 / 4；§1.1）。
- **INV-2**：Identity 载体不得由 Model 定义（规则 2），不得包含 Worker 身份（规则 4）；载体形态参考：V0 `soul.py` 无 model / worker / host 字段（K-11，历史形态）。
- **INV-3**：Memory Provider 不得定义 DaoSheng Memory Ontology（规则 5）；记忆语义归个体，保存 / 召回实现归 Provider。
- **INV-4**：成长判据——"成长不只是增加知识，而是过去的经历能够改变未来的行为"；Memory 与 Reflection 不是成长的终点；判据："经历最终能够改变这个个体"（B1-E5）。
- **INV-5**：初步循环的核心 = "经历事情"，不是"回答问题"（B1-E12）。

### B 认知层

- **INV-6**：记忆双轨与管线——全量经历（历史档案）与长期记忆（记性）分开；管线：经历 → 消化 → 提取 → 记忆 → 复用；聊天记录不得直接当作记忆（B1-E4）。
- **INV-7**：投影内容不得回流为经历（R-12 根因，A-9 症状）——个体的内部投影（prompt / 自我叙述等）不得混入经历流被当作世界经历；V0 的症状级清洗函数（D-05）是本不变量被违反的证据，且 R-12 修复前不得删除（D-05 硬性顺序）。
- **INV-8**：历史经历记录不得被后续解释重写（规则 7）；Correction 修正的是"认识"（Understanding / Insight / 记忆记录），不是"发生过什么"（经历记录本身）。
- **INV-9**：记忆可被更正（Q10 Domain 回答：可以）；如何保留旧版本、如何追踪修订历史 = Implementation。
- **INV-10**：Insight 是当前认识，可检验、可修正、可淘汰；不得提升为绝对事实（Truth），不得与 Identity 或 Doctrine 混同（Q7）。

### C 行动 / 成长层

- **INV-11**：接受任何能力 / 认识 / 记忆 / 结论为可信之前，须经 Verification 检验；未经验证的能力不得进入 active（Q10 + K-04 纪律）。
- **INV-12**：行动不得违反 Doctrine 的行为边界（"哪些行为不应发生"，B1-E9）；个体不得在运行时自改核心原则（Doctrine Owner = 设计层）。
- **INV-13**：行动本身也是经历（B1-E5）——输出环节重新进入经历流，循环闭合。

### D 元层

- **INV-14**：Implementation 不得反向定义 Domain（规则 1）——V0 的 Continuity 五处建模（C-1…C-5）、四目录形态、三维语义层等均为"历史形态"记录（`IMPLEMENTATION` 标签）；追认须经 USER_RATIFIED 或 ADR 才进入 Domain。
- **INV-15**：UNKNOWN 不得猜测（规则 11）——无法验证的事实记录为 UNKNOWN（§3 / `RECONSTRUCTION.md` Open Questions），不得以 GUESS 填充定义。
- **INV-16**：权威顺序不得颠倒：Original Intent > Historical Decision > Validated Evidence > Implementation > Current Guess。
- **INV-17**：四类信息严格分离（用户 2026-09-13 组织原则）——已经知道的 / 不知道的 / 历史上曾经实现过的 / 当前用户明确追认的，各术语定义带对应证据标签，不得混同（如不得声称 Faculty 8 根为 ORIGIN、不得把 6 条 doctrine 当"道"的全部内容）。

## §3 UNKNOWN 汇总（域内）

| UNKNOWN | 为何不决定 | 来源 | 落位 |
|---|---|---|---|
| Identity 延续判据（"仍然是谁"） | ORIGIN 只给支撑项清单，未给判据；Q5 保持 UNKNOWN | B1-E6；`ubiquitous-language.md` Identity 条目（支撑项清单照录 + 延续判据 UNKNOWN 口径） | Domain 后续（用户决策） |
| "道"具体内容 | 材料 1 §8 只给定位，明确"不试图回答'道究竟是什么'"；6 条是当前成文子集，非"道"内容本身（Q1） | B1-E9；Q1 | Domain 后续（用户决策） |
| Memory 消化 / 遗忘机制与判据 | B1-E4 只说"遗忘是结构性组成"，未给机制；Q2 明确"不要为了完整而编造" | B1-E4；Q2 | Domain 后续（须足够 ORIGIN 依据） |
| Insight 单一表征形式 | 一类 Memory vs 独立实体 = 表征 / 架构决定，不是 Domain 定义分歧 | 私有重构历史审计 R-03（原文不随本副本发布；公开口径见 `bounded-contexts.md` §5） | 架构 Step（`bounded-contexts.md` §5） |
| Worker 领域定义 | raw/ 未出现此概念；仅规则 4 约束；Q6："没有定义" ≠ "定义为某种东西" | Q6；`ubiquitous-language.md` Worker 条目（UNKNOWN + 规则 4 唯一约束口径） | 引入须 ADR（规则 8） |
| Tool 独立概念定义 | raw/ 仅泛指"工具"，无独立概念讨论；Q6 保持 UNKNOWN | Q6；`ubiquitous-language.md` Tool 条目（UNKNOWN + 定位参考口径） | 引入须 ADR（规则 8） |
| Host 正式定义 | "Host" 定位 = `LATER_INTERPRETATION`（材料 3 07/11）；V0 无 host 集成层（M-01…M-04） | B3-E6 / E8；私有重构历史审计 M-01…M-04（原文不随本副本发布；公开口径见 `bounded-contexts.md` §3） | ADR ①（`bounded-contexts.md` §3 / §5） |
| Continuity 单一载体归属 | V0 五处 C-1…C-5 = 残留；收敛方向已定（单一载体），位置未定 | C-1…C-5 | ADR ③（`bounded-contexts.md` §5） |
| Capability 正式生命周期状态机 | 四目录 = 历史形态（V0 首创，K-04 / K-06）；正式状态机待追认 | K-04 / K-06；Q8 | ADR ②（`bounded-contexts.md` §5） |
| "AI 个体 / 智能个体 / 数字个体"三词关系 | 原文并存、未解释；Q4 不断言等价 | 材料 1 §1 / §2 / §5；Q4 | Domain 后续（用户决策） |
| V1 是否迁移 V0 既有数据 | soul.json / SQLite 记忆 / capabilities 四目录；联动 R-10 H-4 分支 | 私有重构历史审计 R-10（H-4 分支）（原文不随本副本发布；公开口径见 `bounded-contexts.md` §5） | 架构 Step / 用户决策 |

**非域 UNKNOWN**（非 Domain Model 问题，本文件不展开）：U-1…U-9（V0 审计）/ STEP 07 清单差异来源 / 模型部署关系（U-5）/ 材料日期 / 硬件起点 / `git init` / STEP 编号映射等 → `RECONSTRUCTION.md` Open Questions。
