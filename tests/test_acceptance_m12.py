"""M12 Reality Acceptance 演练（《总路线》13 / system-context.md §3
deletion test）。

验收证据形态 = 实际执行（票 Risks：不以"理论上可移除"代替"实际验证"）：
各 deletion 场景在真实装配上实际运行（真实载体 + 真实 Memory Provider，
唯一构造位 = composition.compose，R-09），并逐项断言"个体状态完整"——
手段层可移除，个体仍在（架构硬要求）；个体状态 = 恰好 5 项清单
（spec-individual.md §4，清单之外的任何文件都不是个体状态）。

演练项（本模块，AC 1 / AC 2 执行证据）：
- 场景 1 host 通道缺失（host 未设定 → 装配结果 host 为 None）：个体回合
  环路照常运转，持久状态 5 项完整；
- 场景 2 全部 Model 替换：认知手段替换为另一实现（个体只依赖 interface
  两级调用面，U-5）——状态不变、行为随新手段；identity 载体无 model
  字段（K-11，恰好 7 支撑项键）；
- 场景 3 Memory Provider 替换（新 runtime：同载体目录新 Provider 实例）：
  全部持久记录可读，状态完整；
- 场景 4 外部工具连接（MCP）形态不存在：V1 对其无 Domain 定义
  （UNKNOWN，规则 11，未实现）——token 扫描证据 + 状态不受影响；
- 回合原子性崩溃演练（spec-individual.md §2）：进行中回合崩溃只丢失该
  回合——持久状态 5 项（identity / continuity / memory / capability /
  faculties）完整，进行中回合不入库。

Deletion 场景 5（历史 worker 形态消失）= M10 验证票交付物（全包零符号
形态 + token 锁定，见 tests/test_architecture_invariants.py 的 M10
棘轮）——本模块不重复扫描，证据引用于验收报告。
"""

import json
import tempfile
import unittest
from pathlib import Path

from dao_sheng import composition
from dao_sheng.continuity import append_continuity, load_continuity
from dao_sheng.faculties import FACULTY_ROOTS
from dao_sheng.individual import Individual, Turn
from dao_sheng.layout import IndividualFiles
from dao_sheng.memory import MemoryOrigin, RecallQuery
from tests.test_doctrine import EXPECTED

REPO_ROOT = Path(__file__).resolve().parents[1]
PRINCIPLES = REPO_ROOT / "docs" / "constitution" / "principles.md"

TURN_ONE = "演练回合一：一次完整观察"
TURN_TWO = "演练回合二：又一次完整观察"
TURN_CRASH = "崩溃演练回合：进行中"
CONTINUITY_CONTENT = "演练：一条 continuity 记录"
CAPABILITY_NAME = "演练能力"


def _carrier_text() -> str:
    """一份完整合法 identity 载体文档（fixture；内容值非设计层内容）。"""
    return json.dumps(
        {
            "name": "DaoSheng",
            "self_appellation": "",
            "voice": "",
            "visual_image": "",
            "behavioral_habits": [],
            "past_experiences": [],
            "continuous_memory": [],
        },
        ensure_ascii=False,
    )


class _ReplacementModel:
    """认知手段测试替身（"另一实现"）：个体只依赖 interface 两级调用面
    （U-5 / K-11：载体无 model 字段，模型部署属 L4）。"""

    def chat(self, messages):
        return "新手段行动"


class _CaptureModel:
    """投影捕获替身：记录个体经 interface 调用面传入的 system 消息
    （个体表征），供「道」节内容与顺序断言。"""

    def __init__(self):
        self.system_texts: list[str] = []

    def chat(self, messages):
        self.system_texts.append(messages[0][1])
        return "验证行动"


class _DrillBase(unittest.TestCase):
    """共享 fixture：真实装配（真实载体 + 真实 Memory Provider；model /
    host 未设定 = U-5 降级形态，INV-1：手段未装配 ≠ 个体故障）。

    清理顺序（Windows：临时目录删除要求存储连接已关）：addCleanup 按
    LIFO 执行——先登记 _tmp.cleanup，后登记 memory.close，则 close 先于
    目录删除执行。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.identity_text = _carrier_text()
        self.faculties_text = json.dumps(list(FACULTY_ROOTS), ensure_ascii=False)
        (self.root / "identity.json").write_text(self.identity_text, encoding="utf-8")
        (self.root / "faculties.json").write_text(self.faculties_text, encoding="utf-8")
        self.a = self._compose()
        self.addCleanup(self.a.memory.close)

    def _compose(self):
        """唯一构造位装配（R-09）：真实载体 + 真实 Memory Provider；
        model / host 未设定（U-5 降级形态）。"""
        return composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )

    def _establish_state(self, individual):
        """建立真实状态：2 个完整回合（memory）+ 1 条 continuity 记录 +
        1 个能力提案（5 项清单中 4 项有内容，5 项载体文件全部存在）。"""
        individual.act(Turn(TURN_ONE, MemoryOrigin.CANONICAL))
        individual.persist()
        individual.act(Turn(TURN_TWO, MemoryOrigin.CANONICAL))
        individual.persist()
        first = self.a.memory.recall(RecallQuery())[0]
        self._ref = first.reference
        self._ref_content = first.content
        append_continuity(
            self.a.individual_files.continuity,
            {"content": CONTINUITY_CONTENT, "reference": self._ref},
        )
        self.a.capability_manager.propose(CAPABILITY_NAME, self._ref)

    def _assert_state_complete(self, memory, expected_turns, absent=()):
        """个体持久状态 5 项完整（spec-individual.md §4）：identity /
        faculties 载体字节不变；continuity 记录完好；memory 恰为已完成
        回合数（absent 内容不得入库）；能力提案记录文件完好（严格 3 键，
        状态 = 目录位置）。"""
        files = IndividualFiles.layout(self.root)
        self.assertEqual(
            files.identity.read_text(encoding="utf-8"), self.identity_text
        )
        self.assertEqual(
            files.faculties.read_text(encoding="utf-8"), self.faculties_text
        )
        self.assertEqual(
            tuple(load_continuity(files.continuity).records),
            ({"content": CONTINUITY_CONTENT, "reference": self._ref},),
        )
        contents = {m.content for m in memory.recall(RecallQuery())}
        self.assertEqual(len(contents), expected_turns)
        for gone in absent:
            self.assertFalse(
                any(gone in c for c in contents), f"丢失回合不得入库：{gone}"
            )
        record = json.loads(
            (files.capabilities_dir / "proposed" / f"{CAPABILITY_NAME}.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            record,
            {
                "name": CAPABILITY_NAME,
                "content": self._ref_content,
                "source_reference": self._ref,
            },
        )


class M12DeletionScenarioHostTest(_DrillBase):
    """Deletion 场景 1（system-context.md §3）：host 通道缺失——个体仍在：
    回合环路照常运转，持久状态 5 项完整。"""

    def test_host_channel_absent_individual_still_turns(self):
        self.assertIsNone(
            self.a.host, "host 未设定 → 装配结果 host 为 None（U-5）"
        )
        self._establish_state(self.a.individual)
        # 新的完整回合：回合环路不依赖 host 通道
        self.a.individual.act(Turn("演练回合三：host 通道缺失后", MemoryOrigin.CANONICAL))
        self.a.individual.persist()
        self._assert_state_complete(self.a.memory, expected_turns=3)


class M12DeletionScenarioModelTest(_DrillBase):
    """Deletion 场景 2：全部 Model 替换——状态不变、行为随新手段；
    identity 载体无 model 字段（K-11）。"""

    def test_model_replaced_state_unchanged_behavior_follows(self):
        self._establish_state(self.a.individual)
        files = self.a.individual_files
        # K-11：identity 载体无 model 字段——恰好 7 支撑项键
        doc = json.loads(files.identity.read_text(encoding="utf-8"))
        self.assertEqual(
            set(doc),
            {
                "name",
                "self_appellation",
                "voice",
                "visual_image",
                "behavioral_habits",
                "past_experiences",
                "continuous_memory",
            },
        )
        # 替换 = 另一手段实现经同一 interface 面进入（个体只依赖调用面）
        replacement = Individual(
            doctrine=self.a.doctrine,
            identity=self.a.identity,
            faculties=self.a.faculties,
            continuity_file=files.continuity,
            memory=self.a.memory,
            model=_ReplacementModel(),
        )
        outcome = replacement.act(Turn("替换后回合", MemoryOrigin.CANONICAL))
        self.assertEqual(outcome.action, "新手段行动")
        replacement.persist()
        self._assert_state_complete(self.a.memory, expected_turns=3)


class M12DeletionScenarioProviderTest(_DrillBase):
    """Deletion 场景 3：Memory Provider 替换（新 runtime = 同载体目录新
    Provider 实例）——全部持久记录可读，状态完整。"""

    def test_provider_replaced_state_complete(self):
        self._establish_state(self.a.individual)
        self.a.memory.close()  # 旧 runtime 退出
        b = self._compose()  # 新 runtime：新 Provider 实例、同载体
        self.addCleanup(b.memory.close)
        self.assertIsNot(b.memory, self.a.memory, "新 runtime 须为新 Provider 实例")
        self._assert_state_complete(b.memory, expected_turns=2)
        # 个体仍在：新 runtime 上新回合
        b.individual.act(Turn("演练回合三：Provider 替换后", MemoryOrigin.CANONICAL))
        b.individual.persist()
        self._assert_state_complete(b.memory, expected_turns=3)


class M12DeletionScenarioMcpTest(_DrillBase):
    """Deletion 场景 4：外部工具连接（MCP）形态不存在——V1 对其无 Domain
    定义（UNKNOWN，规则 11，未实现），断开 = 空操作；token 扫描证据 +
    状态不受影响。本锁防止该形态被静默引入（引入 = 架构级，须先行
    ADR / 票）。"""

    def test_mcp_form_absent_state_unaffected(self):
        self._establish_state(self.a.individual)
        pkg = REPO_ROOT / "dao_sheng"
        for path in sorted(pkg.rglob("*.py")):
            self.assertNotIn(
                "mcp",
                path.read_text(encoding="utf-8").lower(),
                f"{path.name} 含外部工具连接形态 token（V1 无此形态）",
            )
        self._assert_state_complete(self.a.memory, expected_turns=2)


class M12CrashDrillTest(_DrillBase):
    """回合原子性崩溃演练（spec-individual.md §2）：进行中回合崩溃只
    丢失该回合——持久状态 5 项完整，进行中回合不入库（崩溃代价 = 该一回
    合，已持久状态不损坏）；新 runtime 无进行中回合（C-2：runtime 状态
    随进程丢失）。"""

    def test_crash_mid_turn_loses_only_that_turn(self):
        self._establish_state(self.a.individual)
        # 进行中回合（未持久化）→ 崩溃
        self.a.individual.act(Turn(TURN_CRASH, MemoryOrigin.CANONICAL))
        self.a.memory.close()  # 崩溃：进程消失，无清理
        # 新 runtime（新 Provider 实例，同载体）
        b = self._compose()
        self.addCleanup(b.memory.close)
        # 进行中回合丢失、完整回合完好
        self._assert_state_complete(
            b.memory, expected_turns=2, absent=(TURN_CRASH,)
        )
        # 新个体无进行中回合（C-2）
        with self.assertRaises(ValueError):
            b.individual.persist()
        outcome = b.individual.act(Turn("恢复后回合", MemoryOrigin.CANONICAL))
        self.assertEqual(outcome.turn_number, 1)
        b.individual.persist()
        self._assert_state_complete(
            b.memory, expected_turns=3, absent=(TURN_CRASH,)
        )


class M12DoctrineProjectionTest(_DrillBase):
    """Return to the Individual 阶段 A：六条核心原则经真实装配路径
    （principles.md → composition.compose → parse_doctrine → Individual
    投影 system 消息）逐字、按序进入个体表征。

    证据链缺口补齐：test_doctrine.py 证明解析 ↔ 权威源逐字按序；棘轮证明
    代码不内原则文本、只在装配点注入；test_individual.py 证明投影形态
    （合成 doctrine）。本测试证明真实装配产出的 Doctrine 在个体表征中
    逐字按序呈现——不是"源码里存在字符串"，而是个体实际传给认知手段的
    system 消息内容。"""

    def test_six_principles_enter_individual_projection_verbatim_in_order(self):
        capture = _CaptureModel()
        individual = Individual(
            doctrine=self.a.doctrine,
            identity=self.a.identity,
            faculties=self.a.faculties,
            continuity_file=self.a.individual_files.continuity,
            memory=self.a.memory,
            model=capture,
        )
        individual.act(Turn("阶段 A 验证回合：个体表征", MemoryOrigin.CANONICAL))
        projection = capture.system_texts[0]
        dao_section = projection.split("道：\n", 1)[1].split("\n\n", 1)[0]
        self.assertEqual(
            dao_section.splitlines(),
            [f"{i}. {name}：{text}" for i, (name, text) in enumerate(EXPECTED, start=1)],
        )


if __name__ == "__main__":
    unittest.main()
