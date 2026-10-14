# DaoSheng V1

## 1. DaoSheng 是什么

DaoSheng 是一个以「道」为最高设计边界的 AI 个体（Individual）。它从最小完整幼体开始——基本结构完整、能力尚未展开——在现实世界中经历、记忆、行动、反思，逐渐形成自己的能力与个体性。它不是「已经成熟的超级 Agent」。

几条贯穿本项目的核心设计边界：

- **Model 不是 DaoSheng**。Model（Ollama、llama.cpp 等）是个体可以使用的手段，可替换、可缺失（缺失时降级），不定义个体本身。
- **Hermes 不定义 DaoSheng**。Hermes 是历史本地 Agent 系统，在本仓库中仅作为宿主（Host）集成层的对接对象。
- **Worker 不是 Identity**。Worker 概念在冻结的历史材料中不存在，领域定义保持 UNKNOWN，V1 中不引入。
- 无法验证的事实保持 **UNKNOWN**，不猜测填补（规则 11）。

## 2. Runtime 与使用者的角色

DaoSheng Runtime 提供的是**机制**，不是某个固定人格：

- **Runtime 能力**：记忆、经历连续性、反思与成长机制属于 Runtime 的运行能力（见 §4 架构概览），对所有实例一致。
- **使用者角色**：每个实例的角色内容——名字、自称、语气、形象、行为习惯、过往经历、持续记忆——保存在该实例的 `identity.json` 中，由使用者自己定义与修改（见 §5 安装与角色初始化）。
- **「道生」不是新实例的默认人格**：`init-role` 不生成任何默认角色内容，未填写的字段保持为空。一个实例是谁，取决于使用者写入的 identity。

## 3. 当前仓库定位

本仓库是 DaoSheng 的**公开 Runtime 仓库**，可由使用者自定义角色：

- 包含可运行的 Runtime 实现（`dao_sheng/`）、测试（`tests/`）、安装层（`dao-sheng.ps1`）与分层文档（`docs/`）。
- **V1 Reconstruction（重构）已完成**：12/12 Milestone 票 resolved，STEP 15 Real Verification gate verdict = **PASS**（报告：`docs/acceptance/v1-reality-gate.md`）。重构执行历史（STEP 03–15）为冻结历史事实，不再重执行、不重写。
- 项目处于**长期演化阶段**（LONG-TERM EVOLUTION，2026-09-21 确立）：在已验证的 V1 基础上持续演化；无法验证的事实保持 UNKNOWN，不猜测填补。

## 4. 当前架构概览

技术栈：Python ≥3.12，仅标准库（`unittest` 测试），零外部依赖（`pyproject.toml` 唯一正式声明）。

### DaoSheng Runtime Package（`dao_sheng/`）

| 模块 | 职责 |
|---|---|
| `composition.py` | composition root——唯一装配点。所有组件仅在此构造；Model / host 等部署配置经声明位注入，声明位默认全 `None`（无默认 backend、无预设部署值） |
| `individual.py` | Individual 顶层聚合。公共表面恰为 `act(turn)` / `persist()`：两阶段回合，`persist` 是经历落库的唯一提交点（单条 Memory 记录，原子写入） |
| `identity.py` | Identity 载体：frozen 投影，严格 schema 恰好 7 支撑项；**无 model / worker / host 字段**（K-11），运行时不可改写 |
| `continuity.py` | Continuity 载体：append-only 日志（`continuity.jsonl`），唯一写入入口 `append_continuity`（调用方仅成长管线） |
| `faculties.py` | Faculties 载体：单 JSON 文件，初始 8 根，增删根属 Domain 决策 |
| `doctrine.py` | 「道」的运行时 typed 投影：6 条 doctrine 逐条注入，只读来源 |
| `memory.py` | Memory Ontology：三维语义层（origin × status × confidence）+ `MemoryStore` 6 方法 Protocol。Provider 实现不得定义 Ontology |
| `memory_sqlite.py` | embedded SQLite Memory Provider（单文件 + WAL，ADR 0001） |
| `model.py` | Model Interface：显式 `Model` Protocol，两级调用面 `complete` / `chat` + `ModelUnavailable`。Core 调用方仅依赖此 interface，不认识具体 backend |
| `model_ollama.py` / `model_llama_cpp.py` | 两个 Backend Adapter：Ollama native `/api/*` 与 llama.cpp（OpenAI 兼容 `/v1/*`）。agent / reflection 两侧独立配置、独立装配，允许异 backend（ADR 0008） |
| `growth.py` | 成长管线：`import_experience` / `digest` / `extract` / `reflect` / `verify_insight` 五阶段；经历 → 消化 → 提取 → 记忆 → 复用 |
| `capability_lifecycle.py` | Capability 生命周期状态机 `proposed → working → active → retired`，四目录载体形态（ADR 0003） |
| `capability_verifier.py` | 执行前闸门：active 的唯一可达路径，规则式、model-free 三判据 |
| `host_integration.py` / `hermes_host.py` / `host_carrier.py` | host 集成层：中性 Interface（三方法）+ Hermes 宿主 adapter（唯一允许知道宿主名的层，ADR 0002）+ 宿主侧只读连接与 append-only 导入日志 |
| `research.py` / `world.py` | Research seam（纯类型 + Protocol，后端未定）/ World 观察 adapter（只读）。均未接入装配 |
| `layout.py` | 个体持久文件清单（5 项）：`identity.json` / `faculties.json` / `continuity.jsonl` / `memory/` / `capabilities/` |

### 安装层（L4 部署层）

- `dao-sheng.ps1`：唯一安装与角色入口（`install` / `status` / `doctor` / `init-role` / `configure-role` / `migrate-data` 六入口），安装与角色初始化逻辑全部位于 PowerShell，零新增 Python 模块。Python 最低版本运行时自 `pyproject.toml` 的 `requires-python` 派生（当前 ≥3.12）。个人运行时数据（角色配置 / 记忆 / 安装状态 / 日志）位于**仓库外部的数据根**（默认 `%LOCALAPPDATA%\DaoSheng`，可用 `DAO_SHENG_DATA_HOME` 覆盖）；仓库内唯一机器本地产物 `.venv/` 不入库。
- 升级安全层：`tools/repo_tracking_guard.py`（Git 跟踪守卫——Git 一旦跟踪 `instances/` / `config/` / `log/` 下任何路径即失败；接入 CI `.github/workflows/repo-guard.yml`，每次 push / pull request 执行）。`.gitignore` 只防误加，**不是跟踪保护**：被跟踪的路径无论是否 ignore，`git pull` 都会覆盖它。
- 契约文档：`docs/deployment/INSTALLATION_CONTRACT.md`。

### 测试与验证（`tests/`）

- 标准库 `unittest`，基线 **432 tests（431 通过 / 1 跳过，跳过项需真实宿主环境）**（2026-10-13 历史基线；升级安全修复后全量套件尚未重新验证）。
- 升级安全专项测试：`tests/test_data_home.py`（当前 18 个）+ `tests/test_repo_tracking_guard.py`（7 个），当前合计 25 个。历史专项实测 23/23 OK（2026-10-14，专项子集、非全量基线；当时 `test_data_home.py` 为 16 个、合计 23 个，该记录不对应当前 25 项）。
- `tests/test_architecture_invariants.py`：结构棘轮——把已决定的架构约束（构造位、出站通道、公共表面、残留锁等）固化为测试，漂移先红。
- `tests/reality_gate.py`：真实运行验证执行器（非 test* 命名，不在默认测试套件内，需仓库外真实磁盘 workspace 与真实 Model wire）。

## 5. 安装与角色初始化

以下命令与参数均取自 `dao-sheng.ps1` 的真实 Usage（Windows PowerShell 5.1+）：

```text
Usage: .\dao-sheng.ps1 <install|status|doctor|init-role|configure-role|migrate-data> [-InstanceRoot <path>]
  install        : check env, fill missing runtime, verify install (never writes any inventory item)
  init-role      : create identity.json + faculties.json on a FRESH instance (refuses if either exists)
  configure-role : edit an existing identity.json field-by-field (faculties/continuity/memory untouched)
  migrate-data   : move legacy in-repo personal data (instances/ config/ log/) to the data home (never overwrites)
data home        : %LOCALAPPDATA%\DaoSheng (override: DAO_SHENG_DATA_HOME); -InstanceRoot defaults to <data home>\instances\default
```

**数据根（个人运行时数据的唯一默认位置）**：默认 `%LOCALAPPDATA%\DaoSheng`，可用环境变量 `DAO_SHENG_DATA_HOME` 覆盖；解析结果落在仓库内 → 显式拒绝（fail-loud）。默认实例目录为 `<数据根>\instances\default`；用 `-InstanceRoot <path>` 可指定其他实例（同样拒绝仓库内路径）。数据根布局：`instances\default\`（identity / faculties / continuity / memory / capabilities 5 项个体载体）、`config\install-state.json`（安装状态）、`log\`。

### 安装

```powershell
.\dao-sheng.ps1 install   # 检查环境、补齐缺失运行时、验证安装（不写任何 inventory 项）
.\dao-sheng.ps1 status    # 查看运行时与实例状态
.\dao-sheng.ps1 doctor    # 诊断
```

### 首次角色初始化（init-role）

`init-role` 仅用于**全新实例**：`identity.json` 或 `faculties.json` 任一已存在时显式拒绝、绝不覆盖（此时应改用 `configure-role`）。`name` 必填；**不生成任何默认人格**，未填写的字段保持为空；`faculties.json` 由安装层按 8 个 faculty 根自动生成。

```powershell
# 交互模式（不带角色参数时逐项提示）
.\dao-sheng.ps1 init-role

# 参数模式（list 字段以空格分隔多个值；未给出的字段保持为空）
.\dao-sheng.ps1 init-role -Name "我的角色" -Voice "平静" -BehavioralHabits 先观察后行动 每日复盘
```

角色参数（大小写不敏感）：scalar `-Name` / `-SelfAppellation` / `-Voice` / `-VisualImage`（必须跟值）；list `-BehavioralHabits` / `-PastExperiences` / `-ContinuousMemory`（空格分隔多值，直到下一个参数 flag）。

### 修改已有角色（configure-role）

```powershell
# 只改写给出的字段，其余保留
.\dao-sheng.ps1 configure-role -Voice "新的语气"

# 清空某个可选字段（name 不可清空）
.\dao-sheng.ps1 configure-role -Clear voice

# 交互模式：空输入保留当前值；输入 - 清空可选字段
.\dao-sheng.ps1 configure-role
```

`configure-role` 要求 `identity.json` 已存在（否则提示先运行 `init-role`）；只改写 `identity.json`，**`faculties.json` / continuity / memory 不会被触碰**。新 identity 在**下一次 composition** 时加载——不是热更新。

启动与使用流程见 `docs/USER_GUIDE.md`。

## 6. 当前状态

- **Current Phase**：LONG-TERM EVOLUTION（长期演化阶段），**Status**：ACTIVE。
- **测试基线**：432 tests（431 通过 / 1 跳过，跳过项需真实宿主环境）（2026-10-13 历史基线；升级安全修复后全量套件尚未重新验证，升级安全专项 23/23 OK 见 §4）。
- **V1 Real Verification**：gate verdict = PASS（`docs/acceptance/v1-reality-gate.md`，2026-09-21）。
- **部署值未预设**：Model 配置声明位（endpoint / model / backend 等）默认全 `None`，无默认 backend，具体模型 / 硬件 / 部署参数保持 UNKNOWN（U-5 未被填补）。
- **残留 UNKNOWN**：域内 11 项 UNKNOWN（含「道」具体内容、Identity 延续判据、Worker 定义等）状态不变，见 `docs/domain/domain-invariants.md` §3。

## 7. 如何阅读仓库

### 从哪里开始

- **使用者**：`docs/USER_GUIDE.md` —— 安装、角色初始化、启动使用、模型接入、当前版本限制。
- **设计与架构读者**：按 `docs/domain/` → `docs/constitution/` → `docs/architecture/` → `docs/adr/` → `docs/specs/` 顺序阅读。

### 文档分层（`docs/`）

信息冲突时按权威顺序裁决：**Original Intent > Historical Decision > Validated Evidence > Implementation > Current Guess**。

| 目录 | 内容 | 备注 |
|---|---|---|
| `docs/domain/` | Domain 定义：统一语言、核心概念、边界、不变量（含 UNKNOWN 清单） | |
| `docs/constitution/` | Constitution：6 条 doctrine 逐条四层展开 + 不变量 | |
| `docs/architecture/` | V1 架构：系统边界、容器模型、组件与 seam、运行时边界、数据所有权 | |
| `docs/adr/` | ADR 0001–0010（Memory 持久化 / host 集成层 / Capability 生命周期 / Continuity 载体 / 「道」单一来源 / Insight 单一表征 / V0 数据不默认迁移 / Model Runtime 架构 / Model seam 之下 Shared Wire Client / Host Adapter 向 Experience 候选接口的语义供数契约） | 历史 ADR 不修改 |
| `docs/specs/` | V1 规格（总纲 + 7 对象规格） | 非独立权威层，冲突以源文档为准 |
| `docs/research/` | Research Evidence（Memory 持久化调研） | |
| `docs/acceptance/` | Acceptance 记录（M12 验收报告、V1 Real Verification 报告） | 冻结历史记录 |
| `docs/deployment/` | 安装层契约 | |
| `docs/USER_GUIDE.md` | 用户手册（当前实现的正式文档：架构说明 / 配置 / 安装启动 / 角色初始化 / 模型接入 / 使用流程 / 当前版本限制） | 使用者入口 |

### 代码

- `dao_sheng/` — DaoSheng Core（上表）。组件仅在 `composition.py` 装配点构造；部署值一律由装配点注入，包内无默认值。
- `tests/` — 行为测试 + 结构棘轮 + 验收演练；`tests/reality_gate.py` 为真实运行验证执行器（不在默认套件内）。

### 阅读纪律

- 历史与验收类目录（`docs/acceptance/`、`docs/adr/` 等）只在需要时查阅，不整体遍历。
- 本仓库不含任何未实现功能的描述：文档中 UNKNOWN 项均明确标注为 UNKNOWN，不写成已有能力。
