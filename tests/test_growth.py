"""Growth 成长管线 — M07（spec-growth.md 全对象 + data-ownership.md §1）。

Seam（K-10：interface = test surface）：import_experience（经验回流导入，
管线侧幂等）/ digest / extract / reflect / verify_insight——全部 Memory
操作经注入 MemoryStore 的 6 方法契约（R-08 A-1）；continuity 记录只经
注入的 append 通道（唯一调用方 = 成长管线，M03 决定 ⑤）。

- 三维规则（决定 ㉓）：导入 = candidate.origin / OBSERVED / CONFIRMED；
  阶段产出 = DERIVED / REPORTED / UNCERTAIN；verify_insight 修正记录 =
  DERIVED / VERIFIED / CONFIRMED。
- 降级（决定 ㉕ / INV-1）：model 未装配 / 不可用 / 输出为空 → None，
  不写、不追加、不抛异常。
- 认知调用面（D-054）：四个认知阶段全部经 chat(messages) 会话形态
  （M06 决定 ⑨ / ADR 0008 两级调用面 seam 内的用法选择），complete
  不被使用。
- verify_insight 输出归位（ADR 0006 / 决定 ㉔）：insight → Memory
  （correct_memory 形态：原记录不变，INV-8）；continuity 记录 →
  Continuity 单一载体（append-only；schema = {"content", "reference"}）。
- AC 8（INV-4 可测形态，端到端骨架）：经历 → 消化 → 提取 → 记忆 →
  复用（个体投影）→ 后续回合行为变化；现实验收在 M12。
- 棘轮面（表面 / 参数面 / D-06 / A-7 / 构造位）见
  tests/test_architecture_invariants.py::M07GrowthRatchetTest。
"""

import functools
import shutil
import tempfile
import unittest
from pathlib import Path

from dao_sheng.continuity import append_continuity, load_continuity
from dao_sheng.doctrine import Doctrine, Principle
from dao_sheng.faculties import FACULTY_ROOTS, Faculties
from dao_sheng.growth import ExperienceCandidate, Growth
from dao_sheng.identity import Identity
from dao_sheng.individual import Individual, Turn
from dao_sheng.memory import (
    Correction,
    Memory,
    MemoryConfidence,
    MemoryOrigin,
    MemoryStatus,
    RecallQuery,
)
from dao_sheng.memory_sqlite import SqliteMemoryProvider
from dao_sheng.model import ModelUnavailable


def _candidate(content: str, key: str, origin=MemoryOrigin.EXTERNAL):
    return ExperienceCandidate(
        content=content, memory_origin=origin, idempotency_key=key
    )


class FakeMemory:
    """MemoryStore 测试替身（6 方法契约）：内存记录，reference = mem-N；
    correct_memory = 追加修正记录并返回其 reference（原记录不变，INV-8）。"""

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
        raise ValueError(f"memory 缺失：{reference}")

    def correct_memory(self, target, correction):
        if not any(m.reference == target for m in self.stored):
            raise ValueError(f"目标记录缺失：{target}")
        reference = f"mem-{len(self.stored) + 1}"
        self.stored.append(
            Memory(
                reference=reference,
                content=correction.content,
                memory_origin=correction.memory_origin,
                memory_status=correction.memory_status,
                memory_confidence=correction.memory_confidence,
            )
        )
        return reference

    def register_reference(self, source, target):
        raise AssertionError("本票测试不使用 register_reference")

    def resolve_reference(self, reference):
        raise AssertionError("本票测试不使用 resolve_reference")


class FakeReflectionModel:
    """认知手段测试替身（M06 契约面，D-054）：chat → 编排输出 / 故障，
    记录每次调用的 messages；complete → fail-loud——Growth 认知阶段改走
    chat 路径后，任何阶段误用 complete 都会使全部管线测试失败。"""

    def __init__(self, output: str | None = "阶段输出", unavailable: bool = False):
        self.output = output
        self.unavailable = unavailable
        self.messages: list[tuple[tuple[str, str], ...]] = []

    def chat(self, messages):
        self.messages.append(tuple(messages))
        if self.unavailable:
            raise ModelUnavailable("手段不可用")
        return self.output

    def complete(self, prompt):
        raise AssertionError("Growth 认知阶段不得走 complete（D-054：改走 chat）")


class AppendLog:
    """continuity append 通道测试替身：记录每条追加（函数值注入位）。"""

    def __init__(self):
        self.records: list[dict] = []

    def __call__(self, record):
        self.records.append(record)


def make_growth(memory, append, model):
    """按决定 ㉒ 装配 Growth：8 项依赖全部构造注入（R-09，零 import）。"""
    return Growth(
        memory=memory,
        append_continuity=append,
        reflection_model=model,
        origin=MemoryOrigin,
        status=MemoryStatus,
        confidence=MemoryConfidence,
        correction=Correction,
        unavailable=ModelUnavailable,
    )


class ExperienceCandidateTest(unittest.TestCase):
    """决定 ㉓ / ㉑ 输入面：中性候选 fail-loud（无宿主名；U-5 / ADR 0002）。"""

    def test_empty_content_fails_loud(self):
        with self.assertRaises(ValueError):
            _candidate("   ", "k1")

    def test_empty_idempotency_key_fails_loud(self):
        with self.assertRaises(ValueError):
            _candidate("一次经历", "  ")

    def test_valid_candidate_holds_fields(self):
        c = _candidate("一次经历", "k1")
        self.assertEqual(c.content, "一次经历")
        self.assertIs(c.memory_origin, MemoryOrigin.EXTERNAL)
        self.assertEqual(c.idempotency_key, "k1")


class ImportExperienceTest(unittest.TestCase):
    """经验回流导入（双通道模型的允许通道，data-ownership §1）：
    管线侧幂等（决定 ㉑）+ 三维规则（决定 ㉓）。"""

    def setUp(self):
        self.memory = FakeMemory()
        self.append = AppendLog()
        self.growth = make_growth(self.memory, self.append, None)

    def test_import_writes_memory_with_core_rule_dims(self):
        refs = self.growth.import_experience([_candidate("一次经历", "k1")])
        self.assertEqual(len(refs), 1)
        record = self.memory.get(refs[0])
        self.assertEqual(record.content, "一次经历")
        self.assertIs(record.memory_origin, MemoryOrigin.EXTERNAL)
        self.assertIs(record.memory_status, MemoryStatus.OBSERVED)
        self.assertIs(record.memory_confidence, MemoryConfidence.CONFIRMED)

    def test_import_idempotent_same_key(self):
        first = self.growth.import_experience(
            [_candidate("一次经历", "k1"), _candidate("另一经历", "k2")]
        )
        second = self.growth.import_experience(
            [_candidate("一次经历", "k1"), _candidate("另一经历", "k2")]
        )
        self.assertEqual(first, second, "同 key 重导入须返回原 reference")
        self.assertEqual(len(self.memory.stored), 2, "同 key 重导入不得产生新记忆")
        self.assertEqual(len(self.memory.remember_calls), 2)

    def test_import_distinct_keys_distinct_records(self):
        a = self.growth.import_experience([_candidate("一次经历", "k1")])
        b = self.growth.import_experience([_candidate("一次经历", "k2")])
        self.assertNotEqual(a[0], b[0])

    def test_import_rejects_foreign_origin_type(self):
        with self.assertRaises(ValueError):
            self.growth.import_experience(
                [
                    ExperienceCandidate(
                        content="一次经历",
                        memory_origin="external",
                        idempotency_key="k1",
                    )
                ]
            )

    def test_import_empty_batch_returns_empty(self):
        self.assertEqual(self.growth.import_experience([]), ())
        self.assertEqual(self.memory.stored, [])


class DigestExtractTest(unittest.TestCase):
    """digest / extract 阶段（决定 ㉓ / ㉕）：阶段产出 = 派生记忆；
    降级 = None（不写、不抛）；reference 缺失 fail-loud（M05 get 契约）。"""

    def _imported(self, memory, append, model):
        growth = make_growth(memory, append, model)
        return growth, growth.import_experience([_candidate("一次经历", "k1")])[0]

    def test_digest_writes_derived_memory(self):
        memory, append = FakeMemory(), AppendLog()
        model = FakeReflectionModel(output="消化后的记忆")
        growth, ref = self._imported(memory, append, model)
        out = growth.digest(ref)
        self.assertEqual(out, "mem-2")
        record = memory.get(out)
        self.assertEqual(record.content, "消化后的记忆")
        self.assertIs(record.memory_origin, MemoryOrigin.DERIVED)
        self.assertIs(record.memory_status, MemoryStatus.REPORTED)
        self.assertIs(record.memory_confidence, MemoryConfidence.UNCERTAIN)
        # 认知调用为会话形态（D-054）：单条 user 消息 = 指令 + 源内容（决定 ㉕）
        self.assertEqual(len(model.messages), 1, "digest 恰一次 chat 调用")
        ((role, content),) = model.messages[0]
        self.assertEqual(role, "user")
        self.assertIn("一次经历", content)
        self.assertNotIn("消化", content, "digest 消息不得含阶段名之外的输出")
        # digest 阶段不追加 continuity（只有 reflect / verify_insight 追加）
        self.assertEqual(append.records, [])

    def test_extract_writes_insight_memory(self):
        memory, append = FakeMemory(), AppendLog()
        model = FakeReflectionModel(output="可验证的 insight")
        growth, ref = self._imported(memory, append, model)
        out = growth.extract(ref)
        self.assertEqual(out, "mem-2")
        record = memory.get(out)
        self.assertEqual(record.content, "可验证的 insight")
        self.assertIs(record.memory_origin, MemoryOrigin.DERIVED)
        self.assertIs(record.memory_status, MemoryStatus.REPORTED)
        self.assertIs(record.memory_confidence, MemoryConfidence.UNCERTAIN)
        self.assertEqual(append.records, [])

    def test_digest_model_unset_degraded(self):
        memory, append = FakeMemory(), AppendLog()
        growth, ref = self._imported(memory, append, None)
        self.assertIsNone(growth.digest(ref))
        self.assertEqual(len(memory.stored), 1, "降级不得写记忆")
        self.assertEqual(append.records, [])

    def test_digest_model_unavailable_degraded(self):
        memory, append = FakeMemory(), AppendLog()
        growth, ref = self._imported(memory, append, FakeReflectionModel(unavailable=True))
        self.assertIsNone(growth.digest(ref))
        self.assertEqual(len(memory.stored), 1)
        self.assertEqual(append.records, [])

    def test_digest_empty_output_degraded(self):
        memory, append = FakeMemory(), AppendLog()
        growth, ref = self._imported(memory, append, FakeReflectionModel(output="   "))
        self.assertIsNone(growth.digest(ref))
        self.assertEqual(len(memory.stored), 1)

    def test_extract_model_unset_degraded(self):
        memory, append = FakeMemory(), AppendLog()
        growth, ref = self._imported(memory, append, None)
        self.assertIsNone(growth.extract(ref))
        self.assertEqual(len(memory.stored), 1)

    def test_digest_missing_reference_fails_loud(self):
        memory, append = FakeMemory(), AppendLog()
        growth = make_growth(memory, append, FakeReflectionModel())
        with self.assertRaises(ValueError):
            growth.digest("mem-99")

    def test_extract_missing_reference_fails_loud(self):
        memory, append = FakeMemory(), AppendLog()
        growth = make_growth(memory, append, FakeReflectionModel())
        with self.assertRaises(ValueError):
            growth.extract("mem-99")


class CognitiveChatPathTest(unittest.TestCase):
    """D-054 最小改动证明：四个认知阶段（digest / extract / reflect /
    verify_insight）全部经现有 Model Protocol 的 chat(messages) 调用面
    （M06 决定 ⑨ / ADR 0008），每阶段恰一次、单条 user 消息 = 指令 +
    源内容；complete 不被使用（FakeReflectionModel.complete fail-loud，
    误用即测试失败）。空输出 / 无效输出降级语义不变（决定 ㉕，见各阶段
    降级测试）。"""

    def test_all_cognitive_stages_use_chat_once_each(self):
        memory, append = FakeMemory(), AppendLog()
        model = FakeReflectionModel(output="阶段输出")
        growth = make_growth(memory, append, model)
        ref = growth.import_experience([_candidate("一次经历", "k1")])[0]
        digest_ref = growth.digest(ref)
        insight_ref = growth.extract(ref)
        reflect_ref = growth.reflect(ref)
        growth.verify_insight(insight_ref)
        self.assertEqual(len(model.messages), 4, "四个认知阶段各恰一次 chat 调用")
        # 各阶段消息携带其源记录内容：digest/extract/reflect 源 = 经历
        # （"一次经历"）；verify_insight 源 = extract 的 insight（"阶段输出"）
        expected_sources = ["一次经历", "一次经历", "一次经历", "阶段输出"]
        for call, source in zip(model.messages, expected_sources):
            self.assertEqual(len(call), 1, "会话形态 = 单条消息")
            role, content = call[0]
            self.assertEqual(role, "user")
            self.assertIn(source, content, "chat 消息必须携带源记录内容")

    def test_empty_chat_output_degrades_like_complete_semantics(self):
        """决定 ㉕ 语义保持：chat 返回空 / 全空白 → 阶段降级 None——
        不写记忆、不追加 continuity、不抛异常（与改走 chat 前一致）。"""
        for output in ("", "   ", None):
            memory, append = FakeMemory(), AppendLog()
            growth = make_growth(memory, append, FakeReflectionModel(output=output))
            ref = growth.import_experience([_candidate("一次经历", "k1")])[0]
            self.assertIsNone(growth.digest(ref))
            self.assertIsNone(growth.extract(ref))
            self.assertIsNone(growth.reflect(ref))
            self.assertIsNone(growth.verify_insight(ref))
            self.assertEqual(len(memory.stored), 1, "降级不得写记忆")
            self.assertEqual(append.records, [], "降级不得追加 continuity")


class ReflectTest(unittest.TestCase):
    """reflect 阶段（决定 ㉔ / ㉖）：记忆记录 + continuity 记录
    （schema = {"content", "reference"}，经注入通道追加）；降级 →
    不写不追加；能力提案 = 记忆记录形态（content 承载语义）。"""

    def test_reflect_writes_memory_and_continuity_record(self):
        memory, append = FakeMemory(), AppendLog()
        model = FakeReflectionModel(output="reflection 结论")
        growth = make_growth(memory, append, model)
        ref = growth.import_experience([_candidate("一条 insight", "k1")])[0]
        out = growth.reflect(ref)
        self.assertEqual(out, "mem-2")
        record = memory.get(out)
        self.assertEqual(record.content, "reflection 结论")
        self.assertIs(record.memory_origin, MemoryOrigin.DERIVED)
        self.assertIs(record.memory_status, MemoryStatus.REPORTED)
        self.assertIs(record.memory_confidence, MemoryConfidence.UNCERTAIN)
        # continuity 记录恰一条，schema 恰 2 键（决定 ㉔：无判别字段）
        self.assertEqual(len(append.records), 1)
        rec = append.records[0]
        self.assertEqual(set(rec), {"content", "reference"})
        self.assertEqual(rec, {"content": "reflection 结论", "reference": out})

    def test_reflect_degraded_no_write_no_append(self):
        for model in (None, FakeReflectionModel(unavailable=True), FakeReflectionModel(output="")):
            memory, append = FakeMemory(), AppendLog()
            growth = make_growth(memory, append, model)
            ref = growth.import_experience([_candidate("一条 insight", "k1")])[0]
            self.assertIsNone(growth.reflect(ref))
            self.assertEqual(len(memory.stored), 1, "降级不得写记忆")
            self.assertEqual(append.records, [], "降级不得追加 continuity")

    def test_reflect_missing_reference_fails_loud(self):
        memory, append = FakeMemory(), AppendLog()
        growth = make_growth(memory, append, FakeReflectionModel())
        with self.assertRaises(ValueError):
            growth.reflect("mem-99")
        self.assertEqual(append.records, [])


class VerifyInsightTest(unittest.TestCase):
    """verify_insight 域操作（INV-10）：输出归位（ADR 0006 / 决定 ㉔）——
    insight → Memory（correct_memory 形态：追加修正记录，原记录不变
    INV-8；修正记录 DERIVED / VERIFIED / CONFIRMED）；continuity 记录
    → 注入通道追加。"""

    def test_verify_appends_correction_original_unchanged(self):
        memory, append = FakeMemory(), AppendLog()
        model = FakeReflectionModel(output="验证结论：成立")
        growth = make_growth(memory, append, model)
        ref = growth.import_experience([_candidate("一条 insight", "k1")])[0]
        before = memory.get(ref)
        out = growth.verify_insight(ref)
        self.assertEqual(out, "mem-2")
        self.assertEqual(memory.get(ref), before, "INV-8：原记录不得被重写")
        correction = memory.get(out)
        self.assertEqual(correction.content, "验证结论：成立")
        self.assertIs(correction.memory_origin, MemoryOrigin.DERIVED)
        self.assertIs(correction.memory_status, MemoryStatus.VERIFIED)
        self.assertIs(correction.memory_confidence, MemoryConfidence.CONFIRMED)

    def test_verify_appends_continuity_record(self):
        memory, append = FakeMemory(), AppendLog()
        model = FakeReflectionModel(output="验证结论：成立")
        growth = make_growth(memory, append, model)
        ref = growth.import_experience([_candidate("一条 insight", "k1")])[0]
        growth.verify_insight(ref)
        self.assertEqual(
            append.records,
            [{"content": "验证结论：成立", "reference": ref}],
            "verify_insight 的 continuity 记录 reference = 被验证的 insight",
        )

    def test_verify_degraded_no_write_no_append(self):
        for model in (None, FakeReflectionModel(unavailable=True), FakeReflectionModel(output="   ")):
            memory, append = FakeMemory(), AppendLog()
            growth = make_growth(memory, append, model)
            ref = growth.import_experience([_candidate("一条 insight", "k1")])[0]
            self.assertIsNone(growth.verify_insight(ref))
            self.assertEqual(len(memory.stored), 1, "降级不得写记忆")
            self.assertEqual(append.records, [], "降级不得追加 continuity")

    def test_verify_missing_reference_fails_loud(self):
        memory, append = FakeMemory(), AppendLog()
        growth = make_growth(memory, append, FakeReflectionModel())
        with self.assertRaises(ValueError):
            growth.verify_insight("mem-99")
        self.assertEqual(append.records, [])


class VerifyInsightRealProviderTest(unittest.TestCase):
    """M11 S4 B2（ADR 0006 / INV-10）：成长路径的引用链在真实 Memory
    Provider 上核验——verify_insight 的修正记录与 insight 原记录经
    resolve_reference 双向可解析，原记录不变（INV-8）。既有
    VerifyInsightTest 用 FakeMemory（resolve_reference 未实现），本类
    闭合 M05 × M07 集成缝。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.provider = SqliteMemoryProvider(Path(self._tmp.name) / "memory")
        self.addCleanup(self.provider.close)

    def test_verify_insight_links_correction_chain_on_real_provider(self):
        model = FakeReflectionModel(output="验证结论：成立")
        growth = make_growth(self.provider, AppendLog(), model)
        insight = growth.import_experience([_candidate("一条 insight", "k1")])[0]
        before = self.provider.get(insight)
        correction = growth.verify_insight(insight)
        self.assertEqual(
            self.provider.get(insight), before, "INV-8：原记录不得被重写"
        )
        # 显式引用链双向可解析（INV-10：可验证 / 可修正，不删除原记录）
        self.assertIn(
            correction,
            [m.reference for m in self.provider.resolve_reference(insight)],
        )
        self.assertIn(
            insight,
            [m.reference for m in self.provider.resolve_reference(correction)],
        )
        self.assertIs(
            self.provider.get(correction).memory_status, MemoryStatus.VERIFIED
        )


class GrowthEndToEndTest(unittest.TestCase):
    """AC 8（INV-4 可测形态，端到端骨架）：经历 → 消化 → 提取 → 记忆 →
    复用（个体投影记忆节）→ 后续回合行为变化；现实验收在 M12。"""

    MARKER = "insight-标记"

    class ProjectionAwareModel:
        """回合模型测试替身：行为由投影内容决定——复用环节的唯一链接
        （管线输出经 Memory 进入投影 → 行为改变）。"""

        def __init__(self):
            self.projections: list[str] = []

        def chat(self, messages):
            self.projections.append(messages[0][1])
            if GrowthEndToEndTest.MARKER in self.projections[-1]:
                return "经验后行动"
            return "经验前行动"

        def complete(self, prompt):
            raise AssertionError("回合模型不参与管线阶段（管线走 reflection 侧）")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(shutil.rmtree, self._tmp.name, ignore_errors=True)
        self.root = Path(self._tmp.name)

    def _make_identity(self) -> Identity:
        return Identity(
            name="道生",
            self_appellation="小生",
            voice="沉静简练",
            visual_image="白衫老者",
            behavioral_habits=("先答后核",),
            past_experiences=("曾解一难问",),
            continuous_memory=("持续居于工作间",),
        )

    def _make_doctrine(self) -> Doctrine:
        return Doctrine(
            principles=(Principle("测试原理甲", "测试原理甲正文：当行则行。"),)
        )

    def _make_faculties(self) -> Faculties:
        return Faculties(roots=FACULTY_ROOTS)

    def test_experience_changes_future_behavior(self):
        continuity_file = self.root / "continuity.jsonl"
        memory = FakeMemory()
        turn_model = self.ProjectionAwareModel()
        individual = Individual(
            doctrine=self._make_doctrine(),
            identity=self._make_identity(),
            faculties=self._make_faculties(),
            continuity_file=continuity_file,
            memory=memory,
            model=turn_model,
        )
        # 经验前回合（投影无管线输出）
        before = individual.act(Turn("第一回合", MemoryOrigin.CANONICAL))
        individual.persist()
        # 成长管线：导入 → 消化 → 提取（产出落入同一 memory）
        growth = make_growth(
            memory,
            AppendLog(),
            FakeReflectionModel(output=f"insight：{self.MARKER} 成立"),
        )
        ref = growth.import_experience(
            [_candidate("一次经历", "k1", origin=MemoryOrigin.EXTERNAL)]
        )[0]
        self.assertTrue(growth.digest(ref))
        self.assertTrue(growth.extract(ref))
        # 复用：后续回合的投影可见管线输出 → 行为变化（INV-4）
        after = individual.act(Turn("第二回合", MemoryOrigin.CANONICAL))
        individual.persist()
        self.assertEqual(before.action, "经验前行动")
        self.assertEqual(after.action, "经验后行动")
        self.assertNotEqual(before.action, after.action)

    def test_reflect_verify_append_to_real_continuity_carrier(self):
        """归位（ADR 0006 / 决定 ㉔）：reflect / verify_insight 的记录经
        注入的真实 append_continuity 通道（composition 装配面同款
        functools.partial 绑定）落入 Continuity 单一载体——append-only，
        load_continuity 可读，历史行不改动。"""
        continuity_file = self.root / "continuity.jsonl"
        append = functools.partial(append_continuity, continuity_file)
        memory, model = FakeMemory(), FakeReflectionModel(output="阶段输出")
        growth = make_growth(memory, append, model)
        ref = growth.import_experience([_candidate("一次经历", "k1")])[0]
        growth.reflect(ref)
        growth.verify_insight(ref)
        records = load_continuity(continuity_file).records
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0], {"content": "阶段输出", "reference": "mem-2"})
        self.assertEqual(records[1], {"content": "阶段输出", "reference": ref})


if __name__ == "__main__":
    unittest.main()
