# ADR 0010 — Host Adapter 向 Experience 候选接口的语义供数契约

- **Status**: **Accepted**（2026-10-09 起草；**2026-10-09 用户正式裁定接受 = 接受本 ADR 的架构契约；不接受任何尚未经过 Research Gate 验证的具体实现方法**——检测机制选定仍待 Research Gate（规则 9，§Research Gate，RG-Q1–Q4 未完成）；接受范围与明确不在接受范围见 §Acceptance Record）
- **约束来源**: 决定 ㊿（`docs/domain/domain-model.md` §2.1 Experience Boundary，正式条文立于 DaoSheng 私有仓库历史提交，hash 不随公开副本发布；**本 ADR 以其为前提，不再裁定、不再修改**）；ADR 0002 决定 1（host 集成层 = 进程内 adapter，唯一允许知道宿主名 / 存储路径 / 进程调用方式的层）/ 决定 2（经验回流 Interface = 「导入会话 → [Experience 候选]」，候选 origin 中性标注在本层完成）/ 决定 3（seam hypothetical，Interface = contract）/ 决定 4（关系陈述只进 composition root，不进投影文本）/ 决定 6（Host 正式定义 = UNKNOWN）；ADR 0008 决定 4 / 7（seam hypothetical → real、ADR 定「层结构 + seam 状态 + Interface 契约」结构事实，部署值留 UNKNOWN）与 ADR 0009 决定 9（实施另立）/ 决定 10（不修改历史 ADR，引用并延伸）先例；票①（V1 重构历史 handoff 记录，不随公开副本发布；证据事实继承，本票不重跑调查）；票②（V1 重构历史 handoff 记录，不随公开副本发布）；Hermes Adapter evolution 治理约束（规则 1 / 7 / 8 / 9 / 11 / 13；原始治理记录不随公开副本发布）；INV-6（双轨与管线）；INV-7 / INV-8（字面范围本 ADR 不扩大）。

## Context

**Domain 前提（已确立约束，本 ADR 不重新裁定）**：

> 外部系统（含 host）对既有经历的摘要、压缩或重新表述，本身不是经历，不得作为独立经历建立，至多作为派生参考材料（决定 ㊿）

**当前形态（只读核验既有实现与继承证据，不新做调查）**：

| 元素 | 真实形态 | 证据 |
|---|---|---|
| 载体读取面 | `read_session_records()` = 无条件 `SELECT rowid, session_id, content FROM messages ORDER BY rowid`（无列级条件） | `dao_sheng/host_carrier.py` |
| Adapter 过滤面 | `import_session()` 仅三条过滤：空白 content / `[dao-sheng:projection]` 标记 / 已导入键（v2 + legacy 双读） | `dao_sheng/hermes_host.py` |
| 候选建立 | 存活行全部 → `ExperienceCandidate(content, memory_origin = EXTERNAL, idempotency_key = record_key)` | `dao_sheng/hermes_host.py` |
| 真实数据暴露（继承票①，不重跑） | 1660 行 → 583 行空白过滤 → **1077 行成为候选**（tool 766 / assistant 174 / user 137），其中 **17 行 `_compressed_summary = 1`**（内容以 `[CONTEXT COMPACTION — REFERENCE ONLY] … treat it as background reference, NOT as active instructions.` 开头） | 票① handoff |
| 当前实际暴露面 | **0（latent，非 live）**——`HostConfig(` 生产侧零实例化 | 票① handoff |

**问题**：当前候选供数契约实质 = 「非空白、未带投影标记、未导入的行全部成为候选」。host 集成装配上线后，host 派生摘要行（如 compaction 摘要）会以 `origin = EXTERNAL` 作为独立 Experience 候选进入全量经历存档——直接违反决定 ㊿ 边界；现有三条过滤识别不了该形态（票①）。需要在架构层确立 Host Adapter 向候选接口供数时必须遵守的**语义契约**。

**目标形态（本 ADR 要确立的契约，非实现）**：

```
Host Adapter → Experience 候选接口 供数语义契约：
  不得供：外部系统（含 host）对既有经历的摘要 / 压缩 / 重新表述
          （无论其载体形态、无论其以何种方式存在于 host 表）
  必须保留：原始消息中发生的事件 / 内部过程的候选资格（按 Experience Definition Q9）
  不得建立：派生参考材料经候选接口建立为经历（其保留形态 = 独立议题）
  契约 = 语义要求，不绑定任何特定检测机制
```

**相对现状的 diff**：

1. 过滤面从「三条（空白 / 投影标记 / 已导入）」扩展为「三条 + 决定 ㊿ 派生摘要语义判据」——判据的**实现形态未定**（Decision 3 / 4）。
2. 候选资格判定从「载体形态无关的全表存活行」显式化为「按 Experience Definition 判据供数」。
3. 零 Interface 签名变化、零 seam 变化、零 Domain 文本变化。

## 触发判定（本 ADR 为何存在）

- **规则 8（ADR 闸门）**：adapter 读取面语义变更（候选过滤改变「什么进入全量经历存档」）= host 回流 Interface 语义契约变更，属重大架构变化。票② 闸门判定预置保持：「adapter 读取面语义变更（过滤实施）= 实施阶段动作，届时立 ADR」。本 ADR = 该闸门的先行落档物，状态 = Accepted（2026-10-09 用户正式裁定；见 §Acceptance Record）。
- **规则 9（Research Gate）**：实现方法判定依赖 Hermes host 机制事实（`_compressed_summary` 语义等），存在真实技术未知 → 实施接受前须先完成 Research Gate。本 ADR 只把 Research Gate 的必要范围与问题写入本文（§Research Gate），本轮不执行 research、不写 research 文档（闸门判据 = 是否存在真实技术未知；本轮未执行任何 research 动作）。
- **规则 1（Implementation 不得反向定义 Domain）**：Domain 定义已先行（决定 ㊿；正式条文见 `docs/domain/domain-model.md` §2.1）；本 ADR 是其向 adapter 供数面的正向落实，不以实现反推 Domain。

## Decision（2026-10-09 用户正式裁定接受；接受范围 = 架构契约本身，见 §Acceptance Record——不接受任何尚未经过 Research Gate 验证的具体实现方法）

1. **Domain 前提**：决定 ㊿ 边界 = 已确立 Domain 约束。本 ADR 以其为前提，不重新裁定；Domain 正式条文不再修改（票② / 规则 7）。
2. **候选供数语义契约（Domain-required outcome，implementation-agnostic）**：Host Adapter 向 Experience 候选接口供数必须满足——
   a. **不得**将外部系统（含 host）对既有经历的摘要 / 压缩 / 重新表述作为独立 Experience 候选供入（无论其载体形态或存在于 host 表的方式）；
   b. **必须保留**原始消息中发生的事件 / 内部过程的候选资格（按 Experience Definition Q9）；契约不得为过滤派生摘要而将原始消息一概排除；
   c. 派生参考材料（若未来保留）不得经候选接口建立为经历；其保留形态（若有）= 独立议题，不在本 ADR 范围；
   d. 契约以语义要求表达（「什么不得成为候选 / 什么必须保留资格」），**不绑定任何特定检测机制**。
3. **Domain 结果与 Adapter 实现方法分离**：Decision 2 是 Domain-required outcome；检测机制（读哪个字段 / 识别哪种内容形态 / 用哪种读取条件）= Adapter 实现方法。**本 ADR 不预先假定 `_compressed_summary` 字段、内容前缀或某个 SQL 条件就是最终实现方法**；检测机制须等待 Research Gate 证据支持（规则 9）后方可选定。
4. **备选实现路径（记录，不选定）**：

   | 路径 | 描述 | 证据要求 | 兼容性风险 | 未验证问题 |
   |---|---|---|---|---|
   | A. 列级标记过滤 | 读取 host 列（如 `_compressed_summary`）并在 carrier / adapter 过滤 | Research Gate：该列真实语义及其与摘要行的关系（RG-Q1） | adapter / carrier 层持有更多 host schema 细节，ADR 0002 耦合面扩大（locality 一致但耦合变宽）；该列在其他 Hermes 版本 / 其他 host 是否存在 = UNKNOWN | 该标记对候选过滤是否充分（RG-Q2） |
   | B. 内容形态识别 | 按内容前缀 / 形态（如 `[CONTEXT COMPACTION — REFERENCE ONLY]`）识别派生形态 | Research Gate：前缀稳定性与普适性（RG-Q3） | 内容级启发式脆弱；可能误排除原始消息（违反 Decision 2b） | 是否存在无标记派生形态 / 带相似前缀的原始消息（RG-Q3） |
   | C. 其他路径（host 侧独立表 / 字段、候选接口侧二次判定等） | 备选记录 | 证据不足，不展开 | UNKNOWN | 待 Research Gate 后判定 |

   无路径被选定；选定 = Research Gate 证据 + 用户验收裁定（2026-10-09 接受裁定明确：接受契约 ≠ 选定任何路径）。
5. **Interface 形态不变**：候选接口（ADR 0002 决定 2）中性形态不变——契约约束 Adapter 供数行为，不改 Interface 签名；不新增 seam；宿主名仍限于 host adapter 层（ADR 0002 决定 1）。若出现第二宿主形态或 Interface 签名变化 → 另立 ADR（ADR 0002 决定 3 hypothetical → real 升格路径）。
6. **实施另立**（ADR 0009 决定 9 先例）：即使本 ADR 被接受，也只确立语义契约与闸门结构；`hermes_host.py` / `host_carrier.py` 的任何变更 = 后续独立正式演化票；无实施票不改任何生产代码。
7. **本 ADR 不修改历史 ADR**（ADR 0009 决定 10 先例）：ADR 0002 / 0008 / 0009 零修改；本 ADR 引用并延伸其决定。

## Acceptance Record（2026-10-09，用户正式裁定）

**裁定**：接受 ADR 0010 的架构契约；不接受任何尚未经过 Research Gate 验证的具体实现方法。

**接受范围（架构契约本身）**：

1. 外部系统（含 host）对既有经历生成的摘要、压缩或重新表述，不得作为独立 Experience 候选供入经历存档（Decision 2a）。
2. 原始消息记录的事件与内部过程仍按既有 Experience Definition 判断资格，不得为排除派生摘要而一概排除原始消息（Decision 2b）。
3. 派生参考材料不得经 Experience 候选接口被建立为独立经历（Decision 2c）。
4. Domain 契约不绑定具体检测机制（Decision 2d）。

结构决定一并生效：Decision 1（决定 ㊿ 前提，不再裁定、条文不再修改）、Decision 3（Domain 结果与实现方法分离）、Decision 5（Interface 形态不变）、Decision 6（实施另立）、Decision 7（不修改历史 ADR）。

**明确不在接受范围**：

- 检测机制选定——`_compressed_summary` 是否足以可靠识别所有派生摘要仍待 Research Gate；内容前缀、SQL 条件和其他检测方案均不在接受范围；路径 A / B / C 无选定；
- RG-Q1–Q4 尚未完成（Research Gate 未执行）；
- 派生参考材料未来保存 / 引用形态未裁定；
- compaction 行为本身是否构成可记录事件继续 UNKNOWN（ADR 0002 决定 6）；
- `active = 0`、`compacted = 1`、`api_content ≠ content` 和 `profiles/*/state.db` 数据库布局继续不在范围。

**本裁定接受的是架构契约，不是检测机制选定。** 后续闸门顺序不变：Research Gate（RG-Q1–Q4，写 `docs/research/`）完成 → adapter 实施票（Decision 6）；实施票验收判据 = 本契约四项。

## Research Gate（必要范围与问题；本轮未执行）

范围限定为 Hermes host 机制事实四项（规则 9）：

- **RG-Q1**：`_compressed_summary` 字段的真实语义及其与摘要行的关系（生成机制、覆盖面、可靠性）。
- **RG-Q2**：该标记在 Hermes 0.21.5 中对候选过滤是否充分（是否存在无该标记的派生摘要形态）。
- **RG-Q3**：标记 / 内容 / 原始消息之间哪些生成或更新关系仍 UNKNOWN（含 Hermes 维护操作是否重写相关列或 rowid）。
- **RG-Q4**：若现有证据不足以安全决定实现方法，需要什么具体验证（验证计划）。

**显式不在范围**：`active = 0`、`compacted = 1`、`api_content ≠ content`、`profiles/*/state.db` 数据库布局——独立议题，本 ADR 不扩展、不裁定。

## Consequences

**正面**：

- 决定 ㊿ 边界获得架构层落点：候选供数契约成为后续 adapter 实施票的验收判据基准（Domain → 契约 → 实施的可追溯链）。
- Domain 结果与实现方法显式分离：实施票不能以「选了某个 SQL 条件」偷换 Domain 判据。
- 当前实际暴露面 = 0（latent），本 ADR 在 host 集成装配上线前立契约，时序安全。

**代价 / 限制**：

- adapter / carrier 层可能持有更多 host schema 细节（路径 A 风险）——与 ADR 0002「耦合集中一处（locality）」一致但耦合面变宽，须由 Research Gate 证据权衡。
- 契约的可验证性依赖后续检测机制选定；机制选定前契约只能以语义判据核验（棘轮无法固化未定形的机制）。

**规则判定**：

- 规则 8：满足——本 ADR 先于任何 adapter 实施（2026-10-09 Accepted；实施仍须 Research Gate 完成 + 实施票下达，无实施票不改任何生产代码）。
- 规则 9：实施方法选定前须完成 Research Gate（§Research Gate 已记录范围，本轮未执行）。
- 规则 1：满足——Domain 先行（决定 ㊿），本 ADR 不反向定义 Domain。
- 规则 7：满足——冻结历史零触碰；Domain 条文未修改；历史 ADR 未修改。
- 规则 11：满足——UNKNOWN 全部显式记录（见下），不填补。
- 规则 13：满足——当时唯一执行状态文档已同步（该文档不随公开副本发布）。

**未决 / UNKNOWN（规则 11）**：

1. 本 ADR 是否被用户接受 = 已裁定（2026-10-09 Accepted = 接受架构契约；见 §Acceptance Record；检测机制选定仍 UNKNOWN）。
2. 最终检测机制 = UNKNOWN（不预先假定，须 Research Gate 证据）。
3. RG-Q1–Q4 全部 = UNKNOWN（Research Gate 未执行）。
4. compaction 行为本身是否构成可记录事件 = UNKNOWN（取决于 Host 正式定义——ADR 0002 决定 6）。
5. Host 正式定义 = UNKNOWN（ADR 0002 决定 6 保持）。
6. 派生参考材料的保留形态（若有）= 独立议题，未裁定。

## 内部一致性检查（2026-10-09，本 ADR 自核）

| 约束 | 检查 | 结果 |
|---|---|---|
| 决定 ㊿ / Domain §2.1 | 边界条文作为前提引用，未重新裁定、未修改；契约 = 边界在 adapter 供数面的直接表达 | 不违反 |
| ADR 0002 决定 1 | 契约落层 = host adapter 层（供数行为约束）；宿主名 / 存储细节仍限于该层 | 不违反 |
| ADR 0002 决定 2 | 候选 Interface 中性形态不变；origin 中性标注（EXTERNAL）仍在本层完成；未新增 Interface 概念 | 不违反 |
| ADR 0002 决定 3 | 未新增 seam；第二宿主 / Interface 签名变化 → 另立 ADR 路径保持 | 不违反 |
| ADR 0002 决定 4 | 契约不进入投影文本；关系陈述仍只进 composition root | 不违反 |
| ADR 0002 决定 6 | Host 正式定义保持 UNKNOWN；本 ADR 只定层契约，不填补 Host 定义 | 不违反 |
| INV-6 / INV-7 / INV-8 | 字面范围未扩大：契约属 Experience 资格侧（与 INV-6 一致）；未并入 INV-7（其针对 DaoSheng 自身内部投影）或 INV-8（其针对既有记录被重写）——派生摘要与二者属不同向量（票② 一致性核验沿用） | 不违反 |
| Hermes Adapter evolution 治理约束（原始治理记录不随公开副本发布） | 权威层 = ADR 0002 形态；宿主名限于 host adapter 层；未出现新宿主 adapter | 不违反 |
| 规则 1 | Domain 定义先行（决定 ㊿）；本 ADR 未以实现方法反推 Domain | 满足 |
| 规则 8 | adapter 读取面语义变更 → 本 ADR 先于实施（2026-10-09 Accepted；实施仍须 Research Gate + 实施票） | 满足 |
| 规则 9 | 实现方法选定前须过 Research Gate（范围已记录，本轮未执行） | 满足（闸门未执行） |
| 规则 11 | 全部 UNKNOWN 显式记录，不填补 | 满足 |
| 规则 13 | 当时唯一执行状态文档已同步（该文档不随公开副本发布） | 满足 |

## Revision（追加式修订 — 2026-10-12 用户正式裁定接受）

**修订状态与裁定基础**：

- 本章节为用户 2026-10-12 正式裁定的追加式修订记录：用户正式裁定 ADR 0010 修订方向（接受修订 Decision 8–14），并选择 **P4-1**（三态事实范围维持不在范围）。
- 追加式：本章节以上原 Status 行、Context、Decision 1–7、Acceptance Record、Research Gate、Consequences、内部一致性检查全部保持原文不回写（规则 7）；本修订不重裁、不重写、不重新解释任何旧决定。
- 本修订范围 = 下列 Decision 8–14 与 §P4 处置；原契约 Decision 2a–2d 不变。
- **修订接受 ≠ 实施授权**：Decision 8–14 确立契约语义；任何生产代码变更（v4 写入键 / 冲突检测 / legacy 双读实施）= 后续独立实施票 **D-058**（Proposed / Blocked；编号 = 用户裁定 ⑧），阻塞条件全部解除并由用户正式下达前不得实施（D-058 票体与当时执行状态记录不随公开副本发布）。

### 修订 Decision 8 — 新写入身份键契约与 legacy 只读组级兼容

1. **新写入键** = `v4:<location digest>:<message_uid>`（不含 session_id、不含 rowid）。每次新写入只使用 v4 单一键版本（延续 DaoSheng 私有仓库历史提交确立的先例：新写入只用单一键版本）。
2. **legacy 只读组级兼容**：v3（`v3:<location digest>:<session_id>:<message_uid>`）、v2（`v2:<digest>:<session_id>:<rowid>`）、v1（`<session_id>:<rowid>`）保留**只读组级双读**——log 中已存在的 legacy 键用于判重跳过；legacy 键**不再被新写入产生**，log 中既有 legacy 键**永不重写、永不删除**。
3. **location digest 作用域语义** = 防护作用域 **(实例, 导入源 canonical 路径)**：digest 由导入源 canonical 路径派生；同一记录在「副本 canonical 路径 → live canonical 路径」之间迁移时 digest 变化（D-057 §13 实测矩阵：副本 canonical 路径 digest 命中 23/23 vs live canonical 路径 digest 命中 1/23）。
4. **生效边界**：v4 契约语义随本修订生效；但 D-058 正式下达并通过实施前闸门之前，v4 不得进入任何生产写入路径，**不得预写任何 v4 键**（用户裁定 ④）。

### 修订 Decision 9 — message_uid 跨 session 身份含义

1. **message_uid 命名逻辑消息，不命名物理行**：uid 在首次插入时铸造，retarget / clone 的每个副本复制同一 uid（D-057 代码事实核验；`idx_messages_session_uid` unique=False partial=True）。
2. **v4 以 uid 为身份单元** ⇒ 同一 location digest + 同一 message_uid 跨 session 变化（retarget 换 session_id）产生**同一 v4 键** ⇒ 跨 session 幂等，闭合 v3 的已知缺口（v3 键含 session_id，retarget 换 session_id → 键变化 → 重导入）。
3. **证据边界（规则 11）**：当前真实 Hermes 库中跨 session 的 uid 组 = 0、跨 role 的 uid 组 = 0（D-057 §16）——v4 动机在真实数据侧**无观测实例**（残余 UNKNOWN U4）。该 UNKNOWN 不阻止契约语义成立（契约针对 retarget 形态的防护性设计），但不得被表述为「已观测到跨 session 重复」。

### 修订 Decision 10 — 同 uid 不同 content 的冲突语义

1. **同 message_uid、不同 content = 合法 Hermes 语义形态**（D-057 §15 判定：H2「合法历史变更」成立 / H1「真实冲突」无证据 / H3「未确定」不成立）——该形态实为同一逻辑经历的不同载体快照（original vs demoted-stub、full-output vs display-head / persisted-output 等），不是矛盾经历。
2. 该形态在 DaoSheng 导入侧构成**冲突组**，归修订 Decision 11 失败语义管辖：**机器不得裁定权威版本**。
3. **同 uid 同 content = 幂等重复**：max-rowid 仅用于同 content 组内确定性代表选择；**绝不进入新键、绝不用于不同 content 之间选择权威版本**（rowid 不稳定，DaoSheng 私有仓库历史提交确立的先例保持）。

### 修订 Decision 11 — 导入失败语义：整批 fail-loud 与整批重跑

1. **默认 = B1 整批 fail-loud**：任一冲突组存在 → 整批在任何候选建立 / 任何导入 / 任何日志写入**之前**中止（fail-loud 先于一切写入），零副作用（memory.db 零变化、imported.log 零新增、零候选建立）；错误信息含 uid / rowid / content 长度，不输出私人全文。
2. **补充 = B3 人工逐组裁定后整批重跑**：冲突组证据产物产出后，由用户逐组人工裁定，再**整批**重跑（已导入组由键判重跳过）。权威版本由人裁定，机器不猜。
3. **人工逐组裁定必须基于明确、可追溯的裁定记录**；具体记录方式及可追溯依据 = D-058 实施前必须明确（记录为 UNKNOWN，本修订不代为拟定）。**硬性禁止**：不得凭 rowid 最大值、最新时间戳或由模型猜测权威内容自动选择「正确版本」。
4. **B2 部分成功（冲突组隔离、其余继续导入）未授权**（用户裁定 ⑤）；若未来授权 → 属新的导入失败语义决定，须先 ADR（规则 8）。

### 修订 Decision 12 — append-only 日志既有语义（显式化，不改变既有行为）

1. `imported.log` 语义 = **记录真实导入行为**的 append-only 日志：只追加、永不重写、永不删除；既有 v3 / v2 / v1 键行永久保留（当前 log 23 行 = 22 行 v3 + 1 行 legacy 裸键，D-057 §13 实测，未重写）。
2. **禁止无导入而预写键**：向 log 预写 v4 键（或任何键）= 伪造导入记录，违背 log 语义（用户裁定 ④「禁止预写 v4 键」）。

### 修订 Decision 13 — 一次性重复风险的适用范围、重算条件与停止条件

1. **已量化风险** = 22 条一次性重复：digest 命中矩阵（副本 canonical 路径 digest 命中 23/23 vs live canonical 路径 digest 命中 1/23）⇒ 导入源 canonical 路径发生「副本 → live」变化时，22 条已导入 v3 记录因 legacy 键不可再生而被再导入一次（D-057 §13 + D-056 §9 核验轮复现）。
2. **接受范围** = 仅限已验证的「副本 canonical path → live path」迁移场景（用户裁定 ④）；不得扩大接受范围到其他实例 / 其他路径形态。
3. **实施前重算条件** = 实际实施前必须对**实际目标实例**重新只读预量化（mode=ro、零副作用）；**数量或集合与已量化结果不符 ⇒ 停止**，回到用户裁定，不得继续实施。
4. 一次性重复记录的定性沿用既有先例（DaoSheng 私有仓库历史记录 Candidate 4：location migration 可能导致一次性重导入，已明确接受）；本修订不作新的定性裁定。

### 修订 Decision 14 — Fixture 验收与真实 Hermes 验收分离

1. Fixture 自动化测试（临时数据库）与真实 Hermes 数据验证**必须分开**：写入不同产物 / 不同章节，分别记录，不得互相替代（真实验证不能由 Mock 测试代替——D-055 先例）。
2. 真实验证范围纪律：原始 Hermes DB 只 `mode=ro`；真实导入仅在隔离实例（派生子集副本）；前后核验原始 DB sha256 不变；只记录计数 / 来源标识，不输出私人对话全文。

## P4 处置 — 三态事实范围 = P4-1（2026-10-12 用户正式裁定）

1. **`active` / `compacted` / `api_content` 与 `content` 的资格判断不纳入本次 ADR 修订范围**；原 Acceptance Record「明确不在接受范围」条目（含 `profiles/*/state.db` 数据库布局）保持冻结历史原文、继续有效、不回写。
2. **不将这些字段状态用于自动判断同 uid 不同 content 的权威版本**：冲突组继续归修订 Decision 10 / 11 管辖（机器不裁定，人工逐组裁定）。
3. **不得将 P4-1 解释为取消现有通用身份冲突检测或真实数据只读证据**：修订 Decision 10 / 11 的冲突检测与 fail-loud 语义继续完全有效；D-057 类真实数据只读再推导证据继续。
4. D-057 §6 全库唯一双 active 行组（同一 message_uid 的 4 行副本，timestamp 全同；真实消息标识与实际行号不随公开副本发布）仅作证据事实留存于 D-057 报告；其契约意义 = UNKNOWN（P4-1 未裁定其进入契约范围）。

## 追加修订记录（事实性说明，不修改原文）

1. RG-Q1–Q4 已完成 = DaoSheng 私有仓库历史提交（docs: record Hermes derived-summary research gate，2026-10-10 入档；hash 不随公开副本发布；research 结果见 `docs/research/hermes-derived-summary-identification.md`）；原 §Research Gate「本轮未执行」文字保留为冻结历史。
2. 备选路径 A（列级标记过滤）已选定并验收 = DaoSheng 私有仓库历史提交（fix: enforce host experience candidate contract，2026-10-10 用户验收；hash 不随公开副本发布；Research 建议 ≠ 选定，选定 = 用户验收）；原 Decision 4「无路径被选定」文字保留为冻结历史。
3. 原 Acceptance Record「明确不在接受范围」各条目保留为冻结历史；其中三态事实条目的当前处置 = P4-1 已裁定（见上节）。

## 修订残余 UNKNOWN（规则 11）

1. U4：v4 动机（跨 session 幂等）在真实数据侧无观测实例（D-057 §16）——保留，不填补。
2. 冲突组人工裁定的具体记录方式及可追溯依据 = UNKNOWN（D-058 实施前必须明确）。
3. 双 active 行组的契约意义 = UNKNOWN（P4-1 未裁定其进入契约范围）。
4. compaction 行为本身是否构成可记录事件 / Host 正式定义 = UNKNOWN（原条目保持，本修订不填补）。

## 修订规则判定（2026-10-12）

- 规则 7：满足——修订 = 追加章节；原 Status / Decision 1–7 / Acceptance Record / Research Gate / Consequences / 内部一致性检查零回写。
- 规则 8：满足——身份键契约 + 导入失败语义 = host 回流 Interface 语义变更，以本 ADR 追加修订承载；实施（D-058）仍被阻塞，无实施票不改任何生产代码。
- 规则 9：满足——用户裁定 ⑦：当前不启动 Research Gate；新证据满足既有触发规则再另行评估。
- 规则 11：满足——残余 UNKNOWN 显式记录（见上节），不填补。
- 规则 1：满足——修订落 host adapter 供数 / 导入语义层；不改 Domain 条文。
- Hermes Adapter evolution 治理约束（原始治理记录不随公开副本发布）：宿主名仍限于 host adapter 层；未出现第二宿主 adapter；无 Interface 签名变化。
- 规则 13：满足——当时唯一执行状态文档已同步（该文档不随公开副本发布）。
