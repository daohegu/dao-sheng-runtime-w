# Research Gate — Hermes 派生摘要识别与原始消息资格保护（RG-Q1–Q4）

- **日期**：2026-10-09
- **任务**：独立 Research Gate（用户 2026-10-09 下达；ADR 0010 已 Accepted，决定 ㊿ Domain 边界已确立）。本轮只做研究、验证与证据入档，不实施 adapter 修复。
- **闸门归属**：ADR 0010 §Research Gate（规则 9）；完成后进入 adapter 实施票（ADR 0010 Decision 6，等待用户下达）。
- **范围**：当前 Hermes 运行实现（非全版本审计）。**显式不在范围**：`active = 0`、`compacted = 1`、`api_content ≠ content` 资格、`profiles/*/state.db` 数据库布局（ADR 0010 显式排除，本 gate 不扩展、不裁定）。

## 0. 运行版本与源码身份核验（RG-Q1 前置，规则 11）

「当前实现」的判定不依赖版本展示字符串或仓库最新分支：

| 事实 | 值 | 证据 |
|---|---|---|
| Hermes 运行版本 | 0.21.6 | 本机 Hermes 配置目录下的 `gateway_state.json`（占位：`<本机 Hermes 配置目录>/gateway_state.json`） |
| 运行 code_sha | `8bff64d6ed3414a66976bfa8ab72c14b6bca2a6f` | 同上 |
| 源码身份 | hermes-agent 本地源码 git HEAD 与运行 code_sha **精确匹配**（main clean） | 本机 hermes-agent 源码 checkout（占位：`<本机 Hermes 源码目录>`）git 核验 |
| 结论 | 本地源码 = 当前运行实现，源码事实可直接作为运行实现证据 | — |
| 版本漂移记录 | 票① 证据基于 0.21.5 / `69d126be…`；本轮核验时运行版本已为 0.21.6 / `8bff64d6…`。漂移已如实记录；票① 计数在 0.21.6 下复核（见 §3.1），关键结构事实（marked 行计数、前缀形态）与票① 证据一致 | 本轮实测 |

## 1. 证据分级图例（规则 11）

- **[代码事实]** = 直接读取 Hermes 运行实现源码（file:line）。
- **[实测结果]** = 对 live `state.db` 的只读查询（`sqlite3.connect("file:…?mode=ro", uri=True)`；未修改生产数据库、Hermes 文件或 DaoSheng 代码）。
- **[推论]** = 由代码事实 + 实测结果导出的结论，标注导出链。
- **[UNKNOWN]** = 无法验证，显式记录，不猜测填补。

## 2. RG-Q1 — `_compressed_summary` 的真实语义

### 2.1 定义 [代码事实]

- **DB 列**：`messages._compressed_summary INTEGER NOT NULL DEFAULT 0`（`hermes_state_common.py:468`）。
- **来源**：schema migration 14（`hermes_cli/session_schema_history.py:238`；2026-08-25T10:55Z）添加该列，DEFAULT 0。
- **内存形态**：metadata key `_compressed_summary`（`agent/context_compressor.py:302-304` `COMPRESSED_SUMMARY_METADATA_KEY`）。下划线前缀是刻意设计：wire sanitizers 剥离 `_` 前缀 key，使该标记不进入模型 wire 消息。
- **语义**：「该行是 Hermes 自身 context compaction 生成的派生摘要」的布尔标记。它标记的是**行的来源性质**（派生摘要），不是内容状态。

### 2.2 写入路径（stamp 站点，全部 [代码事实]）

摘要进入 messages 表的完整链路 = 内存生成 → stamp metadata key → 持久化时映射为列值：

| 站点 | 形态 | 位置 |
|---|---|---|
| standalone handoff 摘要 | `_assemble_compressed` 生成独立摘要消息并 stamp key | `context_compressor.py:5738-5767`（stamp :5751-5755） |
| merged 摘要 | `_merge_summary_into_tail_row` 把摘要并入 tail 行，merged 行也 stamp | `context_compressor.py:5550-5569`（:5567） |
| user 轮拆分摘要 | `split_user_originated_turn` 拆分超长 user 轮时 stamp | `context_compressor.py:5817-5839`（:5827） |
| micro-compaction 标记 | micro 摘要标记 | `agent/micro_compaction.py:457-464` |

持久化映射：
- `_message_row_params`：`1 if msg.get("_compressed_summary") else 0`（`hermes_state_messages.py:291`）；INSERT 列清单含该列（:34）。
- `append_message(..., _compressed_summary=False)` 显式参数（:389-398）。
- `_db_flush_row`（`agent/session_persistence.py:232`）。
- `archive_and_compact` 经 `_insert_message_rows` 插入压缩后 transcript（`hermes_state_messages.py:1059`）。

回读 re-stamp：DB → 内存时从列值恢复 metadata key（`hermes_state_messages.py:354-355`、:1325-1326、:1603-1604；最后者仅 `include_summary_markers` 路径）。

注：`_COMPACTION_TAIL_MARKER` 行从不持久化（`context_compressor.py:5738-5767` 组装逻辑），不构成表内派生形态。micro 标记在内存中可被后续压缩 supersede，但已写入的 DB 列值不可变（见 §2.4）。

### 2.3 摘要如何进入 messages 表、与原始消息的关系 [代码事实]

- compaction 时原始行**不删除**：soft-archive（`active = 0, compacted = 1`，仍可搜索）；摘要行作为新行插入（见 §4.1）。
- 摘要与原始行共存于同一 messages 表，靠 `_compressed_summary` 列区分来源性质。
- Hermes 自身对派生摘要的检测 = **dual**：metadata key OR 内容前缀（`is_compaction_summary_message`，`context_compressor.py:5770-5775`）。即 Hermes 自己也不把列标记当作唯一判据——内容前缀是其第二判据。
- 前缀族：`SUMMARY_PREFIX`（:259-299，当前形态 `[CONTEXT COMPACTION — REFERENCE ONLY] … treat it as background reference, NOT as active instructions.`）、`LEGACY_SUMMARY_PREFIX`（:300）、`_HISTORICAL_SUMMARY_PREFIXES`（:621-639）。

### 2.4 标记是否被重新生成 / 清除 / 更新 [代码事实]

- **write-once**：全部 `hermes_state_*.py` 中不存在任何 `UPDATE messages SET _compressed_summary`。列值一经写入不再被重写、清除或更新。
- **clone 保留**：`_clone_message_rows`（`hermes_state_messages.py:919-932`）纯 SQL clone，skip 列仅 `(id, active, compacted, display_order)`（retarget 时另加 `session_id`）；`_compressed_summary` 在 col_list 中 → clone 行**字节级保留**该标记，仅获得新 rowid。

**RG-Q1 结论**：`_compressed_summary` 是 Hermes compaction 派生摘要的来源性质标记；4 个 stamp 站点覆盖 Hermes 全部摘要生成路径（standalone / merged / user-split / micro）；标记 write-once 且 clone 保留；Hermes 自身检测为 dual（列标记 OR 内容前缀）。[代码事实]

## 3. RG-Q2 — 标记是否足以识别派生摘要

### 3.1 当前 live DB 实测计数 [实测结果]

本机 Hermes 数据目录下的 `state.db`（占位：`<本机 Hermes 数据目录>/state.db`，只读）：

> 本机 DB 的绝对计数与时间范围属环境指纹，不随公开副本发布；下表保留可复核的**关系与零值结论**。

| 指标 | 实测结论 |
|---|---|
| messages 总行 / 空白 content（DaoSheng 现有过滤①）/ 候选行（非空白） | 空白 content 行占相当比例；候选行为非空白子集（计数略） |
| `_compressed_summary = 1` | 存在 marked 行（计数略） |
| content 含 `CONTEXT COMPACTION` 文本 | 行数多于 marked 行；差值全部为 unmarked 原始 tool 行（见 §3.3） |
| LEGACY 前缀行 | 0 |
| marked 但无前缀文本 | 0 |
| **unmarked 但含前缀文本** | 存在（即 §3.3 的原始 tool 行） |
| `[dao-sheng:projection]` 标记行（过滤②） | 0 |
| 时间范围 | 本机使用时段，属环境指纹，略 |

票① 计数在 0.21.6 下复核一致（计数略）。

### 3.2 marked 行全分类 [实测结果]

- 形态：standalone 为主，另有少量 merged（计数与 rowid 略）。
- role：assistant 与 **user** 两类均存在。user 角色摘要来自 `split_user_originated_turn` 路径——派生摘要不限于 assistant 角色，按 role 过滤不可行。
- 状态：部分行 `active = 0, compacted = 1`（后续 compaction 归档）+ 部分行 `active = 1`（当前活跃）。
- 全部 marked 行 post-migration（本机 DB 最早行晚于 migration 14 的 2026-08-25）。

### 3.3 票① 前缀文本行数与 marked 行数差距已解释 [实测结果]

unmarked 含前缀文本行（计数略） = **role=tool 的原始工具结果行**，其 content 内嵌引用了前缀文本：

- 同一 session 内两组 clone 对：一组 `active = 0`、一组 `active = 1`（见 §4.2）。session 标识与 rowid 属本机 DB 指纹，公开副本略。
- content 即 Hermes 自身查询 messages 表的工具输出（JSON），其中引用了摘要前缀文本；原文属本机消息内容，公开副本不复现。
- 形态 = embedded（前缀出现在行内容中部），不是行首前缀。

**含义**：这 4 行是原始消息（工具调用记录），按契约 2b 必须保留候选资格。

### 3.4 充分性结论（带限定）

- **[实测结果]** 路径 B（内容前缀识别）在当前 DB 实测**误报原始 tool 行**（见 §3.3） → 直接违反契约 2b（不得为排除派生摘要而一概排除原始消息）。
- **[实测结果]** 路径 A（列标记）在当前 DB 覆盖全部实测派生摘要，且**零误报**（marked-without-text = 0；§3.3 的 embedded 原始行均未被标记）。
- **[限定]** 先期实测证据不能证明 100% 覆盖：
  1. 当前 DB 全部行 post-migration（migration 14 之前写入的无标记摘要在本 DB **不可观察**）；
  2. 其他 Hermes 版本 / 其他 DB 的 stamp 覆盖 = UNKNOWN；
  3. Hermes 自身采用 dual 检测（列 OR 前缀），说明 Hermes 代码本身不假设列标记单独完备。

**RG-Q2 结论**：对**当前运行实现（0.21.6 / `8bff64d6`）+ 当前 DB**，列标记对已观察到的全部派生摘要形态充分且零误报；内容前缀实测违反 2b。跨 DB / 跨版本充分性 = UNKNOWN（见 §6）。

## 4. RG-Q3 — 标记 / 内容 / 原始消息的生成与更新关系

### 4.1 compaction 是非破坏性 in-place 操作 [代码事实]

`archive_and_compact`（`hermes_state_messages.py:984-1070`）：

- 原始行 soft-archive：`active = 0, compacted = 1`，**不删除**，仍可搜索（`_ARCHIVE_ACTIVE_SQL` :1052）。
- carried originals 得 rewind flags（`active = 0, compacted = 0`）（:1050）。
- 压缩后 transcript（含摘要行）经 `_insert_message_rows` 作为新行插入（:1059，`_carry_parent_timestamps` :1058 保留父时间戳）。
- tail 原始行经 `_clone_message_rows(tail_ids)` clone（:1061）。

**摘要与原始消息共同保留**；compaction 不删除原始行、不重写原始行 content。

### 4.2 rowid 不稳定 [代码事实 + 实测结果]

- **[代码事实]** `resolve_active_row_id`（`hermes_state_messages.py:1151+`）docstring 明确：in-place compaction 会把行 re-sequence 进新 rowid（"`_clone_message_rows` copies role, content and …"），引用 durable row id 的消费者须按 content 重新解析——Hermes 自身承认 rowid 不稳定。
- **[实测结果]** 当前 DB 存在大量组（数百组）`(session_id, content, timestamp)` 完全相同但 rowid 不同的行（clone 对），重复倍数从 2× 到数十×不等（组数与示例 rowid 属本机 DB 指纹，略）。
- **[实测结果]** 当前 DB 中没有任何 exact-dup 组含 marked 行——marked 行在本 DB 尚无 clone 实例（经验缺口，非矛盾；clone 保留标记由 §2.4 代码事实闭合）。
- **[推论]** DaoSheng 已导入键 `v2:<64hex>:<session_id>:<rowid>`（`dao_sheng/hermes_host.py`）含 rowid → clone 产生新 rowid → 同一内容以新键成为**重复候选**。当前暴露 = 0（latent，host 集成未装配）。此为证据与后果记录，不构成决策；幂等 / content-hash 缓解属实施票。

### 4.3 标记不可重写；内容可被重写 [代码事实]

- 标记：write-once（§2.4），无任何维护操作重写该列。
- 内容重写路径存在：
  - `set_user_message_content`（:1128-1137）：active user 行 in-place content 重写（@-file 展开等），rowid 保留，不触及 `_compressed_summary`。
  - `purge_stale_tool_call_markers`（:1959-1991）：维护操作，`UPDATE messages SET content = ''` 仅针对 bare tool-call marker 行（#78148），执行前 `VACUUM INTO` 备份。
- **[推论]** 内容重写路径不针对摘要行设计，且即使触及也不改标记列——标记与内容相互独立。

### 4.4 删除路径存在，但均为 session 级 [代码事实]

| 路径 | 位置 | 性质 |
|---|---|---|
| `prune_sessions` | `hermes_state_maintenance.py:322-353`（默认 90 天；`DELETE FROM messages WHERE session_id IN (…)` :345；自动维护跳过 guarded rows） | 维护删除，session 粒度 |
| `clear_messages` | `hermes_state_messages.py:1952-1957` | 显式清空 session 全部消息 |
| replace 流 DELETE 分支 | `hermes_state_messages.py:820-859`（:855） | rewind/edit/regenerate 须用 `archive_dropped=True` soft-archive；DELETE 会 evict FTS 无可恢复（#82756） |
| session 删除 / orphan repair | `hermes_state_sessions.py:224/1742/1852/1893`、`hermes_state_profile_repair.py:251` | session 级 / 修复级 |
| `archive_stale_sessions` | `hermes_state_maintenance.py:295-320` | 仅 session flag，不删 messages |

**[推论]** 不存在「针对单条原始消息或摘要行的常规删除」；删除只随 session 消亡发生。

### 4.5 FTS 维护不触碰 messages 行 / rowid [代码事实]

`rebuild_fts`（`hermes_state_search.py:1295-1339`）：FTS5 'rebuild' 命令只从 content 行重建索引 b-tree，**不修改 messages 表行或 rowid**；`optimize_fts`（:1280-1293）同理；`fts_rebuild_admission` 跨进程锁 fail-closed。FTS triggers（`hermes_state_common.py:1001-1036`）只同步索引。

**RG-Q3 结论**：compaction 非破坏（原始共同保留）；标记 write-once 且 clone 保留；内容可被重写但不针对摘要行、不改标记；删除仅 session 级；FTS 维护不动 messages 行/rowid；**rowid 不稳定**（代码事实 + 实测大量 clone 组）→ DaoSheng v2 key 含 rowid 的后果已记录。[代码事实 + 实测结果 + 推论]

## 5. RG-Q4 — 证据不足处的最小可复现验证计划

全部计划为**只读**；不得修改生产数据库、Hermes 文件或 DaoSheng 代码。

| 编号 | 剩余不足 | 最小验证 | 当前可执行性 |
|---|---|---|---|
| V1 | pre-migration（< 2026-08-25T10:55Z）无标记摘要缺口 | 取含更早 timestamp 行的 Hermes DB（备份 / 其他机器），只读查询：`SELECT role, count(*) FROM messages WHERE _compressed_summary = 0 AND (content LIKE '[CONTEXT COMPACTION%' OR content LIKE '<legacy 前缀>%' OR content LIKE '<historical 前缀>%') GROUP BY role` | **当前不可得** → 保持 UNKNOWN；若用户提供此类 DB 即可闭合 |
| V2 | 跨版本 stamp 覆盖 | 程序性核验：读 `gateway_state.json` code_sha → 将 hermes-agent 源码钉到该精确 commit → 审计 stamp 站点（§2.2 四类）+ schema migration 表；每次部署版本变化时重跑 | 已对 0.21.5（`69d126be`）与 0.21.6（`8bff64d6`）完成；作为长期程序保持 |
| V3 | marked 行 clone 实例 | 只读查询模式：exact-dup `(session_id, content, timestamp)` 组内含 marked 行（当前 DB = 0）；出现实例时核验其 `_compressed_summary` 是否保留 | 可选；代码事实（§2.4）已闭合机制 |
| V4 | prune / repair 是否曾对当前 DB 运行（删除无痕迹，不可观察） | 从 DB 本身不可观察；缓解属实施票设计面（content-hash 幂等使删除-重现不产生错误状态） | 不属 research 可闭合项 → 记录为 UNKNOWN + 实施票输入 |

## 6. UNKNOWN（规则 11，不填补）

1. pre-migration 无标记派生摘要是否存在于任何 Hermes DB = **UNKNOWN**（当前 DB 全 post-migration，不可观察）。
2. 其他 Hermes 版本是否对所有派生摘要写入站点 stamp 该标记 = **UNKNOWN**（仅 0.21.5 / 0.21.6 源码已审计）。
3. prune / repair 删除路径是否曾对当前 DB 运行 = **UNKNOWN**（删除无痕迹）。
4. marked 行在其他 DB 是否出现 clone 实例 = **经验缺口**（clone 保留标记已由代码事实闭合；当前 DB 无实例）。
5. compaction 行为本身是否构成可记录事件 = **UNKNOWN**（ADR 0002 决定 6，本 gate 不裁定）。
6. Host 正式定义 = **UNKNOWN**（ADR 0002 决定 6 保持）。

## 7. 检测机制建议（证据支持陈述，不选定、不实施）

ADR 0010 Decision 4 路径表的研究证据判定：

- **路径 A（列标记 `_compressed_summary` 过滤）**：对当前运行实现证据支持最强——覆盖全部实测派生摘要、零误报；标记 write-once、clone 保留、不进入 wire。限定：结论仅对「当前运行实现 + 当前 DB」成立；pre-migration 缺口与跨版本覆盖 = UNKNOWN（§6.1 / §6.2）。
- **路径 B（内容前缀识别）**：实测误报原始 tool 行（见 §3.3） → 违反契约 2b → **证据不支持其作为主检测机制**。Hermes 自身 dual 检测中前缀是「列缺失时的补充」方向，与 DaoSheng 供数场景（列存在且 write-once）方向相反。
- **路径 C**：无新证据，不展开。
- **实施票输入（证据导出，非决策）**：rowid 不稳定（§4.2）+ v2 key 含 rowid → 实施票须处理 clone 重复候选（content-hash 幂等或等效机制）；此属实施票设计面，本 gate 不选定。

**最终机制选定 = 用户验收裁定 + adapter 实施票（ADR 0010 Decision 4 / 6）。本 gate 不选定、不实施。**

## 8. 规则判定与一致性

- **规则 9（Research Gate）**：满足——真实技术未知（RG-Q1–Q4）已由研究闭合至证据边界；结果写入 `docs/research/`。
- **规则 11**：满足——§6 全部 UNKNOWN 显式记录，不填补。
- **规则 1**：满足——本 gate 只产出 host 机制事实，不触及、不反向定义 Domain（决定 ㊿ 未修改）。
- **规则 7**：满足——冻结历史零触碰；票① / 票② / ADR 0010 / 决定 ㊿ 未回溯修改。
- **规则 13**：内部执行状态台账（`RECONSTRUCTION.md`）不随公开副本发布；本 gate 的入档记录 = 本文件（`docs/research/`）。
- **Hermes Adapter evolution 一致性**：Research Gate 完成；宿主名仍限于 host adapter 层；未出现新宿主 adapter；seam 仍 hypothetical。
- **只读纪律**：live DB 仅 `mode=ro` URI 访问；Hermes 文件零修改；DaoSheng 代码零修改；未输出原始聊天正文。公开副本版本进一步将本机 DB 计数、rowid、session 标识与 content 摘录抽象为定性结论（原始指纹不随公开副本发布，见 §3.1 注记）。
- **不在范围保持**：`active = 0` / `compacted = 1` / `api_content ≠ content` / `profiles/*/state.db` 未调查、未裁定。

## 9. 证据索引

- Hermes 源码（= 运行实现，§0）：`agent/context_compressor.py`、`agent/micro_compaction.py`、`agent/session_persistence.py`、`hermes_state_messages.py`、`hermes_state_common.py`、`hermes_state_maintenance.py`、`hermes_state_search.py`、`hermes_state_sessions.py`、`hermes_state_profile_repair.py`、`hermes_cli/session_schema_history.py`。
- Live DB：本机 Hermes 数据目录下的 `state.db`（占位：`<本机 Hermes 数据目录>/state.db`，只读查询）。
- 继承证据：票①（Hermes 0.21.5 影响评估）与票②（experience 派生摘要 Domain 边界）的 handoff 过程记录（不在公开副本范围内）；ADR 0010。
- DaoSheng 只读核验：`dao_sheng/hermes_host.py`（v2 key 形态）、`dao_sheng/host_carrier.py`（读取面形态）。
