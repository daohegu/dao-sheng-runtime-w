# ADR 0009 — Shared Wire Client beneath the Model seam

- **Status**: accepted（2026-10-08，「Model seam → Shared Wire Client 架构裁定」任务，Q1–Q15 两轮 grilling 正式用户裁定；**Accepted 生效点 = Q12 裁定**——此前输出中的「ADR 0009 已 Accepted」属候选状态）
- **约束来源**: ADR 0008（accepted 2026-09-24，**不修改**——本 ADR 引用并延伸）；决定 ㊷（棘轮「Model backend 集合」单一声明位；私有仓库历史提交，hash 不随公开副本发布）；`CLAUDE.md` §6（Architecture evolution / Model replacement 行；规则 8）；规则 7（冻结历史不回改）；规则 9（Research Gate 判定，见 Consequences）；规则 11（U-5 不填补）；规则 13；INV-1（手段故障 ≠ 个体故障）；K-11 / INV-2（Identity 无 model 字段）；R-09（无默认值）；U-5（Model 部署形态 = UNKNOWN）；M09 显式调位纪律（ADR 0008 Consequences）；Q1–Q15 用户裁定（见 §裁定）

## Context

当前形态（2026-10-08 真实代码现状确认，分块读取 + Grep 实测，未全量重读源码）：

| 元素 | 真实形态 | 证据 |
|---|---|---|
| Model Interface | `Model` Protocol 两级调用面 `complete(prompt) -> str` / `chat(messages) -> str`；`ModelUnavailable` 唯一定义位 = `dao_sheng/model.py`（ADR 0008 决定 1） | `dao_sheng/model.py` |
| Ollama Backend Adapter | Ollama native `/api/generate` / `/api/chat`；`__init__` 四校验 ValueError（endpoint / model 不得为空 / timeout_seconds 必须为正数 / retry_limit 不得为负数）；transport 内化；extract 取值 `data["response"]` / `data["message"]["content"]`，catch `(KeyError, TypeError)` → `ModelUnavailable("Model 响应不合契约")`；**无 `isinstance` 结果类型校验——extract 结果可能为 None（JSON null）直接返回** | `dao_sheng/model_ollama.py`（Grep 实测：全包零 `isinstance`） |
| llama.cpp Backend Adapter | OpenAI 兼容 `/v1/completions` / `/v1/chat/completions`；同构 `__init__` 四校验（逐字同文）；transport 内化；extract 取值 `data["choices"][0]["text"]` / `data["choices"][0]["message"]["content"]`，catch `(KeyError, IndexError, TypeError)`；**complete / chat 两路均有 `isinstance(..., str)` 校验 → 非 str → `ModelUnavailable("Model 响应不合契约")`** | `dao_sheng/model_llama_cpp.py`（Grep 实测：complete / chat 两路在位） |
| transport 语义重复 | 两 adapter 逐字重复实现：`_RETRY_BASE_SECONDS = 0.1`（adapter 内部算法参数，不是部署值）/ 重试循环 `range(retry_limit + 1)` / 退避 `time.sleep(_RETRY_BASE_SECONDS * (2**attempt))` / HTTP `>= 500` 重试、4xx 不重试 / `(URLError, OSError)` last_error / `JSONDecodeError` 不重试 / 耗尽 → `ModelUnavailable(f"Model 调用在 {self.retry_limit} 次重试后仍不可用")`（逐字同文） | 两 adapter 文件（Grep 实测） |
| contract enforcement 不一致 | llama.cpp 侧 complete / chat 两路 `isinstance(..., str)` 校验在位；Ollama 侧无结果类型校验（None 可通过）——同一 Model Interface 的响应契约在两 adapter 间不一致 | 两 adapter 文件（Grep 实测） |
| 棘轮现状 | `outbound_allowed`（urlopen 出站 allowlist）派生自 `EXPECTED_MODEL_BACKENDS`（决定 ㊷ 单一声明位）；urlopen 允许位 = 各 Backend Adapter 模块（ADR 0008 Consequences M09 调位） | `tests/test_architecture_invariants.py` |

目标形态：

```
DaoSheng → Model Interface → Backend Adapter → Wire Client (dao_sheng/model_wire.py) → HTTP wire
```

相对现状的 diff：

1. **新 deep module**：Wire Client = `dao_sheng/model_wire.py`，位于 Backend Adapter 之下——Model 出站 HTTP 行为收敛为单一实现位；
2. **transport 语义调位**：重试循环 / 退避 / HTTP 分类 / JSON decode / 耗尽消息从两 adapter 重复实现调位为 Wire Client 单一实现位（行为语义不变）；
3. **contract enforcement 集中**：extract 结果类型统一 enforce 于 `post_json()` 内部（有意的契约收紧，见 Decision 6）；
4. **出站 allowlist 调位**：urlopen 允许位从各 Backend Adapter 模块调位为 `model_wire.py`（实施时执行，见 Decision 7）。

## 触发判定（本 ADR 为何存在）

规则 8 触发（重大 Architecture Change），三点：

1. **新结构层**——Wire Client = Model seam 之下的新结构层（Backend Adapter → Wire Client 调用关系），不是既有形态内的部署值替换（对照 ADR 0008：常规 Model replacement = endpoint / model 部署值替换、无需 ADR；本例 = 结构调位）；
2. **M09 出站 allowlist 调位**——urlopen token 允许位从各 Backend Adapter 模块调位为 `model_wire.py`（M09 显式调位纪律）；
3. **有意的契约收紧**——extract result 统一 enforce `str` = 行为变化（Ollama 原先可能返回 None 的行为被统一纠正），不是「纯重构、零行为变化」（Q3 明确要求记录）。

Q7 / Q12 正式确认建立 ADR 0009 及其 Accepted 状态。ADR 0008 不回改（规则 7）：0009 引用并延伸 0008（0008 的 Model Interface / seam real / Registry / U-5 决定全部继续有效）。

## Decision

1. **模块与术语**：module = `dao_sheng/model_wire.py`；术语 = **Wire Client**——CONTEXT.md 术语表定义（逐字）：「Model seam 之下、Backend Adapter 共用的出站 wire implementation / deep module，负责共享 transport failure semantics 与 wire contract enforcement」。不用 `model_http.py` / `wire_client.py`（Q8）。
2. **职责 = Transport + contract**：Wire Client 提供 `post_json(...)` 共享 transport / retry / backoff / JSON 边界处理、共享 config validation、extract 结果统一 contract enforcement。两 adapter 保留各自 endpoint path / payload shape / extract（协议差异留在 adapter）。**不退化为纯 wire profile 数据壳**（Q2）。
3. **模块级函数形态 + 无状态**：`validate_config(endpoint, model, timeout_seconds, retry_limit) -> None` + `post_json(endpoint, timeout_seconds, retry_limit, path, payload, extract) -> str`。Wire Client 无状态、无 config ownership；config 仍属各 adapter（Q10）。
4. **构造即 fail-loud**：两 adapter `__init__` 各自调用共享 `validate_config()`，构造即 fail-loud，不推迟到首次 request；保留四项 ValueError 语义（endpoint / model 不得为空 / timeout_seconds 必须为正数 / retry_limit 不得为负数）。U-5 / R-09 / 无默认值不变（Q4）。
5. **失败语义五类分类**（本 ADR 明确记录）：

   | 类别 | 可重试性 |
   |---|---|
   | 传输失败（`URLError` / `OSError` / HTTP 5xx） | 可重试 |
   | HTTP 4xx | 不可重试 |
   | JSON decode failure（`JSONDecodeError`） | 不可重试 |
   | extract 失败（`KeyError` / `IndexError` / `TypeError`） | 不可重试——集中捕获、统一转 `ModelUnavailable` |
   | 响应契约违规（extract result 非 `str`） | 不可重试——`ModelUnavailable` |

   `post_json()` 包裹 `extract()` 调用，集中捕获 extract 失败统一转换 `ModelUnavailable`，随后统一 enforce extract result 必须为 `str`。adapter 保持自然取值风格（不改成全 `.get` 防御链）（Q9）。`ModelUnavailable` 保持唯一定义位 = `dao_sheng/model.py`（ADR 0008 决定 1）；Wire Client 只抛出，不重定义。
6. **有意的契约收紧**：extract result 统一 enforce——`str` => 正常返回；`None` / 任意非 `str` => `ModelUnavailable`，不重试。**Ollama 原先可能返回 None 的行为被统一纠正**（现状：llama.cpp 两路 isinstance 校验在位、Ollama 无结果类型校验）。这是有意的收紧，明确记录，不声称「纯重构、零行为变化」（Q3）。
7. **棘轮调位（实施时执行）**：新增 `MODEL_WIRE_MODULES` 刻意声明位；`outbound_allowed = MODEL_WIRE_MODULES`（urlopen 最终只允许 `model_wire.py`）；`EXPECTED_MODEL_BACKENDS`（决定 ㊷）不再推导 outbound allowlist，仍派生装配点结构性豁免与手段模块集合 Model 部分；import 窄例外（仅 Backend Adapter 模块及自身测试可 import `model_wire`）；`model_wire.py` 纳入 M06 手段模块集合；不进 backend / `ADAPTERS` 三元组；棘轮继续不从生产侧自动推导（Q5 / Q11）。目标 = 棘轮强制 transport locality。
8. **测试收敛（实施时执行）**：新增 `tests/test_model_wire.py`，共享 transport / contract 行为只测一次；adapter tests 收敛为 wire 固有 extract + 公共 Model 表面 `chat` / `complete` + 每 adapter 至少一条穿过 Model interface 的完整 mock 成功路径；**删除重复测试前必须建立逐条等价映射**（每个删除断言对应一个存活断言），映射留入实施 handoff 作为「测试强度未弱化」证据（Q6）。
9. **实施另立**：本票 = 设计落档（ADR 0009 + CONTEXT.md + `RECONSTRUCTION.md` + handoff）；不修改生产代码 / 测试 / 棘轮；不创建 `.scratch/` 实施 ticket；实施另立正式演化票（Q1 / Q14）。
10. **与 ADR 0008 的关系**：ADR 0008 不修改（规则 7）。两级调用面 `complete` / `chat` 不变；`ModelUnavailable` 唯一定义位 = `model.py` 不变；Core 不认识 Wire Client（ADR 0008 决定 1 同款定位纪律——Core 不认识 HTTP wire）；Model Registry（进程内装配层）不变；U-5 边界不变；R-09 无默认值不变；K-11 / INV-2 不变；INV-1 不变（`ModelUnavailable` = 手段故障，不是个体故障）。

## 裁定（用户 2026-10-08，Q1–Q15 两轮 grilling）

- **Q1**：先文档后实施；本轮只完成 ADR 0009 + CONTEXT.md + `RECONSTRUCTION.md` 状态同步 + handoff；不修改生产代码 / 测试；实施另立正式演化票。
- **Q2**：确认 (b) Transport + contract；两 adapter 保留 endpoint path / payload shape / extract；不退化为纯 wire profile 数据壳。
- **Q3**：集中 enforce，明确记录为「有意的契约收紧」，不声称「纯重构、零行为变化」；`str` => 正常返回，`None` / 任意非 `str` => `ModelUnavailable`，contract violation 不重试；ADR 必须明确说明 Ollama 原先可能返回 None 的行为被统一纠正。
- **Q4**：确认 (i)；两 adapter `__init__` 各自调用共享 `validate_config()`，构造即 fail-loud；U-5 / R-09 / 无默认值不变。
- **Q5**：新增显式 `MODEL_WIRE_MODULES` 声明位；import ratchet 窄例外（仅 Backend Adapter 模块及自身测试可 import `model_wire`）；`model_wire.py` 纳入 M06 手段模块集合；不进 backend / `ADAPTERS` 三元组；棘轮不从生产侧自动推导。
- **Q6**：确认 (a)；新增 `tests/test_model_wire.py` 共享 transport / contract 行为只测一次；adapter tests 收敛；删除重复测试前建立逐条等价映射，映射留入实施 handoff。
- **Q7**：确认建立 ADR 0009「Shared Wire Client beneath the Model seam」；ADR 0008 不变，0009 引用并延伸，不回改历史 ADR；Research Gate 不触发。
- **Q8**：module = `dao_sheng/model_wire.py`；术语 = Wire Client；CONTEXT.md 术语表加入，定义逐字（见 Decision 1）；不用 `model_http.py` / `wire_client.py`。
- **Q9**：确认 (a)；`post_json()` 包裹 `extract()`，集中捕获 `KeyError` / `IndexError` / `TypeError` → 统一转换 `ModelUnavailable` 且不重试，随后统一 enforce result 必须为 `str`；adapter 保持自然取值风格；ADR 明确五类（见 Decision 5 表）。
- **Q10**：确认 (i)；只提供模块级行为（两函数签名，见 Decision 3）；Wire Client 无状态、无 config ownership。
- **Q11**：确认 (ii)；outbound urlopen 最终只允许 `model_wire.py`；`outbound_allowed = MODEL_WIRE_MODULES`；`EXPECTED_MODEL_BACKENDS` 不再推导 outbound allowlist（仍派生装配点豁免与手段集合 Model 部分）；保留 `MODEL_WIRE_MODULES` 刻意声明位 / import 窄例外 / M06 手段集合 / 不进 `ADAPTERS`；目标 = 棘轮强制 transport locality。
- **Q12**：正式确认 ADR 0009 = Accepted（生效点 = 本条裁定，2026-10-08）；此前输出中的「ADR 0009 已 Accepted」属于候选状态。
- **Q13**：三项全部执行：CONTEXT.md 新增 Wire Client 术语（定义逐字同 Q8）；Model / Backend Adapter 既有条目仅追加 ADR 0009 指针，不重写定义；U-5 / UNKNOWN 内容一字不动。
- **Q14**：不预立 implementation spec / ticket；本票只在 handoff 记录后续实施范围、Required Inputs、实施前置条件；不在 `.scratch/` 创建未开工 ticket。
- **Q15**：单条决定 ㊸ = 本次完整正式裁定（ADR 0009 accepted + Q1–Q14 所有裁定 + 理由摘要），不拆多条。

## Consequences

- **正面**：transport 语义收敛为单一实现位——重试 / 退避 / HTTP 分类 / 耗尽消息不再在两 adapter 各自漂移；响应契约统一 enforce（现状不一致消除）；棘轮强制 transport locality（urlopen 只允许 `model_wire.py`，出站面收缩而非扩位）；协议差异（endpoint path / payload shape / extract）留在 adapter——Model Interface 与 Core 测试表面不变；将来第三 Backend adapter 自动继承 transport + contract 语义。
- **代价 / 限制**：新增 1 模块（`model_wire.py`）+ 1 测试文件（`tests/test_model_wire.py`）（实施时）；两 adapter transport 代码删除并调位（调位，不是新增）；**M09 出站 allowlist 显式调位**（各 Backend Adapter 模块 → `model_wire.py`；M09 纪律：token 允许位调位须显式，棘轮本身保留、不拆）；契约收紧 = 行为变化（Ollama None 路径纠正为 `ModelUnavailable`）；测试收敛以逐条等价映射为前置（防测试强度弱化）。
- **规则 9（Research Gate）判定：不触发**——HTTP transport / retry / 契约校验均为已知技术调位（两 adapter 既有行为 + ADR 0008 真实 wire 实测证据在位），无真实技术未知（STEP 11 先例闸门判据）→ 不写 research 文档，不为过闸而过闸。
- **未决（显式保留）**：
  - U-5 具体部署值（具体模型、模型路径、GPU、量化、context、timeout / retry）= 仍 UNKNOWN / `None`，本 ADR 不填补（规则 11）；
  - 实施票未立——`model_wire.py` / adapter 调位 / 棘轮调位 / 测试收敛全部 = 实施阶段动作，本 ADR 只定设计事实（Q1 / Q14）；
  - 棘轮现状（`outbound_allowed` 派生自 `EXPECTED_MODEL_BACKENDS`）→ 目标态（`outbound_allowed = MODEL_WIRE_MODULES`）= 实施时调位，本落档不动棘轮；
  - 契约收紧对实际部署的影响（既有部署路径是否触发新 `ModelUnavailable`）= 不新增 UNKNOWN——属实施阶段测试面验证事项，不提前填补。

## 内部一致性检查（2026-10-08，本 ADR 自核）

| 约束 | 检查 | 结果 |
|---|---|---|
| ADR 0008 | 0008 不修改（规则 7）；两级调用面 / `ModelUnavailable` 唯一定义位 / seam real / Registry 进程内 / U-5 边界全部保留；0009 = seam 之下延伸，不与 0008 任何决定冲突 | 未违反 |
| 决定 ㊷ | `EXPECTED_MODEL_BACKENDS` 单一声明位纪律保留；「不从生产侧派生」原则不变；outbound allowlist 派生关系 = 实施时调位，本落档不动棘轮 | 未违反 |
| M09 | 出站棘轮保留、不拆；token 允许位显式调位（各 Backend Adapter 模块 → `model_wire.py`）于实施时执行；Core 非 adapter 层无出站通道 | 未违反 |
| INV-1 | `ModelUnavailable` = 手段故障 fail-loud 信号语义不变；contract violation / extract failure 转 `ModelUnavailable` = 手段故障，不是个体故障；降级路径不变 | 未违反 |
| K-11 / INV-2 | Identity 无 model 字段；Wire Client 不进入 Domain / Identity / Continuity / Memory；无新增 Identity 字段 | 未违反 |
| U-5 | 未填补任何部署值；`ModelConfig` 声明位保持全 `None`；config ownership 仍属各 adapter（部署层给值） | 未违反 |
| R-09 | 无默认值引入；`validate_config` 只校验注入值 | 未违反 |
| 规则 7 | ADR 0008 与历史 ADR 不回改；冻结历史零触碰 | 未违反 |
| 规则 8 | 重大 Architecture Change → 本 ADR 先于实施（本 ADR = 触发落地产物；实施另立） | 满足 |
| 规则 9 | 无真实技术未知 → 不触发，不写 research 文档 | 满足 |
