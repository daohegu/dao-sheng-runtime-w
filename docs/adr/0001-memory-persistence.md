# ADR 0001 — Memory 持久化基座与 Provider 形态

- **Status**: accepted（2026-09-13，STEP 11）
- **Research Evidence**: `docs/research/memory-architecture.md`（规则 9）
- **约束来源**: INV-3 / 规则 5（Provider 不得定义 Ontology）；Q2 追认（三维语义层 + 修正引用键 = DaoSheng Memory Ontology）；`bounded-contexts.md` §4（Ontology Owner = 个体，Provider Owner = 部署层）

## Context

V1 的 Memory Provider 必须持久化 DaoSheng Memory Ontology，且 Provider 可替换（INV-3）。当前设计中这是唯一确认的真正外部技术未知（`bounded-contexts.md` §4 锚点）。候选：A 单文件嵌入式 SQLite（WAL）/ B 独立记忆服务器（Hindsight 历史形态）/ C 向量 embedding 检索 / D 纯文件日志。历史形态（最低权威）：V0 = 单 SQLite 文件；Hindsight = 本地 server（历史实例，非 V1 承诺）。本地实测（可复现）：SQLite 3.49.1 内置 FTS5 / JSON1；WAL = 单 writer + 并发 reader；FTS5 trigram 支持 ≥3 字符 CJK 子串查询（unicode61 不支持中文子串）；sqlite-vec 未附带（向量检索 = 新外部依赖）。官方文档因网络约束未能引用（Confidence 降级，见 Research §6/§7）。

## Decision

1. **V1 默认 Memory 持久化基座 = 单文件嵌入式 SQLite（WAL 模式）**。
2. **Provider 形态 = embedded**（进程内 adapter）；独立 server 形态不作默认，多进程 / 多 host 共享需求出现时再评估。
3. **Recall 起点 = 结构化过滤（三维语义层）+ FTS5 trigram 关键词 / 子串**（最小查询长度 3）；向量检索延期，引入时须独立 Research。
4. **Ontology 与存储分离**：三维语义层 + 修正引用键属于个体（Ontology），存储 schema 属于 Provider（实现细节）；Ontology 必须能完整映射到任一 Provider。Memory Interface 方法集与深度（回答 R-05）归 STEP 12 `component-model.md`。

## Consequences

- **正面**：零外部进程 / 零额外依赖；单文件备份 / 迁移 / 审计简单；WAL 并发语义匹配单个体场景；与 V0 实现经验连续（locality）。
- **代价 / 限制**：CJK 召回为关键词级（trigram ≥3 字符）；写入串行（单 writer）；单进程语境。
- **未决（显式保留）**：V1 是否迁移 V0 数据 = UNKNOWN（用户决策，R-10，不在本 ADR 预设）；消化 / 遗忘机制 = UNKNOWN（Q2 / L4 不预设）。
- **Re-evaluation Trigger**（任一触发须复审本 ADR）：网络恢复补官方证据 / 中文 2 字符或语义召回需求 / 多进程多 host 共享 / 记忆规模 > 10^6 或延迟不满足 / 出现第二个真实 Provider 实现。详见 `docs/research/memory-architecture.md` §7。
