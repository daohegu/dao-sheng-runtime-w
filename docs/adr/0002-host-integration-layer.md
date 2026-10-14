# ADR 0002 — host 集成层建立

- **Status**: accepted（2026-09-13，STEP 12）
- **约束来源**: 规则 3（Hermes 不得定义 DaoSheng）；`docs/audit/move.md` M-01…M-05（统一观察：**V0 缺的不是代码改写，而是一个 host 集成层的存在**）；R-11 / R-12；`docs/domain/bounded-contexts.md` §3（Host 有界上下文 = 核心与外部手段 / 历史系统之间的集成层，正式定义 UNKNOWN）/ §5（ADR ①）；材料 3 07/11（Hermes 在重构路线中定位为 "Host"，`LATER_INTERPRETATION`）；K-11（Identity 载体无 host 字段）

## Context

V0 中 host 集成层**不存在**：host 知识（Hermes 内部 messages 表 schema、`profiles/<name>/state.db` 路径结构、Desktop subprocess 调用、host 身份宣称文本）散在 `growth/`（`hermes_import.py` 842 行、`sync_hermes()`）、`life/`（`bridge.py`、`_state_db_path`）、`app.py`（身份宣称）——Core 的 Interface 知道 "Hermes" 存在（H-2），Core 生成的投影文本宣称 "你正在作为道生的 Primary Agent Hermes"（M-04：H-6/H-7，规则 3 最直接的措辞级证据）。材料 3 07/11 将 Hermes 定位为 "Host"（正式定义 UNKNOWN，落地须 ADR = 本 ADR）。

## Decision

1. **建立 host 集成层（进程内 adapter，位于 DaoSheng Runtime 容器内，composition root 装配）**：唯一允许知道 host 名字、host 存储路径、host 进程调用方式的层（M-01…M-05 收敛落点）。它不是独立容器——host 本身（Hermes Desktop）是独立容器，"与它的集成"是 Core 侧 adapter 代码（`container-model.md` §4）。
2. **Interface = 中性概念**（回合 / 会话 / 经验回流 / 上下文投影），不含 host 名；经验回流 Interface = "导入会话 → [Experience 候选]"，候选的 origin 标注（中性值）在本层完成（M-01 / R-10 联动）。
3. **seam 状态 = hypothetical**（单 adapter，如实记录）；第二个 host 实现出现时升格 real seam，Interface（中性概念）即其契约——Interface 不随 adapter 变化。
4. **"DaoSheng 与 host 的关系"表述只出现在 composition root 声明**（启动配置说明），不进入 Core 生成的任何文本——尤其不进入会被回流为 Experience 的投影文本（R-12：身份宣称一旦进投影即回流，污染 Identity 证据链）。
5. **V0 host 知识全部收敛本层**：`hermes_import`（M-01）/ `bridge`（M-02）/ `sync_hermes()` + 路径结构 + `source` 前缀（M-03；`sync_hermes()` 从 Growth 核 Interface **移除**而非改名）/ 身份宣称（M-04）；症状级清洗函数（D-05）随 R-12 根因修复删除，不随迁。
6. **Host 正式定义保持 UNKNOWN**：本 ADR 决定的是"层的建立"这一结构事实（位置、职责、Interface 形态、seam 状态、声明位），不是 Host 的完整 Domain 定义；Host 定义若进入 Domain 文档，须另行裁定（规则 8）。

## Consequences

- **正面**：规则 3 获得结构前提——"V1 实现中任何知道 'Hermes' 名字、具体模型名、SQLite 细节的非 adapter 层代码 = 漂移"从此可检查（`system-context.md` §3）；R-12（投影不回流）与 M-01…M-05 有落地层；host 重启 / 消失不影响个体状态（`runtime-boundaries.md` §2）。
- **代价 / 限制**：单 adapter hypothetical seam 保留不过度设计；若 V1 的 host 不是（或不止）Hermes，schema 知识正是 adapter 该持有的东西——切换代价集中一处（locality）。
- **未决（显式保留）**：Host 正式定义、"DaoSheng 与 host 的关系"的 Domain 级表述 = UNKNOWN（材料 3 07/11 仅为 `LATER_INTERPRETATION` 定位，不升格为 ORIGIN）。
