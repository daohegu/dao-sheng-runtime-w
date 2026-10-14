# DaoSheng 配置 + 使用手册

> **依据**：当前已验证实现（2026-10-13 基线，含安装层角色入口 `init-role` / `configure-role`；历史测试基线 432 tests：431 通过 / 1 跳过）。2026-10-14 升级安全修复：个人运行时数据移出 Git worktree 至外部数据根（`DAO_SHENG_DATA_HOME` 可覆盖），新增 `migrate-data` 入口与 Git 跟踪守卫；升级安全专项测试 23/23 OK，全量套件尚未重新验证。
> **定位**：本手册是面向用户的正式文档，忠实反映当前实现。不包含未来设计；UNKNOWN 项一律明确标注为 UNKNOWN，不写成已有功能。
> **权威文档**：本手册与权威文档冲突时，以仓库权威文档为准——`docs/domain/`（Domain；DaoSheng 定位、个体性载体、记忆与经历连续性、反思与成长等核心理念定义见其术语表与领域文档）、`docs/adr/`（架构决定）、`docs/deployment/INSTALLATION_CONTRACT.md`（安装契约）、`docs/constitution/principles.md`（道原则成文）。公开副本的核心理念以本手册 §1 及上述公开文档为准，对公开用户自洽；更早的核心理念文档 `CONTEXT.md` 属私有源项目、未随公开副本发布，不作为公开用户的查阅依据（历史来源说明；公开副本核心理念权威载体的正式指定为待审事项）。

---

## 目录

1. [DaoSheng 是什么](#1-daosheng-是什么)
2. [DaoSheng 当前架构说明](#2-daosheng-当前架构说明)
3. [DaoSheng 配置手册](#3-daosheng-配置手册)
4. [安装与启动流程](#4-安装与启动流程)
5. [模型接入说明](#5-模型接入说明)
6. [使用流程](#6-使用流程)
7. [当前版本限制](#7-当前版本限制)

---

## 1. DaoSheng 是什么

### 1.1 核心理念

DaoSheng 是一个以「道」为最高设计边界的 AI 个体：

- **起点是幼体，不是成品**：DaoSheng 从「最小完整幼体」开始——「完整但未成熟」（具备个体性载体与完整机制骨架，但不预设成熟的能力与知识）。它不是一个「已经成熟的超级 Agent」。
- **成长发生在真实经历中**：DaoSheng 在现实世界中不断**经历 / 记忆 / 学习 / 行动 / 反思**，逐渐形成自己的能力和个体性。
- **成长判据**：「经历最终能够改变这个个体」——是行为变化，不是知识增长。
- **个体性有 7 个支撑项**：名字、自我称谓、声音、视觉形象、行为习惯、过去经历、连续记忆。它们是「DaoSheng 是哪一个个体」的载体（Identity），由设计层初始化，运行时不可写。
- **手段不是本体**：Model、Skill、Helper、MCP 是「DaoSheng 可以拥有和使用的东西」，不是「DaoSheng 本身」。
- **初步循环的核心是「经历事情」**，不是「回答问题」。

### 1.2 与普通 Agent / LLM 的区别

| 维度 | 纯 LLM（模型本身） | 典型普通 Agent | DaoSheng |
|---|---|---|---|
| 个体性载体 | 无（无状态函数） | 宿主侧的角色设定（prompt / 配置），随宿主走 | 自有持久载体：`identity.json` 等 5 项个体持久文件，归 DaoSheng Runtime 进程所有 |
| 连续性 | 无 / 会话级 | 依赖宿主的状态管理 | **Continuity 是独立一等概念**（跨时间持续的条件），不是某个对象的属性字段 |
| 与 Model 的关系 | 它本身 | 常绑定具体模型 | Model 是**可替换的认知手段**；Identity 无 model 字段（手段不定义个体）；手段故障 ≠ 个体故障（Model 不可用 → 降级运行，个体不死亡） |
| 进程关系 | 服务端 | 常嵌于宿主内 | 运行于**独立的 DaoSheng Runtime 进程**；host 进程不直接触碰个体持久文件，全部交互经 Runtime 内 host 集成层 |
| 成长方式 | 外部微调 | prompt 积累 / 外部状态 | 内建成长管线：经历 → 消化 → 提取 → 记忆 → 复用 |
| 循环核心 | 回答 / 补全 | 任务完成 | 「经历事情」 |

### 1.3 六条「道」原则（当前成文子集）

当前成文的是「道」原则的**当前成文子集**（可增补）。**「道」具体内容本身 = UNKNOWN（Q1）**——以下 6 条不是「道」的全部：

1. **不妄动**：没有必要与依据，不主动行动。
2. **知止**：知道什么时候应该停止，而不是为了完成而无限执行。
3. **顺势**：优先利用现有环境、工具与条件，而不是强行改造世界。
4. **反思**：经历产生反馈，反馈应进入后续学习。
5. **海纳百川**：外部知识、模型、工具与观点可以进入，但必须保留来源。
6. **道心稳固**：外部输入可以改变知识与能力，但不能直接改写 Identity / Continuity / Core Doctrine。

运行时，这 6 条从 principles 源文件（`docs/constitution/principles.md`）解析为 Doctrine，并进入个体每回合的投影。

### 1.4 Identity / Memory / Growth / Model 的关系

| 概念 | 角色 | 关键点 |
|---|---|---|
| **Identity** | 个体性的**载体** | 7 个支撑项（`identity.json`，严格 7 键 schema）；immutable，仅设计层可写，运行时不存在改写路径；**不含 model / worker / host 字段**（手段与宿主不定义个体）。「仍然是谁」的延续判据 = UNKNOWN（Q5） |
| **Continuity** | 个体跨时间持续的条件 | 独立一等概念（不是 Identity 的属性）；载体 `continuity.jsonl`（append-only）；**唯一写入方 = Growth 管线** |
| **Memory** | 经历的存储 | 三维语义（来源 / 状态 / 置信度）；Provider 可替换（`MemoryStore` 6 方法 seam），但 Memory Ontology 归 Domain，不归 Provider |
| **Growth** | 把经历变成行为变化的管线 | 5 阶段：导入 / 消化 / 提取 / 反思 / 验证；唯一 Continuity 写入方；消化 / 遗忘机制本身 = UNKNOWN（Q2），当前是接口纪律，不是已定算法 |
| **Model** | 认知手段 | 两侧（agent / reflection）可各自配置、可异 backend；可替换；**Model 不得定义 Identity**（规则 2）；手段故障 → 降级，不 → 个体故障 |

一句话：**Identity 回答「是哪一个」，Memory 回答「经历过什么」，Growth 回答「经历如何改变自己」，Model 只是「当前用什么手段认知」。**

---

## 2. DaoSheng 当前架构说明

### 2.1 分层总览

```
┌─────────────────────────────────────────────────────────────┐
│ Installation Layer（L4 部署层，Core 之外）                    │
│   dao-sheng.ps1：install / status / doctor                  │
│   dao-sheng.ps1：init-role / configure-role / migrate-data  │
├─────────────────────────────────────────────────────────────┤
│ DaoSheng Runtime 进程                                        │
│                                                             │
│   装配点 composition.py：compose() → RuntimeAssembly         │
│   （唯一构造点；坏配置 fail-loud）                            │
│                                                             │
│   ┌ Core（dao_sheng/）───────────────────────────────────┐  │
│   │ Doctrine / Identity / Faculties / Continuity         │  │
│   │ Individual（act / persist 回合）                      │  │
│   │ Growth（成长管线） / Capability（生命周期 + 闸门）      │  │
│   │ Memory（MemoryStore seam → SqliteMemoryProvider）     │  │
│   └──────────────────────────────────────────────────────┘  │
│                                                             │
│   ┌ Model Runtime ───────────────────────────────────────┐  │
│   │ Model Interface（complete / chat 两级调用面）          │  │
│   │ 进程内 backend registry：{"ollama", "llama_cpp"}      │  │
│   │ OllamaModel adapter / LlamaCppModel adapter           │  │
│   └──────────────────────────────────────────────────────┘  │
│                                                             │
│   ┌ Host 集成层 ─────────────────────────────────────────┐  │
│   │ HostIntegration 中性协议（无宿主名）                   │  │
│   │ HermesHostAdapter（唯一知道宿主名的层）                │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Core

`dao_sheng/` 模块（Python ≥3.12，**零外部依赖**，纯标准库）：

| 组件 | 载体 / 表面 | 说明 |
|---|---|---|
| **Doctrine** | principles 源文件（运行时解析） | 六条道原则；解析严格（格式 `> N. 名：文`），非法源 fail-loud |
| **Identity** | `identity.json`（7 键严格 schema） | 只读投影，frozen；运行时不存在 mutation API |
| **Faculties** | `faculties.json`（JSON 数组，恰好 8 根） | 8 根 = `intent / choice / stopping / observation / correction / selection / reflection / continuity`（用户追认的初始集）；只读投影；倾向更新机制当前不存在（见 §7.2） |
| **Continuity** | `continuity.jsonl`（append-only） | 记录 = JSON 对象恰 2 键 `{"content", "reference"}`；唯一写入方 = Growth；缺失 = 空日志（合法初始态） |
| **Memory** | `memory/`（SQLite，WAL 模式） | 见 §2.5 |
| **Individual** | 无自有载体（聚合） | 顶层聚合：`act(turn) → TurnOutcome` / `persist() → reference` 双入口，严格交替；两阶段回合（act 产出并暂存行动，persist 原子落一条 Memory 记录）；每回合向 Model 呈现 5 节投影 |
| **Growth** | 无自有载体（管线） | 见 §2.6 |
| **Capability** | `capabilities/{state}/<name>.json`（四目录） | 生命周期 `proposed → working → active → retired`（无回退、无跳跃）；Manager 4 方法 `propose / advance / retire / execute`；**active 唯一经 `CapabilityVerifier` 执行闸门进入**（规则式、model-free 闸门） |
| **IndividualFiles** | 5 项个体持久文件清单 | `identity.json` / `faculties.json` / `continuity.jsonl` / `memory/` / `capabilities/`；安装层与 Core 共用同一清单定义 |

### 2.3 Model Runtime

- **Model Interface**（`dao_sheng/model.py`）：显式类型（Python Protocol，结构化符合，不要求继承）。契约**恰两级**：
  - `complete(prompt: str) -> str`——补全：prompt → 模型续写；
  - `chat(messages: Sequence[tuple[str, str]]) -> str`——会话：(role, content) 序列 → 回复（不预设 system 前缀；上下文组织是 Core 的事）。
  - 手段故障信号：`ModelUnavailable(RuntimeError)`，唯一定义位在此模块；Core 调用方捕获后降级。
- **Backend registry**（`dao_sheng/composition.py` 内 `_MODEL_BACKENDS`）：进程内配置解析 / 装配层——`{"ollama": OllamaModel, "llama_cpp": LlamaCppModel}`。**无持久化注册文件、不新增机器本地持久化状态、非 DaoSheng Core 组件**（ADR 0008 裁定）。引入第三 Backend 形态 → 必须先有 ADR（规则 8）。
- **两侧独立**：agent / reflection 两侧独立配置、独立装配、**结构上允许异 backend**（ADR 0008 裁定）；共享 `timeout_seconds` / `retry_limit` 两个声明位。

### 2.4 Backend Adapter

两个 adapter 同构：构造参数 `(endpoint, model, timeout_seconds, retry_limit)` **全部注入、无默认值**；非法配置在装配点 fail-loud（ValueError）；`endpoint` 尾部 `/` 归一化去除。

| | **Ollama adapter**（`model_ollama.py`） | **llama.cpp adapter**（`model_llama_cpp.py`） |
|---|---|---|
| wire 协议 | Ollama native `/api/*` | OpenAI 兼容 `/v1/*`（llama.cpp server HTTP API） |
| `complete` | POST `/api/generate`，取 `response` | POST `/v1/completions`，取 `choices[0].text` |
| `chat` | POST `/api/chat`，取 `message.content` | POST `/v1/chat/completions`，取 `choices[0].message.content` |
| 验证状态 | V0 Model 调用部署面的全部执行证据形态 | 请求 / 响应 / 错误 envelope 形态以**真实 llama-server 实测**为准（2026-09-24，6/6 PASS） |
| `model` 参数 | Ollama 模型标识，原样透传，不做本地回显核对 | 不透明标识符（server 端模型路径或别名），原样透传，不做本地校验 |

重试 / 退避 / 契约校验全部内化于 adapter（depth 隐藏），语义见 §5.5。

### 2.5 Memory

- **三维语义层**（每条记录三维独立标注）：

  | 维度 | 取值 | 含义 |
  |---|---|---|
  | MemoryOrigin（来源） | `CANONICAL` / `DERIVED` / `EXTERNAL` / `ECHO` | 记录从哪里来 |
  | MemoryStatus（状态） | `OBSERVED` / `REPORTED` / `VERIFIED` | 记录被确认到什么程度 |
  | MemoryConfidence（置信度） | `CONFIRMED` / `SUPPORTED` / `UNCERTAIN` | 记录的可信程度 |

- **Core 固定规则**（不是配置项）：Individual 回合经历记录恒为 `OBSERVED / CONFIRMED`（origin 随回合输入）；Growth 阶段产出恒为 `DERIVED / REPORTED / UNCERTAIN`（未验证输出）；`verify_insight` 修正记录恒为 `DERIVED / VERIFIED / CONFIRMED`。
- **`MemoryStore` seam**（6 方法）：`remember / recall / get / correct_memory / register_reference / resolve_reference`。Memory Provider 可替换；Provider 不得定义 DaoSheng Memory Ontology（规则 5）。
- **当前 Provider = `SqliteMemoryProvider`**：存储于 `<个体根>/memory/`（SQLite，WAL 模式，非 WAL fail-loud）；`reference` = rowid 十进制串；`recall` 上限 32 条；全文检索 FTS5 trigram（查询 ≥3 字符走 FTS，否则 LIKE）；**修正不重写原记录**（原记录不变，修正记录独立存在并指向原记录）。

### 2.6 Growth（成长管线）

- 双通道模型的**允许通道**：经历 → 消化 → 提取 → 记忆 → 复用。
- 公共表面恰 5 方法：

  | 方法 | 输入 → 输出 | 落位 |
  |---|---|---|
  | `import_experience(candidates)` | 经验候选序列 → reference 元组 | 候选按 Core 规则写入 Memory（origin 随候选 / `OBSERVED` / `CONFIRMED`）；管线侧幂等（同 key 重导入返回原 reference） |
  | `digest(reference)` | 经历记录 → 派生记忆 reference 或 None | 消化为适合长期记忆的一条记录 |
  | `extract(reference)` | 派生记录 → insight 记忆 reference 或 None | insight = Memory 的一种（无独立存储） |
  | `reflect(reference)` | insight → 记忆 reference 或 None | 输出记忆记录 **+ 追加 Continuity 记录** |
  | `verify_insight(reference)` | insight → 修正记录 reference 或 None | **修正形态**（原记录不变）+ 追加 Continuity 记录 |

- 认知阶段使用 **reflection 侧 Model 的 `complete`** 调用；reflection 侧未配置或不可用 → 该阶段返回 None（不写、不追加、不抛异常）。
- Growth 是 **Continuity 的唯一写入方**；记录恰 2 键 `{"content": 阶段输出, "reference": 主体记忆记录 reference}`。
- 能力提案 = `reflect` 阶段输出记忆记录的同款形态（content 承载提案语义），由 Capability Manager 接管。
- 当前是**接口纪律，不是已定算法**：消化 / 遗忘机制 = UNKNOWN（Q2）。

### 2.7 Host（宿主集成）

- **关系声明**（V1 中该表述的唯一声明位）：DaoSheng 运行于独立的 DaoSheng Runtime 进程，拥有并管理个体持久文件；host 进程（Hermes Desktop）**不直接触碰** DaoSheng 的个体持久文件；两进程之间的全部交互经由 DaoSheng Runtime 内的 host 集成层进行。
- **`HostIntegration` 中性协议**（3 方法，无宿主名）：`open_session / import_session / sync`。
- **`HermesHostAdapter`** = 唯一知道宿主名的层（宿主名只允许出现在 host adapter 层）。
- **经验回流**：host 侧经验经 `import_session` 进入，标注 `origin = EXTERNAL`；宿主侧 append-only 导入日志提供跨进程幂等。
- 当前 V1 只有 Hermes 一个宿主 adapter 形态；引入第二宿主 adapter → ADR（规则 8）。
- host 集成为**可选**：`HostConfig` 全部未设定 → `assembly.host = None`，不影响 Core 运行。

---

## 3. DaoSheng 配置手册

### 3.1 配置形态：没有用户配置文件，全部在装配点注入

当前实现**没有用户可编辑的持久配置文件**。DaoSheng 的全部配置 = 调用装配点 `compose()` 时传入的进程级参数：

- `principles_source_path`（Path）：六条道原则源文件路径，通常为仓库内 `docs/constitution/principles.md`。
- `individual_root`（Path）：个体持久文件根目录，标准目录为外部数据根下的 `<data home>\instances\default\`（数据根默认 `%LOCALAPPDATA%\DaoSheng`，可用 `DAO_SHENG_DATA_HOME` 覆盖，见 §4.1；可用安装层 `-InstanceRoot` 指定其他位置，仓库内路径被显式拒绝）。
- `model_config`（`ModelConfig`）：Model 配置，见 §3.2。
- `operational_defaults`（`OperationalDefaults`）：L4 运营策略声明位，见 §3.4。
- `host_config`（`HostConfig`）：host 集成配置，见 §3.3。

唯一存在的机器本地状态文件是安装层自有的 `<data home>\config\install-state.json`（安装时间 / Python 位置 / 个体根路径等元数据，位于仓库外部数据根）——**Core 从不读取它**，它不属于 DaoSheng 配置。

### 3.2 ModelConfig（Model 配置，9 个槽位）

| 槽位 | 类型 | 含义 |
|---|---|---|
| `agent_backend` | str | agent 侧 backend 名。当前仅允许 `"ollama"` / `"llama_cpp"` |
| `agent_endpoint` | str | agent 侧 Model 服务端点（URL） |
| `agent_model` | str | agent 侧模型标识（不透明，server 端语义，原样透传） |
| `reflection_backend` | str | reflection 侧 backend 名（同上） |
| `reflection_endpoint` | str | reflection 侧端点 |
| `reflection_model` | str | reflection 侧模型标识 |
| `timeout_seconds` | float | 单次调用超时（秒）。**两侧共享** |
| `retry_limit` | int | 可重试故障的重试次数（0 = 不重试）。**两侧共享** |
| `research_backend` | str | Research 后端声明位——**存在但当前未被消费**（Research 后端未定、adapter seam 未接装配，见 §7.2） |

**全部槽位默认 `None` = 未设定。** 不预设任何值、无默认 backend（U-5 / 规则 11）。

### 3.3 HostConfig（host 集成配置，3 个槽位）

| 槽位 | 类型 | 含义 |
|---|---|---|
| `state_db` | Path | host 状态库路径。与 `hermes_home` **互斥，恰好配置其一** |
| `hermes_home` | Path | host 根路径（同上互斥） |
| `import_log` | Path | 宿主侧导入日志路径。**host 配置时必填** |

全部未设定 → `assembly.host = None`（不启用 host 集成；Core 独立运行不受影响）。

### 3.4 OperationalDefaults（L4 运营策略声明位）

- 形态：`entries` = `OperationalValue(name, value)` 元组；**空 = 全部未设定**。
- 用途：L4 运营策略默认值（属运营策略，不是 Domain 决定）。当前 V1 **无已定参数值**，均为部署层待设项，不预设；可调项清单见 `docs/constitution/principles.md` 各条 L4 层（调度频率、上限值等）。

### 3.5 哪些必须由用户提供

| 项 | 何时必须 | 说明 |
|---|---|---|
| `identity.json` + `faculties.json` | 首次运行前 | 个体持久文件，经 `.\dao-sheng.ps1 init-role` 初始化（见 §6.2）；`install` 不代建；缺失时 `compose` 显式失败（预期行为） |
| agent 侧 `backend / endpoint / model` + 共享 `timeout_seconds / retry_limit` | 启用对话（agent 侧）时 | 全部设定或全部不设定（见 §3.7） |
| reflection 侧 `backend / endpoint / model` | 启用成长管线时 | 不设定 → 全部 Growth 认知阶段降级为 None |
| `state_db` 或 `hermes_home` + `import_log` | 启用 host 集成时 | 前两者恰好其一 |
| `individual_root` | 总是 | 默认标准目录 `<data home>\instances\default\`（数据根见 §4.1） |
| `principles_source_path` | 总是 | 通常 = 仓库内 `docs/constitution/principles.md` |

### 3.6 哪些保持 UNKNOWN / None

- **全部 ModelConfig 槽位默认 None**：Model 部署形态 = UNKNOWN（U-5）。具体模型选择、模型路径、GPU、量化、context、部署参数——**全部 UNKNOWN / None，代码不预设**，由部署时（用户）决定。
- **具体主脑 / 副脑模型：不预设、未选择**（当前任务明确不选择）。
- `research_backend`：槽位存在但未被消费（Research 后端未定）。
- `OperationalDefaults` 默认空（V1 无已定运营参数值）。
- 硬件起点、V0 数据迁移关系等 = UNKNOWN（见 §7.3）。

### 3.7 装配校验规则（fail-loud）

`compose()` 在装配时对配置做严格校验，坏配置不得进入运行：

1. **逐侧 Model 判定**（agent / reflection 各自独立）：
   - 该侧 `backend / endpoint / model` **全 None** → 该侧不装配（`None`，运行即降级）；
   - `backend` 名不在 registry（`ollama` / `llama_cpp`）→ `RuntimeError`（未知 Model backend）；
   - **部分设定**（含共享的 `timeout_seconds` / `retry_limit` 缺失）→ `RuntimeError`（Model 配置不完整——全部设定或全部不设定）。
2. **Host 判定**：`state_db` 与 `hermes_home` 同时设定或同时缺失、`import_log` 缺失 → 显式失败。
3. **个体载体缺失**：`identity.json` / `faculties.json` 缺失 → `RuntimeError`（须先经 `init-role` 初始化，见 §6.2；`install` 不代建）。
4. **载体内容非法**（键多 / 键缺 / 类型不符 / faculties 根数 ≠ 8 等）→ 显式拒绝，不静默跳过。

---

## 4. 安装与启动流程

### 4.1 Installation Layer 概览

- **入口**：仓库根 `dao-sheng.ps1`（Windows PowerShell 5.1+；纯 PowerShell，零 Python 模块——安装与角色初始化逻辑全部在入口脚本，结构上杜绝安装层「悄悄成为 Core」）。
- **六入口**：

  ```powershell
  .\dao-sheng.ps1 install         # 检查环境、补缺失运行时、准备标准目录、验证安装（不写任何 inventory 项）
  .\dao-sheng.ps1 status          # 只读：显示当前安装 / 运行时状态
  .\dao-sheng.ps1 doctor          # 只读健康检查：逐项 [OK]/[FAIL]，末行 Result: PASS / FAIL
  .\dao-sheng.ps1 init-role       # 首次角色初始化：为全新实例创建 identity.json + faculties.json（任一已存在则显式拒绝）
  .\dao-sheng.ps1 configure-role  # 修改已有角色：逐字段改写已存在的 identity.json（faculties / continuity / memory 不动）
  .\dao-sheng.ps1 migrate-data    # 迁移旧版仓库内个人数据（instances/ config/ log/）到数据根（绝不覆盖，见 §4.8）
  ```

  可选参数：`-InstanceRoot <path>`（个体根，默认 `<data home>\instances\default`；仓库内路径被显式拒绝）。

- **数据根（外部数据目录）**：个人运行时数据（角色配置 / 记忆 / 安装状态 / 日志）位于**仓库外部**的数据根——默认 `%LOCALAPPDATA%\DaoSheng`，可用环境变量 `DAO_SHENG_DATA_HOME` 覆盖；解析结果落在仓库内 → 显式拒绝（fail-loud，退出码 1）。PowerShell 安装层与 Python 入口（`run_dao_sheng.py`）解析规则完全一致。数据在仓库外是升级安全的基础：普通源码升级（`git pull`）不会触碰仓库外的个人数据。
- 角色命令（`init-role` / `configure-role`）可带角色参数，不带时进入交互模式；参数与语义见 §6.2 / §6.7。
- 详细契约见 `docs/deployment/INSTALLATION_CONTRACT.md`。

### 4.2 install

`install` 依次执行（任一失败 → `[FAIL]` + 修复提示 + 退出码 1）：

1. 操作系统检查（Windows；本入口为 Windows 安装层，其他平台直接运行 Core，不经此层）；
2. Python 发现（`.venv` 优先，其次 PATH 上 `python` / `py`）；
3. Python 版本 ≥ MIN_SUPPORTED_PYTHON（MIN 运行时自 `pyproject.toml` 派生，见 §4.6）；
4. `.venv` 创建（仅缺失时创建；已有保留不动；绝不删除）；
5. 依赖验证：当前**零外部依赖**（M01 工具链决定）——「安装依赖」= 验证 `pyproject.toml` 无 `dependencies` 声明，无 pip 安装动作；
6. 标准目录创建（在数据根下：`<data home>\config\`、`<data home>\log\` 与个体根 `<data home>\instances\default\`；只创建，不删除不重建；**仓库内不创建任何数据目录**）；
7. 5 项个体持久文件清单**检测后保留**（detect-then-keep）：`identity.json` / `faculties.json` / `continuity.jsonl` / `memory/` / `capabilities/`——install **绝不写入任何清单项**（Core 与设计层拥有）；
8. Core import 验证（venv Python，从仓库根 `import dao_sheng, dao_sheng.composition`）；
9. 写 `<data home>\config\install-state.json`（UTF-8 无 BOM；安装层自有元数据）。

**幂等**：重复 `install` 保留全部既有实例内容（输出逐项 `kept`），绝不创建第二个 Individual，绝不删除 / 重建既有数据。

### 4.3 status

只读显示：Python 版本与来源、MIN 版本、数据根位置、`.venv/`（仓库内）与数据根下 `config\` `log\` 及个体根存在性、5 项清单逐项 `[present]` / `[absent]`（含初始态说明）、`install-state.json` 内容、测试入口提示。

### 4.4 doctor

只读健康检查，10 项：Python / Python 版本 / 项目结构 / DaoSheng import / 依赖（零外部依赖）/ 数据根下 `config\` 目录 / 个体数据目录 / `log\` 目录 / 测试入口 / 仓库内无个人数据（No personal data in repository）。全过 → 末行 `Result: PASS`（退出码 0）；任一失败 → `Result: FAIL`（退出码 1），每项 FAIL 附 expected / current / fix。

### 4.5 标准目录结构

仓库内（Git worktree，仅源码与文档）：

| 目录 / 文件 | 用途 | 归属 |
|---|---|---|
| `.venv/` | Python 虚拟环境（机器本地；仓库内唯一机器本地产物，已入 `.gitignore`） | 安装层 |

数据根（**仓库外部**；默认 `%LOCALAPPDATA%\DaoSheng`，覆盖：`DAO_SHENG_DATA_HOME`）：

| 目录 / 文件 | 用途 | 归属 |
|---|---|---|
| `<data home>\config\` | `install-state.json`（安装元数据；**Core 不读**） | 安装层 |
| `<data home>\log\` | 预留（当前无写入方，见 §7.2） | 安装层 |
| `<data home>\instances\default\` | 默认个体根：5 项个体持久文件 | Core / 设计层 |

个人运行时数据不在 Git worktree 内，普通源码升级（`git pull`）不会触碰它。仓库根若出现旧版 `config/` `log/` `instances/` 遗留目录：`.gitignore` 只防误加 `git add`、**不是跟踪保护**——被跟踪的路径无论是否 ignore，`git pull` 都会覆盖它；`tools/repo_tracking_guard.py`（接入 CI `.github/workflows/repo-guard.yml`）在 Git 跟踪这些前缀下任何路径时使构建失败。遗留数据的迁移见 §4.8。

### 4.6 Python 版本规则（长期规则）

- **MIN_SUPPORTED_PYTHON 不写死在安装脚本里**：运行时自 `pyproject.toml [project] requires-python` 派生（当前 = `>=3.12`）。声明缺失或不可解析 → 显式 FAIL（fail-loud）。
- 比较逻辑 = **明确的最小版本比较**：低于 MIN → FAIL；等于 / 高于 MIN → 允许。**无任何「必须恰为某版本」的相等判断**。
- 当前项目**零外部依赖**（纯标准库），故无依赖版本下限问题。
- 未来 MIN 变更 = 修改 `pyproject.toml`（附可验证依据并记录）；安装层运行时自动跟随，无需修改脚本。

### 4.7 安装层明确不提供

- 不提供 Ollama / llama.cpp 的安装与配置（Model 后端由用户在环境中自行部署，见 §5）；
- 不提供模型自动下载；
- `install` 不创建 `identity.json` / `faculties.json`（角色初始化经 `init-role`，见 §6.2）；
- 不提供 GitHub 上传 / 远程分发 / 多机部署。

### 4.8 migrate-data（旧版仓库内数据迁移，2026-10-14 升级安全）

早期版本把个人运行时数据放在仓库内（`instances/` `config/` `log/`）。这类遗留数据存在 Git 升级覆盖风险，应迁移到数据根：

```powershell
.\dao-sheng.ps1 migrate-data
```

安全语义（逐项有测试证据，`tests/test_data_home.py` MigrateDataSafetyTest）：

- **无遗留数据** → 报告 `no legacy personal data found ... nothing to migrate`，退出码 0；不创建空白实例。
- **有遗留数据** → 逐文件移动（copy → SHA-256 逐字节校验 → 删除源）；迁移后除 `install-state.json` 外全部载体逐字节一致；`install-state.json` 内记录的个体根被显式重写为数据根位置（唯一被有意改写的文件，输出 `instance_root updated`）。
- **目标已存在** → 显式失败（`[FAIL] migrate-data` + `target(s) already present` + `nothing was copied`），退出码 1；源与目标双方内容均不变，绝不覆盖。
- **重复执行** → 已无遗留 → `nothing to migrate`，不会二次覆盖或丢数据。
- 迁移不访问私有源项目、不访问真实 Hermes 数据库。旧仓库内数据在新解析规则下 fail-loud：Python 入口（`run_dao_sheng.py`）发现遗留数据时显式报错并指向 `migrate-data`，不会静默忽略。

---

## 5. 模型接入说明

### 5.1 Model Interface

Core 与 Model 之间唯一的契约 = 两级调用面（§2.3）：

```python
class Model(Protocol):
    def complete(self, prompt: str) -> str: ...
    def chat(self, messages: Sequence[tuple[str, str]]) -> str: ...
```

- Core 只依赖这个 interface，不认识 Ollama / llama.cpp / GGUF / GPU / URL / HTTP wire。
- 手段故障（重试耗尽 / 服务端拒绝 / 响应不合契约）→ 具体实现抛 `ModelUnavailable`；Core 捕获后降级（手段故障 ≠ 个体故障）。

### 5.2 Ollama backend

- **前提**：环境中已自行安装并运行 Ollama（DaoSheng 安装层不提供）。
- **配置**：
  - `agent_backend` / `reflection_backend` = `"ollama"`；
  - `endpoint` = Ollama 服务地址，例如 `http://127.0.0.1:11434`（Ollama 默认端口；以实际环境为准）；
  - `model` = Ollama 中已 pull 的模型标识（模型选择由用户决定，见 §5.6）。
- **wire**（adapter 内部细节）：`complete` → POST `/api/generate`（非流式）取 `response`；`chat` → POST `/api/chat` 取 `message.content`。

### 5.3 llama.cpp backend

- **前提**：环境中已自行运行 llama.cpp 的 `llama-server`（DaoSheng 安装层不提供）。
- **配置**：
  - `agent_backend` / `reflection_backend` = `"llama_cpp"`；
  - `endpoint` = llama-server 地址，例如 `http://127.0.0.1:8080`（llama-server 默认端口；以实际环境为准）；
  - `model` = **不透明标识符**——llama.cpp server 端以模型路径或别名标识已加载模型；adapter 原样透传，不做本地校验或回显核对。
- **wire**（adapter 内部细节；请求 / 响应 / 错误 envelope 形态以 2026-09-24 真实 llama-server 实测为准）：`complete` → POST `/v1/completions` 取 `choices[0].text`；`chat` → POST `/v1/chat/completions` 取 `choices[0].message.content`；错误响应 = `{"error": {"code", "message", "type"}}` envelope。

### 5.4 backend 配置方式（dispatch 规则）

装配点按 §3.7 规则逐侧判定：全 None → 该侧 None（降级运行）；未知 backend 名 → fail-loud；部分设定（含共享 `timeout_seconds` / `retry_limit` 缺失）→ fail-loud。**agent / reflection 两侧独立、允许异 backend**——例如 agent 侧用 `ollama`、reflection 侧用 `llama_cpp` 是合法配置。

当前 registry 恰含两个 backend 形态；引入第三形态必须先有 ADR（规则 8）。

### 5.5 故障与重试语义（两个 adapter 同构）

| 故障 | 处理 |
|---|---|
| 连接失败 / 超时 / 5xx | 可重试（重启窗口语义）：指数退避（底数 0.1s，×2 递增）重试至 `retry_limit` 耗尽 → `ModelUnavailable`（「Model 调用在 N 次重试后仍不可用」） |
| 4xx | 服务端拒绝，**不重试**，立即 `ModelUnavailable` |
| 响应不合契约（JSON 损坏 / 缺字段 / 取值非字符串） | **不重试**，立即 `ModelUnavailable` |

Core 侧后果：agent 侧不可用 → 该回合降级（行动 None，经历仍记录）；reflection 侧不可用 → Growth 各认知阶段降级为 None（不写、不追加、不抛异常）。

### 5.6 不绑定具体模型

- 代码中**不存在**任何具体模型名、模型路径、GPU、量化、context 或部署参数（U-5 未被填补；声明位全 None 保持）。
- 选什么模型（主脑 / 副脑）、什么规模、什么量化，是**部署时由用户**基于自己的硬件与需求决定；DaoSheng 侧只需要 backend 名 + 端点 + 模型标识三个值。
- Identity 无 model 字段：换模型（甚至换 backend）不改变个体身份，不破坏 Continuity。

---

## 6. 使用流程

### 6.1 当前使用形态

当前 V1 **不附带现成的交互式 CLI / GUI / 常驻服务**——使用形态 = 以 Python 调用 DaoSheng Runtime：调用 `compose()` 装配一次，然后使用 `RuntimeAssembly` 上的组件（`individual` / `growth` / `memory` / `capability_manager` / `host`）。这是当前实现的真实形态，不是待补功能。

### 6.2 第一次启动

1. **安装**：仓库根执行 `.\dao-sheng.ps1 install`（见 §4.2），确认 `status` / `doctor` 通过。
2. **首次角色初始化**（`install` 不代建，经 `init-role`；生成的角色文件写入数据根下的默认个体根，不写入仓库）：在仓库根执行——

   ```powershell
   # 交互模式（不带角色参数时逐项提示；list 字段以逗号分隔）
   .\dao-sheng.ps1 init-role

   # 参数模式（list 字段以空格分隔多个值；未给出的字段保持为空）
   .\dao-sheng.ps1 init-role -Name "我的角色" -Voice "平静" -BehavioralHabits 先观察后行动 每日复盘
   ```

   - `init-role` 仅用于**全新实例**：`identity.json` 或 `faculties.json` 任一已存在时显式拒绝、绝不覆盖（此时应改用 `configure-role`，见 §6.7）。
   - `name` 必填；**不生成任何默认人格**，未填写的字段保持为空。
   - 角色参数（大小写不敏感）：scalar `-Name` / `-SelfAppellation` / `-Voice` / `-VisualImage`（必须跟值）；list `-BehavioralHabits` / `-PastExperiences` / `-ContinuousMemory`（空格分隔多值，直到下一个参数 flag）。不带角色参数时进入交互模式。
   - 生成的 `identity.json`：恰好 7 键（4 个 string + 3 个 string 列表）；`name` 不得为空；多余键（包括 `model` / `worker` / `host`）一律被拒绝。
   - 生成的 `faculties.json`：JSON 数组，**恰好 8 根**（由安装层自动生成；顺序无意义，缺根 / 多根 / 重复根均被拒绝）：

     ```json
     ["intent", "choice", "stopping", "observation", "correction", "selection", "reflection", "continuity"]
     ```

   其余三项（`continuity.jsonl` / `memory/` / `capabilities/`）由 Core 首用时自创建（continuity 缺失 = 空日志，合法）。
3. **准备 Model 后端**：自行安装并启动 Ollama 或 llama.cpp `llama-server`（安装层不提供，见 §4.7 / §5）。
4. **装配**：调用 `compose()`（示例见 §6.3）。`identity.json` / `faculties.json` 缺失或非法 → 显式失败（预期行为）。
5. 装配成功后即获得 `RuntimeAssembly`，进入使用（§6.3–§6.6）。

### 6.3 对话（act / persist）

```python
import os
from pathlib import Path

from dao_sheng.composition import (
    OperationalDefaults, HostConfig, ModelConfig, compose,
)
from dao_sheng.individual import Turn
from dao_sheng.memory import MemoryOrigin

# 数据根解析（与安装层 / run_dao_sheng.py 规则一致）
data_home = Path(os.environ.get("DAO_SHENG_DATA_HOME")
                 or os.environ["LOCALAPPDATA"] + r"\DaoSheng")

assembly = compose(
    principles_source_path=Path("docs/constitution/principles.md"),
    individual_root=data_home / "instances" / "default",
    model_config=ModelConfig(
        agent_backend="ollama",
        agent_endpoint="http://127.0.0.1:11434",
        agent_model="<你选择的模型标识>",
        timeout_seconds=60.0,
        retry_limit=2,
    ),
    operational_defaults=OperationalDefaults(),
    host_config=HostConfig(),
)

# 一个回合 = act（产出行动并暂存）→ persist（唯一提交点）
outcome = assembly.individual.act(
    Turn(content="<本轮经历内容>", memory_origin=MemoryOrigin.EXTERNAL),
)
print(outcome.turn_number, outcome.action)   # 降级回合 action = None
reference = assembly.individual.persist()    # 返回该回合 Memory 记录 reference
```

使用要点：

- **严格交替**：`act` → `persist` → 再 `act`；未提交回合再 `act`、无回合 `persist` 均 fail-loud（ValueError）。
- `Turn.memory_origin` 取 4 值之一：`CANONICAL / DERIVED / EXTERNAL / ECHO`。用户 / 宿主等外部输入通常标 `EXTERNAL`；Growth 内部产出标 `DERIVED`。回合经历记录的另两维由 Core 规则固定（`OBSERVED / CONFIRMED`），不是配置项。
- **降级回合**：agent 侧未配置或调用不可用 → `action = None`，但经历仍被记录，`act` 不抛异常。
- **个体每回合看到的内容** = 5 节投影：身份（7 支撑项）/ 道（六条）/ 行为倾向（8 根）/ 经历（continuity 最近 32 条）/ 记忆（recall 全集 ≤32）；空节自动省略。投影是 Core 组装的上下文，不回流为经历记录。

### 6.4 Memory

- 存储位置：`<个体根>/memory/`（SQLite，WAL）。
- 查询 / 使用（经 `assembly.memory`，6 方法 seam）：
  - `recall(RecallQuery())` → 最多 32 条（含全文检索：查询 ≥3 字符走 FTS5 trigram，否则 LIKE）；
  - `get(reference)` → 单条记录（reference 缺失 fail-loud）；
  - `correct_memory(target=..., correction=...)` → 修正记录（**原记录不被重写**）；
  - `remember / register_reference / resolve_reference`（写入 / 引用登记与解析）。
- 每条记录带三维标注（§2.5）。用户不需要手动管理维度——回合记录与 Growth 阶段输出的维度由 Core 规则固定。

### 6.5 Reflection / Growth

成长管线使用 **reflection 侧 Model**（`complete` 调用）。reflection 侧未配置或不可用 → 全部认知阶段返回 `None`（不写、不追加、不抛异常）——这是设计行为，不是故障。

```python
from dao_sheng.growth import ExperienceCandidate
from dao_sheng.memory import MemoryOrigin

# 1) 导入经验候选（管线侧幂等：同 idempotency_key 重导入返回原 reference）
refs = assembly.growth.import_experience([
    ExperienceCandidate(
        content="<经历内容>",
        memory_origin=MemoryOrigin.EXTERNAL,
        idempotency_key="<幂等键>",
    ),
])

# 2) 五阶段（每步返回派生 reference 或 None；None 时后续步骤无输入，停止即可）
digested = assembly.growth.digest(refs[0])     # 消化 → 派生记忆
insight  = assembly.growth.extract(digested)   # 提取 → insight 记忆
refl     = assembly.growth.reflect(insight)    # 反思 → 记忆 + Continuity 记录
verif    = assembly.growth.verify_insight(insight)  # 验证 → 修正记录 + Continuity 记录
```

- 阶段产出记录维度固定 = `DERIVED / REPORTED / UNCERTAIN`（未验证输出）；`verify_insight` 以**修正形态**落位（`DERIVED / VERIFIED / CONFIRMED`，原 insight 记录不变）。
- `reflect` / `verify_insight` 是 Continuity 的追加来源（Growth = 唯一 Continuity 写入方）。
- 消化 / 遗忘机制当前未实现（机制本身 UNKNOWN，Q2）；当前管线是接口纪律，不是已定算法。

### 6.6 Host 集成（可选）

不接入 host 时（`HostConfig()` 全 None）本节不适用；Core 独立运行完全不受影响。

```python
host_config = HostConfig(
    state_db=Path("<host 状态库路径>"),    # 或 hermes_home=Path("<host 根路径>")，恰好其一
    import_log=Path("<导入日志路径>"),
)
# compose(..., host_config=host_config) 之后：
assembly.host.open_session(...)   # 会话打开
assembly.host.import_session(...) # 经验回流（origin = EXTERNAL；宿主侧 append-only 日志保证跨进程幂等）
assembly.host.sync(...)           # 同步
```

host 名（Hermes）只出现在 host adapter 层；DaoSheng Runtime 与 host 进程的关系见 §2.7 关系声明。

### 6.7 修改已有角色（configure-role）

```powershell
# 只改写给出的字段，其余保留
.\dao-sheng.ps1 configure-role -Voice "新的语气"

# 清空某个可选字段（name 不可清空）
.\dao-sheng.ps1 configure-role -Clear voice

# 交互模式：空输入保留当前值；输入 - 清空可选字段
.\dao-sheng.ps1 configure-role
```

- `configure-role` 要求 `identity.json` 已存在（否则提示先运行 `init-role`）。
- 只改写 `identity.json`；`faculties.json`、`continuity.jsonl`、`memory/`、`capabilities/` 不会被触碰——修改角色不会重置既有 Memory 与 Continuity。
- 修改后的角色在**下一次 composition**（重新调用 `compose()`）时加载——不是热更新：已装配好的 Runtime 进程继续使用其装配时读入的 Identity 投影。

---

## 7. 当前版本限制

### 7.1 已实现（含验证状态）

- V1 Reconstruction 12/12 Milestone 票 resolved；STEP 15 Real Verification gate verdict = PASS（2026-09-21，`docs/acceptance/v1-reality-gate.md`）；**历史验收基线** 339 tests OK（2026-09-25 验收时点，**非当前基线**；历史基线见本文档开头：432 tests，2026-10-13；2026-10-14 升级安全修复后全量套件尚未重新验证，升级安全专项测试 23/23 OK）。
- **Core**：Doctrine 解析 / Identity（7 键严格 schema，immutable）/ Faculties（8 根只读）/ Continuity（append-only）/ Individual（两阶段回合 + 5 节投影 + 降级回合）/ Memory（SQLite WAL Provider，三维语义，FTS 检索，修正不重写）/ Growth（5 方法管线）/ Capability（生命周期 4 状态 + 四目录载体 + Manager + Verifier 执行闸门）/ 5 项个体持久文件清单。
- **Model Runtime**：Model Interface（两级调用面）+ 进程内 backend registry + 两个 Backend Adapter（`ollama` / `llama_cpp`）；Ollama wire 有 V0 执行证据；llama.cpp wire 有真实 llama-server 实测验证（2026-09-24，6/6 PASS）；逐侧 dispatch + 异 backend 支持 + fail-loud 配置校验。
- **Host 集成**：`HermesHostAdapter`（`state_db` / `hermes_home` 互斥 + `import_log` 幂等回流）。
- **Installation Layer**：`install / status / doctor / init-role / configure-role / migrate-data` 六入口（角色初始化 fresh-only、角色修改逐字段、遗留数据迁移绝不覆盖）、外部数据根（仓库外个人运行时数据，`DAO_SHENG_DATA_HOME` 可覆盖，解析结果在仓库内则拒绝）、标准目录、幂等安装、Python 最小版本长期规则（运行时自 `pyproject.toml` 派生）。
- **升级安全层**：Git 跟踪守卫 `tools/repo_tracking_guard.py`（接入 CI `.github/workflows/repo-guard.yml`）——Git 跟踪 `instances/` / `config/` / `log/` 下任何路径即构建失败；专项测试 `tests/test_data_home.py` + `tests/test_repo_tracking_guard.py` 实测 23/23 OK（2026-10-14）。

### 7.2 未实现 / 当前不存在

| 项 | 状态 |
|---|---|
| 现成交互式 CLI / GUI / 常驻 daemon | 不存在；使用形态 = Python 调用（§6.1） |
| Research 后端 | 声明位 `research_backend` 存在但**未被消费**；adapter seam 存在但未接装配（后端未定） |
| World 观察（`dao_sheng/world.py`） | 模块存在（seam），未接装配（无声明位） |
| Worker 形态 | V1 中不存在；Worker 概念定义 = UNKNOWN（Q6）；出现真实 Worker 协议 → 先停止、先 ADR |
| Memory 消化 / 遗忘机制 | 未实现；机制本身 = UNKNOWN（Q2），不臆造 |
| Faculties 倾向更新机制 | 未实现；faculties 当前为只读投影，写接口结构性不存在（倾向强度等 per-root 状态无已定值） |
| `log\` 目录内容 | 数据根下 `log\` 目录为安装层预留，当前无写入方 |
| 第二宿主 adapter | 不存在（当前仅 Hermes 形态）；引入 → ADR（规则 8） |
| 第三 Model backend | 不存在；引入 → ADR（规则 8） |

（Identity 运行时不可写 = 设计决定，不属于「未实现」。）

### 7.3 UNKNOWN（规则 11：不猜测；以下均非已有功能）

| UNKNOWN 项 | 说明 |
|---|---|
| Identity 延续判据（「仍然还是谁」） | Q5。Identity 只是载体；判据未定（用户决策） |
| Memory 消化 / 遗忘机制 | Q2。机制未定，当前管线不隐含任何遗忘行为 |
| 「道」具体内容 | Q1。六条只是当前成文子集 |
| 「AI 个体 / 智能个体 / 数字个体」三词关系 | Q4。raw 材料并存、关系未定；当前正式名称 = Individual（个体） |
| Worker / Tool 概念定义 | Q6。V1 无 Worker 形态；Tool 无独立概念定义 |
| Model 部署形态（U-5） | 具体模型选择、模型路径、GPU、量化、context、部署参数——全部未定，代码不预设，由部署时用户决定 |
| Research 后端选择 | 未定 |
| 「DaoSheng Core」+「Hermes Host」正式定义 | 未定（当前仅关系声明与 adapter 形态） |
| V0 数据迁移 / V0 默认模型关系 | 未定 |
| 原始材料日期 / 硬件起点 | 未知 |
| Brain Architecture 第 4 / 5 项模型来源 | UNKNOWN |

---

*本手册基于当前已验证实现（2026-10-13 基线；2026-10-14 升级安全修复同步更新）编写。实现演化时须同步更新本手册（随演化任务进行）；不得在实现未落地前把规划写入本手册，不得把 UNKNOWN 写成已有功能。*
