# DaoSheng Installation Layer — 安装契约（任务契约，持久文件）

> 本文件是「Installation Layer」任务的持久契约，创建于任何实际修改之前。
> 若发生 context compaction，本任务恢复时**必须先重新读取本文件**，再核对
> 仓库状态与 git status，然后继续**同一任务**（compaction ≠ 任务重启）。
> 本文件只描述安装系统（Deployment / Installation Layer，L4 部署层），
> **不重新定义 DaoSheng 本体（ontology）**——Domain / Identity / Continuity /
> Memory / Growth 等的定义以 `docs/domain/`、ADR 与既有票为准。
>
> 2026-10 角色初始化改造增补：本契约已扩展覆盖两个设计层角色入口
> `init-role` / `configure-role`（见 §4.4 / §4.5）。install / status / doctor
> 的职责与边界**不变**——install 仍是安装层唯一可写入口，且 NEVER writes
> any inventory item（identity / faculties 仍属设计层所有）。
>
> 2026-10 升级安全增补（Git 升级数据丢失风险修复）：个人运行时数据（角色
> 配置 / 记忆 / 安装状态 / 日志）已移出 Git worktree，位于**外部数据根**
> （默认 `%LOCALAPPDATA%\DaoSheng`，`DAO_SHENG_DATA_HOME` 可覆盖；解析结果
> 落在仓库内 → fail-loud 拒绝）。安装层新增第六入口 `migrate-data`（§4.6），
> 把旧仓库内遗留个人数据安全迁移到数据根（永不覆盖）。Git 跟踪守卫
> `tools/repo_tracking_guard.py` 接入 CI（`.github/workflows/repo-guard.yml`）：
> Git 一旦跟踪 `instances/` / `config/` / `log/` 下任何路径即失败退出 1。
> `.gitignore` 只防误加，**不是跟踪保护**。§2 / §2.1 / §6 / §7 为契约验收
> 时点的历史记录，不改写。

## 0. 最高约束（冻结 DaoSheng Core）

当前 DaoSheng Core 是**冻结资产**（V1 Reconstruction 已完成；STEP 15 gate
verdict = PASS；阶段 = LONG-TERM EVOLUTION）。本任务**只增加外围安装入口**，
禁止：

1. 重构、移动、重命名、删除任何 `dao_sheng/` 内文件；
2. 改变 Core 语义（任何组件行为、fail-loud 语义、装配规则）；
3. 修改任何既有测试以迁就安装系统；
4. 把安装逻辑放进 `dao_sheng/`（**不新增任何 Python 模块**——安装逻辑全部
   位于 PowerShell 入口，从结构上杜绝"悄悄成为 Core"）；
5. 重新定义 Domain，或从安装需求反推 DaoSheng 本体；
6. 为"看起来更标准"而修改 Core 持久化语义；
7. 删除 / 覆盖 / 移动 / 格式化 / 重命名与本任务无关的未提交文件
   （明确包括 `docs/dao-sheng-view.html`）；
8. 上传 GitHub / 创建 Public 或 Private Repository / 推送任何远程仓库
   （只修改当前本地工作区）。

若安装需求与 Core 现状存在摩擦，**在周边适配**，不修改 Core。

## 1. 目标

为 DaoSheng 提供**一个**简单、稳定、可重复、可验证的 Windows 安装入口：

```
dao-sheng.ps1          （仓库根目录，唯一入口）
  ├─ install         安装层：环境检查 + 补全缺失运行环境 + 准备标准目录 + 验证安装
  ├─ status          显示当前安装与运行环境的基本状态（只读）
  ├─ doctor          只读体检：逐项 [OK/FAIL] + 最终 Result: PASS / FAIL
  ├─ init-role       设计层初始化：identity 与 faculties 均不存在时才创建（§4.4）
  ├─ configure-role  设计层修改：修改现有 identity 的字段，faculties / Continuity / Memory 不重置（§4.5）
  └─ migrate-data    升级安全：把旧仓库内遗留个人数据迁移到数据根（永不覆盖，§4.6）
```

一句话：**在完全不动已经完成的 DaoSheng Core 的前提下，给它增加一个简单、
可重复、可验证的外围安装入口（install / status / doctor），并经同一入口暴露
两个设计层角色入口（init-role / configure-role）与升级安全迁移入口
（migrate-data）——schema 权威仍在 Core，个人运行时数据位于仓库外部数据根。**

## 2. 基线事实（只读检查确认，2026-09-22）

| 事实 | 依据 |
|---|---|
| Python >= MIN_SUPPORTED_PYTHON（当前 = 3.12；长期规则见 §2.1），**零外部依赖**（仅标准库 + unittest） | `pyproject.toml`（M01 工具链决定；唯一正式声明） |
| 无进程入口 / CLI（composition root 无调用方，属设计决定） | `dao_sheng/composition.py` docstring |
| 个体持久文件清单 = 5 项，全部由 `IndividualFiles.layout(root)` 派生 | `dao_sheng/layout.py`（spec-individual.md §4） |
| `identity.json` / `faculties.json` 缺失 → 装配 fail-loud，**设计层初始化**，Runtime 不代建 | `composition.py`（M02 决定 ①②） |
| `continuity.jsonl` 缺失 = 空日志（初始态） | `composition.py`（M03 决定 ③） |
| `memory/` 缺失 = 初始态，Provider 自建 | `composition.py`（M05 决定 ⑥，ADR 0001/0007） |
| `capabilities/` 状态目录由生命周期模块 `mkdir(parents=True, exist_ok=True)` 自建 | `dao_sheng/capability_lifecycle.py:154,284`（M08 决定 ㉘） |
| 测试入口 = `PYTHONIOENCODING=utf-8 python -m unittest discover -s tests`；2026-09-22 契约验收时点基线 **322 tests OK**（历史基线，非当前基线） | 交接文件 + STEP 15 |
| `scripts/` 与 `docs/deployment/` 不存在（全部为新增）；唯一未跟踪文件 = `docs/dao-sheng-view.html`（受保护） | 2026-09-22 git status |
| `.gitignore` 已有 `.venv/`（venv 为预期运行环境形态） | `.gitignore` |

推论：**"安装项目依赖"在本项目的现实 = 验证 pyproject 未声明外部依赖**
（M01 零依赖决定）；不执行任何 pip 包安装。

## 2.1 Python Runtime Compatibility 长期规则（用户 2026-09-22 正式下达；长期有效，非临时修复）

DaoSheng Installation Layer **不绑定某个具体 Python 小版本**。

### 禁止

1. 禁止 `Python == 3.13` 式的固定版本相等判断（任何具体小版本同理）；
2. 禁止把当前开发机使用的 Python 版本自动提升为 DaoSheng 的永久部署要求；
3. 禁止"不是某个具体版本就失败"的判断逻辑。

### 规则

DaoSheng 采用 `Python >= MIN_SUPPORTED_PYTHON`。MIN_SUPPORTED_PYTHON 必须来自
项目自身可验证的兼容性依据：

- `pyproject.toml` 声明（`requires-python`）；
- 依赖约束；
- 代码实际使用的 Python 语法 / API；
- 已通过的测试；
- 项目明确声明的最低支持版本。

不得仅因为当前开发机使用某个版本就推导最低版本为该版本。

### 当前确定值（证据链，2026-09-22）

**MIN_SUPPORTED_PYTHON = 3.12**（非 TBD，非 3.13）：

| 证据 | 内容 |
|---|---|
| 项目明确声明的最低支持版本 | `pyproject.toml` `[project] requires-python = ">=3.12"` |
| M01 工具链决定（Historical Decision） | "Python ≥3.12 + 标准库 `unittest`，零外部依赖" |
| 依赖约束 | 零外部依赖 → 无高于 3.12 的依赖下限 |
| 已通过的测试 | 322 tests OK（2026-09-22 证据链时点 Python 3.13 实测，历史基线、非当前基线；更高版本默认允许，见下第 3/4 条） |

### 五条长期规则

1. 低于 MIN_SUPPORTED_PYTHON → Installation FAIL；
2. 等于 MIN_SUPPORTED_PYTHON → 允许安装；
3. 高于 MIN_SUPPORTED_PYTHON → 默认允许安装；
4. 更高版本实际兼容性问题必须通过真实验证发现后再处理，不得提前用"只能某版本"规避；
5. 版本判断必须使用明确的最小版本比较逻辑（major > min → 允许；major == min → minor >= min minor → 允许；其余 FAIL），不得使用"不是某版本就失败"的逻辑。

### 实现形态（本安装系统）

- `dao-sheng.ps1` 在运行时从 `pyproject.toml` `requires-python` 派生
  MIN_SUPPORTED_PYTHON（`Get-PythonMinVersion`）；**版本号不写进脚本**——
  `pyproject.toml` 是唯一正式声明，install / status / doctor 三入口读取同一
  声明，与本合同结构上不可能漂移（一致性 = 运行时读声明本身，无需人工同步）；
- 声明缺失或不可解析 → 显式 FAIL（fail-loud，与 Core 语义一致），提示在
  `pyproject.toml` 声明 `requires-python`（M01 工具链决定）；
- `Test-PythonVersionOk` = 明确的最小版本比较（第 5 条），全文无任何
  固定版本字面量或相等判断。

### 长期目标

- 同一份 DaoSheng 安装系统应能跨机器复用，不因 Python 小版本变化失效；
- Machine Profile、Runtime Profile、Model Profile 都不得把 Python 具体小版本
  写死为 DaoSheng 的身份或核心要求。

### 未来 MIN 变更流程

变更 MIN_SUPPORTED_PYTHON = 修改 `pyproject.toml` `requires-python` 声明
（附可验证兼容性依据：新依赖约束 / 实际使用的语法 API / 验证证据）+ 在
`RECONSTRUCTION.md` 与交接文件记录依据。安装层运行时自动跟随，无需修改
`dao-sheng.ps1`。

### 本规则验证记录（2026-09-22，Python 3.13 当前环境）

- install PASS / 重复 install PASS / Clean Install PASS（删除全部机器本地
  产物 `.venv/` `config/` `log/` `instances/` 后重装成功）/ status PASS /
  doctor PASS（9 项全 [OK]）；
- `dao-sheng.ps1` 零版本数字字面量、无固定版本相等判断逻辑（Grep 证据）；
- `dao_sheng/` 与 `tests/` 零业务修改；本验证记录当时基线 322 tests OK（2026-09-22 历史基线，非当前基线）。

## 3. 标准目录规则（Deployment Layer L4 决定，本契约定义，Core 不读取）

| 目录 | 位置 | 内容 | 创建者 |
|---|---|---|---|
| Python 运行环境 | 仓库根 `.venv/` | 系统 Python >= MIN_SUPPORTED_PYTHON 派生的 venv（无外部包；版本规则见 §2.1） | install |
| 配置目录 | `<数据根>\config\` | 安装层元数据 `install-state.json`（Core 不读取；当前 Core 无配置文件形态） | install |
| 日志目录 | `<数据根>\log\` | 空目录（当前 Core 无 logging 形态；预留） | install |
| 实例目录（默认个体 root） | `<数据根>\instances\default\` | 标准个体持久文件清单（5 项）的 root | install 建根目录（init-role 缺失时亦建根，§4.4） |

**数据根（外部数据根，2026-10 升级安全增补）**：默认 `%LOCALAPPDATA%\DaoSheng`
（不可用时回退 `%USERPROFILE%\AppData\Local\DaoSheng`）；环境变量
`DAO_SHENG_DATA_HOME` 可覆盖（值 trimmed；`~` 经 USERPROFILE 展开；相对路径
相对当前工作目录解析）。PowerShell 安装层（`Resolve-DataHome`）与 Python
入口（`run_dao_sheng.py` `resolve_data_home`）解析规则**完全一致**（跨进程
parity 测试验证）。解析结果落在仓库内 → fail-loud 拒绝（exit 1 /
RuntimeError），什么都不写。个人运行时数据由此位于 Git worktree 之外，普通
源码升级（`git pull`）无法覆盖它。

- 默认个体 root 固定为 `<数据根>\instances\default\`；`-InstanceRoot` 参数可
  指定其他位置（绝对路径原样使用；相对路径相对数据根解析）。**解析结果落在
  仓库内 → 显式拒绝（fail-loud，exit 1，什么都不写）。** **重复 install
  始终使用同一位置，绝不创建第二个 Individual。** install / status / doctor /
  init-role / configure-role / migrate-data 使用完全相同的数据根与实例 root
  解析规则（含 `-InstanceRoot`）。
- 5 项清单内容中：
  - `identity.json` / `faculties.json`：**install 不创建**（设计层初始化，
    Core fail-loud 语义是预期行为，install 只报告状态）；
  - `continuity.jsonl`：**install 不创建**（缺失 = 空日志，Core 语义）；
  - `memory/` / `capabilities/`：**install 不代建**（Core 首用时自建，
    已核实上述代码位）。
  - 即：**install 只建目录脚手架（含实例根目录本身），不制造任何清单文件
    或清单子目录**，与 Core "不代建"语义完全一致。
- `.venv/` 是仓库内唯一机器本地产物，已在 `.gitignore`。个人运行时数据
  （`config/`、`log/`、`instances/`）位于仓库外部数据根（2026-10 升级安全
  增补）。`.gitignore` 中对应条目只防对遗留目录的误加 `git add`，**不是
  跟踪保护**：路径一旦被跟踪（如上游 commit 开始跟踪
  `instances/default/identity.json`），普通 `git pull` 退出 0 并静默覆盖本地
  个人数据。跟踪保护由 `tools/repo_tracking_guard.py` 提供（CI：
  `.github/workflows/repo-guard.yml`，每次 push / pull request 执行）：Git
  跟踪上述任一前缀下的路径即失败退出 1。

## 4. 各入口的职责

install / status / doctor 为安装层三入口；init-role / configure-role 为经同一
PowerShell 入口暴露的**设计层角色入口**（§4.4 / §4.5）；migrate-data 为升级
安全迁移入口（§4.6）。install 仍是**安装层唯一可写入口**——角色入口只在用户
显式请求时写 identity / faculties，不属于安装层行为。

### install（安装层唯一可写入口）
1. 检查 OS（Windows；非 Windows 显式 FAIL）；
2. 检查 Python 可发现（`.venv` 优先，其次 `python` / `py`）；
3. 检查 Python 版本 >= MIN_SUPPORTED_PYTHON（运行时自 pyproject
   `requires-python` 派生；长期规则见 §2.1；明确的最小版本比较，无固定
   版本相等判断）；
4. 创建 / 准备 Python 运行环境（`.venv` 不存在才创建；已存在原样保留）；
5. "安装项目依赖" = 验证 `pyproject.toml` 未声明 `dependencies`（零依赖
   现实，§2）；声明了即 FAIL（与 M01 决定冲突，须人工裁决）；
6. 准备标准目录（数据根下）：`<数据根>\config\`、`<数据根>\log\`、实例根
   目录（`New-Item -Force` 幂等，**只创建、永不删除、永不重建**；**不在
   仓库内创建任何数据目录**）；
7. **先检测后保留**：逐项检测实例内 5 项清单现存内容（identity /
   faculties / continuity / memory / capabilities），存在 → 报告 "kept"
   并原样保留；不存在 → 报告初始态说明；
8. 验证安装成功：venv Python 于仓库根 `import dao_sheng` +
   `import dao_sheng.composition` 成功；
9. 写 `<数据根>\config\install-state.json`（安装层自己的元数据：时间戳 / Python /
   版本 / 实例 root；**重写此文件不是"覆盖用户配置"**——它是 install 的
   自有状态，且 Core 不读取）；
10. 输出逐项 [OK] 摘要；任一步失败 → 输出该项的检查对象 / 期望 / 现状 /
    建议修复，退出码 1。

### status（只读）
显示：Python（exe + 版本 + venv/系统）、`.venv` 状态、数据根位置、数据根下
`config` / `log` / 实例 root 存在性、实例 5 项清单逐项存在性（identity /
faculties 未初始化时报告"待设计层初始化——compose 将 fail-loud，为预期
语义"）、
`install-state.json` 内容（若存在）、测试入口命令。不改写任何文件。

### doctor（只读体检，逐项 [OK/FAIL]）
最少 9 项：Python / Python 版本 / Project structure / DaoSheng import /
Dependencies / Config directory / Data directory / Log directory /
Test entry point。每项 FAIL 必须给出：**检查对象、期望状态、当前状态、
建议修复**。末行输出 `Result: PASS` 或 `Result: FAIL`（退出码 0/1）。
doctor 不创建、不删除、不修改任何文件。Config / Data / Log 三项均在数据根下
检查（2026-10 升级安全增补）。

### init-role（设计层初始化入口，§4.4）

Identity + Faculties 载体的设计层初始化。§0 规则 4 仍成立：不新增任何
Python 模块，流程全部位于 PowerShell；**schema 权威仍在 Core**——写出的
载体由 `dao_sheng.identity.parse_identity`（严格 7 键 schema）校验并
canonicalize；`faculties.json` 由 Python 从 `dao_sheng.faculties.FACULTY_ROOTS`
生成（8 根：intent / choice / stopping / observation / correction / selection /
reflection / continuity；**FACULTY_ROOTS 是唯一来源，脚本不硬编码 schema、
也不硬编码 8 根**）。

命令语法（从当前 `dao-sheng.ps1` 参数解析核实）：

```
.\dao-sheng.ps1 init-role [-InstanceRoot <path>]
    [-Name <文本>] [-SelfAppellation <文本>] [-Voice <文本>] [-VisualImage <文本>]
    [-BehavioralHabits <项1> <项2> ...] [-PastExperiences <项1> ...] [-ContinuousMemory <项1> ...]
```

- **参数模式 vs 交互模式**：出现任一角色参数 token → 参数模式；完全没有
  角色参数 token → 交互模式（依次提示 Name / Self appellation / Voice /
  Visual image / Behavioral habits / Past experiences / Continuous memory；
  空行 = 空值；list 字段一行逗号分隔）。
- flag 名大小写不敏感；scalar flag 恰好取一个值；list flag 吸收其后所有裸
  token 直到下一个 flag。**参数模式的值不得以 `-` 开头**（此类 token 会被
  解析为 flag）。未知 flag、裸值、重复 flag、scalar flag 缺值 → Fail-Step，
  什么都不写。
- 未指定的字段保持空——**默认不生成任何 persona**（无 persona 注入）。
- `name` 是唯一必填字段：为空（参数模式 `-Name ""` 或交互空输入）→
  Fail-Step，什么都不写。

前置条件：
1. Python 可发现（`.venv` 优先，其次 PATH `python` / `py`）——载体必须经
   Core Python 模块校验；找不到 → Fail-Step 提示先运行 install（不要求
   install 已执行过，只要求 Python 运行时存在）；
2. 实例 root 按 §3 解析（同一 `-InstanceRoot` 规则）；不存在则自动创建
   （`New-Item -Force`，目录创建幂等且无害）。

拒绝语义（核心边界）：
- **只在 identity.json 与 faculties.json 均不存在时创建**；任一载体已存在
  → Fail-Step 拒绝，**永不覆盖**，并提示改用 configure-role 修改现有
  identity；
- 写前竞态复查：运行过程中载体出现 → 删除 tmp 文件，Fail-Step，不覆盖。

写入流程（原子，无 partial state）：
1. 写 `identity.json.new.tmp`（UTF-8 无 BOM）；
2. Python 子进程：`parse_identity` 校验（严格 7 键 schema）+ canonicalize，
   随后写 `faculties.json.new.tmp` = `FACULTY_ROOTS` 的 JSON 数组；
3. 校验失败 → 删除两个 tmp → Fail-Step（"no partial state was left behind"）；
4. 通过 → 竞态复查 → `Move-Item` 就位 → `[OK]`，exit 0。

失败行为：任何失败 = Fail-Step（输出检查对象 / 期望 / 现状 / 建议修复）+
exit 1。

### configure-role（设计层修改入口，§4.5）

修改**现有** identity.json 的字段；**faculties.json / continuity.jsonl /
memory/ 永不触碰**（成功输出中明确声明）。

命令语法：

```
.\dao-sheng.ps1 configure-role [-InstanceRoot <path>]
    [-Name <文本>] [-SelfAppellation <文本>] [-Voice <文本>] [-VisualImage <文本>]
    [-BehavioralHabits <项1> ...] [-PastExperiences <项1> ...] [-ContinuousMemory <项1> ...]
    [-Clear <字段> <字段> ...]
```

- flag 解析规则与 init-role 相同。
- `-Clear` 接字段名 token（小写 snake_case：`self_appellation` / `voice` /
  `visual_image` / `behavioral_habits` / `past_experiences` /
  `continuous_memory`）：清空可选字段（scalar → 空字符串，list → 空数组）。
  `name` 不可清空（必填字段）→ Fail-Step；未知 token → Fail-Step；同一字段
  既作为自身参数出现、又出现在 `-Clear` 中 → Fail-Step。
- 参数模式：指定的字段**替换**其值；**未指定的字段保留当前值**（不重置）。
- 交互模式：先打印当前 identity 的 7 个字段；空输入 = 保留当前值；`-` =
  清空可选字段；对 `name`，空输入与 `-` 均保留当前值（name 永不为空）。

前置条件：
1. identity.json 存在——缺失 → Fail-Step 提示先运行 init-role；
2. Python 可发现（同 init-role）；
3. 现有 identity.json 必须通过 `parse_identity`（只读校验）：非法载体 →
   **拒绝、原文件不动**——configure-role 从不修复或损坏它。

写入流程：读当前值 → 合并参数/交互输入 → name 非空检查 → 写 tmp →
Python 校验 + canonicalize → 失败：删除 tmp，Fail-Step（原文件不动）→
成功：`Move-Item` 覆盖 identity.json，exit 0。

**生效语义（重要）**：更新后的 identity 由**下一次 composition**（Runtime
装配）读取。已运行实例**不会热更新**；要让新 identity 在 Runtime 生效，
必须重新执行 composition。

### migrate-data（升级安全迁移入口，§4.6，2026-10 升级安全增补）

把旧版本遗留在仓库内（相对仓库根的 `instances/`、`config/`、`log/`）的个人
数据迁移到数据根。安全语义（测试证据：`tests/test_data_home.py`
MigrateDataSafetyTest，关键哨兵文件逐项 SHA-256 比较）：

1. **无遗留数据** → 报告 `no legacy personal data found ... nothing to
   migrate`，exit 0；**不创建空白实例**；
2. **有遗留数据** → 逐文件迁移：复制 → SHA-256 逐字节校验通过 → 删除源；
   迁移后除 `install-state.json` 外全部载体逐字节一致；`install-state.json`
   记录的实例 root 被显式重写为数据根下位置（唯一有意改写的文件，输出
   `instance_root updated`）；
3. **目标已存在** → Fail-Step（`[FAIL] migrate-data` + `target(s) already
   present` + `nothing was copied`），exit 1；源与目标内容均不变，**永不
   覆盖**；
4. **重复执行** → 无遗留 → `nothing to migrate`，不会二次覆盖或丢数据；
5. 迁移不访问私有源项目、不访问真实 Hermes 数据库；Python 入口发现旧仓库内
   数据 → fail-loud 指向 `migrate-data`，不会静默忽略。

已知边界：迁移逐文件进行，不是跨文件原子事务——中途失败时已校验并移动的
文件源已删除、未校验文件保留在源处；失败场景不删除未校验的源数据、不静默
创建空白实例，"部分迁移完成"状态需重新执行 migrate-data 续迁剩余文件。

## 5. 幂等与数据安全规则

1. 重复 `install` 必须幂等：**不得**删除 / 重建 Identity，不得删除 / 重建
   Continuity，不得删除 Memory，不得覆盖用户配置，不得创建第二个
   Individual，不得清空既有数据，不得修改任何历史。
2. 一切写操作 = 目录创建（`-Force` 幂等）+ `install-state.json` 重写
   （install 自有元数据）+ `.venv` 首建。除此之外 install 不写任何字节。
3. install 对 5 项清单现存内容**零写入**：只读检测 + 报告。
4. 角色入口（init-role / configure-role）数据安全：
   - init-role 永不覆盖任何既有载体（§4.4 拒绝语义）；
   - configure-role 只重写 identity.json，**永不触碰** faculties /
     continuity / memory；
   - 两入口均只经"tmp 文件 → Core 校验 → Move-Item"写入；校验失败不留
     partial state，原文件不动；
   - install / status / doctor 携带任何角色参数 token → Fail-Step（旧严格
     性保留：安装层入口从不接受角色参数）。
5. migrate-data 数据安全（2026-10 升级安全增补，§4.6）：目标已存在 →
   fail-loud、`nothing was copied`、双方内容不变，**永不覆盖**；仅在
   SHA-256 逐字节校验通过后才删除源；无遗留数据不创建空白实例；重复执行
   安全。

## 6. 验证规则（自检，最低项）

1. install 可成功执行；
2. 重复 install 不破坏实例（对**预置的合法既有实例**做前后指纹比对：
   `identity.json` / `faculties.json` / `continuity.jsonl` 逐字节一致，
   且无新增清单文件——用 `-InstanceRoot` 指向临时目录做演练，结束后清理
   自建的演练产物）；
3. status 可成功执行；
4. doctor 可成功执行且 9 项全 [OK]、`Result: PASS`；
5. 既有全部 DaoSheng 测试通过（2026-09-22 契约验收时点基线 322 tests OK——
   历史基线，非当前基线；
   `PYTHONIOENCODING=utf-8 python -m unittest discover -s tests`）；
6. Identity 未被重建（#2 指纹）；
7. Continuity 未被重建（#2 指纹）；
8. Memory 未被重建（install 对 `memory/` 零写入，#2 同证）；
9. 未创建第二个 Individual（默认 root 固定 + install 不新建实例目录）;
10. 无关未提交文件（`docs/dao-sheng-view.html`）未被触碰（git status 核对）；
11. git status 与任务预期一致（新增 = 本任务交付物 + 角色改造新增的
    `tests/test_role_init.py`；修改 = `.gitignore` / `RECONSTRUCTION.md` /
    `dao-sheng.ps1` / 本文件；无任何 `dao_sheng/` 改动，`tests/` 内除新增
    角色测试文件外无改动）。
12. 角色入口自检（2026-10 角色初始化改造，`tests/test_role_init.py` 20 个
    测试，实测 20/20 OK——角色初始化**专项测试结果，是专项子集，不是全量测试基线**）：init-role 创建 schema 合法载体 / 无 persona 注入
    / 任一载体已存在时拒绝；configure-role 要求现有 identity / 只改指定字段
    / 非法载体拒绝且无损伤 / memory 与 continuity 字节保留；下一次
    composition 读到配置后的 identity；以及 install×2 幂等（不写任何清单
    项）后角色入口端到端（init-role → 真实 composition → act/persist →
    Growth → configure-role → 再 composition）。

## 7. Definition of Done（13 项全部成立）

1. Installation Layer 已实现（`dao-sheng.ps1`，五入口：install / status /
   doctor / init-role / configure-role）；
2. `dao-sheng.ps1` 可执行；
3. install 可用；4. status 可用；5. doctor 可用；
6. install 可重复执行（幂等，§5）；
7. 不破坏既有 DaoSheng 数据（§6 #2/#6–#9）；
8. 既有测试全部通过（2026-09-22 契约验收时点 322 OK，历史基线、非当前基线）；
9. Core 未被为安装需求重构（`dao_sheng/` 零 diff）；
10. 本契约文件在盘上（本文件）；
11. git status 已核对（§6 #10/#11）；
12. 最终结果明确 PASS / FAIL（不伪装未完成为完成）；
13. 角色入口可用且已验证（§4.4 / §4.5；§6 #12 实测 20/20 OK，专项子集、非全量基线；install
    边界不变）。

## 8. 交付物与边界

- 新增：`dao-sheng.ps1`（仓库根）、本文件、
  `docs/handoffs/2026-09-22-installation-layer.md`；
- 修改：`.gitignore`（+3 行机器本地目录）、`RECONSTRUCTION.md`（唯一执行
  状态，规则 13）；
- 角色初始化改造（2026-10）新增：`tests/test_role_init.py`（20 个测试）与
  `dao-sheng.ps1` 的 init-role / configure-role 入口；本契约相应扩展
  §4.4 / §4.5（install / status / doctor 边界不变）；
- 升级安全修复（2026-10）新增：`run_dao_sheng.py` 数据根解析与旧数据
  fail-loud、`dao-sheng.ps1` 的 `Resolve-DataHome` / 仓库内 root 拒绝 /
  `migrate-data` 入口、`tools/repo_tracking_guard.py`（Git 跟踪守卫）、
  `.github/workflows/repo-guard.yml`（CI 接线）、`tests/test_data_home.py`
  （16 个测试）与 `tests/test_repo_tracking_guard.py`（7 个测试）（实测
  23/23 OK——升级安全**专项测试结果，是专项子集，不是全量测试基线**）；
  本契约相应扩展 §1 / §3 / §4.6 / §5；
- 生成（不入库）：`.venv/`（仓库内，gitignore）；个人运行时数据位于仓库
  外部数据根（`<数据根>\config\`、`<数据根>\log\`、`<数据根>\instances\`），
  不在 Git worktree 内；
- 明确不交付（任务范围外）：GitHub 上传 / 仓库公开 / 4080 / 4060 专属配置 /
  模型自动下载 / Hermes / llama.cpp / Ollama 自动安装 / 更新系统。遗留个人
  数据的一次性安全迁移入口 = `migrate-data`（§4.6），不属于持续更新系统。

## 9. 层级与闸门判断（CLAUDE.md §6）

本任务 = **Deployment / Installation Layer（L4 部署层）**，属"Model
replacement（部署层 L4）"行的部署层范畴外围，不触及 8 类演化中任何一类的
权威层（不改 Domain / Constitution / Architecture / Capability / Memory
Provider / Worker / Hermes Adapter）；`dao_sheng/` 与 `tests/` 零 diff，
无重大 Architecture Change → 规则 8 未触发（无 ADR）；无真实技术未知
（Python venv / PowerShell 均为已知技术）→ 规则 9 未触发（无 Research
Gate 文档）。标准目录位置 = 本契约 §3 的 L4 部署层决定，以部署层文档为
权威，不反推 Core（规则 1 守住：Core 不读取、不依赖本契约定义的任何目录）。

角色入口（init-role / configure-role）同样全部留在 PowerShell 入口内：它们
只经 Python 子进程调用 Core 校验器（`dao_sheng.identity.parse_identity`、
`dao_sheng.faculties.FACULTY_ROOTS`），不硬编码 schema、不硬编码 faculty
根；`dao_sheng/` 保持零 diff（§0 规则 4 成立：不新增 Python 模块）。
schema 权威留在 Core，部署层只是把设计层的初始化 / 修改入口暴露出来——
角色入口不改变任何 Core 语义，也不把设计层载体变成部署层资产。
