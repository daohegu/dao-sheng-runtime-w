# V1 Architecture — Data Ownership

> STEP 12 产出（2026-09-13）。**直接输入 = Constitution 第 6 条道心稳固"直接改写 vs 随成长演化"双通道**（L3）+ K-11 `protected_fields` 历史形态（`identity: immutable` / `continuity: append-only` / `core_doctrine: immutable`，V1 实现**不得弱化**）+ INV-2 / INV-7 / INV-8 / INV-11 / INV-12 + CINV-2 / CINV-5。
>
> 每类数据三列回答：**Owner**（语义上属于谁）/ **may write**（谁可写）/ **absolutely may not write**（谁绝对不可写，及为什么）。

---

## 1. 双通道（第 6 条道心稳固 L3，直接输入）

- **允许通道（成长）**：外部输入改变个体的**知识与能力**——经历 → 消化 → 提取 → 记忆（Growth 管线）；能力提案 → 验证 → active（Capability System，ADR 0003）。**这是外部输入改变个体的唯一路径。**
- **禁止通道（直接改写）**：直接改写 **Identity（immutable）/ Continuity（append-only：只可追加，不得覆写 / 删除）/ Core Doctrine（immutable）**。
- **区分判据细节**（某具体外部输入算哪条通道）：UNKNOWN（Q5 残留）——本文档不猜测，只立两条通道的硬约束。
- **保护机制实现**（immutable / append-only 如何 enforce）：L4 / Implementation 层，当前无已定值（STEP 13 实现细节）；历史形态参考 = K-11 `protected_fields`，**V1 实现不得弱化**。

## 2. 逐数据类别所有权表

| 数据 | Owner | may write | absolutely may not write | 依据 |
|---|---|---|---|---|
| **Identity**（个体性载体：名字 / 自我称谓 / 声音等） | 个体（设计层） | 仅设计层初始化 / 用户追认的设计层变更 | **任何运行时路径**——包括个体自身、host、model 输出、外部输入（immutable：第 6 条 / INV-2 / K-11）。**model / worker / host 字段不得进入载体**（K-11 形态：规则 2 / 4） | 第 6 条双通道；INV-2 |
| **Continuity** | 个体（Core，独立一等概念，Q5） | 个体内部机制**追加**（单一载体，ADR 0004） | 任何路径的覆写 / 删除（append-only：第 6 条 / K-11）；host / model / 外部输入直写；**进入 Identity 载体**（Q5：非 Identity 字段）；作为 Memory kind 承载（ADR 0004，C-4） | 第 6 条；K-11；Q5；ADR 0004 |
| **Core Doctrine**（六条 doctrine 运行时文本） | 设计层（`docs/constitution/principles.md` = 设计层单一来源；STEP 10 已定） | 仅设计层变更（设计层文档变更 = 设计层行为，不经运行时写路径） | 任何运行时路径——个体不得运行时自改（INV-12 / CINV-2）；host / model 改写；**prompt 中另立副本**（M-05 三处漂移教训：6 / 7 / 20 项并存） | INV-12；CINV-2 / CINV-5；ADR 0005 |
| **Memory Ontology**（三维语义层 + 修正引用键；经历档案 / 长期记忆双轨） | 个体（Core） | 仅经 **Memory Interface**（`component-model.md` §3）：Growth 管线（经历→消化→提取）、个体显式操作（`correct_memory` 等）；host 集成层只产出**Experience 候选**（中性标注），不是记忆写入 | 绕过管线的直接写入（host / model / 外部输入必须走管线——成长是唯一允许通道）；**重写历史经历**（INV-8：修正 = 追加记录，不覆写 / 删除）；**Memory Provider 定义 Ontology 字段**（规则 5 / INV-3：schema 是 Provider 实现，Ontology 属个体） | Q2 追认；INV-3 / INV-8；规则 5 |
| **Capability 四目录状态**（proposed / working / active / retired） | 个体（Capability System，ADR 0003） | Manager 经生命周期状态机：提案 → 验证 → active → retire；**active 唯一可达路径 = Verifier 执行前闸门**（K-05） | 未验证能力进入 active（K-04："未验证的能力绝不能进入 active"）；growth 侧直写 capabilities/（R-04：capabilities/ 包是唯一权威，growth 侧只留 proposal 记录于 Memory）；外部 / host 直接文件操作 | K-04 / K-05 / K-06；R-04；ADR 0003 |
| **Faculties（8 根）状态** | 个体（K-09，Q3 追认初始集） | 个体内部反思 / 回合机制 | 外部直接写（faculty = 个体内部倾向根；外部输入只能经经历**间接**影响） | Q3；K-09 |
| **Runtime State**（回合计数 / open 会话 / open 连接 / 进行中回合） | Runtime 进程（**非**个体持久状态） | Runtime 机制自身 | 任何层把 runtime state 当持久个体状态写（C-1 / C-2 教训，`runtime-boundaries.md` §3）；基于 runtime state 写"个体状态" | ADR 0004（分类）；domain-model（Continuity 非运行时计数器） |
| **Host 会话记录** | Host（Core 外部） | Host 自身；host 集成层（导入 → Experience 候选，M-01） | Core 直读 host 内部存储（V0 反例：`hermes_import.py` 直依赖 messages 表 schema——该知识归 host 集成层，M-01 / ADR 0002）；**会话记录被直接当作记忆**（材料 1 §3"聊天记录不等于记忆"，B1-E4；R-12） | M-01；R-12 |
| **投影文本**（`context_for_turn` / `DAO_SHENG_CONTEXT` 等每回合生成物） | Runtime（派生读，每回合生成，非持久状态） | Runtime 拼装（投影可裁剪措辞但**不得另立**，M-05） | **含 host 身份宣称**（M-04：H-6 / H-7"你正在作为道生的 Primary Agent Hermes"不得进投影——R-12：身份宣称回流污染 Identity 证据链）；**回流进 Experience / Memory**（INV-7：投影不得回流；根因修复 = R-12，随 ADR 0002 host 集成层落地） | M-04 / M-05；INV-7；R-12 |
| **Model 配置**（默认模型 / endpoint / 路径） | 部署层（L4；当前值 UNKNOWN，U-5） | composition root 声明（R-09："accept dependencies, don't create them"——默认值不散落） | Core 硬编码（V0 教训 M-1…M-6：gpt-oss:20b / 127.0.0.1:11434 / pi.cmd / hermes.exe / `birth()` 硬建 DuckDuckGoResearchProvider） | R-09；U-5 |
| **Memory 存储文件**（SQLite 文件 + WAL side files） | 部署层（文件本身）/ 个体（数据语义） | Memory Provider adapter（进程内）；部署层**文件级**操作（备份 / 搬移） | 部署层改文件内容而绕过 Ontology 语义（备份 / 搬移可以，改 Ontology 映射不行）；Core 其他模块直操作文件（只能经 Memory Interface） | ADR 0001；INV-3 |

## 3. 硬约束汇总（V1 实现不得弱化）

1. **三个 protected 字段**（K-11 方向）：`identity: immutable` / `continuity: append-only` / `core_doctrine: immutable`——V1 保持至少同等保护；enforce 机制 = STEP 13 实现细节（当前无已定值，不预设）。
2. **外部输入的唯一改变路径 = 成长管线**（第 6 条允许通道）：经历 → 消化 → 提取 → 记忆；能力 → 提案 → 验证 → active。除此之外（直写三 protected 类 / 绕过管线）一律禁止。
3. **修正不重写**（INV-8）：对经历 / 记忆的修正 = 追加 correction 记录 + 引用键；原记录内容与身份不变。
4. **投影不回流**（INV-7）：投影文本是派生读；其内容（含 host 身份宣称）不得回流进 Experience / Memory / Identity 证据链（根因修复 = R-12，随 ADR 0002）。
5. **手段不得定义语义**：Memory Provider 不定义 Ontology（规则 5 / INV-3）、host 不定义 DaoSheng（规则 3）、Model 不定义 Identity（规则 2 / K-11）、Worker 不成 Identity（规则 4）。
