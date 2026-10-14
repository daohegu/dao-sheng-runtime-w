# Research — Memory 持久化与 Provider 形态（STEP 11）

> **STEP 11（Research Gate）产出（2026-09-13）**。本文件是 V1 当前唯一确认的外部技术 Research Evidence（CLAUDE.md 规则 9；锚点：`docs/domain/bounded-contexts.md` §4"V1 的 Provider 选择属外部技术选择，须 Research Evidence"）。
>
> 信息标签按 INV-17 四类分离：§3.1 = 本 Step 本地复现的 Validated Evidence；§3.2 = Historical Experience / Implementation（最低权威，仅作形态参考）；§3.3 = 证据约束（UNKNOWN 诚实记录，规则 11）。
>
> **本 Research 只选实现基座与形态，不修改已定 Domain**（三维语义层 Ontology、INV-1…INV-17、CINV-1…CINV-5 均不变）。

---

## §0 Gate Survey — 候选主题处置

STEP 11 须对候选主题逐一裁定（research / defer / out-of-scope + 理由）：

| 候选主题 | 处置 | 理由 |
|---|---|---|
| **Memory 持久化与 Provider 形态** | **Research**（本文档 + ADR 0001） | 唯一确认的真正外部技术未知（`bounded-contexts.md` §4 锚点；V1 尚无选定基座，且 Provider 可替换性是 INV-3 的硬要求） |
| Long-running Runtime / Recovery | **Defer to STEP 12** | 不是外部技术选择，是架构结构决定（状态归属、重启语义、谁持有 persistent state）；其答案依赖本文档的持久化基座（作为输入），由 STEP 12 `container-model.md` / `runtime-boundaries.md` 回答 |
| Model 部署（U-5：V0 默认模型部署关系） | **Out-of-scope（保持 UNKNOWN）** | U-5 是 V0 历史部署证据的歧义（规则 11，无材料不猜测）；Model 是可替换手段（INV-1），部署属部署层（L4 运营策略，当前不预设）；V1 设计决定不依赖其裁决。触发：STEP 13/14 实际需要模型部署方案时 |
| MCP | **Out-of-scope** | MCP 是标准外部协议（有 official spec，无设计未知）；其 V1 定位已由 Domain 确定（外部手段层，B1-E3 / B1-E13："这些都不是 DaoSheng 本身"）；当前设计中不存在真正的技术未知 |
| Worker Protocol | **Out-of-scope（前提未成立）** | Worker 无领域定义（UNKNOWN，引入须 ADR——"没有定义" ≠ "定义为某种东西"，STEP 09 Q6）；无法为一个未定义概念研究协议。触发：Worker 被定义之后（如有） |

---

## §1 Problem

V1 的 Memory Provider 必须持久化 **DaoSheng Memory Ontology**（三维语义层 `memory_origin × memory_status × memory_confidence` + 修正引用键，Q2 用户追认）。两个待决子问题：

1. **持久化基座**：默认采用哪种存储技术？
2. **Provider 形态**：embedded（单文件、进程内）还是独立服务（server，Hindsight 历史形态）？

约束（来自 Domain / Constitution，**本 Research 不得以"发现更酷技术"为由修改**）：

- INV-3 / 规则 5：Memory Provider 不得定义 DaoSheng Memory Ontology——Ontology 拥有者 = 个体（核心），Provider 拥有者 = 部署层，Provider 可替换（须存在 seam，`bounded-contexts.md` §4）
- Q2 追认：三维语义层 + 修正引用键 = Ontology 基础；消化 / 遗忘机制 UNKNOWN（不预设）
- INV-8：修正认识不重写经历记录（`correct_memory` 形态 = 追加 correction 记录，历史一致性证据）
- V1 是否迁移 V0 既有数据 = UNKNOWN（用户决策，R-10）——**本 Research 不预设**

## §2 Options

| 选项 | 内容 |
|---|---|
| **A. 单文件嵌入式数据库（SQLite，WAL）** | 进程内连接，单文件 + WAL side files；三维语义层为结构化列；recall = 结构化过滤 + 关键词 / 子串（FTS5） |
| **B. 独立记忆服务器（Hindsight 历史形态）** | 独立进程 + 本地 API（retain/recall）；Provider = 服务 |
| **C. 向量 embedding 检索** | embedding 模型 + 向量索引（sqlite-vec 或外部 vector DB）；语义召回 |
| **D. 纯文件 / JSONL append-only 日志** | 无数据库，纯文本日志 |

组合关系：A 是基座；C 可在 A 之上作为召回通道增补；B 是形态选择（与 A 不互斥，但默认形态取其一）；D 独立。

## §3 Evidence

### 3.1 本地验证（本 Step 实测，可复现，Validated Evidence）

环境：Windows 11 Pro / Python 3.12.10 / SQLite 3.49.1（`COMPILER=msvc-1943`，`MUTEX_W32`）。全部命令可在本仓库外以 `python` + 标准库 `sqlite3` 复现。

| # | 测试 | 结果 |
|---|---|---|
| E1 | FTS5 / JSON1 可用性 | 均内置可用（`ENABLE_FTS5`；JSON1 enabled） |
| E2 | WAL 模式 | `PRAGMA journal_mode=WAL` 成功；产生 side files `.db-wal` / `.db-shm` |
| E3 | WAL 读写并发 | 写连接持有 open write transaction 时：读连接可读到已提交数据（返回事务前 count）；第二写连接被阻塞（`busy_timeout` 耗尽后 `database is locked`）；第一写 rollback 后第二写成功。**语义 = 单 writer + 并发 reader** |
| E4 | FTS5 `unicode61` 对中文 | 中文连续文本被当作**单个 token**：全文 MATCH = 1；子串 "管线" / "记忆" / "提取的过程" MATCH = 0；前缀 "记忆\*" = 1（整 token 前缀）。**unicode61 不适用于中文子串召回** |
| E5 | FTS5 `trigram` 对中文 | **≥3 字符**子串查询命中（"到提取" = 1、"记忆管" = 1）；2 字符查询 = 0（trigram 最小查询长度 3）。**trigram 是 CJK 关键词 / 子串召回的可行路径，最小查询长度 3** |
| E6 | compile_options 关键值 | `MAX_EXPR_DEPTH=1000`（对应 V0 recall ≤32 LIKE 项上限，避免 expression depth）；`MAX_VARIABLE_NUMBER=32766`；`MAX_LENGTH` = 1GB；`DEFAULT_WAL_AUTOCHECKPOINT=1000` 页；`MAX_ATTACHED=10`；`ENABLE_FTS5` / `ENABLE_RTREE` / `ENABLE_MATH_FUNCTIONS` |
| E7 | `vec0`（sqlite-vec） | **未随标准 SQLite 附带**（`load_extension("vec0")` 失败：找不到模块）→ 向量检索 = 引入额外外部依赖，本身即新的外部技术选择（届时须独立 Research） |

### 3.2 历史证据（Historical Experience / Implementation，最低权威，仅作形态参考）

- **V0 `SQLiteMemory`**（`dao-sheng-v0.1.1/dao_sheng/memory/sqlite.py`）：单 SQLite 文件、单表 `memories`；三维语义层存于 `metadata_json`；recall = 有界关键词 LIKE（≤32 terms）+ Python 端分层排序（origin / status / confidence）+ 显式 reference 解析优先；`correct_memory` = 追加 `kind="correction"` 记录，原记忆内容与身份不变（与 INV-8 形态一致）。
- **V0 `MemoryStore` Protocol**（`memory/protocol.py`，5 方法）滞后于实现（11 方法）——**R-05**：interface 未表达真实契约，调用方必须知道 implementation。V1 的 Memory **Interface 方法集与深度**由 STEP 12（`component-model.md`）决定，**不属于本 Research 范围**。
- **Hindsight**（B2-E12）：本地长期记忆服务器（retain/recall；部署手册 v1.0，2026-07-25）= Provider **历史实例**，**不是 V1 承诺**（`bounded-contexts.md` §4；规则 5）。

### 3.3 证据约束（UNKNOWN 诚实记录，规则 11）

- 本环境 **WebSearch 无结果、WebFetch 被网络 / 安全分类器阻断**（sqlite.org 与 github.com 均不可达）→ **官方 spec / docs 未能引用**。
- 因此本 Research 的证据等级 = "本地可复现行为"，不是"官方文档引用"。该约束是 Confidence 降级的主因，并进入 §7 Re-evaluation Trigger。

## §4 Trade-offs

| 选项 | 优势 | 代价 |
|---|---|---|
| A 嵌入式 SQLite | 零外部进程 / 零额外依赖（FTS5 / JSON1 内置，E1）；单文件 = 备份 / 迁移 / 审计简单；WAL 并发读单写（E3）匹配 V1 单个体单主机场景；历史形态有 V0 实现经验（locality：修改集中在一处） | 单进程语境（多 host 共享须改形态）；CJK 召回为关键词级（trigram ≥3 字符，E5），无语义检索；写入串行（单 writer） |
| B 独立服务器 | 进程隔离、多客户端共享、可独立扩缩 | 引入进程 / API / 生命周期管理（新增 host 集成类关注点，与 ADR ① 交叠）；V1 当前单个体场景收益未证实（YAGNI）；Hindsight 形态是历史实例、非承诺 |
| C 向量检索 | 语义召回（相似含义而非仅关键词） | E7：须引入外部依赖（sqlite-vec 或 vector DB）+ embedding 模型（Model = 可替换手段，须另行 Research）；当前记忆规模（幼体阶段）收益未证实（YAGNI；顺势 / 不妄动） |
| D 纯文件日志 | 最简 | 无结构化查询（三维过滤须全量扫描）；无并发 / 完整性保证；与 Q2 三维语义层的查询需求矛盾 |

## §5 Decision

1. **V1 默认 Memory 持久化基座 = 单文件嵌入式 SQLite（WAL 模式）**（选项 A）。
2. **Provider 形态 = embedded**（进程内 adapter，单文件 + side files）。**独立 server 形态（选项 B）不作默认**——出现真实的多进程 / 多 host 共享需求时再评估（§7）。
3. **Recall 起点 = 结构化过滤（三维语义层列）+ FTS5 trigram 关键词 / 子串**（trigram 最小查询长度 3，E5；2 字符查询走 LIKE 或结构化过滤）。排序可参考 V0 分层思想（Implementation 参考，非权威）。**向量检索（选项 C）延期**——将来引入须独立 Research（外部依赖 + embedding model，E7）。
4. **Ontology 不变**：三维语义层 + 修正引用键 = DaoSheng Memory Ontology，拥有者 = 个体；存储 schema = Provider 实现细节。Ontology 必须能完整映射到任一 Provider（这是 seam 的语义要求）。Interface 方法集与深度归 STEP 12（回答 R-05）。
5. **V1 是否迁移 V0 数据：此处不决定**（UNKNOWN，用户决策，R-10）。
6. 正式决定记录于 **ADR 0001**（`docs/adr/0001-memory-persistence.md`）。

## §6 Confidence

**MEDIUM。**

- 高置信部分：E1–E7 全部本机可复现；决定不依赖任何不可验证的断言。
- 降级原因：官方来源（sqlite.org spec / docs、sqlite-vec GitHub）因网络约束未能引用（§3.3）。
- 决定本身保守（取最成熟最简形态、fancy 选项全部延期）：即使官方行为细节与本地实测有出入，决定的方向不翻转。

## §7 Re-evaluation Trigger

任一触发 → 重开本 Research（更新本文档 + ADR 0001 复审）：

1. **网络恢复**：补验官方证据（WAL / FTS5 trigram / compile limits）——升级 Confidence 或修正细节
2. **中文 2 字符查询或语义召回需求**（trigram ≥3 字符限制或关键词级召回在使用中证实不够）：重评估 CJK 分词（新外部依赖，须独立 Research）/ 向量检索（sqlite-vec + embedding model，须独立 Research）
3. **多进程 / 多 host 访问同一份记忆**（如多个 Worker / host 实例共享个体记忆）：重评估 server 形态（选项 B）
4. **记忆规模**（如 > 10^6 条，或 recall 延迟不满足需要）：重评估索引 / 存储形态
5. **需要第二个真实 Provider 实现**（one adapter = hypothetical seam，two = real：Provider seam 当前为单 adapter 状态——seam 保留、不过度设计）

## §8 与后续 Step 的关系

- **STEP 12 输入**：持久化基座已定（SQLite WAL）；Provider seam 存在且语义已定（§5.4）。Memory Interface 方法集与深度（R-05）归 `component-model.md`；memories 文件的 data ownership（谁写、谁不得写）归 `data-ownership.md`；重启后什么持久归 `runtime-boundaries.md`。
- **Domain / Constitution 零改动**：本 Research 只选实现基座与形态。
