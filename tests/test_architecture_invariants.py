"""骨架级结构守卫 — M01（+ M03 Continuity append-only 棘轮）。

这些测试固化架构边界（棘轮）：后续 Milestone 的任何改动若破坏边界，
这里先红。对应各票验收的结构面：

- 验收 1（R-09）：I/O 只允许出现在 composition root；组件间不互相
  import / 构造——只有装配点接线。
- 验收 2（CINV-2 / K-11）：无写路径；运行时包内无第二成文"道"来源
  （代码中不内嵌任何成文文本 / 原则名）。
- 验收 4（ADR 0004 决定 1）：无独立 life 层。
- 验收 5（spec-adapters.md §5）：个体持久文件清单只由 composition root
  构造（Runtime 进程侧）。
- 验收 6（U-5）：无硬编码端点 / 超时 / 后端默认值（M-1…M-3 泄漏检查）。
- M03（决定 ⑤，M02 决定 ② 对齐）：I/O 限于装配点 + continuity 追加
  通道（唯一差异 = 合法内部追加通道，data-ownership §2）；continuity.py
  内 open( 仅 append / read 模式；全包无写模式；Continuity 记录唯一
  写入入口 = 成长管线（M07 接线，composition 为注入位）；C-1 / C-3 /
  C-4 残留位符号全包不出现；FACULTY_ROOTS 初始集恰好 8 根。
- M05（决定 ⑥⑦⑧）：I/O / open( / sqlite3 允许位 = {composition,
  continuity, memory_sqlite}（memory_sqlite = 合法 Memory 存储通道，
  ADR 0001）；memory_sqlite 是唯一可 import 其他 V1 模块的组件（且只
  单向 import Ontology 模块，方向锁 INV-3 / 规则 5）；mkdir 初始态
  创建例外仅 memory_sqlite（ADR 0007）；MemoryStore 契约形态固化 =
  恰好 6 方法（R-05）；存储细节字符串仅存于 provider（AC 4）；无宿主
  值 / 无 provenance 字段（H-4 / ADR 0007）；无独立 Insight 存储
  （ADR 0006）；Provider 初始化参数面仅 memory_dir（AC 7）。
- M06（决定 ⑨–⑫）：五个感知 / 认知手段模块（model_ollama /
  model_llama_cpp / model_wire / research / world）= 手段，不是写通道——
  不引用任何个体状态写入口（INV-7 投影不回流结构面，AC 6）；FileWorld
  公共表面恰为 observe（AC 1 depth）；V0 ResearchService pass-through
  壳形态不存在（D-04，AC 7）；包内 Model 出站通道 = 共享 Wire Client
  模块（`urlopen(` 仅限 model_wire.py；M09 棘轮显式调位，ADR 0009
  Decision 7；调位前 = 各 Backend Adapter 模块，ADR 0008
  Consequences）。
  「Model backend 集合」单一声明位 = EXPECTED_MODEL_BACKENDS（决定 ㊷）；
  「Model 出站通道」单一声明位 = MODEL_WIRE_MODULES（ADR 0009
  Decision 7）。
- M04（决定 ⑬–⑲）：Individual 顶层聚合（individual.py）——公共表面恰为
  act / persist 唯一入口对（R-01 / K-10，interface = test surface）；全包
  无跨类私有方法调用（R-08 A-5/A-6）；Individual 构造位仅 composition
  （R-09，决定 ⑲）；个体持久文件清单恰 5 项（spec-individual.md §4）；
  D-05 根因声明位（HOST_RELATION_STATEMENT）存在性正面检查；individual
  测试只经接口面（不穿透 Individual 私有成员，K-10）；individual.py 的
  import 面 = 类型 / 枚举值 / 异常类型引用显式白名单（决定 ⑲）；V0 症状级
  清洗函数符号残留位固化（D-05 顺序：R-12 根因修复前不删除；V1 未移植
  该函数，规则 12）。
- M07（决定 ⑳–㉗）：Growth 成长管线（growth.py，零 `dao_sheng` import，
  决定 ⑤）——公共表面恰为 5 方法（决定 ㉗）；8 项构造注入参数面全部
  keyword-only 无默认值（R-09 / 决定 ㉒）；D-06 五个薄 pass-through 名 +
  `sync_hermes` 形态全包不存在（形态 = 符号定义位，prose 引用不构成
  形态，AC 6）；growth.py 无 `Memory(` 直接记录
  构造（AC 2 / A-1 形态消除）；growth.py 无 `capabilities`（AC 5 / A-7）；
  `Growth(` 构造位仅 composition（R-09）。
- M08（决定 ㉘–㉚）：Capability 生命周期（capability_lifecycle.py，零
  `dao_sheng` import）——状态集恰 4 值（ADR 0003 决定 1；状态集扩展 =
  Domain 决定，这里先红）；Manager 公共表面恰 4 方法（propose /
  advance / retire / execute = 唯一权威，无旁路）；3 项构造注入参数面
  （R-09 / 决定 ㉙）；闸门契约位 `def verify(` 全包仅
  capability_lifecycle.py（D-03：legacy 验证旁路形态不存在；M11 交付真
  闸门时该模块允许位显式调位）；I/O 允许位显式扩至
  capability_lifecycle.py + 写 marker 增 "rename" + 该模块 write_text /
  mkdir / rename 例外位（状态转换 = 文件移动，决定 ㉘）；无裸 `open(`
  （文件 I/O = Path 方法，open 棘轮允许位不扩）；`capabilities_dir`
  引用位仅 layout / composition / capability_lifecycle（A-7）；
  `CapabilityManager` 引用位仅 composition / capability_lifecycle（spec
  §5 边界：Growth 侧无能力生命周期引用）；`CapabilityManager(` 构造位
  仅 composition（R-09）。
- M09（决定 1–6；S1–S6 起逐步固化）：host 集成层——"hermes" token
  允许位 = {hermes_host, composition}（ADR 0002 决定 1，AC 1 /
  H-1…H-9 收敛）；中性 Interface 恰三方法（AC 2 / 决定 2）；
  hermes_host.py import 面 = 显式白名单（S2 类型引用 + S3 宿主载体
  通道引用，不构造组件）；I/O / 裸 open( / read_text 允许位扩至
  host_carrier.py（S3：宿主侧载体通道 = 宿主层唯一 I/O 通道——会话
  记录读 / 导入日志读 / 导入日志追加 / 布局确保）+ host_carrier 内
  open( 仅 append / read 模式 + mkdir 布局确保例外 + sqlite3 允许位
  （宿主状态库 = 只读连接；fts5 / trigram / journal_mode / PRAGMA
  仍仅 memory_sqlite）；`HermesHostAdapter(` 构造位仅 composition
  （S5 装配接线：HostConfig 声明位 + RuntimeAssembly.host，R-09）；
  宿主三模块不触碰个体持久文件清单 5 项（S6 / AC 4 / §5 进程
  边界）+ V0 漂移形态零残留（S6 / AC 7：无 `subprocess` 桥 / 无
  `hermes:` 前缀 / 无 842 行单文件形态）。
- M10（约束验证型，规则 4 / 规则 11；UNKNOWN 维持）：包内无任何
  worker 符号定义（形态 = 符号定义位，M07 先例）；"worker" token
  仅限 identity.py 的 INV-2 负约束引文行（同现 model 与 host 的
  K-11 形态；扩位须显式调位，M09 纪律）。
- M11（决定 ㊱–㊵）：闸门唯一实现 CapabilityVerifier（capability_
  verifier.py，零 `dao_sheng` import）——构造位仅 composition（R-09）；
  引用位仅 composition / 定义位本模块；闸门调用位 `.verify(` 仅
  Manager 内部（无第二条验证路径，D-03 调用位面）；全部测试经各
  组件 Interface（K-10：测试不穿透组件私有成员，component-model.md
  §3；M11 交付时点全测试目录零违规，违规即先红）；测试目录
  "sqlite3" 仅存于文档化位（M05 carrier 形态例外 / 宿主侧状态库
  fixture / 本文件 marker 词表自身）。
"""

import ast
import inspect
import re
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "dao_sheng"

# 「Model backend 集合」单一声明位（决定 ㊷）：棘轮侧刻意声明常量——两处
# data 位（装配点结构性豁免 frozenset / 手段模块集合的 Model 部分）由它
# 派生，两处永远一致（urlopen 出站 allowlist 已调位至 MODEL_WIRE_MODULES
# 单一声明位，ADR 0009 Decision 7，不再由本常量推导）。plain 三元组
# (backend 名, adapter 类名, 模块文件名)；元组排列顺序 = 纯声明顺序、
# 零优先级语义（U-5 未裁定的部署偏好不被测试文件固化）。
# 不从生产侧 registry 派生（与 dao_sheng/composition.py 的
# _MODEL_BACKENDS 刻意区分，两者零运行时耦合）：棘轮不得从被守卫的代码
# 派生自己的放行名单——若从 registry 派生，未经 ADR 0008 的新 backend
# 会令 allowlist 自动扩位、出站棘轮静默放行，摧毁 M09 显式调位纪律
# （ADR 0008 Consequences）。
EXPECTED_MODEL_BACKENDS = (
    ("ollama", "OllamaModel", "model_ollama.py"),
    ("llama_cpp", "LlamaCppModel", "model_llama_cpp.py"),
)

# 「Model 出站通道」单一声明位（ADR 0009 Decision 7）：Model 出站 allowlist
# （`urlopen(` 位置）只由本常量构成，不再由 EXPECTED_MODEL_BACKENDS 推导
# （transport 调位至共享 Wire Client）。与决定 ㊷ 同一纪律：棘轮侧刻意
# 声明、不从生产侧派生——新增出站模块须显式调位本常量，棘轮变红而非
# 自动扩位。model_wire.py 不进 backend 三元组（不是 backend，ADR 0009
# Decision 7）。
MODEL_WIRE_MODULES = ("model_wire.py",)


def _sources() -> dict[str, str]:
    return {
        p.name: p.read_text(encoding="utf-8") for p in sorted(PKG.rglob("*.py"))
    }


def _bare_open(src: str) -> re.Match | None:
    """裸文件 `open(` 调用检测（排除 `urlopen(` 等更长标识符——
    M06：model_wire.py 的 `urllib.request.urlopen(` 是 Model 出站通道，
    合法且仅限共享 Wire Client 模块（MODEL_WIRE_MODULES；ADR 0009
    Decision 7；调位前 = 各 Backend Adapter 模块，ADR 0008
    Consequences），见其 docstring 棘轮注记）。"""
    return re.search(r"\bopen\(", src)


class CompositionRootOnlyWiringTest(unittest.TestCase):
    """验收 1（R-09 结构测试）：只有装配点做 I/O 与模块接线。"""

    #: M04 决定 ⑲：individual.py（顶层聚合）的 import 面显式白名单——
    #: 仅类型 / 枚举值 / 异常类型引用（依赖注入面 R-09），不构造任何
    #: 组件；构造位仍仅 composition root（M04IndividualRatchetTest 固化）。
    INDIVIDUAL_IMPORT_WHITELIST = frozenset(
        {
            "from dao_sheng.continuity import load_continuity",
            "from dao_sheng.doctrine import Doctrine",
            "from dao_sheng.faculties import Faculties",
            "from dao_sheng.identity import Identity",
            "from dao_sheng.memory import MemoryConfidence, MemoryOrigin, MemoryStatus, MemoryStore, RecallQuery",
            "from dao_sheng.model import Model, ModelUnavailable",
        }
    )

    #: M09 S2/S3：hermes_host.py（Hermes 宿主 adapter）的 import 面显式
    #: 白名单——仅中性 Interface 句柄 / 报告类型 + ExperienceCandidate
    #: 类型引用（S2）+ 宿主载体通道函数引用（S3；同 ⑲ 先例：引用，
    #: 不构造组件——载体通道 = 模块函数，非组件）。D-058 / ADR 0010 修
    #: 订 Decision 12：裁定日志读面（read_adjudications）+ 指纹 / 内容
    #: 哈希函数引用加入；`append_adjudication` 刻意不入白名单——结构保
    #: 证：宿主 adapter 层只能读裁定、不能写裁定（机器永不自动裁定，人
    #: 工裁定只能经载体通道外部追加）。
    HERMES_HOST_IMPORT_WHITELIST = frozenset(
        {
            "from dao_sheng.growth import ExperienceCandidate",
            "from dao_sheng.host_carrier import append_imported, candidate_set_fingerprint, content_sha256, location_digest, read_adjudications, read_imported_keys, read_session_records",
            "from dao_sheng.host_integration import HostSession, SyncReport",
        }
    )

    #: ADR 0009 Decision 7：Wire Client import 窄例外允许位 = Backend
    #: Adapter 模块集合（由棘轮侧声明位 EXPECTED_MODEL_BACKENDS 派生，
    #: 零生产侧耦合——与决定 ㊷ 同一纪律）。
    MODEL_WIRE_IMPORT_ALLOWED = frozenset(
        module for _, _, module in EXPECTED_MODEL_BACKENDS
    )

    def test_io_only_in_composition_and_authorized_channels(self):
        """Path-method I/O（read_text / read_bytes / write_text）限于装配点
        + continuity 追加通道（M03）+ memory_sqlite 存储通道（M05 决定 ⑥）
        + capability 载体通道（M08 决定 ㉘/㉚）+ 宿主载体通道（M09 S3：
        host_carrier = 宿主层唯一 I/O 通道；唯一差异皆为合法内部通道）。
        裸 `open(` 的唯一守卫 = test_open_only_in_io_authorized_modules
        （M03 独立棘轮），本测试不重复断言。"""
        io_markers = ("read_text", "read_bytes", "write_text")
        for name, src in _sources().items():
            if name in (
                "composition.py",
                "continuity.py",
                "memory_sqlite.py",
                "capability_lifecycle.py",
                "host_carrier.py",
            ):
                continue
            for m in io_markers:
                self.assertNotIn(
                    m,
                    src,
                    f"{name} 含 I/O {m!r}（只允许在装配点 / continuity / "
                    "memory_sqlite / capability 载体 / 宿主载体通道）",
                )

    def test_no_internal_imports_outside_composition(self):
        """组件不 import 其他组件——跨模块构造只允许在装配点发生。

        M05 例外（方向锁，INV-3 / 规则 5）：adapter（memory_sqlite）
        单向 import Ontology 模块（dao_sheng.memory）= 唯一允许的
        组件间 import 方向。
        ADR 0008 决定 ① 例外：Model interface 模块（dao_sheng.model）
        = seam，不是组件——类型 / 异常引用（Protocol / ModelUnavailable，
        不构造组件）任何模块（Backend adapter / 消费方）可导入。
        ADR 0009 Decision 7 例外：Wire Client 模块（dao_sheng.model_wire）
        = 共享 wire implementation——仅 Backend Adapter 模块可导入
        （窄例外，允许位 = MODEL_WIRE_IMPORT_ALLOWED 棘轮侧声明位）。"""
        for name, src in _sources().items():
            if name == "composition.py":
                continue
            for line in src.splitlines():
                stripped = line.strip()
                if name == "memory_sqlite.py" and stripped.startswith(
                    "from dao_sheng.memory import"
                ):
                    continue
                if name == "individual.py" and stripped.startswith(
                    "from dao_sheng"
                ):
                    # M04 决定 ⑲：顶层聚合 import 面 = 显式白名单
                    # （类型 / 枚举值 / 异常类型引用，不构造组件）
                    self.assertIn(
                        stripped,
                        self.INDIVIDUAL_IMPORT_WHITELIST,
                        f"individual.py 的 import 面超出白名单：{stripped}",
                    )
                    continue
                if name == "hermes_host.py" and stripped.startswith(
                    "from dao_sheng"
                ):
                    # M09 S2：宿主 adapter import 面 = 显式白名单
                    # （中性 Interface 句柄 / 报告 + 候选类型引用，不构造组件）
                    self.assertIn(
                        stripped,
                        self.HERMES_HOST_IMPORT_WHITELIST,
                        f"hermes_host.py 的 import 面超出白名单：{stripped}",
                    )
                    continue
                if stripped.startswith("from dao_sheng.model import"):
                    # ADR 0008 决定 ①：interface 模块 = seam（仅类型 /
                    # 异常引用，不构造组件）
                    continue
                if stripped.startswith("from dao_sheng.model_wire import"):
                    # ADR 0009 Decision 7：Wire Client import 窄例外——
                    # 仅 Backend Adapter 模块可导入（validate_config /
                    # post_json = 共享 wire implementation 引用，不构造
                    # 组件）
                    self.assertIn(
                        name,
                        self.MODEL_WIRE_IMPORT_ALLOWED,
                        f"{name} import 了 Wire Client（只允许 Backend "
                        f"Adapter 模块）：{stripped}",
                    )
                    continue
                self.assertFalse(
                    stripped.startswith(("from dao_sheng", "import dao_sheng")),
                    f"{name} 内部 import 了 V1 模块：{stripped}",
                )


class DoctrineSingleSourceTest(unittest.TestCase):
    """验收 2（结构面）：'道'文本只经装配点从 principles.md 注入——
    V1 代码中不内嵌任何成文文本或原则名（无第二成文来源，M-05 教训）。"""

    PRINCIPLE_NAMES = ("不妄动", "知止", "顺势", "反思", "海纳百川", "道心稳固")

    def test_no_doctrine_text_embedded_in_code(self):
        for name, src in _sources().items():
            for n in self.PRINCIPLE_NAMES:
                self.assertNotIn(n, src, f"{name} 内嵌了原则名 {n!r}")

    def test_no_write_path_anywhere(self):
        """运行时任何路径不可改写持久 / 成文状态（CINV-2 / K-11 结构面）。

        M03：`open(` 移入独立棘轮（见
        test_open_only_in_io_authorized_modules）——continuity.py 的
        合法内部追加通道用 open() append 模式；其余写 marker 全包禁止。
        M05 决定 ⑥：`mkdir` 初始态创建例外仅 memory_sqlite.py（目录 /
        DB 缺失 = 初始态，Provider 自建，ADR 0007）。
        M08 决定 ㉘/㉚：写 marker 增 "rename"（文件移动 = 状态转换的
        物理形态），capability_lifecycle.py 的 write_text / mkdir /
        rename = capability 载体通道唯一例外位。
        M09 S3：`mkdir` 布局确保例外增 host_carrier.py（导入日志父
        目录；宿主状态库 = 只读连接，非写路径）。
        """
        write_markers = (
            "write_text",
            "write_bytes",
            "mkdir",
            "rename",
            "unlink",
            "rmtree",
            "shutil",
        )
        for name, src in _sources().items():
            for m in write_markers:
                if m == "mkdir" and name == "memory_sqlite.py":
                    continue  # M05 决定 ⑥：初始态创建 = 唯一 mkdir 例外
                if m == "mkdir" and name == "host_carrier.py":
                    continue  # M09 S3：导入日志父目录布局确保
                if name == "capability_lifecycle.py" and m in (
                    "write_text",
                    "mkdir",
                    "rename",
                ):
                    continue  # M08 决定 ㉘/㉚：capability 载体通道
                self.assertNotIn(m, src, f"{name} 含写路径 {m!r}")


class ContinuityAppendOnlyRatchetTest(unittest.TestCase):
    """M03 决定 ⑤（M02 决定 ② 对齐）：Continuity append-only 的
    enforce 结构面——合法内部追加通道存在且唯一，写 / 覆写模式不存在。"""

    def test_open_only_in_io_authorized_modules(self):
        """裸文件 `open(` 仅装配点 + continuity 追加通道（M03）+
        memory_sqlite 存储通道（M05 决定 ⑥；sqlite3.connect 内部落盘，
        包内无裸 open(）+ 宿主载体通道（M09 S3：导入日志追加；宿主
        状态库 = sqlite3 只读连接，非裸 open(）；`urlopen(` 为 Model
        出站通道（M06），不属文件 I/O 棘轮范围。"""
        for name, src in _sources().items():
            if name in (
                "composition.py",
                "continuity.py",
                "memory_sqlite.py",
                "host_carrier.py",
            ):
                continue
            self.assertIsNone(
                _bare_open(src),
                f"{name} 含 open(（只允许在装配点 / continuity / "
                "memory_sqlite / 宿主载体通道）",
            )

    def test_continuity_module_append_only_surface(self):
        """continuity.py 内每个 `open(` 行必须显式 append / read 模式
        （"a" / "r"）——写 / 覆写模式（w / x / +）不存在（AC 1 结构面）。"""
        src = _sources().get("continuity.py", "")
        for line in src.splitlines():
            if "open(" in line:
                self.assertTrue(
                    '"a"' in line or "'a'" in line
                    or '"r"' in line or "'r'" in line,
                    f"continuity.py 内 open( 必须 append / read 模式：{line.strip()}",
                )

    def test_append_continuity_referenced_only_by_allowed_sources(self):
        """AC 5 结构面：`append_continuity` 引用源限于定义处 + growth
        （M07 接线）+ composition（R-09 注入位）——M03 零调用方，无其他
        写入入口。"""
        for name, src in _sources().items():
            if name in ("continuity.py", "growth.py", "composition.py"):
                continue
            self.assertNotIn(
                "append_continuity",
                src,
                f"{name} 引用了 continuity 追加通道（只允许在 growth / composition 注入位，M07 接线）",
            )


class V0ResidueRatchetTest(unittest.TestCase):
    """M03 AC 2 结构面：V0 残留位符号在 V1 包内不复存在
    （spec-self-state.md §2 处置表：C-1 / C-3 / C-4）。M05 决定 ⑦ 追加：
    修正 / Insight 无 `kind` 判别列（ADR 0006 单一表示，三维语义层是唯一
    语义载体）。"""

    RESIDUE = (
        "last_action_experience_id",  # C-1 → runtime state，不持久
        "continuity_revision",  # C-3 → 不复存在（被单一载体取代）
        'kind="continuity"',  # C-4 → 不复存在（非 Memory 的一种 kind）
        "kind='continuity'",
        'kind="insight"',  # M05 决定 ⑦ / ADR 0006 → Insight 无独立存储形态
        "kind='insight'",
        'kind="correction"',  # M05 决定 ⑦ → 修正无 kind 判别列
        "kind='correction'",
        # D-05 顺序：V0 症状级清洗函数（R-12 根因修复验证前不得删除）；
        # V1 未移植该函数（规则 12 不默认 KEEP）→ 符号残留位固化。
        "_strip_dao_sheng_context",
        "_clean_user_message",
    )

    def test_no_v0_residue_symbols_in_package(self):
        for name, src in _sources().items():
            for s in self.RESIDUE:
                self.assertNotIn(s, src, f"{name} 含 V0 残留位符号 {s!r}")


class FacultyRootsRatchetTest(unittest.TestCase):
    """M03 AC 3 结构面：Faculties 初始集恰好 8 根、无增无减——
    `FACULTY_ROOTS` 单一来源（keep.md K-09 / D-7）。增删根 = Domain 决策
    （spec-self-state.md §3）：代码集合任何改动这里先红，须域文档先行。"""

    def test_faculty_roots_exactly_eight(self):
        from dao_sheng.faculties import FACULTY_ROOTS

        self.assertEqual(
            len(FACULTY_ROOTS), 8, "Faculties 初始集必须是 8 根（Q3 USER_RATIFIED）"
        )
        self.assertEqual(len(set(FACULTY_ROOTS)), 8, "Faculties 根不得重复")


class NoLifeLayerTest(unittest.TestCase):
    """验收 4（ADR 0004 决定 1）：无独立 life 层。"""

    def test_no_life_module(self):
        """'独立 life 层' = 名为 life 的包目录或 life.py 模块（精确匹配；
        子串匹配会误伤 capability_lifecycle 等合法模块名，M08 / ADR 0003 领域）。"""
        for p in sorted(PKG.rglob("*.py")):
            rel = p.relative_to(PKG)
            dirs = {part.lower() for part in rel.parts[:-1]}
            self.assertNotIn("life", dirs, f"存在 life 层目录 {rel.parent}")
            self.assertNotEqual(
                rel.name.lower(), "life.py", f"存在 life 层模块 {rel.name}"
            )

    def test_no_life_runtime_class(self):
        for name, src in _sources().items():
            self.assertNotIn("LifeRuntime", src, f"{name} 含 life 层类")


class ProcessBoundaryTest(unittest.TestCase):
    """验收 5（骨架层面）：个体持久文件清单只由 Runtime 侧装配点构造——
    host 进程（Hermes Desktop）不存在直接触碰清单的路径。"""

    def test_individual_files_constructed_only_by_composition(self):
        """除清单定义模块（layout）与装配点（composition）外，任何模块不得
        构造 / 触碰清单。"""
        for name, src in _sources().items():
            if name in ("composition.py", "layout.py"):
                continue
            self.assertNotIn(
                "IndividualFiles", src, f"{name} 触碰了个体持久文件清单"
            )


class U5NotPresetTest(unittest.TestCase):
    """验收 6（U-5 不预设）：骨架 / 未来 adapter 内无硬编码端点 / 超时 /
    后端默认值——V0 审计项 M-1…M-3 / M-5 的泄漏检查（只查值，不查审计编号）。"""

    LEAKS = (
        "http://",
        "https://",
        "127.0.0.1",
        "localhost",
        "0.0.0.0",
        "gpt-",
        "ollama",
        "duckduckgo",
        "11434",
        "pi.cmd",
    )

    # ADR 0008 决定 ②④ / 裁定 ①：装配点 import Backend Adapter 模块的行 +
    # backend 名 → adapter 类 registry 行 = 结构性引用（模块名 / 类名 /
    # backend 名，非部署值）——豁免泄漏检查；其余内容全检不变。
    ADAPTER_STRUCTURAL_LINES = frozenset(
        line
        for backend, cls, module in EXPECTED_MODEL_BACKENDS
        for line in (
            f"from dao_sheng.{module.removesuffix('.py')} import {cls}",
            f'"{backend}": {cls},',
        )
    )

    def test_no_hardcoded_deployment_values(self):
        for name, src in _sources().items():
            if name == "composition.py":
                src = "\n".join(
                    line
                    for line in src.splitlines()
                    if line.strip() not in self.ADAPTER_STRUCTURAL_LINES
                )
            for leak in self.LEAKS:
                self.assertNotIn(leak, src, f"{name} 含硬编码部署值 {leak!r}")
            # 硬编码 Windows 可执行文件路径检测用词边界（M05 精化）：
            # "app.exe\"" 命中；stdlib sqlite3 的 .execute 方法调用
            # （".exe" 后随字母）不命中。
            self.assertIsNone(
                re.search(r"\.exe\b", src),
                f"{name} 含硬编码 Windows 可执行文件路径 (.exe)",
            )


class MemoryRatchetTest(unittest.TestCase):
    """M05 结构面（决定 ⑥⑦⑧；AC 1–4 / AC 7 结构判据）：MemoryStore
    契约形态固化 = 恰好 6 方法（R-05）；存储细节不外露（AC 4）；无宿主值
    / 无 provenance（H-4 / ADR 0007）；无独立 Insight 存储（ADR 0006）；
    Provider 初始化参数面仅 memory_dir（AC 7 结构面）。"""

    CONTRACT = frozenset(
        {
            "remember",
            "recall",
            "get",
            "correct_memory",
            "register_reference",
            "resolve_reference",
        }
    )

    def test_protocol_exactly_six_methods(self):
        """契约形态固化（R-05）：MemoryStore 协议成员恰好 6——不得出现
        5 方法浅层形态或 11 方法实现表形态。

        Python 3.12+：Protocol 不再填 `__abstractmethods__`，协议成员的
        权威读取 = typing.get_protocol_members。
        """
        from typing import get_protocol_members

        from dao_sheng.memory import MemoryStore

        self.assertEqual(get_protocol_members(MemoryStore), self.CONTRACT)

    def test_adapter_public_surface_subset_of_contract(self):
        """adapter 公共表面 ⊆ 6 方法 + close（生命周期，装配点调用）——
        实现细节（表 / 索引 / 通道 / 排序）不成为公共方法（AC 2 / AC 4）。"""
        from dao_sheng.memory_sqlite import SqliteMemoryProvider

        public = {
            name
            for name, value in vars(SqliteMemoryProvider).items()
            if not name.startswith("_") and callable(value)
        }
        self.assertLessEqual(public, self.CONTRACT | {"close"})

    def test_storage_detail_strings_only_in_provider(self):
        """存储细节字符串仅存于 provider（AC 4 结构面）：调用方代码不知道
        SQLite / FTS5 / trigram / journal_mode / PRAGMA。

        M09 S3：host_carrier.py（宿主载体通道）读宿主状态库 = 只读
        sqlite3 连接——宿主库的 schema 知识归宿主层（ADR 0002 决定 1）
        → "sqlite3" / "sqlite" 允许位扩至该模块；FTS5 / trigram /
        journal_mode / PRAGMA（Memory provider 存储细节）仍仅
        memory_sqlite.py。"""
        detail_markers = ("sqlite3", "fts5", "trigram", "journal_mode", "PRAGMA")
        for name, src in _sources().items():
            if name == "memory_sqlite.py":
                continue
            for m in detail_markers:
                if m == "sqlite3" and name == "host_carrier.py":
                    continue  # M09 S3：宿主载体通道（只读连接）
                self.assertNotIn(
                    m, src, f"{name} 含存储细节字符串 {m!r}（只允许在 memory_sqlite.py）"
                )
        # "sqlite"（小写）= 模块名 import 允许位 + provider 本体 +
        # M09 S3 宿主载体通道（只读连接）；
        # 其余调用方（含 memory.py Ontology）不得出现。
        for name, src in _sources().items():
            if name in ("memory_sqlite.py", "composition.py", "host_carrier.py"):
                continue
            self.assertNotIn("sqlite", src, f"{name} 含 'sqlite'（只允许在装配点 import / provider / 宿主载体通道）")

    def test_no_provenance_or_host_value_in_package(self):
        """H-4 / ADR 0007：宿主名不进包；provenance 字段不复存在（仅
        memory.py 的 H-4 引用注记例外）。"""
        for name, src in _sources().items():
            self.assertNotIn("hermes_desktop", src, f"{name} 含宿主值 hermes_desktop")
            if name != "memory.py":
                self.assertNotIn("provenance", src, f"{name} 含 provenance 字段（V0 形态残留）")

    def test_no_independent_insight_storage(self):
        """ADR 0006：Insight = Memory 的一种，无独立 Insight 存储
        （V0 growth/insight.py 形态不复存在）。"""
        for p in sorted(PKG.rglob("*.py")):
            self.assertFalse(
                p.name.lower().startswith("insight"),
                f"存在独立 Insight 模块 {p.name}（ADR 0006 单一表示）",
            )

    def test_provider_init_signature_only_memory_dir(self):
        """AC 7 结构面：初始化参数面仅 memory_dir——无外部存储参数可传入
        （不读 V0 存储、不迁移，ADR 0007）。"""
        from dao_sheng.memory_sqlite import SqliteMemoryProvider

        params = list(inspect.signature(SqliteMemoryProvider.__init__).parameters)
        self.assertEqual(params, ["self", "memory_dir"])


class M06AdapterRatchetTest(unittest.TestCase):
    """M06 结构面（AC 1 / AC 6 / AC 7）：五个感知 / 认知手段模块
    （model_ollama / model_llama_cpp / model_wire / research / world；
    model_wire = 共享 Wire Client，ADR 0009 纳入手段集合）= 手段，不是
    写通道——模块不引用任何个体状态写入口（INV-7：观察 / 投影无回流
    路径，消费侧决定点 = Core，M04 接线）；FileWorld 公共表面恰为
    observe（depth）；V0 ResearchService pass-through 壳形态不存在
    （D-04）。"""

    ADAPTERS = (
        *(module for _, _, module in EXPECTED_MODEL_BACKENDS),
        # ADR 0009 Decision 7：model_wire.py 纳入手段集合（受 INV-7
        # 写入口扫描守卫），但不进 backend 三元组 EXPECTED_MODEL_BACKENDS。
        *MODEL_WIRE_MODULES,
        "research.py",
        "world.py",
    )

    #: 个体状态写入口（memory 6 方法契约的写侧 + continuity 唯一追加
    #: 通道；continuity 侧另有全包引用源棘轮，此处补齐 memory 侧）。
    WRITE_ENTRY_POINTS = (
        "remember(",
        "correct_memory(",
        "register_reference(",
        "append_continuity",
    )

    def test_adapters_no_experience_write_reference(self):
        """AC 6 结构面（INV-7）：手段模块不引用任何个体状态写入口——
        观察 / 投影回流路径结构性不存在（回流只能发生在 M04 / M07 的
        Core 消费侧决定点，那是合法位置）。"""
        for name in self.ADAPTERS:
            src = _sources().get(name, "")
            for m in self.WRITE_ENTRY_POINTS:
                self.assertNotIn(
                    m,
                    src,
                    f"{name} 引用了个体状态写入口 {m!r}（INV-7：观察 / 投影不回流）",
                )

    def test_no_research_service_shell(self):
        """AC 7（D-04）：V0 `ResearchService` 47 行 pass-through 壳形态
        在包内不存在（空查询校验已并入 seam 契约，M06；类定义检测——
        docstring 中的 D-04 引文不算形态）。"""
        for name, src in _sources().items():
            self.assertIsNone(
                re.search(r"\bclass\s+ResearchService\b", src),
                f"{name} 含 class ResearchService（D-04：pass-through 壳不复存在）",
            )

    def test_world_surface_only_observe(self):
        """AC 1 depth（world 侧）：FileWorld 调用方公共表面恰为单个
        观察调用 observe（interface = test surface；root 经构造注入）。"""
        from dao_sheng.world import FileWorld

        surface = {
            name
            for name, value in vars(FileWorld).items()
            if callable(value) and not name.startswith("_")
        }
        self.assertEqual(surface, {"observe"})

    def test_urlopen_only_in_model_wire_modules(self):
        """包内 Model 出站通道 = 共享 Wire Client 模块（M09 棘轮显式调位，
        ADR 0009 Decision 7；调位前 = model_ollama.py（Ollama adapter）+
        model_llama_cpp.py（llama.cpp adapter），ADR 0008 Consequences）：
        `urlopen(` 不得出现在任何其他模块。"""
        outbound_allowed = set(MODEL_WIRE_MODULES)
        for name, src in _sources().items():
            if name in outbound_allowed:
                continue
            self.assertNotIn(
                "urlopen(",
                src,
                f"{name} 发起了出站调用（只允许在 Wire Client 模块通道）",
            )


class M04IndividualRatchetTest(unittest.TestCase):
    """M04 结构面（决定 ⑬–⑲；AC 1 / 4 / 5 / 6 / 7）：Individual 顶层
    聚合的边界固化——公共表面恰为 act / persist（R-01 / K-10）；无跨类
    私有方法调用（R-08 A-5/A-6）；构造位仅 composition（R-09）；个体
    持久文件清单恰 5 项（§4）；D-05 根因声明位存在性正面检查；individual
    测试只经接口面。"""

    def test_individual_public_surface_only_act_and_persist(self):
        """AC 1 结构面（R-01 / K-10）：Individual 调用方公共表面恰为
        act / persist 唯一入口对——V0 三入口形态不复存在。"""
        from dao_sheng.individual import Individual

        surface = {
            name
            for name, value in vars(Individual).items()
            if callable(value) and not name.startswith("_")
        }
        self.assertEqual(surface, {"act", "persist"})

    def test_no_cross_class_private_method_calls(self):
        """AC 5 结构面（R-08 A-5/A-6）：全包无跨类私有方法调用形态——
        私有成员只允许 self 访问（类内深模块边界）。"""
        pattern = re.compile(r"([A-Za-z_]\w*)\.(_[A-Za-z_]\w*)\s*\(")
        for name, src in _sources().items():
            for m in pattern.finditer(src):
                self.assertEqual(
                    m.group(1),
                    "self",
                    f"{name} 跨类私有调用 {m.group(0).strip()!r}（R-08 A-5/A-6）",
                )

    def test_individual_files_list_exactly_five(self):
        """AC 4 结构面（§4）：个体持久文件清单 = 恰 5 项（root 容器
        除外）——清单外文件不是个体状态。"""
        from dataclasses import fields

        from dao_sheng.layout import IndividualFiles

        items = {f.name for f in fields(IndividualFiles)} - {"root"}
        self.assertEqual(
            items,
            {"identity", "continuity", "memory_dir", "capabilities_dir", "faculties"},
        )

    def test_individual_constructed_only_in_composition(self):
        """R-09 结构面：Individual 构造位仅装配点——顶层聚合不在组件内
        被构造（决定 ⑲）。"""
        for name, src in _sources().items():
            if name in ("composition.py", "individual.py"):
                continue
            self.assertNotIn(
                "Individual(", src, f"{name} 构造了 Individual（构造位仅装配点）"
            )

    def test_d05_root_cause_declaration_site_present(self):
        """AC 6 / D-05 顺序：R-12 根因声明位（Core 文本无宿主关系表述的
        声明点）在装配点正面存在——声明位丢失 = 根因修复状态不可验证。"""
        src = _sources().get("composition.py", "")
        self.assertIn("HOST_RELATION_STATEMENT", src)

    def test_individual_tests_only_through_interface_surface(self):
        """AC 7 结构面（K-10）：individual 测试只经接口面——不引用
        Individual 任何私有（非双下划线）成员（穿透内部实现）。"""
        from dao_sheng.individual import Individual

        test_src = (PKG.parent / "tests" / "test_individual.py").read_text(
            encoding="utf-8"
        )
        privates = {
            name
            for name in dir(Individual)
            if name.startswith("_") and not name.startswith("__")
        }
        for p in privates:
            self.assertNotIn(
                f".{p}", test_src, f"test_individual.py 穿透了私有成员 {p!r}"
            )


class M07GrowthRatchetTest(unittest.TestCase):
    """M07 结构面（决定 ⑳–㉗；AC 2 / 5 / 6）：Growth 成长管线的边界
    固化——公共表面恰 5 方法（决定 ㉗）；8 项构造注入参数面（R-09 /
    决定 ㉒）；D-06 薄 pass-through 与 `sync_hermes` 形态不复存在
    （AC 6）；无直接记录构造（A-1 形态消除，AC 2）；无能力载体目录
    触碰（A-7，AC 5）；构造位仅装配点（R-09）。"""

    #: D-06：五个薄 pass-through 名（内联到调用方，不独立成接口）；
    #: + `sync_hermes`（ADR 0002 决定 5：同步属 M09 host 层，移除非改名）。
    PASS_THROUGH_NAMES = (
        "remember_user_preference",
        "remember_user_habit",
        "research_once",
        "propose_capability",
        "recall_experience_packages",
        "sync_hermes",
    )

    def test_growth_public_surface_exactly_five(self):
        """AC 6 结构面（决定 ㉗）：Growth 调用方公共表面恰为
        import_experience / digest / extract / reflect / verify_insight
        ——V0 管线表面（含 pass-through / 同步形态）不复存在。"""
        from dao_sheng.growth import Growth

        surface = {
            name
            for name, value in vars(Growth).items()
            if callable(value) and not name.startswith("_")
        }
        self.assertEqual(
            surface,
            {"import_experience", "digest", "extract", "reflect", "verify_insight"},
        )

    def test_growth_init_exactly_eight_injected_params(self):
        """R-09 / 决定 ㉒：8 项依赖全部构造注入（函数值 + 类型），
        全部 keyword-only、无默认值——无白名单 import、无隐藏依赖位。"""
        from dao_sheng.growth import Growth

        params = list(inspect.signature(Growth.__init__).parameters)
        self.assertEqual(
            params,
            [
                "self",
                "memory",
                "append_continuity",
                "reflection_model",
                "origin",
                "status",
                "confidence",
                "correction",
                "unavailable",
            ],
        )
        for name, p in inspect.signature(Growth.__init__).parameters.items():
            if name == "self":
                continue
            self.assertIs(
                p.kind,
                inspect.Parameter.KEYWORD_ONLY,
                f"{name} 必须 keyword-only 注入（R-09）",
            )
            self.assertIs(p.default, inspect.Parameter.empty, f"{name} 无默认值（R-09）")

    def test_no_d06_pass_through_or_sync_hermes_in_package(self):
        """AC 6 结构面（D-06 / ADR 0002 决定 5）：五个薄 pass-through
        名 + sync_hermes 形态在全包不存在——形态 = 符号定义位（def /
        class / 赋值 / import 绑定）；prose（docstring / 注释）引用名
        不构成形态（S4 收敛位 docstring 按名引用决定 5，M09）。"""
        for name, src in _sources().items():
            defined: set[str] = set()
            for node in ast.walk(ast.parse(src, name)):
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    defined.add(node.name)
                elif isinstance(node, ast.Assign):
                    defined.update(
                        t.id for t in node.targets if isinstance(t, ast.Name)
                    )
                elif isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name
                ):
                    defined.add(node.target.id)
                elif isinstance(node, ast.ImportFrom):
                    defined.update(
                        a.asname or a.name for a in node.names
                    )
                elif isinstance(node, ast.Import):
                    defined.update(
                        (a.asname or a.name).split(".")[0] for a in node.names
                    )
            for symbol in self.PASS_THROUGH_NAMES:
                self.assertNotIn(
                    symbol, defined, f"{name} 含 D-06 / 同步形态 {symbol!r}"
                )

    def test_growth_no_direct_record_construction(self):
        """AC 2 结构面（R-08 A-1 形态消除）：growth.py 无 `Memory(` 直接
        记录构造——全部 Memory 写经 6 方法契约（ADR 0006 决定 2）。"""
        src = _sources().get("growth.py", "")
        self.assertNotIn("Memory(", src)

    def test_growth_no_capability_directory_touch(self):
        """AC 5 结构面（R-04 / A-7）：growth.py 无 `capabilities` 字符串
        ——不触碰能力载体目录、不构造路径（提案 = Memory 记录形态，
        决定 ㉖）。"""
        src = _sources().get("growth.py", "")
        self.assertNotIn("capabilities", src)

    def test_growth_constructed_only_in_composition(self):
        """R-09 结构面：`Growth(` 构造位仅装配点——管线不在组件内被
        构造（决定 ㉗）。"""
        for name, src in _sources().items():
            if name in ("composition.py", "growth.py"):
                continue
            self.assertNotIn("Growth(", src, f"{name} 构造了 Growth（构造位仅装配点）")


class M09HostRatchetTest(unittest.TestCase):
    """M09 结构面（AC 1–7 结构判据；S1 起逐步固化）：host 集成层的
    边界——"hermes" token 允许位仅宿主 adapter 层 + 装配点声明位
    （AC 1 / H-1…H-9 收敛，个体级 deletion test）；中性 Interface 恰
    三方法（AC 2 / ADR 0002 决定 2）；宿主三模块不触碰个体持久文件
    清单 5 项（AC 4 / §5 进程边界，S6）；V0 漂移形态零残留（AC 7 /
    M-01/M-02/M-03 收敛，S6）。"""

    def test_hermes_token_only_in_allowed_sites(self):
        """AC 1 结构面（H-1…H-9 收敛）：宿主名 token（大小写不敏感）
        全包仅允许在 hermes_host.py（唯一知道宿主名的层，ADR 0002 决定
        1）与 composition.py（声明位，决定 4）——Core 枚举 / 文本 /
        中性 Interface 均不得出现。"""
        for name, src in _sources().items():
            if name in ("hermes_host.py", "composition.py"):
                continue
            self.assertNotIn(
                "hermes",
                src.lower(),
                f"{name} 含宿主名 token（只允许在宿主 adapter 层 / 装配点声明位）",
            )

    def test_host_integration_protocol_exactly_three(self):
        """AC 2 结构面（ADR 0002 决定 2）：Interface 成员恰为中性三方法——
        契约形态固化，宿主名成员 / V0 同步形态不得出现。"""
        from typing import get_protocol_members

        from dao_sheng.host_integration import HostIntegration

        self.assertEqual(
            get_protocol_members(HostIntegration),
            frozenset({"open_session", "import_session", "sync"}),
        )

    def test_host_carrier_open_append_or_read_mode_only(self):
        """M09 S3：host_carrier.py 内每个 `open(` 行必须显式 append /
        read 模式（"a" / "r"）——写 / 覆写模式（w / x / +）不存在
        （导入日志 = append-only 载体，同 continuity 纪律镜像；宿主
        状态库 = sqlite3 只读连接，不经 open(）。"""
        src = _sources().get("host_carrier.py", "")
        for line in src.splitlines():
            if "open(" in line:
                self.assertTrue(
                    '"a"' in line or "'a'" in line
                    or '"r"' in line or "'r'" in line,
                    f"host_carrier.py 内 open( 必须 append / read 模式：{line.strip()}",
                )

    def test_hermes_host_adapter_constructed_only_in_composition(self):
        """M09 S5 结构面（R-09）：`HermesHostAdapter(` 构造位仅装配点——
        宿主 adapter 不在组件内被构造（同 `Growth(` 先例）。"""
        for name, src in _sources().items():
            if name in ("composition.py", "hermes_host.py"):
                continue
            self.assertNotIn(
                "HermesHostAdapter(", src, f"{name} 构造了 HermesHostAdapter（构造位仅装配点）"
            )

    def test_host_layer_no_individual_persistent_files_touch(self):
        """M09 S6 结构面（AC 4 / §5 进程边界）：宿主三模块（中性
        Interface / 宿主 adapter / 宿主载体通道）不触碰个体持久文件
        清单 5 项——无 layout import、无 `IndividualFiles` 引用、无任
        一项载体名 token；清单保持 5 项不变（导入日志 = 宿主侧载体，
        不派生进清单，S5 决定）。"""
        host_layer = ("host_integration.py", "hermes_host.py", "host_carrier.py")
        forbidden = (
            "dao_sheng.layout",
            "IndividualFiles",
            "identity.json",
            "continuity.jsonl",
            "faculties.json",
            "memory_dir",
            "capabilities_dir",
        )
        for name in host_layer:
            src = _sources().get(name, "")
            for token in forbidden:
                self.assertNotIn(
                    token,
                    src,
                    f"{name} 触碰个体持久文件清单项 {token!r}"
                    "（§5 进程边界：host 进程不直接触碰）",
                )

    def test_no_subprocess_bridge_in_package(self):
        """M09 S6 结构面（AC 7 / M-02 收敛）：subprocess 桥形态（V0
        `life/bridge.py` 跨进程桥）在 V1 无对应形态——"subprocess"
        token 全包零出现；host 集成 = 进程内 adapter 层（ADR 0002
        决定 1），进程边界经宿主集成层，不经桥进程。"""
        for name, src in _sources().items():
            self.assertNotIn(
                "subprocess",
                src,
                f"{name} 含 subprocess 桥形态（M-02：V1 无对应形态）",
            )

    def test_no_m03_source_prefix_in_package(self):
        """M09 S6 结构面（AC 7 / M-03 收敛）：`source="hermes:"` 前缀
        形态在 V1 无对应形态——"hermes:"（冒号前缀形态）token 全包零
        出现；三位置 fallback + 前缀收敛到宿主 adapter 层内部解析
        （决定 1：布局知识只属于本层；决定 5：移除非改名）。"""
        for name, src in _sources().items():
            self.assertNotIn(
                "hermes:",
                src,
                f"{name} 含 M-03 源前缀形态",
            )

    def test_no_monolithic_single_file_form(self):
        """M09 S6 结构面（AC 7 / M-01 收敛）：V0 842 行单一文件
        （`hermes_import.py`：导入 + 桥 + 同步合一）形态在 V1 无对应
        形态——全包无模块达该规模；形态 = host 集成层三模块分工
        （Interface / adapter / 载体通道）。"""
        for name, src in _sources().items():
            self.assertLess(
                len(src.splitlines()),
                842,
                f"{name} 达 {len(src.splitlines())} 行：V0 842 行单文件"
                "形态重现（M-01）",
            )


class M10WorkerConstraintRatchetTest(unittest.TestCase):
    """M10 结构面（规则 4 / 规则 11；UNKNOWN 维持）：包内无 Worker
    定义 / 枚举值 / 语义字段——形态 = 符号定义位（M07 先例：prose
    引用不构成形态）；"worker" token（大小写不敏感）仅限
    identity.py 的 INV-2 负约束引文行（同现 `model` 与 `host` 的
    K-11 形态）——允许位扩位须显式调位（M09 纪律）。"""

    def _defined_symbols(self, src: str, name: str) -> set[str]:
        defined: set[str] = set()
        for node in ast.walk(ast.parse(src, name)):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                defined.update(
                    t.id for t in node.targets if isinstance(t, ast.Name)
                )
            elif isinstance(node, ast.AnnAssign) and isinstance(
                node.target, ast.Name
            ):
                defined.add(node.target.id)
            elif isinstance(node, ast.ImportFrom):
                defined.update(a.asname or a.name for a in node.names)
            elif isinstance(node, ast.Import):
                defined.update(
                    (a.asname or a.name).split(".")[0] for a in node.names
                )
        return defined

    def test_no_worker_symbol_defined_in_package(self):
        """AC 2 结构面：全包无任何 worker 符号定义（def / class /
        赋值 / import 绑定）——Worker 定义 / 枚举值 / 语义字段形态
        不存在（UNKNOWN 维持，规则 11）。"""
        for name, src in _sources().items():
            for symbol in self._defined_symbols(src, name):
                self.assertNotIn(
                    "worker",
                    symbol.lower(),
                    f"{name} 定义了 worker 符号 {symbol!r}（规则 4 / 规则 11）",
                )

    def test_worker_token_only_in_identity_citation(self):
        """token 允许位：全包仅 identity.py 的负约束引文行（INV-2 /
        K-11：载体无 model / worker / host 字段的引用，行须同现
        `model` 与 `host`）——他处出现或引文形态漂移 → 先红；允许位
        扩位须显式调位（M09 纪律）。"""
        for name, src in _sources().items():
            for line in src.splitlines():
                if "worker" not in line.lower():
                    continue
                self.assertEqual(
                    name,
                    "identity.py",
                    f"{name} 含 'worker' token（只允许在 identity.py "
                    "负约束引文行）",
                )
                lowered = line.lower()
                self.assertIn(
                    "model",
                    lowered,
                    f"identity.py 的 'worker' 行须为 K-11 负约束引文"
                    f"（同现 model / host）：{line.strip()}",
                )
                self.assertIn(
                    "host",
                    lowered,
                    f"identity.py 的 'worker' 行须为 K-11 负约束引文"
                    f"（同现 model / host）：{line.strip()}",
                )


class M08CapabilityRatchetTest(unittest.TestCase):
    """M08 结构面（决定 ㉘–㉚；AC 1 / 2 / 5 / 6 / 7 结构判据）：Capability
    生命周期边界固化——状态集恰 4 值（ADR 0003 决定 1；扩展 = Domain
    决定，这里先红）；Manager 公共表面恰 4 方法（唯一权威，无旁路）；
    3 项构造注入参数面（R-09 / 决定 ㉙）；构造位仅 composition（R-09）；
    闸门契约位 `def verify(` 全包仅 capability_lifecycle.py（D-03：
    legacy 验证旁路形态不存在；M11 交付真闸门时该模块允许位显式调位）；
    capability 载体根引用位仅 layout / composition / 本模块（A-7）；
    Growth 侧无能力生命周期引用（spec §5 边界）。"""

    def test_state_set_exactly_four(self):
        """AC 1 结构面（ADR 0003 决定 1）：状态机恰 4 状态，无新增——
        状态集扩展 = Domain 决定，这里先红、ADR 复审先行。"""
        from dao_sheng.capability_lifecycle import CapabilityState

        self.assertEqual(
            {s.value for s in CapabilityState},
            {"proposed", "working", "active", "retired"},
        )

    def test_manager_public_surface_exactly_four(self):
        """AC 2 / 5 结构面（ADR 0003 决定 2/3）：Manager 调用方公共
        表面恰为 propose / advance / retire / execute——无旁路方法、无
        直接状态写（active 唯一可达路径 = 闸门，结构性保证）。"""
        from dao_sheng.capability_lifecycle import CapabilityManager

        surface = {
            name
            for name, value in vars(CapabilityManager).items()
            if callable(value) and not name.startswith("_")
        }
        self.assertEqual(surface, {"propose", "advance", "retire", "execute"})

    def test_manager_init_exactly_three_injected_params(self):
        """R-09 / 决定 ㉙：3 项依赖全部构造注入（载体根 + memory +
        闸门契约位），全部 keyword-only、无默认值。"""
        from dao_sheng.capability_lifecycle import CapabilityManager

        params = inspect.signature(CapabilityManager.__init__).parameters
        self.assertEqual(
            list(params),
            ["self", "capabilities_dir", "memory", "verifier"],
        )
        for name, p in params.items():
            if name == "self":
                continue
            self.assertIs(
                p.kind,
                inspect.Parameter.KEYWORD_ONLY,
                f"{name} 必须 keyword-only 注入（R-09）",
            )
            self.assertIs(p.default, inspect.Parameter.empty, f"{name} 无默认值（R-09）")

    def test_manager_constructed_only_in_composition(self):
        """R-09 结构面：`CapabilityManager(` 构造位仅装配点——唯一权威
        不在组件内被构造。"""
        for name, src in _sources().items():
            if name in ("composition.py", "capability_lifecycle.py"):
                continue
            self.assertNotIn(
                "CapabilityManager(",
                src,
                f"{name} 构造了 CapabilityManager（构造位仅装配点）",
            )

    def test_gate_contract_slot_unique(self):
        """AC 6 结构面（D-03）：`def verify(` 全包仅 capability_lifecycle.py
        （闸门契约位）+ capability_verifier.py（真闸门，M11 交付）——legacy
        验证旁路形态不存在。M11 显式调位（M08 决定 ㉚ 预先约定，非静默
        扩位）：真闸门机制交付，允许位随交付同步调整并记录于本注记。"""
        for name, src in _sources().items():
            if name in ("capability_lifecycle.py", "capability_verifier.py"):
                continue
            self.assertIsNone(
                re.search(r"def\s+verify\(", src),
                f"{name} 含非闸门契约位 / 真闸门的验证形态（D-03：legacy 验证旁路不存在）",
            )

    def test_capability_directory_only_in_allowed_sites(self):
        """A-7 结构面：`capabilities_dir` 引用位仅 layout（清单定义）/
        composition（注入位）/ capability_lifecycle（载体通道）——无
        组件直接构造 `root/"active"/name` 路径"提升"能力。"""
        for name, src in _sources().items():
            if name in ("layout.py", "composition.py", "capability_lifecycle.py"):
                continue
            self.assertNotIn(
                "capabilities_dir",
                src,
                f"{name} 引用了能力载体根（A-7：载体触碰位仅 capability 生命周期模块）",
            )

    def test_capability_manager_reference_only_in_allowed_sites(self):
        """spec §5 边界结构面：`CapabilityManager` 引用位仅 composition /
        capability_lifecycle——Growth 侧无能力生命周期操作（Growth 只产
        提案，提案通道 = Memory 记录，决定 ㉖）。"""
        for name, src in _sources().items():
            if name in ("composition.py", "capability_lifecycle.py"):
                continue
            self.assertNotIn(
                "CapabilityManager",
                src,
                f"{name} 引用了 CapabilityManager（Growth 侧边界：无能力生命周期操作）",
            )


class M11VerificationRatchetTest(unittest.TestCase):
    """M11 结构面（决定 ㊱–㊵；AC 1 / 2 / 5 结构判据）：验证体系边界
    固化——闸门唯一实现 CapabilityVerifier（capability_verifier.py，零
    `dao_sheng` import）构造位仅装配点（R-09）；`CapabilityVerifier`
    引用位仅 composition / 定义位本模块；闸门调用位 `.verify(` 仅
    Manager 内部（无第二条验证路径，D-03 调用位面）；全部测试经各
    组件 Interface（K-10：测试不穿透组件私有成员，component-model.md
    §3，AC 5）；测试目录存储细节 "sqlite3" 仅存于文档化位。"""

    def test_verifier_constructed_only_in_composition(self):
        """R-09 结构面：`CapabilityVerifier(` 构造位仅装配点——闸门不在
        组件内被构造（决定 ㊲）。"""
        for name, src in _sources().items():
            if name in ("composition.py", "capability_verifier.py"):
                continue
            self.assertNotIn(
                "CapabilityVerifier(",
                src,
                f"{name} 构造了 CapabilityVerifier（构造位仅装配点）",
            )

    def test_verifier_reference_only_in_allowed_sites(self):
        """闸门引用位边界：`CapabilityVerifier` 仅 composition（注入位）/
        capability_verifier.py（定义位本身）——无组件引用闸门类型。"""
        for name, src in _sources().items():
            if name in ("composition.py", "capability_verifier.py"):
                continue
            self.assertNotIn(
                "CapabilityVerifier",
                src,
                f"{name} 引用了 CapabilityVerifier（引用位仅装配点 / 定义位）",
            )

    def test_verify_callsite_only_in_manager(self):
        """D-03 调用位面（AC 2 结构）：`.verify(` 调用位仅
        capability_lifecycle.py（唯一调用方 = Manager）——无第二条
        验证路径。"""
        for name, src in _sources().items():
            if name == "capability_lifecycle.py":
                continue
            self.assertIsNone(
                re.search(r"\.verify\(", src),
                f"{name} 含闸门调用位（唯一验证路径 = Manager 内部）",
            )

    def test_tests_only_through_component_interface_surface(self):
        """K-10 结构面（AC 5）：全部测试经各组件 Interface——测试不穿透
        组件私有成员（component-model.md §3：interface is the test
        surface）。私有集 = dao_sheng 定义类的类级单下划线成员 ∪ 组件
        源码实例级 `self._x` 赋值位；AST 扫描全测试目录，接收者为
        `self`（测试类自有成员）除外。M11 交付时点零违规；新增违规
        = 测试面纪律回归，这里先红。"""
        import importlib

        privates: set[str] = set()
        for path in sorted(PKG.rglob("*.py")):
            if path.stem == "__init__":
                continue
            module = importlib.import_module(f"dao_sheng.{path.stem}")
            for attr in dir(module):
                cls = getattr(module, attr)
                if isinstance(cls, type) and cls.__module__ == module.__name__:
                    privates |= {
                        name
                        for name in vars(cls)
                        if name.startswith("_") and not name.startswith("__")
                    }
            source = path.read_text(encoding="utf-8")
            for match in re.finditer(r"self\.(_\w+)\s*=", source):
                privates.add(match.group(1))
        tests_dir = Path(__file__).resolve().parent
        for test_path in sorted(tests_dir.glob("test_*.py")):
            tree = ast.parse(test_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                receiver = node.value
                if isinstance(receiver, ast.Name) and receiver.id == "self":
                    continue
                if node.attr in privates:
                    self.fail(
                        f"{test_path.name}:{node.lineno} 穿透组件私有成员 "
                        f"{node.attr}（K-10：interface is the test surface）"
                    )

    def test_sqlite3_in_tests_only_in_documented_sites(self):
        """存储细节泄漏面（K-10 配套）：测试目录 "sqlite3" 仅存于
        文档化位——test_memory.py（M05 ProviderFormTest 载体形态文档化
        例外）、test_compose.py / test_host_integration.py（宿主侧状态
        库 fixture）、本文件（棘轮 marker 词表自身）。"""
        tests_dir = Path(__file__).resolve().parent
        allowed = {
            "test_memory.py",
            "test_compose.py",
            "test_host_integration.py",
            "test_architecture_invariants.py",
        }
        for test_path in sorted(tests_dir.glob("test_*.py")):
            if test_path.name in allowed:
                continue
            self.assertNotIn(
                "sqlite3",
                test_path.read_text(encoding="utf-8"),
                f"{test_path.name} 引用存储细节 sqlite3（K-10：测试不触碰存储细节）",
            )


if __name__ == "__main__":
    unittest.main()
