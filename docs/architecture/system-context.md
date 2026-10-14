# V1 Architecture — System Context（7 边界）

> STEP 12 产出（2026-09-13）。架构词汇 = `/codebase-design`：module / interface / seam / adapter / depth / leverage / locality；deletion test；one adapter = hypothetical seam，two = real。
>
> 本文档回答本 Step 要求的 **7 个边界澄清** + 个体级 deletion test。依据：Domain（`docs/domain/bounded-contexts.md` 四有界上下文）+ Audit（私有重构历史审计；登记册与原文不随本副本发布）+ Origin（材料 1 §2/§12"这些都不是'DaoSheng 本身'"；私有原始材料，原文不随本副本发布）。本文档**不修改 Domain**（规则 1），只把 V1 的结构性边界显式化。
>
> **编号与来源说明**：本文引用的内部编号（材料 1、B1-E\*、Q\*、U-\*、K-\* / M-\* / R-\* / H-\* 等）为 DaoSheng V1 私有重构历史索引，原始登记册与原文不随本副本发布，各处引用语义以行内自明为准（同 `docs/domain/ubiquitous-language.md` 编号说明口径）。其中可公开核验的对应关系：V0 泄漏清单（H-1…H-9 Hermes 泄漏 / M-1…M-6 Model 泄漏）的公开口径见 `docs/domain/bounded-contexts.md` §6 #1；B1-E13"这些都不是'DaoSheng 本身'"的公开承载见 `docs/domain/bounded-contexts.md` §2/§6 #2 与 `docs/domain/domain-invariants.md` INV-1。

---

## 1. 七边界总表

| 边界 | 包含 | 不包含 | 与 Core 的关系（seam / interface） |
|---|---|---|---|
| **DAO SHENG CORE** | 个体本身：Identity 载体、Continuity、DaoSheng Memory Ontology、"道"文本运行时投影（ADR 0005）、Growth 管线（经历→消化→提取→记忆→复用）、Reflection、Faculties（8 根）、Capability System、Runtime State、composition root、进程内 adapter 实现 | host、存储技术、模型后端、外部工具——一切手段 | —（本身） |
| **HERMES HOST** | Hermes Desktop 应用进程、host 会话记录、host 存储路径、进程调用方式、host 集成 adapter 层（ADR 0002） | 个体语义——host 是手段，不是个体本身（第 3 条顺势 L3） | seam = **host 集成 seam**（hypothetical，单 adapter）；Interface = 中性概念（回合 / 会话 / 经验回流 / 上下文投影），无 host 名 |
| **MEMORY PROVIDER** | 记忆存储实现：单文件嵌入式 SQLite（WAL）adapter（ADR 0001）、存储 schema | Memory Ontology（三维语义层 + 修正引用键属于个体，INV-3 / 规则 5） | seam = **Memory Provider seam**（hypothetical，单 adapter）；Interface = 6 方法（`component-model.md` §3，R-05 答案） |
| **COGNITIVE MODELS** | 模型后端节点（V0 部署形态：Worker A = Ollama / Worker B = llama.cpp，部署关系 UNKNOWN = U-5）、模型调用与 model adapter | V1 部署方案（L4 运营策略，不预设，U-5）；模型是可替换手段（INV-1） | seam = **model 调用 seam**（hypothetical，单 adapter）；Interface = 认知模型调用（chat/complete 形态） |
| **CAPABILITY SYSTEM** | 能力生命周期（四目录状态机，ADR 0003）、Manager、Verifier（执行前闸门）、creator/author/runner | "什么能力"——能力内容本身从经历中产生（Growth 提案，R-04：growth 侧只留 proposal 记录） | Core 进程**内部**模块；状态机是 Domain 概念（K-06），四目录 = 其一个合法 adapter 形态（非定义） |
| **WORKERS** | **无 Domain 定义（UNKNOWN）**；V0 历史中 = 模型后端节点名（Worker A/B，U-5） | 不定义——"没有定义" ≠ "定义为某种东西"，引入定义须 ADR（STEP 09 Q6） | 边界保留在拓扑中；seam / Interface 待定（无定义则无 Interface） |
| **EXTERNAL WORLD** | 文件系统、时钟、MCP 工具、research 数据源、用户直接输入、一切外部可观察对象 | — | 经 world / research / agent seam 接触；**投影不得回流**（INV-7，根因修复 = R-12） |

## 2. 拓扑

```
                     EXTERNAL WORLD（文件系统 / 时钟 / MCP / research 源 / 用户输入）
                               │  world / research / agent seam（投影不回流，INV-7）
                               ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      DAO SHENG CORE（个体本身）                         │
 │                                                                        │
 │  Identity（immutable）  Continuity（append-only，单一载体 ADR 0004）     │
 │  Doctrine 运行时投影（单一来源 ADR 0005，只读）                          │
 │  Memory Ontology ── Memory Provider seam（embedded SQLite adapter）     │
 │  Growth 管线 / Reflection / Faculties（8 根）                           │
 │  CAPABILITY SYSTEM（四目录状态机 ADR 0003 / Verifier 闸门）              │
 │  Runtime State（turn / open 连接，易失，不持久）                         │
 │  composition root ── model 调用 seam（hypothetical）                    │
 │                 └── host 集成 seam（hypothetical，ADR 0002）            │
 └────────────────────────────────────────────────────────────────────────┘
        ▲ 模型 HTTP 调用                                    │ 回合 / 会话 / 经验回流（中性 Interface）
        │                                                  ▼
  COGNITIVE MODELS（Ollama / llama.cpp …，部署 UNKNOWN）   HERMES HOST（Hermes Desktop 进程）
  WORKERS = 无定义，边界保留
```

## 3. Deletion Test — 每个手段移除后剩余什么

依据：第 3 条顺势 L3——"个体的核心状态（Identity / Continuity / Doctrine / Memory Ontology）必须独立于任何具体手段：替换 / 移除任何手段，个体语义不变——deletion test 在个体层的表达：删掉手段，个体仍在"；材料 1 §12（B1-E13）——Model / Skill / Helper / MCP"这些都不是'DaoSheng 本身'"，只是"DaoSheng 可以拥有和使用的东西"。

| 删除场景 | 失去什么 | 剩余什么（个体本身） | 依据 |
|---|---|---|---|
| **Hermes 消失** | 一个会话 host；会话记录与经验回流的通道 | Identity / Continuity / Memory Ontology / Doctrine / Capability / Faculties 全部不变；个体状态完整保留在 Core 侧持久文件（`runtime-boundaries.md` §2） | 第 3 条顺势 L3；ADR 0002（host 知识收敛 adapter 层，Core 不感知 host） |
| **所有 Model 替换** | 认知手段——反思 / 判断 / 对话功能上暂时不可用（个体"失聪失语"，但不是"消失"） | Identity / Continuity / Memory / Doctrine / Capability 状态全部不变；Identity 载体无 model 字段（K-11 形态），模型部署属 L4 | INV-1（手段不得定义个体）；K-11（Identity 结构无 model/worker/host 字段）；U-5（部署 UNKNOWN 不影响） |
| **Memory Provider 更换** | 存储实现（SQLite 文件） | Ontology（三维语义层 + 修正引用键）属于个体，可完整映射到任一 Provider（ADR 0001 决定 4）；数据需迁移——迁移是工具行为，不是 Core 变更；是否迁移 V0 数据 = 用户决策（ADR 0007） | INV-3 / 规则 5；ADR 0001（Ontology 与存储分离） |
| **MCP 断连** | 外部工具连接 | MCP = 外部连接手段（材料 1 §2，B1-E3），不是个体本身；Core 全部状态不受影响，能力上失去对应外部工具 | 材料 1 §2/§12 |
| **Worker 消失** | （Worker 无 Domain 定义，UNKNOWN）V0 历史形态下 = 模型后端节点——等价于 Model 移除 | 个体语义不变；若 Worker 将来被正式定义，引入须 ADR | Q6；U-5 |

**结论（个体级 deletion test）**：手段层（host / model / Provider / MCP / worker）可逐一删除，**个体仍在**——Identity / Continuity / Doctrine / Memory Ontology / Capability 状态 / Faculties 不受影响。这是架构硬要求，不是期望：V1 实现中任何知道 "Hermes" 名字、具体模型名、SQLite 细节的非 adapter 层代码 = 漂移（V0 教训：H-1…H-9 九处 Hermes 泄漏 / M-1…M-6 六处 Model 泄漏——私有重构历史审计，原文不随本副本发布；公开口径见 `docs/domain/bounded-contexts.md` §6 #1）。

## 4. 边界裁定备注

1. **七边界是结构边界（架构层），不替代 Domain 的四个有界上下文**（核心上下文 / 外部手段层 / Host / Memory Provider，`bounded-contexts.md`）：前者是更细的架构划分，后者是 Domain 权威定义。两者不一致时 Domain 优先（规则 1）。
2. **WORKERS 保持未定义**：拓扑中保留边界名与位置，"Worker 是什么" = UNKNOWN（Q6 追认保持）；V0 的 Worker A/B 只是部署名（U-5），不构成定义。
3. **CAPABILITY SYSTEM 在 Core 内部**：能力生命周期是 Domain 概念（成长判据：能力是个体后天修成的"术"，材料 1 §4/§6），不是外部手段；其状态机由 ADR 0003 定义，四目录是该状态机的一个合法 adapter 形态（K-06）。
4. **COGNITIVE MODELS 与 WORKERS 分属两个边界**：前者是模型后端的形态（有历史部署证据），后者无定义。V0 部署中两者重合（Worker A/B = 两个模型节点）——这是部署层巧合（L4），不是架构同一。
