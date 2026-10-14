# V1 Architecture — Runtime Boundaries

> STEP 12 产出（2026-09-13）。回答：persistent state vs runtime state 分类；重启语义（Hermes 重启 / Runtime 重启 / Model 重启）；Continuity C-1…C-5 的分类与处置方向（**载体由 ADR 0004 定义，本文档只给分类与约束**）。
>
> 本文档是 research §0"Long-running Runtime / Recovery = defer to STEP 12"的架构回答：其答案 = 状态归属 + 重启语义 + 回合原子性，**不是**一个新子系统。

---

## 1. Persistent vs Runtime State

| 数据 | 分类 | 持久化介质 | 写入时机 / 约束 |
|---|---|---|---|
| Identity | **Persistent**（immutable，K-11） | Identity 载体（V0 `soul.json` 形态参考；V1 载体实现形态 = STEP 13 实现细节） | 仅设计层初始化 / 用户追认的设计层变更（`data-ownership.md` §2）；**任何运行时路径禁写** |
| Continuity | **Persistent**（append-only，ADR 0004） | **单一载体**（ADR 0004 决定 2；实现形态 = STEP 13） | 仅个体内部机制**追加**；不得覆写 / 删除（第 6 条 / K-11） |
| Memory（三维语义层 + 修正引用键；经历档案 / 长期记忆双轨） | **Persistent** | Memory Provider（embedded SQLite WAL，ADR 0001） | 仅经 Memory Interface（`component-model.md` §3）；修正 = 追加（INV-8） |
| Capability 四目录（proposed / working / active / retired） | **Persistent** | 文件系统目录（K-06 形态） | 仅 Capability System（Manager，ADR 0003 状态机）；active 须经 Verifier（K-05） |
| Faculties（8 根）状态 | **Persistent**（个体内部倾向状态，K-09，Q3 追认初始集） | 个体状态载体（实现形态 = STEP 13） | 仅个体内部反思 / 回合机制 |
| 回合计数（`state.turn`，V0 C-2） | **Runtime** | 进程内存 | 不持久（§3：C-2 降级） |
| `state.last_action_experience_id`（V0 C-1，自述 "persisted runtime continuity, not Identity"） | **Runtime**（V0 把它持久化是**错位**：运行时机制状态不是 Continuity） | 不持久 | 不持久（§3：C-1 降级） |
| open host 会话 / open 模型连接 / 进行中回合 | **Runtime** | 进程内存 / socket | — |
| digest 中间产物（未提交的管线阶段） | **Runtime**（崩溃即弃；经验回流 append-only 可重导入） | — | — |
| Host 会话记录 | **Persistent，但 host-owned**（Core 外部） | host 存储（V0：`profiles/<name>/state.db`；路径构造属 host 集成层，M-03，Core 不感知） | host 自身 + host 集成层导入（→ Experience 候选，M-01）；**会话记录 ≠ 记忆**（材料 1 §3，B1-E4；R-12） |

**判据（一句话）**：数据属于"个体仍然是谁 / 经历过什么 / 记住了什么 / 会做什么" = persistent；属于"当前进程正在做什么" = runtime。V0 的 C-1 错位正是把后者写进了持久层。

## 2. 重启语义

| 事件 | 后果 | 机制 |
|---|---|---|
| **Hermes Desktop 重启** | 个体状态**完全不受影响** | 个体持久状态全在 Runtime 拥有的文件；host 会话记录是 host 自己的文件。host 丢失的只是自身进程状态。第 3 条顺势 L3 的个体级表达：host 是手段，重启手段，个体仍在 |
| **DaoSheng Runtime 重启** | 持久文件全部保留；Runtime State（回合计数、open 会话、进行中回合）丢失 | **无需恢复子系统**（下条） |
| **Model 进程重启** | 个体状态不受影响（INV-1） | 重连 = adapter 行为 |
| **进程崩溃（未正常退出）** | 同 Runtime 重启：最多丢失进行中回合 | 回合原子性（下条） |

**回合原子性（V1 的恢复语义）**：

1. **单个回合是原子单位**：回合要么完成（状态已写），要么未完成（弃）。**不引入 mid-turn checkpoint**（YAGNI：幼体阶段单进程，崩溃代价 = 一个进行中回合）。
2. **崩溃代价可恢复**：经验回流是 append-only——host 会话记录仍在 host 侧，重启后 host 集成层可重新导入（幂等，去重属 host 集成层职责，M-01）；Memory / Capability / Identity / Continuity 均为已提交状态。
3. **回合计数丢失无害**：C-2 是 runtime 机制状态，下一个回合从头计（它不承载个体语义）。
4. **将来触发重评估**：若出现"长回合"（单回合跨越数分钟以上、崩溃代价不可接受）或中断-恢复需求，重开本文档——届时是 Recovery 的 Research / ADR 时机，不是现在预设。

## 3. Continuity C-1…C-5 处置（载体 = ADR 0004）

V0 五处残留（`v0-drift.md` §2.6；Q5 已定 Continuity = 独立一等概念，**非 Identity 字段**）：

| # | V0 形态 | V1 分类 | 处置 |
|---|---|---|---|
| C-1 | `state.last_action_experience_id`（自述 "persisted runtime continuity, not Identity"） | **Runtime 机制状态，不是 Continuity**——V0 自述语义正确，但持久化错位 | 不持久；属回合机制 |
| C-2 | `state.turn` | **Runtime**（回合计数；domain-model：Continuity 非运行时计数器） | 进程内存，不持久 |
| C-3 | `soul.continuity_revision` | Continuity 语义——但放在 Identity 载体是**分类错位**（Q5：Continuity 非 Identity 字段） | 移出 Identity 载体；并入 Continuity 单一载体（ADR 0004 决定 2） |
| C-4 | MemoryItem `kind="continuity"`（verify_insight 写入） | Continuity 语义 | Memory **不承载 Continuity 作为 kind**；verify_insight 的 Continuity 输出写入 Continuity 载体（ADR 0004，与 ADR 0006 联动：verify_insight 输出经 Interface 归位） |
| C-5 | faculties "continuity" 根 | **Faculty**（8 根之一，Q3 追认，K-09）——faculty 是能力根，**不是** Continuity 状态载体 | 保留于 faculties 初始集；与 Continuity 概念的区别 = faculty 是"维持连续性的能力根"，Continuity 是"连续性的状态记录"；两者耦合机制本 Step 不设（Domain 描述需要时由 Domain 文档处理） |

**结论**：Continuity = Core 内**单一载体**（ADR 0004），append-only，独立于 Identity 载体与 Runtime State。C-1 / C-2 降级 runtime（不持久）；C-3 / C-4 并入单一载体；C-5 保留为 faculty（非载体）。五处漂移 → 一个载体（locality）。
