# V1 Architecture — Container Model

> STEP 12 产出（2026-09-13）。回答：容器 / 进程划分；容器间交互；**Hermes 重启后什么持久**；ADR 0002（host 集成层）的结构落点。

---

## 1. V1 容器拓扑

V1 默认形态 = **单主机、单个体**（幼体阶段，材料 1 §14 最小完整体）。容器划分：

| 容器 | 进程 | Owner | 持有 | 持久化 |
|---|---|---|---|---|
| **DaoSheng Runtime** | Core 进程（DaoSheng 拥有的唯一进程） | 个体（Core） | Identity、Continuity、Memory Ontology、Doctrine 运行时投影、Capability System、Faculties、Runtime State；进程内：Memory Provider adapter（embedded，ADR 0001）、model 调用 adapter、host 集成 adapter 层（ADR 0002，composition root 装配） | 个体持久文件（§3） |
| **Hermes Desktop（host）** | host 进程（外部，host 自己拥有） | host | host 会话记录、host 存储（V0 形态：`profiles/<name>/state.db` 等——该知识属 host 集成层，Core 不感知，M-03）、Desktop UI | host 文件（Core 不拥有） |
| **Cognitive Models（每后端 1..n）** | 本地模型服务进程（V0 形态：Ollama / llama.cpp；**V1 部署 = L4，UNKNOWN 不预设**，U-5） | 部署层 | 模型权重、推理状态 | 模型文件（Core 不拥有） |
| **External World 服务（MCP / research 源等）** | 各异 | 外部 | — | — |

## 2. 容器间交互

| 从 → 到 | 方式 | seam / Interface |
|---|---|---|
| Runtime → Hermes Desktop | host 集成 adapter：启动 host 进程（subprocess 形态 = V0 `life/bridge.py`，M-02）、开启会话、取回会话记录回流 | **host 集成 seam**（hypothetical，单 adapter，ADR 0002）；Interface = 中性概念（回合 / 会话 / 经验回流 / 上下文投影） |
| Hermes Desktop → Runtime | host 不调用 Core 内部 API：经验回流 = host 会话记录 → host 集成层导入 → **Experience 候选**（M-01，Interface = "导入会话 → [Experience 候选]"）；R-12 投影过滤随迁 | 同一 seam（host 集成层是唯一允许知道 host 的层） |
| Runtime → Models | model 调用 adapter：HTTP API（V0 部署形态：Ollama `/v1` / llama.cpp；具体 endpoint / 默认模型 = L4 值，composition root 声明，R-09） | **model 调用 seam**（hypothetical，单 adapter） |
| Runtime → External World | world / research / agent adapter（MCP、research provider、文件观察） | world / research / agent seam；**投影不得回流**（INV-7；根因修复 = R-12，随 ADR 0002 host 集成层落地） |

**进程边界硬要求**：Hermes Desktop 进程不直接触碰 Core 持久文件；一切交互经 host 集成 adapter。V0 反例：`hermes_import.py`（842 行）直接依赖 Hermes 内部 messages 表 schema，且该知识散在 Core growth/ 层（M-01 / M-03 / M-04——收敛见 ADR 0002 决定 5）。

## 3. 重启后什么持久

| 事件 | 个体状态 | 说明 |
|---|---|---|
| **Hermes Desktop 重启** | **完全不受影响** | 个体全部持久状态在 Runtime 的持久文件；host 会话记录是 host 自己的文件——host 重启只丢 host 自身进程状态（open 会话等），个体语义不受影响。第 3 条顺势 L3 的个体级表达：host 是手段，重启 / 移除手段，个体仍在 |
| **DaoSheng Runtime 重启** | 持久文件全部保留；**Runtime State（turn 计数、open host 会话、open 模型连接、进行中回合）丢失** | persistent vs runtime 分类见 `runtime-boundaries.md` §1/§2；无需恢复子系统（回合原子性） |
| **Model 进程重启** | 个体状态不受影响 | Model = 手段（INV-1）；重连 = adapter 行为 |

**个体持久文件清单（Runtime 拥有）**：Identity 载体 / Continuity 单一载体（ADR 0004）/ Memory 存储（embedded SQLite + WAL side files，ADR 0001）/ Capability 四目录 / Faculties 状态。清单之外的任何文件都不是个体状态（host 文件、模型文件属各自 owner，`data-ownership.md`）。

## 4. ADR 0002（host 集成层）的结构落点

- **V0 现状（审计事实）**：host 集成层**不存在**——host 知识（Hermes 内部 schema、`profiles/` 路径、Desktop subprocess、host 身份宣称文本）散在 `growth/` / `life/` / `app.py`。M-01…M-04 统一观察：**V0 缺的不是改写代码，而是一个 host 集成层的存在**。
- **V1 落点**（ADR 0002 全文见 `docs/adr/0002-host-integration-layer.md`）：
  - **进程内**：host 集成 adapter 在 DaoSheng Runtime 容器**内**（composition root 装配），不是独立容器——host 本身（Hermes Desktop）是独立容器，但"与它的集成"是 Core 侧 adapter 代码。
  - **层职责**：唯一允许知道 "Hermes" 名字 / 存储路径 / Desktop 进程调用方式的层（M-01…M-05 前提）；对 Core 的 Interface 只含中性概念，无 host 名。
  - **seam 状态**：单 adapter = **hypothetical seam**；第二个 host 实现出现时升格 real，Interface（中性概念）是其契约。
  - **composition root 是声明位**："DaoSheng 与 host 的关系"表述只出现在 composition root 声明（M-04）；host 身份宣称**不得**进入投影文本或 Core——身份宣称进投影会回流污染 Identity 证据链（R-12 联动）。

## 5. 不采用（YAGNI，显式记录）

- **独立 Memory server 容器**：不采用（ADR 0001 决定 2；research §2 选项 B）——V1 单进程语境；多进程 / 多 host 共享需求出现时重评估（research §7 触发 3）。
- **独立模型管理 / 编排容器**：模型部署 = L4 运营策略，不预设（U-5）。
- **多个体 / 多 host 共享容器形态**：不预设（research §7 触发 3）。
