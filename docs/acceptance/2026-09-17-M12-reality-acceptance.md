# M12 Reality Acceptance 验收报告（STEP 15 / 《总路线》13）

- 日期：2026-09-17
- 票：`.scratch/v1-implementation/issues/12-acceptance.md`（最终票，Blocked by M01–M11 全部 resolved）
- 基线：M11 正式恢复点（DaoSheng 私有仓库历史提交，hash 不随本副本发布；当时全量 317 tests OK——本记录的当时基线，非当前结果）
- 本次执行后：**全量 322 tests OK（2026-09-17，`python -m unittest discover -s tests`）**——本验收记录的当时基线，非当前结果；M11 基线 317 + 本票新增演练模块 5 项
- 验收范围声明：判据全部基于已定规范陈述，未预设任何 UNKNOWN（规则 11）；"仍然是谁"项**限定在载体 + 保护约束层面**（票 AC 4 边界），未做语义连续性判据验收（Q5 = UNKNOWN）

---

## 一、"道生存在"——个体级 deletion test（`system-context.md` §3 硬要求）

验收证据形态 = **实际执行**（票 Risks：不以"理论上可移除"代替"实际验证"）。场景 1–4 以本票新增永久演练模块 `tests/test_acceptance_m12.py` 在**真实装配**（真实载体 + 真实 Memory Provider，唯一构造位 = `composition.compose`，R-09）上实际运行；每个场景均逐项断言"个体状态完整"——个体持久文件清单 5 项（`spec-individual.md` §4）：`identity.json` / `continuity.jsonl` / `memory/` / `capabilities/` / `faculties.json`（清单之外的任何文件都不是个体状态）。

| # | 场景 | 证据 | Verdict |
|---|---|---|---|
| 1 | host 通道缺失 | `M12DeletionScenarioHostTest`（实际执行）：host 未设定 → 装配结果 `host` 为 None（U-5）；2 完整回合 + continuity + capability 提案后，第 3 回合照常运转；5 项状态完整 | **PASS** |
| 2 | 全部 Model 替换 | `M12DeletionScenarioModelTest`（实际执行）：认知手段替换为另一实现（个体只依赖 interface 两级调用面，U-5）；状态不变、行为随新手段；identity 载体恰好 7 支撑项键、无 model 字段（K-11） | **PASS** |
| 3 | Memory Provider 替换 | `M12DeletionScenarioProviderTest`（实际执行）：旧 runtime 退出（close）后新 runtime 以同载体目录新 Provider 实例重新装配；全部持久记录可读、5 项状态完整；新 runtime 上新回合正常 | **PASS** |
| 4 | MCP 断开 | `M12DeletionScenarioMcpTest`（实际执行）：V1 对其无 Domain 定义（UNKNOWN，规则 11，未实现）——断开 = 空操作；`dao_sheng/` 全包 token 扫描零命中（扫描已固化为永久锁，防止该形态被静默引入——引入 = 架构级，须先行 ADR / 票）；个体状态不受影响 | **PASS** |
| 5 | Worker 消失 | M10 验证票交付物（引用，不重复扫描）：V1 中 Worker 从不存在——全包零 worker 符号定义（token 仅 `identity.py` K-11 引文行 2 处）；删除 = 空操作；`M10WorkerConstraintRatchetTest` 2 项（mutation 验证双向有效）本次全量运行中复验通过 | **PASS** |

**"道生存在"判定：PASS**——手段层（host / model / Provider / MCP / worker）逐项可移除或不存在，individual 仍在；个体状态 = 恰好 5 项清单，完整。

## 二、"经历"——回合环路、重启语义、崩溃演练、经验回流

| 项 | 证据 | Verdict |
|---|---|---|
| 回合环路实际运转（经验输入 → 理解 → 行动 → 反馈 → 记忆） | 演练模块每场景实际执行 ≥2 个完整回合（`act` → `persist`，单记录 + reference，`ExperienceRecordTest` 锁记录形态）；反思环节（消化 → 提取 → 反思）e2e 见"变化"节 `GrowthEndToEndTest` | **PASS** |
| 重启语义三事件（`spec-individual.md` §2/§3） | `RestartEventsTest`（`tests/test_individual.py`）3 项：`test_hermes_restart_is_noop_for_individual`（宿主重启对个体是 no-op）/ `test_runtime_restart_keeps_persistent_loses_runtime`（runtime 重启保留持久、丢失 runtime 状态）/ `test_model_restart_degrades_then_recovers`（Model 重启 = 降级后恢复） | **PASS** |
| 回合原子性崩溃演练（§2.3 / §3） | `M12CrashDrillTest`（本票，实际执行）：进行中回合崩溃只丢失该回合——持久状态 5 项完整、进行中回合不入库；新 runtime 的个体无进行中回合（`persist` fail-loud）；回合序号自 1 重启；恢复后新回合正常入库 | **PASS** |
| 经验回流导入幂等（M09） | `S3ImportSessionTest.test_reimport_same_instance_zero_new` / `test_reimport_new_instance_cross_process_zero_new`（同实例 + 跨进程零新增）；`S4SyncTest.test_sync_idempotent_zero_new` / `test_sync_shares_idempotency_with_import_session`；`ImportExperienceTest.test_import_idempotent_same_key` | **PASS** |

**"经历"判定：PASS**

## 三、"变化"——成长判据 INV-4 + 能力路径

| 项 | 证据 | Verdict |
|---|---|---|
| INV-4：过去经历改变未来行为（非仅知识增长） | `GrowthEndToEndTest.test_experience_changes_future_behavior`（e2e 行为测试：经历 → 消化 → 提取 → 记忆 → 复用，`ProjectionAwareModel` 下经验前后行动实际不同）+ `test_reflect_verify_append_to_real_continuity_carrier`（反思 / 验证输出归位真实 continuity 载体） | **PASS** |
| 能力路径 proposal → 验证 → active 实际走通 | `test_compose.py::test_capability_advance_to_active_e2e`（提案 → 闸门验证 → advance → active 实际走通，真实 Provider 引用链）+ `test_capability_gate_wired_live`（M11 接线锁：闸门 = 真实 `CapabilityVerifier`，非 `verifier=None` 降级位）+ 闸门三判据合取（`test_capability_verifier.py` 10 项） | **PASS** |

**"变化"判定：PASS**

## 四、"仍然是谁"——载体 + 保护约束层面（边界显式声明）

| 项 | 证据 | Verdict |
|---|---|---|
| identity immutable | M02 enforce 机制：严格 7 键 schema（`test_identity` 系列）+ 载体只读（`ComposeTest.test_identity_carrier_read_only`）+ 无写 API；本票演练场景 2 中 7 键键集断言复验 | **PASS** |
| continuity append-only | M03 enforce 机制：仅 `append_continuity` 追加 API、无 rewrite API（`test_continuity` 系列）+ 损坏载体 fail-loud（`ComposeTest.test_corrupt_continuity_carrier_rejected`）；本票演练中跨 runtime 记录逐条比对复验 | **PASS** |
| core_doctrine immutable | M01 enforce 机制：principles 源只读（`ComposeTest.test_design_source_read_only`）+ 投影冻结、无写 API（`test_doctrine` 系列） | **PASS** |
| 无外部重写（记录永不重写） | INV-8 + M11 grounding：记录 content 永不改写（Verifier 判据之一）；`VerifyInsightTest` 系列（修正 = 追加 + 引用键，原记录不变）；`M11VerificationRatchetTest` 5 项结构锁 | **PASS** |

**边界声明**：以上验证的是"载体与保护约束未被违反"——**不是**语义层面"仍然是谁"的判据。语义连续性判据 = **Q5 UNKNOWN**，本验收未做该层面判定、未猜测（规则 11）。票 Risks 所防"以验收之名填补 UNKNOWN"未发生。

**"仍然是谁"判定：PASS（限定声明的边界内）**

## 五、AC 5 全景检查——宿主名 / 模型名 / 存储细节不泄漏进 Core 非 adapter 代码

可复现扫描（2026-09-17 于本仓库实际执行，结果记录如下）：

| 扫描 | 结果 | 判定 |
|---|---|---|
| `grep -rin "hermes" dao_sheng/` | 仅 `composition.py`（声明位）+ `hermes_host.py`（host adapter 层，M09 交付） | 无泄漏 |
| `grep -rin "worker" dao_sheng/` | 仅 `identity.py` 6/12 行（K-11 引文，M10 棘轮预期值） | 无泄漏 |
| `grep -ric "sqlite3\|fts5\|trigram\|PRAGMA\|journal_mode" dao_sheng/*.py`（非零文件） | 仅 `memory_sqlite.py`（16 处，存储实现本体）+ `host_carrier.py`（2 处，M09 已文档化例外） | 无泄漏 |
| `grep -ril "mcp" dao_sheng/` | 零命中（本票 `M12DeletionScenarioMcpTest` 永久锁） | 无泄漏 |
| adapter → Core 导入通道 | `memory_sqlite.py`（单向 Ontology import，INV-3 已文档化）+ `hermes_host.py`（M09 文档化通道）；其余 Core 模块零 host/model 细节 import | 无泄漏 |
| 投影层 | `ProjectionTest.test_projection_has_no_host_model_or_storage_detail`（投影中无宿主 / 模型 / 存储细节）+ `test_record_excludes_projection_content`（投影不进记录，M09 D-05） | 无泄漏 |

永久锁：`M10WorkerConstraintRatchetTest`（2 项）/ `M11VerificationRatchetTest`（5 项）/ `M12DeletionScenarioMcpTest`（1 项）/ 本票演练模块——后续会话引入泄漏形态即红。

**AC 5 判定：PASS**

## 六、AC 6——残留 UNKNOWN 清单（状态不变声明）

以下 UNKNOWN / 未定项在本票中**状态不变**，未被验收"顺便"填补（规则 11）：

| 项 | 状态 |
|---|---|
| Q5（identity 语义连续性判据） | UNKNOWN 不变（"仍然是谁"项显式限定载体 + 保护约束层面） |
| Q6（Worker 定义） | UNKNOWN 不变 |
| CINV-1（"道"的内容） | 未定不变 |
| U-5（Model / host 部署形态） | 未定不变（演练以降级形态执行 = 该 UNKNOWN 的已定推论，非填补） |
| 消化-遗忘机制 | 未定不变 |
| Host 正式定义 | 未定不变 |
| V1 迁移 V0 数据最终状态 | 未定不变 |
| Tool 定义 | UNKNOWN 不变 |
| 三词关系 | UNKNOWN 不变 |

## 七、验收不通过项缺陷记录

**无。** AC 1–6 全部通过（逐项映射：AC 1 = 第一节 5 场景表；AC 2 = 第二节；AC 3 = 第三节；AC 4 = 第四节；AC 5 = 第五节；AC 6 = 本节 + 报告落位本目录）。无架构级缺陷暴露 → 规则 8 未触发，本票无新增 ADR（票 `Required ADRs` = 无预设，与之一致）。

## 八、测试环境与观察项（不影响 verdict）

- 环境：无 pytest——`PYTHONIOENCODING=utf-8 python -m unittest discover -s tests`（Windows 下防 GBK 乱码）。
- 结果：322 tests OK（317 当时基线 + 5 演练；2026-09-17 当时基线，非当前结果）。
- 观察项（既有，本票未触碰对应文件，未修复，留待后续票）：
  1. `tests/test_model_client.py:85-86` `addCleanup` LIFO 顺序 → Windows stderr `OSError [WinError 10038]` 噪音（M11 交接已记录；修复 = 交换两行，须触碰该文件的票顺带做）。
  2. `tests/test_host_integration.py` 部分 `tempfile.TemporaryDirectory()` 未显式登记清理 → GC 时 `ResourceWarning`（既有模式，测试全 OK）。
