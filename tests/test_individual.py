"""Individual 顶层聚合 — M04（spec-individual.md 全对象）。

Seam：`act(turn: Turn) -> TurnOutcome` / `persist() -> str`（R-01：V0 三入口
收敛为一；K-10：interface = test surface——全部测试只经此面，不穿透内部）。

- 两阶段回合（决定 ⑬）：act 产出行动并暂存（runtime 状态）；persist = 唯一
  提交点（单条 Memory 记录，原子）；生命周期严格交替 act → persist。
- 回合 = 原子单位（§2）：无回合内 checkpoint；崩溃代价 = 一个进行中回合，
  持久状态 = 上一完整回合（重启语义测试用真 Memory Provider 同目录新实例）。
- 三维语义层（Q2）：回合经历记录恒 status=OBSERVED / confidence=CONFIRMED；
  origin 由回合输入携带（Turn.memory_origin，决定 ⑭），不推断。
- 手段失败 → 降级回合（决定 ⑯）：model 未装配或调用不可用 → 行动为 None，
  经历仍记录，act 不抛异常（INV-1）。
- 投影纪律（§5 / R-12 / INV-7）：投影 = 四载体 + Doctrine 的装配产物；
  不得引入宿主 / 模型 / 存储细节；投影内容不得回流为经历记录。
- continuity 读通道（决定 ⑱）：每回合按需读取，不携带装配时快照；
  本模块不追加 continuity（唯一调用方 = 成长管线，M07）。
"""

import dataclasses
import tempfile
import unittest
from pathlib import Path

from dao_sheng.continuity import append_continuity
from dao_sheng.doctrine import Doctrine, Principle
from dao_sheng.faculties import FACULTY_ROOTS, Faculties
from dao_sheng.identity import Identity
from dao_sheng.individual import Individual, Turn, TurnOutcome
from dao_sheng.memory import (
    Memory,
    MemoryConfidence,
    MemoryOrigin,
    MemoryStatus,
    RecallQuery,
)
from dao_sheng.memory_sqlite import SqliteMemoryProvider
from dao_sheng.model import ModelUnavailable


class FakeMemory:
    """MemoryStore 测试替身：记录 remember 入参（三维显式断言依据）；
    recall 返回最近记录（契约上限 ≤32）。"""

    def __init__(self):
        self.stored: list[Memory] = []
        self.remember_calls: list[dict] = []

    def remember(self, *, content, memory_origin, memory_status, memory_confidence):
        self.remember_calls.append(
            {
                "content": content,
                "memory_origin": memory_origin,
                "memory_status": memory_status,
                "memory_confidence": memory_confidence,
            }
        )
        reference = f"mem-{len(self.stored) + 1}"
        self.stored.append(
            Memory(
                reference=reference,
                content=content,
                memory_origin=memory_origin,
                memory_status=memory_status,
                memory_confidence=memory_confidence,
            )
        )
        return reference

    def recall(self, query):
        assert isinstance(query, RecallQuery)
        return list(self.stored[-32:])

    def get(self, reference):
        for m in self.stored:
            if m.reference == reference:
                return m
        raise ValueError(f"记忆缺失：{reference}")

    def correct_memory(self, target, correction):
        raise AssertionError("本票测试不使用 correct_memory")

    def register_reference(self, source, target):
        raise AssertionError("本票测试不使用 register_reference")

    def resolve_reference(self, reference):
        raise AssertionError("本票测试不使用 resolve_reference")


class FakeModel:
    """Model 测试替身：记录 chat 入参；responder 可编排回复 / 故障。"""

    def __init__(self, responder=None):
        self.messages_log: list = []
        self._responder = responder or (lambda messages: "答：好")

    def chat(self, messages):
        self.messages_log.append([tuple(m) for m in messages])
        return self._responder(messages)

    def complete(self, prompt):
        raise AssertionError("回合骨架只使用 chat 调用")


def make_identity(**overrides) -> Identity:
    doc = dict(
        name="道生",
        self_appellation="小生",
        voice="沉静简练",
        visual_image="白衫老者",
        behavioral_habits=("先答后核",),
        past_experiences=("曾解一难问",),
        continuous_memory=("持续居于工作间",),
    )
    doc.update(overrides)
    return Identity(**doc)


def make_doctrine() -> Doctrine:
    return Doctrine(principles=(Principle("测试原理甲", "测试原理甲正文：当行则行。"),))


def make_faculties() -> Faculties:
    return Faculties(roots=FACULTY_ROOTS)


class TurnContractTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def test_turn_and_turn_outcome_frozen(self):
        """输入 / 结果均为不可变值对象（回合机制不保留可变输入引用）。"""
        turn = Turn("一次观察", MemoryOrigin.EXTERNAL)
        outcome = TurnOutcome(turn_number=1, action="答")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            turn.content = "改写"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            outcome.action = "改写"

    def test_turn_rejects_blank_content(self):
        """回合输入空 / 空白 = 无内容回合，无意义 → fail-loud（不静默吞掉）。"""
        with self.assertRaises(ValueError):
            Turn("", MemoryOrigin.EXTERNAL)
        with self.assertRaises(ValueError):
            Turn("   \n  ", MemoryOrigin.EXTERNAL)

    def test_individual_constructor_all_injected_no_defaults(self):
        """R-09：全部依赖注入、无默认值——构造只发生在装配点（R-09 结构
        棘轮另固化构造位）。"""
        self.assertEqual(
            [f.name for f in dataclasses.fields(Turn)],
            ["content", "memory_origin"],
        )
        self.assertEqual(
            [f.name for f in dataclasses.fields(TurnOutcome)],
            ["turn_number", "action"],
        )
        import inspect

        sig = inspect.signature(Individual.__init__)
        self.assertEqual(
            list(sig.parameters),
            ["self", "doctrine", "identity", "faculties", "continuity_file", "memory", "model"],
        )
        for p in sig.parameters.values():
            if p.name == "self":
                continue
            self.assertEqual(p.kind, p.KEYWORD_ONLY, f"{p.name} 必须 keyword-only")
            self.assertIs(p.default, inspect.Parameter.empty, f"{p.name} 不得有默认值")


class TurnLifecycleTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.memory = FakeMemory()
        self.model = FakeModel()
        self.ind = Individual(
            doctrine=make_doctrine(),
            identity=make_identity(),
            faculties=make_faculties(),
            continuity_file=self.tmp / "continuity.jsonl",
            memory=self.memory,
            model=self.model,
        )

    def test_persist_without_turn_fails_loud(self):
        """无进行中回合可提交 → 显式失败（严格交替，fail-loud）。"""
        with self.assertRaises(ValueError):
            self.ind.persist()

    def test_second_act_before_persist_fails_loud(self):
        """已有未提交回合时再次 act → 显式失败（单回合原子；先 persist）。"""
        self.ind.act(Turn("第一回合", MemoryOrigin.CANONICAL))
        with self.assertRaises(ValueError):
            self.ind.act(Turn("第二回合", MemoryOrigin.CANONICAL))

    def test_act_persist_alternation_progresses(self):
        """act → persist 交替推进：turn 计数递增；每完整回合一条 Memory
        记录（决定 ⑬）。"""
        o1 = self.ind.act(Turn("第一回合", MemoryOrigin.CANONICAL))
        r1 = self.ind.persist()
        o2 = self.ind.act(Turn("第二回合", MemoryOrigin.CANONICAL))
        r2 = self.ind.persist()
        self.assertEqual(o1.turn_number, 1)
        self.assertEqual(o2.turn_number, 2)
        self.assertEqual(self.memory.recall(RecallQuery()), [
            self.memory.stored[0],
            self.memory.stored[1],
        ])
        self.assertNotEqual(r1, r2)


class ExperienceRecordTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.memory = FakeMemory()
        self.model = FakeModel()
        self.ind = Individual(
            doctrine=make_doctrine(),
            identity=make_identity(),
            faculties=make_faculties(),
            continuity_file=self.tmp / "continuity.jsonl",
            memory=self.memory,
            model=self.model,
        )

    def test_persist_writes_single_record_with_reference(self):
        """persist 唯一提交点：恰好一条 Memory 记录；reference = 该记录
        句柄（M09 幂等重导入去重依据）。"""
        self.ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        reference = self.ind.persist()
        self.assertEqual(len(self.memory.stored), 1)
        self.assertEqual(self.memory.get(reference).reference, reference)

    def test_record_dims_explicit_no_inference(self):
        """三维显式（Q2）：origin 由回合输入透传（不推断）；回合经历记录
        恒 OBSERVED / CONFIRMED（Core 规则，固定不参数化）。"""
        self.ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        self.ind.persist()
        call = self.memory.remember_calls[0]
        self.assertIs(call["memory_origin"], MemoryOrigin.EXTERNAL)
        self.assertIs(call["memory_status"], MemoryStatus.OBSERVED)
        self.assertIs(call["memory_confidence"], MemoryConfidence.CONFIRMED)

    def test_record_content_exact_form(self):
        """记录内容 = 经历 / 行动 两行（决定 ⑮）：不含 turn 计数
        （C-2 runtime，不持久）、不含投影文本（INV-7）。"""
        self.ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        self.ind.persist()
        self.assertEqual(
            self.memory.stored[0].content, "经历：一次观察\n行动：答：好"
        )

    def test_degraded_record_marks_no_action(self):
        """降级回合（决定 ⑯）：手段故障 → 行动缺失 = 记录行动为"无"
        （经历仍记录）。"""
        def flaky(messages):
            raise ModelUnavailable("不可用")

        degraded = Individual(
            doctrine=make_doctrine(),
            identity=make_identity(),
            faculties=make_faculties(),
            continuity_file=self.tmp / "continuity.jsonl",
            memory=self.memory,
            model=FakeModel(responder=flaky),
        )
        degraded.act(Turn("手段故障回合", MemoryOrigin.CANONICAL))
        degraded.persist()
        self.assertEqual(
            self.memory.stored[0].content, "经历：手段故障回合\n行动：无"
        )


class DegradedTurnTest(unittest.TestCase):
    def _individual(self, model):
        tmp = Path(self._tmp.name)
        return Individual(
            doctrine=make_doctrine(),
            identity=make_identity(),
            faculties=make_faculties(),
            continuity_file=tmp / "continuity.jsonl",
            memory=FakeMemory(),
            model=model,
        )

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._tmp = tmp

    def test_model_unset_is_degraded_turn(self):
        """model 未装配（U-5）→ 降级回合：action None，act 不抛异常。"""
        ind = self._individual(model=None)
        outcome = ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        self.assertIsNone(outcome.action)
        ind.persist()

    def test_model_unavailable_is_degraded_turn(self):
        """手段调用不可用（ModelUnavailable）→ 降级回合：手段故障 ≠ 个体
        故障（INV-1），act 不抛异常，经历仍记录。"""

        def flaky(messages):
            raise ModelUnavailable("不可用")

        ind = self._individual(model=FakeModel(responder=flaky))
        outcome = ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        self.assertIsNone(outcome.action)
        ind.persist()


class ProjectionTest(unittest.TestCase):
    """投影装配与纪律（决定 ⑰ / §5 / R-12 / INV-7）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.memory = FakeMemory()
        self.model = FakeModel()
        self.ind = Individual(
            doctrine=make_doctrine(),
            identity=make_identity(),
            faculties=make_faculties(),
            continuity_file=self.tmp / "continuity.jsonl",
            memory=self.memory,
            model=self.model,
        )

    def test_messages_shape_system_projection_plus_user_turn(self):
        """messages = [(system, 投影), (user, 回合内容)]——上下文组织是
        Core 的事（决定 ⑰）；adapter 不预设。"""
        self.ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        (messages,) = self.model.messages_log
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0][0], "system")
        self.assertEqual(messages[1], ("user", "一次观察"))
        self.assertTrue(messages[0][1])

    def test_projection_contains_four_carriers_and_doctrine(self):
        """投影 = 身份 / 道 / 行为倾向 / 经历 / 记忆 的装配：前一完整回合
        的记录与 continuity 记录进入后续回合投影。"""
        self.ind.act(Turn("第一回合：到达工作间", MemoryOrigin.CANONICAL))
        self.ind.persist()
        append_continuity(self.tmp / "continuity.jsonl", {"event": "早前经历事件"})
        self.ind.act(Turn("第二回合", MemoryOrigin.CANONICAL))
        projection = self.model.messages_log[1][0][1]
        # 身份载体
        self.assertIn("道生", projection)
        self.assertIn("小生", projection)
        # 道（Doctrine 注入）
        self.assertIn("测试原理甲正文：当行则行。", projection)
        # 行为倾向（Faculties 根）
        self.assertIn("intent", projection)
        # 经历（continuity 按需读，决定 ⑱）
        self.assertIn("早前经历事件", projection)
        # 记忆（上一完整回合的记录）
        self.assertIn("经历：第一回合：到达工作间", projection)

    def test_projection_omits_empty_sections(self):
        """空载体的节省略（不输出空节占位）——初始态（无 continuity /
        无记忆）投影只有身份 / 道 / 行为倾向。"""
        self.ind.act(Turn("初始态回合", MemoryOrigin.CANONICAL))
        projection = self.model.messages_log[0][0][1]
        self.assertIn("身份：", projection)
        self.assertIn("道：", projection)
        self.assertNotIn("经历：\n", projection)
        self.assertNotIn("记忆：\n", projection)

    def test_projection_has_no_host_model_or_storage_detail(self):
        """投影纪律（R-12 / INV-7）：宿主名 / 模型名 / 存储细节 / 存储
        句柄不进投影文本。"""
        self.ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        self.ind.persist()
        self.ind.act(Turn("第二回合", MemoryOrigin.CANONICAL))
        projection = self.model.messages_log[1][0][1]
        for leak in ("localhost", "http://", "mem-"):
            self.assertNotIn(leak, projection)

    def test_record_excludes_projection_content(self):
        """INV-7：投影内容不得回流为经历——记录只含回合输入 + 行动，
        不含身份 / 道 / 倾向 / 记忆内容。"""
        self.ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        self.ind.persist()
        content = self.memory.stored[0].content
        self.assertNotIn("测试原理甲正文", content)
        self.assertNotIn("小生", content)
        self.assertNotIn("持续居于工作间", content)
        self.assertNotIn("intent", content)
        self.assertIn("经历：一次观察", content)

    def test_continuity_truncated_to_recent_32(self):
        """投影裁剪：continuity 只取最近 32 条（决定 ⑰；可裁剪，M-05）。"""
        path = self.tmp / "continuity.jsonl"
        for i in range(1, 41):
            append_continuity(path, {"event": f"rec-{i}"})
        self.ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        projection = self.model.messages_log[0][0][1]
        self.assertIn('"event": "rec-40"', projection)
        self.assertIn('"event": "rec-9"', projection)
        self.assertNotIn('"event": "rec-8"', projection)
        self.assertNotIn('"event": "rec-1"', projection)


class ContinuityReadChannelTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.memory = FakeMemory()
        self.model = FakeModel()
        self.ind = Individual(
            doctrine=make_doctrine(),
            identity=make_identity(),
            faculties=make_faculties(),
            continuity_file=self.tmp / "continuity.jsonl",
            memory=self.memory,
            model=self.model,
        )

    def test_continuity_loaded_per_turn_not_snapshot(self):
        """决定 ⑱：每回合按需读取，不携带装配时快照——act 之后追加的
        记录进入后续回合投影。"""
        self.ind.act(Turn("第一回合", MemoryOrigin.CANONICAL))
        self.ind.persist()
        append_continuity(self.tmp / "continuity.jsonl", {"event": "后发生事件"})
        self.ind.act(Turn("第二回合", MemoryOrigin.CANONICAL))
        projection = self.model.messages_log[1][0][1]
        self.assertIn("后发生事件", projection)

    def test_individual_does_not_append_continuity(self):
        """data-ownership：continuity 唯一追加调用方 = 成长管线（M07）——
        本模块只读；act + persist 全回合后文件仍不存在。"""
        self.ind.act(Turn("一次观察", MemoryOrigin.EXTERNAL))
        self.ind.persist()
        self.assertFalse((self.tmp / "continuity.jsonl").exists())


class RestartEventsTest(unittest.TestCase):
    """重启语义三事件（spec-individual.md §3，逐事件测试）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _make(self, root, memory, model):
        return Individual(
            doctrine=make_doctrine(),
            identity=make_identity(),
            faculties=make_faculties(),
            continuity_file=root / "continuity.jsonl",
            memory=memory,
            model=model,
        )

    def test_hermes_restart_is_noop_for_individual(self):
        """事件 1：host 进程重启 → 个体完全不受影响——host 不存在于
        个体依赖面（结构性由宿主值泄漏棘轮守卫）；行为面：重启模拟为
        no-op 后下一回合照常推进。"""
        tmp = Path(self._tmp.name)
        memory = FakeMemory()
        ind = self._make(tmp, memory, FakeModel())
        o1 = ind.act(Turn("第一回合", MemoryOrigin.CANONICAL))
        ind.persist()
        # host 重启 = 对个体 no-op（无重启调用面存在）
        o2 = ind.act(Turn("第二回合", MemoryOrigin.CANONICAL))
        self.assertEqual(o1.turn_number, 1)
        self.assertEqual(o2.turn_number, 2)
        ind.persist()
        self.assertEqual(len(memory.stored), 2)

    def test_runtime_restart_keeps_persistent_loses_runtime(self):
        """事件 2：Runtime 重启 → persistent 保留、runtime 丢失。
        用真 Memory Provider 同目录新实例（重启 = 新 Runtime 进程）：
        崩溃时进行中回合被丢弃（未 persist），持久状态 = 上一完整回合；
        turn 计数（C-2）不持久——新实例从 1 起。"""
        tmp = Path(self._tmp.name)
        memory_a = SqliteMemoryProvider(tmp / "memory")
        self.addCleanup(memory_a.close)
        a = self._make(tmp, memory_a, None)  # model 未装配 → 降级回合
        a.act(Turn("完整回合：一次观察", MemoryOrigin.EXTERNAL))
        a.persist()
        a.act(Turn("进行中回合（崩溃前未提交）", MemoryOrigin.EXTERNAL))
        # —— Runtime 崩溃 / 重启 ——
        memory_b = SqliteMemoryProvider(tmp / "memory")
        self.addCleanup(memory_b.close)
        b = self._make(tmp, memory_b, None)
        # 持久状态 = 上一完整回合
        records = memory_b.recall(RecallQuery())
        self.assertEqual(len(records), 1)
        self.assertIn("完整回合：一次观察", records[0].content)
        self.assertNotIn("进行中回合", records[0].content)
        # runtime 丢失：无进行中回合可提交；turn 计数从 1 起
        with self.assertRaises(ValueError):
            b.persist()
        outcome = b.act(Turn("重启后回合", MemoryOrigin.EXTERNAL))
        self.assertEqual(outcome.turn_number, 1)

    def test_model_restart_degrades_then_recovers(self):
        """事件 3：Model 重启 → 个体不受影响（INV-1）：重启窗口内该回合
        降级（行动缺失，经历仍记录），窗口后行动照常——个体状态无损伤。"""
        tmp = Path(self._tmp.name)
        calls = {"n": 0}

        def responder(messages):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ModelUnavailable("重启窗口")
            return "答：窗口后"

        ind = self._make(tmp, FakeMemory(), FakeModel(responder=responder))
        o1 = ind.act(Turn("窗口内回合", MemoryOrigin.CANONICAL))
        self.assertIsNone(o1.action)
        ind.persist()
        o2 = ind.act(Turn("窗口后回合", MemoryOrigin.CANONICAL))
        self.assertEqual(o2.action, "答：窗口后")
        ind.persist()


if __name__ == "__main__":
    unittest.main()
