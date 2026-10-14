# ADR 0008 — Model Runtime 架构：Model Interface 与多 Backend Adapter seam

- **Status**: accepted（2026-09-24，「Model Runtime Architecture Correction」任务，用户裁定 2026-09-24——三项裁定见 §裁定）
- **约束来源**: M06 决定 ⑨（`RECONSTRUCTION.md` Decisions + `dao_sheng/model_client.py` 模块 docstring 同文：wire 形态 = Ollama native `/api/*` 属 adapter 内部细节（depth 隐藏）；「若出现第二协议形态使 seam 转 real → 按规则 8 立 ADR（票 Required ADRs 触发条件）」）；`CLAUDE.md` §6 Model replacement 行（「出现第二 wire 协议形态 → ADR（规则 8）」）；`docs/specs/spec-adapters.md` §2 / §4（chat / complete 两级调用；Model 调用 seam = hypothetical，单 adapter、不预设第二个协议形态——经 M06 模块 docstring 引文核验，未重读 spec 原文）；规则 8；K-11 / INV-2（Identity 无 model 字段）；U-5（Model 部署形态 = UNKNOWN）；规则 11；规则 9（未触发，见 Consequences）；用户裁定 2026-09-24（三项裁定，见 §裁定）

## Context

当前形态（2026-09-24 真实代码现状确认，「Model Runtime Architecture Correction」任务）：

| 元素 | 真实形态 | 证据 |
|---|---|---|
| Model 调用 adapter | 单具体类 `ModelClient`，公共表面恰为两级 `complete(prompt) -> str` / `chat(messages) -> str`；**无显式 Model Interface 类型**——两级调用面即 interface（interface = test surface，depth），但类型是具体类本身 | `dao_sheng/model_client.py`（M06） |
| wire 形态 | Ollama native：`complete` → `POST {endpoint}/api/generate`，`chat` → `POST {endpoint}/api/chat`；硬编码于 adapter 内（depth 隐藏，不是部署决定） | `model_client.py:80-112` |
| 故障语义 | 重试 / 退避 / 超时 / 契约校验全内化（M06 决定 ⑩）；`ModelUnavailable` = 手段故障 fail-loud 信号（INV-1：手段故障 ≠ 个体故障） | `model_client.py:36-41,114-148` |
| 配置声明位 | `ModelConfig` frozen dataclass 7 槽（agent / reflection × endpoint / model + 共享 timeout / retry + `research_backend`），全 `None` = U-5 不预设，声明位不预设任何值（规则 11） | `dao_sheng/composition.py:68-83` |
| 装配 | `_build_model_client`（M06 决定 ⑪）：endpoint 与 model 全未设 → 该侧 `None` 不装配；部分设定 → fail-loud；两侧独立判定、共享 timeout / retry 槽位；`RuntimeAssembly.model / reflection_model: ModelClient \| None` | `composition.py:163-200,156-157` |
| 出站棘轮 | `ModelClient` = V1 内唯一允许发起 Model 出站调用的通道（棘轮：`urlopen` 仅限本模块） | `model_client.py:19-20` + M06 票 |
| Model Registry | **不存在**。「独立模型管理 / 编排容器：模型部署 = L4 历史歧义（U-5 UNKNOWN），不预设容器结构」 | `RECONSTRUCTION.md` 拒绝项 |
| ADR | 零 ADR 触及 Model wire / runtime / deployment（`docs/adr/` 全部 7 份，`Ollama\|wire\|llama\|Model 调用\|Model 部署\|U-5` Grep 零命中） | `docs/adr/` |

纠偏目标形态（用户 2026-09-24 正式下达）：

```
DaoSheng → Model Interface → Backend Adapter → llama.cpp / Ollama → Model Registry / Model
```

相对现状的 diff：

1. Model Interface 由「隐式（两级调用面）」显式化为**类型**；
2. 现行 `ModelClient`（Ollama wire）是 backend adapter 之一——**Ollama 保留**，非替换；
3. **新增 llama.cpp backend adapter** = 第二 wire 协议形态出现（llama.cpp server wire ≠ Ollama native `/api/*`：不同 endpoint 路径与请求 / 响应契约）；
4. **Model Registry** = 新结构（注册 / 选择机制：部署层值 → 哪个 backend / endpoint / model），现状中从不存在。

## 触发判定（本 ADR 为何存在）

两处**已记录在案的触发条件**同时命中：

- M06 决定 ⑨（frozen historical decision，作为 Historical Decision 持续有效）：「若出现第二协议形态使 Model 调用 seam 转 real → 按规则 8 立 ADR」（票 Required ADRs 触发条件原文）；
- `CLAUDE.md` §6 Model replacement 行：「出现第二 wire 协议形态 → ADR（规则 8）」。

引入 llama.cpp backend 不是「换现有 seam 之后的模型」——那是 L4 常规演化（endpoint / model 为部署值，adapter 内部不动，无需 ADR）——而是 **seam 从 hypothetical 升格 real** + **新结构（Model Registry）引入** → 重大 Architecture Change → 规则 8 触发 → 本 ADR 先于实施。

## Decision

1. **Model Interface 显式化为类型**：契约 = 现行两级调用面 `complete(prompt) -> str` / `chat(messages) -> str`，**仅暴露此两级**（M06 决定 ⑨ 表面不变；interface = test surface 不变；depth 隐藏不变）。Core 调用方（agent / reflection 两侧）只依赖 interface，不依赖任何具体 adapter 类。Interface 中性：不含 backend 名、不含 endpoint / URL、不含任何 backend 专属参数（ADR 0002 决定 2 同款中性纪律）；**Core 不认识 Ollama、llama.cpp、GGUF、GPU、URL、HTTP wire**——这些概念只存在于各 Backend Adapter 模块内部（M09 棘轮同款定位纪律）。Interface 的具体 Python 形态（Protocol / ABC / 其他）= 实现阶段决定项，本 ADR 只定结构事实。
2. **`ModelClient` 转位为 Ollama backend adapter**：Ollama native wire 形态不变（`/api/generate` + `/api/chat`）；重试 / 退避 / 超时 / 契约校验（决定 ⑩）全部保留并内化；`ModelUnavailable` 语义不变（INV-1）。既有 M06 行为测试面随转位保持有效（行为断言不变）。
3. **新增 llama.cpp backend adapter（seam 与职责边界）**：实现同一 Model Interface；llama.cpp server wire 形态（endpoint 路径 / 请求响应契约）、重试 / 退避、契约校验全部内化于该 adapter（与 Ollama adapter 同一 depth 纪律——wire 细节不进 Interface、不进 Core）；构造注入规则与 Ollama adapter 一致（endpoint / model / timeout / retry 全注入、无默认值，R-09）。**本 ADR 只确定 Backend Adapter seam 与职责边界；llama-server 的真实 wire 请求 / 响应必须在后续实施阶段用真实 llama-server 实测验证；该验证属于 Implementation / Reality Verification，不作为规则 9 的 ADR 前置条件**（裁定 3）。
4. **Model 调用 seam 状态：hypothetical → real**（本 ADR = M06 决定 ⑨ 触发条件的落地产物）；real seam 的契约 = Model Interface；Interface 不随 backend 增减变化（第二个 adapter 出现后 Interface 即为稳定契约，ADR 0002 决定 3 同款升格路径）。
5. **Agent / Reflection 允许异 backend（裁定 2）**：结构上允许 Agent Model 与 Reflection Model 使用不同 Backend；两侧独立配置、独立装配（M06 决定 ⑪ 独立判定规则保留：全未设 → `None`、部分设定 → fail-loud、共享 timeout / retry 槽位不变）；**当前不预设具体 Backend、不预设具体模型**；不把 llama.cpp 或 Ollama 写入 Domain / Identity / Doctrine（backend 名是部署层值，只出现在部署层配置与 adapter 层）。
6. **Model Registry = 进程内配置解析 / 装配层 Registry（裁定 1）**：模型注册 / 选择机制——把部署层值（哪个 backend / 哪个 endpoint / 哪个 model 名）解析为对应 backend adapter 实例；**仅负责 Model Backend + Model configuration 的解析与装配**。**不引入持久化注册文件，不新增机器本地持久化状态，不扩展 Installation Contract**。定位 = 装配层结构（composition root 或其调用的独立模块），**不是 DaoSheng Core 组件**：不进入 Domain / Identity / Continuity / Memory，不进入个体持久文件清单 5 项，不定义 Identity（K-11），不进入 Core 生成文本，不携带运营策略（与 `OperationalDefaults` 声明位分立）。
7. **U-5 边界**：本 ADR 决定的是「层结构 + seam 状态 + Interface 契约 + Registry 定位 + 异 backend 权限」的结构事实（ADR 0002 决定 6 先例：决定层的结构，不是完整定义）；**U-5 的具体部署值——具体模型、模型路径、GPU、量化、context、部署参数（timeout / retry 等）——全部继续 UNKNOWN / `None`**（`ModelConfig` 声明位保持全 `None`，规则 11）——部署层给值，Registry 消费值。

## 裁定（用户 2026-09-24）

三项裁定（对应草案开放点 1–3，全部已裁）：

1. **Model Registry**：采用「进程内配置解析 / 装配层 Registry」；不引入持久化注册文件；不新增机器本地持久化状态；不扩展 Installation Contract；Registry 仅负责 Model Backend + Model configuration 的解析与装配；Registry 不是 DaoSheng Core 组件，不进入 Domain / Identity / Continuity / Memory。
2. **Agent / Reflection**：结构上允许 Agent Model 与 Reflection Model 使用不同 Backend；两侧独立配置、独立装配；当前不预设具体 Backend，也不预设具体模型；不把 llama.cpp 或 Ollama 写入 Domain / Identity / Doctrine。
3. **llama.cpp wire**：ADR 只确定 Backend Adapter seam 与职责边界；llama.cpp server 的真实 wire 请求 / 响应必须在后续实施阶段用真实 llama-server 做验证；该验证属于 Implementation / Reality Verification，不作为规则 9 的 ADR 前置条件。

## Consequences

- **正面**：backend 可替换 / 可扩展（Ollama / llama.cpp），切换代价集中于 adapter + Registry（locality，ADR 0002 先例）；Identity 连续性结构保证不变（K-11 / INV-2：Identity 无 model 字段——「换 Model → Identity 连续」已于 STEP 15 Real Verification 重点验证 ① 实测，新形态必须保留该性质）；depth 不变（wire / 重试 / 超时全部内化，Core 测试表面维持两级）；INV-1 不变（手段故障 ≠ 个体故障，`ModelUnavailable` 语义不变，降级路径不变——M04 决定 ⑯：agent 侧未装配 → 全部回合降级）；两侧异 backend 的结构权限为部署层保留选项（裁定 2），当前不预设。
- **代价 / 限制**：新增 1 模块（llama.cpp adapter）+ 1 结构（Registry，进程内、零持久化）+ 1 类型显式化（Interface）；**M09 出站棘轮显式调位**——现行「`urlopen` 仅限 `model_client.py`」扩为「`urlopen` 仅限各 Backend Adapter 模块」（M09 纪律：外部 Model HTTP 出站只能存在于各 Backend Adapter 模块；token 允许位扩位须显式调位，M09 先例；棘轮本身保留，不拆）；既有 M06 测试面（`tests/test_model_client.py` 等）随模块转位重锚（行为断言不变，模块路径 / 符号名变）。
- **规则 9（Research Gate）判定：不触发**——llama.cpp（server）与 Ollama 均为已知技术：Ollama wire 有真实执行证据（V0 Model 调用部署面全部执行证据形态 + STEP 15 Real Verification 真实 wire 15+ 次调用）；llama.cpp server API 为已知公开接口。无真实技术未知（STEP 11 先例闸门判据）→ 不写 research 文档，不为过闸而过闸。llama.cpp wire 的真实请求 / 响应验证按裁定 3 归实施阶段（Implementation / Reality Verification），不以 Research Gate 形式前置。
- **未决（显式保留）**：
  - U-5 具体部署值（具体模型、模型路径、GPU、量化、context、timeout / retry）= 仍 UNKNOWN / `None`，本 ADR 不填补（规则 11）；
  - 「独立模型管理 / 编排容器」仍不采用——Registry 是进程内装配层结构，不是独立容器（`RECONSTRUCTION.md` 拒绝项先例 + 裁定 1）；Registry 是否 / 何时升格为容器 = 另案（规则 8）；
  - Research 调用面不受本 ADR 影响（M06 决定 ⑫：Research / world 观察不随装配，`ModelConfig.research_backend` 槽位仍未定）。

## 内部一致性检查（2026-09-24，本 ADR 自核）

| 约束 | 检查 | 结果 |
|---|---|---|
| U-5 | 具体模型 / 模型路径 / GPU / 量化 / context / 部署参数全部继续 UNKNOWN / `None`；`ModelConfig` 声明位保持全 `None`；本 ADR 只定结构事实，未填补任何部署值（规则 11） | 未违反 |
| M06 | 决定 ⑨：两级调用面 `complete` / `chat` 表面不变（Interface 契约 = 该表面，仅暴露此两级）；决定 ⑩：重试 / 退避 / 故障语义内化不变；决定 ⑪：两侧独立判定、全未设 → `None`、部分设定 → fail-loud 保留（决定 5 在其上加权限，不改其判定规则）；决定 ⑫：Research 不随装配、`research_backend` 仍未定；Ollama wire 形态不变 | 未违反 |
| M09 | 出站棘轮保留：外部 Model HTTP 出站（`urlopen`）只能存在于各 Backend Adapter 模块（现行 `model_client.py` = Ollama adapter；扩位后 = 各 Backend Adapter 模块）；Core 非 adapter 层无出站通道；Core 不认识 URL / HTTP wire | 未违反 |
| K-11 | Identity 载体无 model 字段；Registry 不定义 Identity（裁定 1：不进入 Domain / Identity / Continuity / Memory）；本 ADR 未新增任何 Identity 字段 | 未违反 |
| INV-2 | Identity 连续性不依赖 model（STEP 15 Real Verification 重点验证 ① 实测）；backend 替换 / 两侧异 backend（裁定 2）不改变 Identity、不破坏连续性 | 未违反 |
