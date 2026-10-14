# V1 Spec — Individual 与回合模型（spec-individual）

> **STEP 13 产出（2026-09-13）**。固化对象：顶层聚合 Individual、单一回合入口、回合原子性与重启语义、persistent / runtime 分类、投影文本要求。
>
> 源（随本副本发布的公开文档）：`docs/architecture/component-model.md` §1/§2、`runtime-boundaries.md`、`container-model.md` §2/§3、ADR 0002/0004、`docs/domain/domain-invariants.md` INV-5/7/13、`docs/architecture/data-ownership.md`。
>
> 编号说明：正文出现的 R-01/R-08/R-09/R-12、K-01/K-10、M-04/M-05、D-05/D-6、C-1/C-2 等编号（R-\* / K-\* / M-\* / D-\* / C-\*）为 DaoSheng V1 私有重构历史索引，其原始登记册（`docs/audit/`）与原文不随本副本发布，属历史证据标签、不作为权威来源（同 `docs/constitution/invariants.md` 编号说明与 §3、`domain-model.md` / `ubiquitous-language.md` / `bounded-contexts.md` 编号说明口径）。各处引用语义以本文件及其他公开正文中行内自明、并可在公开文档中核验为准：R-01（三入口收敛一处）与 R-08 A-5（不得跨类调用私有 `_persist()`）——ADR 0004 决定 1、`component-model.md` §1；R-09（accept don't create）——`component-model.md` §1、`data-ownership.md` §2；R-12（投影不回流）/ M-04（host 身份宣称文本）/ M-05·D-6（doctrine 三处 6/7/20 漂移）——ADR 0002 决定 4/5、ADR 0005、`data-ownership.md` §2、INV-7；K-01（1171 行 god object 明示排除于 KEEP）/ K-10（KEEP 的是判定与方向，不是逐字代码）——`component-model.md` §2；D-05（清洗函数在根因修复前不得删除的硬性顺序）——INV-7、ADR 0002 决定 5；C-1/C-2——`runtime-boundaries.md` §3。
>
> 与上述公开源文档冲突时以公开源文档为准（`spec-index.md` §1 口径，限随本副本实际发布的文档）；私有历史编号不作为公开读者必须服从的权威依据。已解决（2026-10-14）：此前 REVIEW 记录的「`spec-index.md` §1 映射表仍将 `docs/audit/` 列为本文件直接源、与本文件口径不一致」已由 `spec-index.md` §1 来源口径统一解决——该索引不再将 `docs/audit/` 列为任何规格的直接源，公开源文档与私有历史来源分列，与本文件头部对齐（见 `spec-index.md` §1 来源口径注记）。

## §1 Individual = 顶层聚合

- Individual 是 V1 的顶层聚合（`component-model.md` §1 行 1）。它把依赖编排、回合机制、digest 管线调度、投影拼装、reflection 调度、faculty 更新全部藏在自己内部——**调用方只知道"一个回合"**。
- **Interface = `act(...)` 单一回合入口 + `persist()`**。V0 的 `observe` / `act` / `complete_turn` 三处入口收敛为一处（R-01）。
- **深（depth）**：depth 是对 Interface 的 leverage，不是行比——V0 的 1171 行聚合 god object 不在 KEEP 内（K-01 明示排除），但"入口收敛 + 内部隐藏"的方向保留（K-10：KEEP 的是判定与方向，不是逐字代码）。
- **顶层无 seam**：Individual 本身 = 整个个体的聚合，其 Interface 就是测试面（the interface is the test surface）——测试经 `act` / `persist` 进行，不穿透内部类。
- **R-08 A-5 硬要求**：不得跨类调用私有 `_persist()`——V0 中 life 侧直接调用 Individual 私有持久化方法是漂移形态；V1 中持久化只经 `persist()`。

## §2 回合原子性（恢复语义）

源：`runtime-boundaries.md` §2。

1. **单回合 = 原子单元**：完成 = 状态已写；未完成 = 弃。不引入 mid-turn checkpoint（YAGNI）。
2. **崩溃代价 = 一个进行中回合**。不引入 Recovery 子系统；回合计数丢失无害。
3. **经验回流 append-only 幂等重导入**：崩溃后可重放未完成的回流导入；去重是 host 集成 adapter 层的职责（见 `spec-adapters.md` §1）。
4. 长回合的触发条件已在 `runtime-boundaries.md` 记录；若触发，恢复语义的复审走 ADR 流程（规则 8），规格不预设机制。

## §3 重启语义（三事件）

源：`container-model.md` §3。

| 事件 | 个体影响 |
|---|---|
| Hermes Desktop 重启 | **个体完全不受影响**（第 3 条"顺势"的个体级表达：手段消失，个体仍在） |
| DaoSheng Runtime 重启 | 持久文件保留；Runtime State 丢失（turn 计数 C-2、open host 会话、open 模型连接、进行中回合）——无需恢复子系统（回合原子性，§2） |
| Model 重启 | 个体不受影响（INV-1）；重连是 adapter 行为（见 `spec-adapters.md` §2） |

## §4 Persistent vs Runtime 判据

源：`runtime-boundaries.md` §1。

- **判据**："个体仍然是谁 / 经历过什么 / 记住了什么 / 会做什么" = **persistent**；"当前进程正在做什么" = **runtime**。
- 分类落点：

| 数据 | 分类 | 规格落点 |
|---|---|---|
| Identity | persistent，immutable | `spec-self-state.md` §1 |
| Continuity | persistent，append-only，单一载体 | `spec-self-state.md` §2 |
| Memory | persistent，经 Memory Interface | `spec-memory.md` |
| Capability 四目录 | persistent | `spec-capability.md` |
| Faculties 8 根状态 | persistent | `spec-self-state.md` §3 |
| 回合计数（C-2）/ `last_action_experience_id`（C-1） | runtime，不持久 | `spec-self-state.md` §2（C-1/C-2 处置） |
| open host 会话 / open 模型连接 | runtime | 本文件 §3 |
| digest 中间产物 | runtime，崩溃即弃 | 本文件 §2 |
| Host 会话记录 | persistent，host-owned（非个体状态） | `spec-adapters.md` §1 |

**个体持久文件清单**（Runtime 容器拥有，`container-model.md` §3）：Identity 载体 / Continuity 单一载体（ADR 0004）/ Memory 存储（embedded SQLite + WAL side files，ADR 0001）/ Capability 四目录 / Faculties 状态——**清单之外的任何文件都不是个体状态**。

## §5 投影文本要求

源：R-12 / M-04 / M-05；INV-7；`data-ownership.md`。

1. **"DaoSheng 与 host 的关系"的表述只出现在 composition root 的声明位**（ADR 0002 决定 4），不进入 Core 生成的任何文本（R-12）。V0 反例：M-04 身份宣称文本出现在 `context_for_turn` / `app.py`。
2. **投影可裁剪、可改写措辞，不得另立来源**（M-05 / D-6：V0 doctrine 6 / decision 7 / reflection 20 三处漂移）；唯一运行时来源见 `spec-composition-root.md` §2。
3. **投影内容不得回流为经历**（INV-7）：D-05 症状级清洗函数在 R-12 根因修复**之前不得删除**（INV-7 硬性顺序）；根因修复后随 R-12 删除（ADR 0002 决定 5 关联项，`spec-adapters.md` §1）。

## §6 依赖装配

- Individual 的**全部依赖构造注入**，自身不创建依赖（R-09：accept don't create）；装配点 = composition root（`spec-composition-root.md` §1）。
- **V1 不设独立 life 层**（ADR 0004 决定 1）：回合机制归 Individual（本文件）；host 会话归 host 集成 adapter 层（`spec-adapters.md` §1）。

## §7 未定项

本对象无"当前无已定值"的未定项：入口形态、原子性、重启语义、投影纪律均已有源出处。实现阶段（STEP 14+）决定的是各方法签名与内部结构，不得反向改变本文件的规范性陈述。
