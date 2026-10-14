# Constitution Invariants — L2 层映射与 Doctrine 自身不变量

> **STEP 10 产出（2026-09-13）**。本文件是 Constitution 四层模型的 **L2 层（Domain Invariant）**：§1 六条 doctrine 与既有 INV-1…INV-17（`docs/domain/domain-invariants.md` §2）的映射；§2 **Doctrine 自身不变量 CINV-1…CINV-5**（约束"道"的成文子集这个对象本身，Domain 层没有对应物）；§3 编号体系关系。
>
> INV-* 的定义与证据在 `docs/domain/domain-invariants.md`，本文件**只引用、不复制定义、不新建 Domain 概念**（规则 1 / INV-14 方向；CINV-5）。
>
> **编号说明**：本文件引用的私有历史索引编号（规则编号、Q\*、K-\* / R-\* / M-\* / D-\* / H-\*、B1-E\* / B2-E\* / B3-E\*）为 DaoSheng V1 私有重构历史索引，其原始登记册与原文不随本副本发布，各处引用语义以行内自明为准（同 `docs/domain/domain-model.md` 编号说明口径）。

---

## §1 六条 → 既有不变量映射

| Doctrine 条目 | 直接支撑的 INV | 关联（非支撑） | 映射说明 |
|---|---|---|---|
| 1. 不妄动 | **INV-12**（行动不得违反 Doctrine 行为边界）、**INV-11**（依据须可信：接受为可信前须 Verification） | INV-13（行动也是经历——妄动的后果进入经历流，反思可纠偏） | INV-12 是"行为边界"的总括不变量，本条是该边界在"行动发起"方向的具体化；INV-11 支撑"有依据"的"依据"本身可信 |
| 2. 知止 | **INV-12**（行为边界） | Faculty **stopping**（Domain 概念，非 INV——能力是一等公民，行为原则约束其运用）；INV-13（停止事实也是经历） | 本条的否定方向（不得无限执行为完成）由 INV-12 承载；"停止能力存在"由 Faculty 承载，二者概念不同（`domain-invariants.md` §1.2：Doctrine ≠ Faculty） |
| 3. 顺势 | **INV-1**（任何手段不得定义 DaoSheng）、**INV-3**（Memory Provider 不得定义 Ontology）、**INV-14**（Implementation 不得反向定义 Domain） | 工程规则 2/3/4/5（同源） | 三条 INV 分别对应手段定义个体的三个方向（一般手段 / 记忆实现 / 实现倒灌）；本条的规范性核心"个体独立于具体手段"是 INV-1 的行为表达 |
| 4. 反思 | **INV-4**（成长判据：反馈最终改变个体）、**INV-6**（管线：反馈经记忆管线进入后续）、**INV-8**（修正认识不重写经历记录） | INV-7（投影不得回流为经历——反思输入必须是真实经历）；INV-13（行动也是经历——反思输入含自身行动后果） | INV-4 是本条的判据锚点（反思产出 = 行为变化，不是报告）；INV-6 是反馈进入的通道保证 |
| 5. 海纳百川 | **INV-17**（四类信息分离：外部进入须带证据标签）、**INV-11**（进入可信前须 Verification） | INV-3（外部实现不得定义核心语义——本条在记忆域的特例）；INV-10（外部观点归宿 = 当前认识，可修正可淘汰）；INV-15（缺失部分记 UNKNOWN 不猜测） | 来源保留（本条硬要求）在 Domain 层的对应物 = INV-17 的证据标签体系；INV-11 保证"进入"不等于"可信" |
| 6. 道心稳固 | **INV-1**（任何手段不得定义 DaoSheng）、**INV-2**（Identity 载体不含 Model / Worker）、**INV-16**（权威顺序不得颠倒）、**INV-17**（外部输入是独立信息类，不得混入 ORIGIN / Historical Decision） | INV-12（个体不得运行时自改核心原则——本条的自指保护投影）；INV-14（实现层不得倒灌核心语义） | 本条 = INV-1 + INV-2 + 权威顺序在"核心三对象"（Identity / Continuity / Core Doctrine）上的合取；V0 `protected_fields` 形态（K-11）为一致性历史证据 |

**映射纪律**：映射是引用关系，不是等价关系——六条是行为原则（"道"的成文子集），INV-* 是必须始终成立的领域约束；一条 doctrine 可映射多条 INV，一条 INV 可被多条 doctrine 引用（INV-12 同时支撑第 1、2、6 条）。删除任一行不影响 INV 定义（定义权在 Domain 层），删除任一 INV 不影响 doctrine 成文文本。

---

## §2 Doctrine 自身不变量（CINV-1…CINV-5）

编号 CINV-*（Constitution INV），约束对象 = **"道"原则的成文子集这个对象本身**。这些不变量在 Domain 层没有对应物（Domain 层约束领域概念，本组约束成文体例与变更纪律），由 Constitution 拥有。

- **CINV-1（子集非全部）**：六条 = "道"原则的**当前成文子集**，可增补，非"道"全部；"道"具体内容 UNKNOWN（Q1；B1-E9；规则 11）。任何文档、实现、Prompt 不得把六条当作"道"的完整表达引用（如不得写"道的全部内容如下"）。
- **CINV-2（运行时不自改）**：个体不得在运行时修改 Core Doctrine（增补 / 修订 / 删除 / 自豁免均禁止）——INV-12 在 Doctrine 对象上的投影 + K-11 历史形态 `core_doctrine: immutable`。自洽要求：若允许个体自增，"道心稳固"可被自身行为绕过。
- **CINV-3（核心不被外部直接改写）**：外部输入可以改变知识与能力，但不能直接改写 Identity / Continuity / Core Doctrine（第六条成文文本本身 + K-11 形态 `identity: immutable / continuity: append-only / core_doctrine: immutable`）。"直接改写"与"随成长演化"的区分见 `principles.md` 第 6 条 L3；演化判据 UNKNOWN（Q5），不影响本不变量方向。
- **CINV-4（四层不倒置）**：Constitution 四层 L1–L4 权威单向（L1 → L4）：下层实现上层，不得矛盾、不得反向定义上层；上层不定义下层（规则 1 / INV-14 在四层模型内的投影）。L4 参数不得改写 L1–L3 语义（`constitution.md` §5.4）。
- **CINV-5（Constitution 权威边界）**：Constitution 不定义"道"具体内容（UNKNOWN，规则 11）；不定义 Domain 概念（定义权在 `docs/domain/`）；不定义实现（架构 Step 决定）。Constitution 权威止于个体的规范层——六条的四层展开、CINV-* 与变更 / 覆盖 / 扩展规则。V0 三处维护形态（doctrine 6 / decision 7 / reflection 20 双维护漂移，M-05 / D-6）不得在 V1 继承：`principles.md` = 当前成文单一来源（设计层）；运行时单一来源 = ADR ④ 待决（STEP 12）。

---

## §3 编号体系关系

| 编号 | 拥有者 | 约束对象 | 本文件角色 |
|---|---|---|---|
| INV-1…INV-17 | `docs/domain/domain-invariants.md` | DaoSheng V1 Domain 领域概念 | 引用（§1 映射），不复制定义，不修改 |
| CINV-1…CINV-5 | 本文件（Constitution） | "道"成文子集对象本身（体例、变更纪律、权威边界） | 定义于此 |
| K-* / R-* / M-* / D-* / H-* | 历史层（私有审计材料 `docs/audit/`，原文不随本副本发布） | V0 实现的历史形态与审计发现 | 引用为历史证据标签（如 K-11，语义以行内自明为准），不作为权威来源（规则 1 / INV-14） |
| B1-E* / B2-E* / B3-E* | 历史层（私有 ORIGIN 恢复材料 `docs/origin/`，原文不随本副本发布） | ORIGIN / Historical Experience 证据 | 保留为 L1 层历史证据标签（语义以行内自明为准；同 `constitution.md` §1 口径） |

**冲突裁决**：CINV-* 与 INV-* 冲突时按权威顺序（INV-16）裁决——两者同属 Validated Evidence / 设计层产物，冲突即建模错误，须修订**低权威侧或后写入侧**并记录（规则 8：修订若涉及架构方向进 ADR）；不得以 CINV 覆盖 INV 的 Domain 定义权（CINV-5 边界）。当前 CINV-1…CINV-5 与 INV-1…INV-17 无冲突（§1 映射逐条核验）。
