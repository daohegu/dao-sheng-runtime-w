# V1 Reality Gate — STEP 15 Real Verification

- 日期：2026-09-21
- Step：STEP 15 — Real Verification（独立执行阶段，用户 2026-09-21 正式下达）
- 执行器：`tests/reality_gate.py`（本 Step 新增，非 test* 命名、不在默认测试套件内）
- 基线：M12 恢复点（DaoSheng 私有仓库历史提交，hash 不随公开副本发布）；当时全量 unit test 套件 OK（322 项——2026-09-21 当时基线，非当前基线）
- 执行后状态：**gate verdict = PASS**（`evidence/SUMMARY.json` `"gate": "PASS"`，P0–P9 全 ok，P4crash `exit_code = 1` 为预期内失败）
- 验收范围声明：判据全部基于 Validated Evidence（evidence JSON 逐条提取 + 执行器代码核实），未预设任何 UNKNOWN（规则 11）；身份/记忆等语义连续性判据不做判定（Q5 = UNKNOWN），只做行为与保护约束层面验证。

## 一、Gate 结果总览

| Phase | 内容 | 结果 | 证据文件（sha256 见 P9 workspace_tree） |
|---|---|---|---|
| P0 | 前置：workspace 初始化、identity / faculties 载体落盘、host seed 注入、端点探活 | ok | `evidence/P0.json` |
| P1 | A 模型（qwen3-coder:30b）：真实 wire 3 回合 + 经验导入 2 条 + 成长管线首跑 | ok | `evidence/P1.json` |
| P2 | B 模型（gpt-oss:20b）新进程：identity / continuity 不变 + 行为随新手段 | ok | `evidence/P2.json` |
| P3 | Hermes（host）重启：重导入零新增 + sync 零新增 + 个体状态不变 | ok | `evidence/P3.json` |
| P4a | 死端点降级回合（http://127.0.0.1:9，不可达）：action = None，"行动：无"，经历仍记录 | ok | `evidence/P4a.json` |
| P4crash | 崩溃进程演练：进行中回合进程退出 | exit_code = 1（预期内） | 无独立 JSON（失败即断言） |
| P4post | 崩溃后新进程：persist fail-loud + 历史引用全可解析 + turn 序号自 1 重启 | ok | `evidence/P4post.json` |
| P5 | 外部世界变化：2 回合 + 成长管线 4 段（digest → extract → reflect → verify）+ 引用链 | ok | `evidence/P5.json` |
| P6 | Memory Provider 换新实例（新进程）：18 条记录逐字一致 + 三维值域 + 跨实例引用链 | ok | `evidence/P6.json` |
| P7 | Worker 约束复验 + Capability 断开 + minimal root（无 model 降级） | ok | `evidence/P7.json` |
| P9 | 终检：5 项个体持久文件完整 + continuity 3 条 append-only + workspace 树哈希 | ok | `evidence/P9.json` |

时间线（evidence 文件 mtime）：P0 11:29 → P1 11:34 → P2 11:49 → P3 11:49 → P4a 11:49 → P4post 12:00 → P5 12:18 → P6 12:18 → P7 12:37 → P9 12:37，全程约 68 分钟（SUMMARY `started` 2026-09-21T11:29:40 / P9 `finished` 2026-09-21T12:37:37）。

## 二、4 类证据区分（本 Gate 的分类声明）

| 类别 | 载体 | 本 Step 中的角色 |
|---|---|---|
| Unit Test | 当时 322 项套件（`python -m unittest discover -s tests`；当时基线，非当前基线） | 基线：M12 恢复点（DaoSheng 私有仓库历史提交，hash 不随公开副本发布）当时全量 OK；本 Gate 不以其代替真实运行验证 |
| Integration Test | 进程内装配测试（`test_compose` 系列等） | 佐证：装配面 / 闸门接线已在进程内锁住 |
| System Test | M12 永久演练模块 `tests/test_acceptance_m12.py`（真实载体 + 真实 Memory Provider，唯一构造位 `composition.compose`） | 佐证：deletion 5 场景 / 崩溃演练 / 重启三事件的进程内系统级证据 |
| **Real Runtime Verification** | **本报告**：`tests/reality_gate.py` 于仓库外真实磁盘 workspace（使用者显式提供的演练目录，`--workspace` 参数或环境变量 `DAO_SHENG_REALITY_GATE_WORKSPACE`）+ 独立子进程边界 + 真实 Ollama wire（127.0.0.1:11434，15+ 次真实调用）+ 崩溃进程 + 死端点 | **本 Gate 的判定依据**。前三类均无法替代：真实进程退出、真实跨进程持久化、真实网络 wire 与超时/不可达 |

## 三、12 领域覆盖矩阵

| 领域 | 证据 phase | Verdict |
|---|---|---|
| Identity | P0（7 键载体落盘）/ P2（换 Model 后 sha256 不变）/ P4a / P7 / P9（identity_chain_ok） | PASS |
| Continuity | P2（跨 Model 文本逐字相同）/ P3（重启不变）/ P5（恰 +2）/ P9（3 条 append-only chain_ok） | PASS |
| Experience | P1（3 真实 wire 回合，action 280/397/408 字符）/ P4a（降级回合仍记录"行动：无"）/ P5（2 回合） | PASS |
| Memory | P1（导入 2 条 + 成长 3 条，三维齐备）/ P4post（18 条历史引用全可解析）/ P6（18 条逐字一致 + 三维值域） | PASS |
| Understanding | P1 / P2 / P5 真实 wire 行动输出（非空、随手段与经历变化） | PASS（行为层面；语义判据 Q5 不判） |
| Growth | P1（digest ref6 / extract ref7 / reflect ref8，(derived, reported, uncertain)）/ P5（4 段 + verify (derived, verified, confirmed) + INV-8 原记录不变 + 引用链） | PASS |
| Capability | P7（propose 真实落盘 `capabilities/proposed/真实演练能力.json` + 2 回合后目录字节不变 = 断开态 Core 照常运转） | PASS |
| Hermes Adapter | P0（seed 注入，s2 投影标记 + 空白被过滤，恰 2 条导入）/ P3（重启 no-op + 重导入零新增） | PASS |
| Worker Protocol | P7（`dao_sheng/` 零 worker 符号定义；token 仅 `identity.py` ×2 = K-11 引文行；identity 恰 7 键无 worker 字段） | PASS（V1 中 Worker 从不存在，删除 = 空操作，与 M10 一致） |
| Failure Recovery | P4a（端点不可达 → 降级回合不抛异常）/ P4post（崩溃后 fail-loud + 恢复回合 4763 字符 action 正常入库） | PASS |
| Restart | P2（Model 更换 = 新进程重启）/ P3（host 重启三事件 no-op 面）/ P4post（崩溃重启，turn 序号自 1，C-2） | PASS |
| Persistence | P6（跨 Provider 实例、跨进程 18 条持久记录逐字一致）/ P9（5 项个体持久文件 + workspace 19 文件哈希） | PASS |

## 四、6 项重点验证（逐项 verdict）

| # | 重点验证项 | Phase | 关键证据 | Verdict |
|---|---|---|---|---|
| ① | 更换 Model 后 Identity 仍然连续 | P2 | `identity_sha256` 与 P1 相同（`f29109…57dcd9`）；continuity 文本与 P1 逐字相同；旧 8 条引用逐字可解析（content + 三维）；新 2 回合 action 570/924 字符，中文弯引号风格随 B（gpt-oss）变化——手段变了、个体没变、行为随新手段 | **PASS** |
| ② | Hermes 重启后 Continuity 仍然存在 | P3 | 重导入 `reimport_refs = []`、sync `new_references = []`（`error = null`）、import_log 键位 `[s1:1, s1:2]` 未变；旧 10 条引用全可解析；continuity 未变（no-op，无 model 调用） | **PASS** |
| ③ | Memory Provider 更换后 DaoSheng Ontology 仍然成立 | P6 | 新 Provider 实例（新进程）：`refs_verified = 18`、`total_records = 18`，全部按 ref 去重逐字一致；`chain_across_provider = true`（insight 16 ↔ verify 18 跨实例可解析）；`ontology_value_domain_ok = true`（全部记录 origin / status / confidence 落在枚举值域）；identity 未变 | **PASS** |
| ④ | Worker 消失后 Identity 仍然成立 | P7 | V1 中 Worker 从不存在（`definitions_in_dao_sheng = 0`；token 仅 `identity.py` ×2 引文行）——"消失"= 空操作；identity 恰 7 键、无 worker 字段、`identity_sha256 == P0` | **PASS** |
| ⑤ | Capability 断开后 DaoSheng Core 仍然成立 | P7 | 能力仅停在 proposed 态（`proposed/真实演练能力.json` 落盘，sha256 `6999df…1bc`）；随后 2 回合（A 模型）后能力目录字节不变（`capability_dir_unchanged = true`）；minimal root（无 capabilities/、`ModelConfig()` 全未设定）：`assembled = true`、降级回合 action = None、capabilities 不代建（ADR 0007） | **PASS** |
| ⑥ | External World 变化后 Experience / Understanding / Growth 按 Domain 工作 | P5 | 2 新回合（refs 13/14，action 630/973 字符）→ digest 15 / extract 16 / reflect 17 / verify 18；三维：前 3 段 (derived, reported, uncertain)、verify (derived, verified, confirmed)；`inv8_original_unchanged = true`（被验证 insight 16 content 不变）；`reference_chain_built = true`（16 的 resolve_reference 链含 18）；continuity 恰 +2（reflect 17 + verify 指向 16）→ 总 3 条 | **PASS**（行为层面观察；"按 Domain 工作"= 管线形态、三维语义、引用链、INV-8 均按规格；语义正确性 Q5 不判） |

## 五、UNKNOWN 状态不变声明（规则 11）

- Open Questions 口径（V1 重构历史基线；原始状态文档不随公开副本发布）："11 项域内 UNKNOWN（`docs/domain/domain-invariants.md` §3 全表）状态不变"。本 Step 未读 `docs/domain/`（不在本 Step 允许清单内），不引用其内容、不改动其口径。
- 承接 M12 报告 §6"残留 UNKNOWN 9 项状态不变声明"，本 Gate 中以下 9 项**状态不变**，未被验证"顺便"填补：

| 项 | 状态 |
|---|---|
| Q5（identity 语义连续性判据） | UNKNOWN 不变（⑥及"Understanding"只做行为观察，未做语义连续性判定） |
| Q6（Worker 定义） | UNKNOWN 不变（④按 M10 已证形态执行：从不存在 = 空操作） |
| CINV-1（"道"的内容） | 未定不变 |
| U-5（Model / host 部署形态） | 未定不变（P4a / minimal root 以降级形态执行 = 该 UNKNOWN 的已定推论，非填补） |
| 消化-遗忘机制 | 未定不变（成长管线只验证已定的 digest / extract / reflect / verify 段） |
| Host 正式定义 | 未定不变 |
| V1 迁移 V0 数据最终状态 | 未定不变 |
| Tool 定义 | UNKNOWN 不变 |
| 三词关系 | UNKNOWN 不变 |

**P0 演练值声明**：identity 载体 7 键值（name = DaoSheng、self_appellation = "我"、voice = "平静、克制" 等）由执行器代行设计层写入，为**演练值**，非生产设计值；faculties 8 根同为演练值。本 Gate 验证的是载体 / 约束 / 行为形态，不验证这些具体取值的设计正确性。本报告引用的 identity / content / capability sha256（含 P9 `workspace_tree`）均为该演练实例的指纹，非真实 persona 数据。

## 六、测试环境、时延实测与模型对

- 环境：Windows 11 桌面机（原测试机具体硬件规格略）；Python 3.13（stdlib only）；Ollama 本机端点 127.0.0.1:11434。
- 时延实测（`tests/timing_probe.py` 单调用探针，执行记录见下；探针已随本 Step 收尾删除，数值记录于此）。下表数值为原测试机上的历史实测记录，仅用于说明当时模型对的选择理由，不构成跨平台性能结论：

| 模型 | 形态 | 实测 |
|---|---|---|
| A = qwen3-coder:30b | MoE 3.3B active | ≈15.7 s / call |
| B = gpt-oss:20b | MoE 5.1B active | ≈41.3 s / call |
| 原 B 候选 qwen3.6:27b | dense | 空闲时 ≈611 s / call；机器负载下 >2800 s（run4 实测超时） |

- **模型对 B 更换理由**（记录于执行记录 run1 → run4）：原 B 候选 qwen3.6:27b 为 dense 模型，单调用空闲 611 s，在 run4 时机器负载下单调用即超过 3600 s 相位超时，不可用于验证。更换为 gpt-oss:20b（OpenAI gpt-oss 家族，与 A 的 Qwen3-Coder 家族不同、架构不同，满足"更换 Model"的跨家族语义），实测 41.3 s/call 可用。
- **模型卸载纪律**：Ollama 模型每次用完后必须卸载（模型常驻会导致机器卡顿，属演练纪律）。已固化为执行器 `stop_models()`（运行前 / 每 phase 后 / FAIL 路径 / PASS 终点）；本次终版运行结束已确认 `curl /api/ps` = `{"models":[]}`，无残留。
- **失败证据保留**（诚实执行，未删）：run3 / run4 的失败证据保留于当时各自演练 workspace（原测试机上仓库外的独立目录）的 `evidence\` 下——run3：P0–P5 真实 ok，P6 runner 缺陷 FAIL；run4：P2 负载超时 FAIL。这些 workspace 目录属原测试机本地产物，不随公开副本发布。

## 七、诚实执行记录（五次运行）

| Run | 结果 | 根因 | 修复 |
|---|---|---|---|
| run1 | FAIL @ P1 | qwen3.6:27b 默认思考模式单调用 611 s，超 900 s 回合超时 | 模型对 A/B 互换（A 取快模型）+ TIMEOUT 900 + PHASE_TIMEOUT 3600；断言未弱化 |
| run2 | FAIL @ P2 | 双模型常驻争抢内存 / 计算 | 固化 `stop_models()` hygiene（每 phase 后卸载） |
| run3 | FAIL @ P6 | 执行器自身缺陷：`TypeError: 'MemorySnapshot' object is not subscriptable`（对 Provider 返回对象误用下标） | 改为属性访问；同时加入 FAIL / 超时路径部分输出落盘。期间出现 gbk reader-thread `UnicodeDecodeError` traceback = 无害噪音（子进程管道读取线程，stop 本身成功），已修复执行器 encoding |
| run4 | FAIL @ P2 | 机器负载下 qwen3.6:27b 单调用 >2800 s，超 3600 s 相位超时 | B 换 gpt-oss:20b（理由见第六节）+ PHASE_TIMEOUT 3600 → 7200 + 超时部分输出落盘 + 回合进度打印 |
| **run5** | **PASS** | — | 终版：P0–P9 全 ok，全程 ≈68 分钟，`SUMMARY.json "gate": "PASS"` |

五次运行中无任何断言被弱化或删除；修复全部作用于执行器 / 环境侧（超时预算、模型选择、hygiene），判定标准自 run1 起不变。

## 八、观察项（既有，带入，不影响 verdict）

1. `tests/test_model_client.py:85-86` `addCleanup` LIFO 顺序 → Windows stderr `OSError [WinError 10038]` 噪音（M11 起已记录；修复 = 交换两行，须触碰该文件的票顺带做）。
2. `tests/test_host_integration.py` 部分 `tempfile.TemporaryDirectory()` 未显式登记清理 → GC 时 `ResourceWarning`（既有模式，测试全 OK）。

## 九、workspace 位置与复现

- 终版 workspace：原测试机上的仓库外演练目录（由 `--workspace` 参数或环境变量显式提供，无默认目录；个体持久位 `individual/`、minimal 演练位 `individual-minimal/`、宿主位 `host/`、证据 `evidence/` 11 个 JSON，全部文件 sha256 记录于 `evidence/P9.json` `workspace_tree` 19 项）。该目录属原测试机本地产物，不随公开副本发布。
- 复现命令：

  ```
  PYTHONIOENCODING=utf-8 python tests/reality_gate.py --workspace <仓库外演练目录>
  ```

  也可经环境变量 `DAO_SHENG_REALITY_GATE_WORKSPACE` 提供 workspace；两者均缺失时执行器 fail-loud，不会回退到任何默认目录。重跑前须先清空 workspace 目录（持久位为真实磁盘，重跑不清空 = 污染历史状态）。Ollama 需在本机可用；模型对 = qwen3-coder:30b（A）+ gpt-oss:20b（B）为本次演练的部署值，公开使用者应按本机 Model 库存自行调整（见执行器头部注释）。

## 十、最终判定

**V1 Reality Gate = PASS。**

- 12 领域全覆盖 PASS（第三节）；6 项重点验证全部 PASS（第四节）；P0–P9 全 ok（第一节）。
- 本 Gate 是 4 类证据中唯一的 Real Runtime Verification 层（第二节）：真实磁盘、真实进程边界、真实 Ollama wire、真实崩溃、真实死端点。
- 无架构级缺陷暴露 → 规则 8 未触发，本 Step 无新增 ADR。
- 9 项残留 UNKNOWN 状态不变（第五节）；Q5 边界守住，未以验证之名填补 UNKNOWN。
- 证据边界：本 PASS 判定是 2026-09-21 于原测试机（Windows 11 桌面机 + 本机 Ollama + 上述模型对）完成的历史验收证据；复现依赖使用者本机 Model 服务并按自身库存调整模型对，未经其他平台复验，不可扩展为"所有平台均已验证"。
- 按 STEP 15 下达条件：真实验证通过 → V1 重构历史状态置为 COMPLETE，Exact Next Action = STEP 16（长期演化）。原始状态文档不随公开副本发布，此处为历史决定记录。
