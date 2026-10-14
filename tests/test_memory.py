"""Memory Ontology + Interface 6 方法 + embedded Provider — M05。

Seams（票 `.scratch/v1-implementation/issues/05-memory-abstraction.md` Comments
Seam 清单）：Ontology 类型（三维 + Memory / RecallQuery / Correction）→
remember → get → recall（过滤 / 关键词通道 / 隐藏排序 / ≤32）→
correct_memory（INV-8）→ register / resolve_reference（显式链接）→
Provider 形态（WAL / 初始态 / 持久化）。

依据：spec-memory.md §1–§5、component-model.md §3（6 方法；实现隐藏列）、
ADR 0001 / 0006 / 0007、Q2 / H-4 / R-05 / A-1、INV-3 / INV-8 / INV-10。

The interface is the test surface：行为测试全部经 6 方法进行——调用方
不知道表结构 / FTS 索引 / 排序 / 上限形态（实现隐藏列）。
"""

import tempfile
import unittest
from pathlib import Path

from dao_sheng.memory import (
    Correction,
    Memory,
    MemoryConfidence,
    MemoryOrigin,
    MemoryStatus,
    RecallQuery,
)
from dao_sheng.memory_sqlite import SqliteMemoryProvider


class ThreeDimensionEnumsTest(unittest.TestCase):
    """Q2 三维语义层：精确值集本身 = 结构检查（AC 3：无宿主名）。"""

    def test_origin_values_exact(self):
        self.assertEqual(
            {m.value for m in MemoryOrigin},
            {"canonical", "derived", "external", "echo"},
        )

    def test_status_values_exact(self):
        self.assertEqual(
            {m.value for m in MemoryStatus},
            {"observed", "reported", "verified"},
        )

    def test_confidence_values_exact(self):
        self.assertEqual(
            {m.value for m in MemoryConfidence},
            {"confirmed", "supported", "uncertain"},
        )

    def test_no_host_name_in_any_enum_value(self):
        """H-4 provenance 中性化：枚举无宿主名（具体检查 = hermes，大小写不敏感）。"""
        for cls in (MemoryOrigin, MemoryStatus, MemoryConfidence):
            for m in cls:
                self.assertNotIn("hermes", m.value.lower())
                self.assertNotIn("hermes", m.name.lower())


class OntologyTypesTest(unittest.TestCase):
    def test_memory_is_frozen_projection(self):
        m = Memory(
            reference="r1",
            content="内容",
            memory_origin=MemoryOrigin.CANONICAL,
            memory_status=MemoryStatus.OBSERVED,
            memory_confidence=MemoryConfidence.CONFIRMED,
        )
        with self.assertRaises(AttributeError):
            m.content = "改写"

    def test_recall_query_defaults_are_empty_query(self):
        q = RecallQuery()
        self.assertIsNone(q.memory_origin)
        self.assertIsNone(q.memory_status)
        self.assertIsNone(q.memory_confidence)
        self.assertIsNone(q.keyword)

    def test_recall_query_empty_keyword_rejected(self):
        """空关键词无查询意义 → fail-loud（不静默当"无关键词"处理）。"""
        with self.assertRaises(ValueError):
            RecallQuery(keyword="")
        with self.assertRaises(ValueError):
            RecallQuery(keyword="   ")

    def test_correction_is_frozen(self):
        c = Correction(
            content="修正",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.CONFIRMED,
        )
        with self.assertRaises(AttributeError):
            c.content = "x"


class RememberGetTest(unittest.TestCase):
    """Seams 2–3：remember（三维显式 + content 非空 → reference）+
    get（精确取回 / 缺失 fail-loud）。

    Provider 载体形态（决定 ⑥）：memory_dir 内单 embedded SQLite 文件；
    行为测试只经 6 方法（interface = test surface）。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.provider = SqliteMemoryProvider(Path(self._tmp.name) / "memory")
        self.addCleanup(self.provider.close)

    def test_remember_returns_reference_retrievable_via_get(self):
        ref = self.provider.remember(
            content="一条记忆内容",
            memory_origin=MemoryOrigin.CANONICAL,
            memory_status=MemoryStatus.OBSERVED,
            memory_confidence=MemoryConfidence.CONFIRMED,
        )
        self.assertIsInstance(ref, str)
        m = self.provider.get(ref)
        self.assertIsInstance(m, Memory)
        self.assertEqual(m.reference, ref)
        self.assertEqual(m.content, "一条记忆内容")
        self.assertEqual(m.memory_origin, MemoryOrigin.CANONICAL)
        self.assertEqual(m.memory_status, MemoryStatus.OBSERVED)
        self.assertEqual(m.memory_confidence, MemoryConfidence.CONFIRMED)

    def test_remember_rejects_empty_content(self):
        with self.assertRaises(ValueError):
            self.provider.remember(
                content="",
                memory_origin=MemoryOrigin.CANONICAL,
                memory_status=MemoryStatus.OBSERVED,
                memory_confidence=MemoryConfidence.CONFIRMED,
            )
        with self.assertRaises(ValueError):
            self.provider.remember(
                content="   ",
                memory_origin=MemoryOrigin.CANONICAL,
                memory_status=MemoryStatus.OBSERVED,
                memory_confidence=MemoryConfidence.CONFIRMED,
            )

    def test_remember_rejects_non_enum_dimensions(self):
        """三维字段必须为枚举实例显式传入——字符串不得被静默接受（无推断行，Q2 / H-4）。"""
        for kwargs in (
            {"memory_origin": "canonical", "memory_status": MemoryStatus.OBSERVED, "memory_confidence": MemoryConfidence.CONFIRMED},
            {"memory_origin": MemoryOrigin.CANONICAL, "memory_status": "observed", "memory_confidence": MemoryConfidence.CONFIRMED},
            {"memory_origin": MemoryOrigin.CANONICAL, "memory_status": MemoryStatus.OBSERVED, "memory_confidence": "confirmed"},
        ):
            with self.assertRaises(ValueError):
                self.provider.remember(content="内容", **kwargs)

    def test_get_missing_reference_fails_loud(self):
        with self.assertRaises(ValueError):
            self.provider.get("nonexistent-reference")


class RecallTest(unittest.TestCase):
    """Seam 4：recall = 三维结构化过滤（任意子集）+ 可选关键词（通道隐藏：
    ≥3 字符 → FTS5 trigram / <3 → LIKE，AC 5 行为面）+ 隐藏排序（决定 ⑧：
    插入序倒序，最新优先）+ ≤32 上限（Interface 固化）。

    行为测试只验证命中集合 / 顺序 / 上限——不验证通道名（实现细节不外露，
    AC 4 / AC 5）。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.provider = SqliteMemoryProvider(Path(self._tmp.name) / "memory")
        self.addCleanup(self.provider.close)

    def _remember(self, content, **dims) -> str:
        return self.provider.remember(
            content=content,
            memory_origin=dims.get("memory_origin", MemoryOrigin.CANONICAL),
            memory_status=dims.get("memory_status", MemoryStatus.OBSERVED),
            memory_confidence=dims.get("memory_confidence", MemoryConfidence.CONFIRMED),
        )

    def _refs(self, query: RecallQuery) -> list[str]:
        return [m.reference for m in self.provider.recall(query)]

    def test_empty_query_returns_all_newest_first(self):
        a = self._remember("第一条")
        b = self._remember("第二条")
        c = self._remember("第三条")
        self.assertEqual(self._refs(RecallQuery()), [c, b, a])

    def test_result_capped_at_32(self):
        refs = [self._remember(f"记忆 {i:02d}") for i in range(35)]
        got = self._refs(RecallQuery())
        self.assertEqual(len(got), 32)
        self.assertEqual(got, list(reversed(refs[3:])))

    def test_filter_by_origin(self):
        k1 = self._remember("甲")
        self._remember("乙", memory_origin=MemoryOrigin.DERIVED)
        k2 = self._remember("丙")
        self.assertEqual(
            self._refs(RecallQuery(memory_origin=MemoryOrigin.CANONICAL)), [k2, k1]
        )

    def test_filter_by_status(self):
        k1 = self._remember("甲")
        self._remember("乙", memory_status=MemoryStatus.VERIFIED)
        k2 = self._remember("丙")
        self.assertEqual(
            self._refs(RecallQuery(memory_status=MemoryStatus.OBSERVED)), [k2, k1]
        )

    def test_filter_by_confidence(self):
        k1 = self._remember("甲")
        self._remember("乙", memory_confidence=MemoryConfidence.UNCERTAIN)
        k2 = self._remember("丙")
        self.assertEqual(
            self._refs(RecallQuery(memory_confidence=MemoryConfidence.CONFIRMED)),
            [k2, k1],
        )

    def test_filter_combination(self):
        hit = self._remember(
            "甲",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.VERIFIED,
        )
        self._remember("乙", memory_origin=MemoryOrigin.DERIVED)
        self._remember("丙", memory_status=MemoryStatus.VERIFIED)
        self._remember("丁")
        self.assertEqual(
            self._refs(
                RecallQuery(
                    memory_origin=MemoryOrigin.DERIVED,
                    memory_status=MemoryStatus.VERIFIED,
                )
            ),
            [hit],
        )

    def test_non_matching_filter_returns_empty(self):
        self._remember("内容")
        self.assertEqual(self._refs(RecallQuery(memory_origin=MemoryOrigin.EXTERNAL)), [])

    def test_keyword_cjk_three_plus_chars_substring(self):
        """≥3 字符 CJK 子串命中（行为面：trigram 通道，AC 5；不验证通道名）。"""
        hit = self._remember("成长管线提取记忆的过程记录")
        self._remember("无关内容")
        self.assertEqual(self._refs(RecallQuery(keyword="提取记")), [hit])

    def test_keyword_two_chars_substring(self):
        """<3 字符 CJK 子串命中（行为面：LIKE 通道，AC 5；不验证通道名）。"""
        hit = self._remember("成长管线提取记忆的过程记录")
        self._remember("无关内容")
        self.assertEqual(self._refs(RecallQuery(keyword="记忆")), [hit])

    def test_keyword_single_char_substring(self):
        hit = self._remember("独有字的内容")
        self._remember("无关内容")
        self.assertEqual(self._refs(RecallQuery(keyword="独")), [hit])

    def test_keyword_ascii_case_insensitive_across_channels(self):
        hit = self._remember("含有 abc 子串")
        self.assertEqual(self._refs(RecallQuery(keyword="ABC")), [hit])  # 3 字符通道
        self.assertEqual(self._refs(RecallQuery(keyword="ab")), [hit])  # 2 字符通道

    def test_keyword_with_embedded_quote(self):
        """关键词内嵌引号不得破坏查询构造（行为面：短语正确转义）。"""
        hit = self._remember('他说"你好"然后离开')
        self._remember("无关内容")
        self.assertEqual(self._refs(RecallQuery(keyword='"你好"')), [hit])

    def test_keyword_no_match_returns_empty(self):
        self._remember("内容一")
        self.assertEqual(self._refs(RecallQuery(keyword="不存在")), [])

    def test_keyword_combined_with_dimension_filter(self):
        hit = self._remember("关于记忆", memory_origin=MemoryOrigin.DERIVED)
        self._remember("关于记忆", memory_origin=MemoryOrigin.CANONICAL)
        self._remember("其他记忆", memory_origin=MemoryOrigin.DERIVED)
        self.assertEqual(
            self._refs(
                RecallQuery(
                    memory_origin=MemoryOrigin.DERIVED, keyword="关于记"
                )
            ),
            [hit],
        )

    def test_keyword_sort_newest_first(self):
        """隐藏排序与通道无关：同一命中集同序（决定 ⑧，最新优先）。"""
        a = self._remember("旧的记忆内容")
        b = self._remember("新的记忆内容")
        self.assertEqual(self._refs(RecallQuery(keyword="记忆")), [b, a])


class CorrectMemoryTest(unittest.TestCase):
    """Seam 5：correct_memory = 追加修正 + 显式引用链（original → correction），
    原记录不变（INV-8 行为测试，AC 1）。修正是普通记忆行（决定 ⑦：无 kind
    判别列）；Insight 修正走同一路径（ADR 0006 / INV-10）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.provider = SqliteMemoryProvider(Path(self._tmp.name) / "memory")
        self.addCleanup(self.provider.close)

    def _original(self) -> str:
        return self.provider.remember(
            content="原始认识",
            memory_origin=MemoryOrigin.CANONICAL,
            memory_status=MemoryStatus.OBSERVED,
            memory_confidence=MemoryConfidence.CONFIRMED,
        )

    def _correction(self, content="修正后的认识", **dims) -> Correction:
        return Correction(
            content=content,
            memory_origin=dims.get("memory_origin", MemoryOrigin.CANONICAL),
            memory_status=dims.get("memory_status", MemoryStatus.REPORTED),
            memory_confidence=dims.get("memory_confidence", MemoryConfidence.CONFIRMED),
        )

    def test_original_record_unchanged(self):
        """INV-8：原记录 content / 三维 / identity 不变（修正不重写）。"""
        original = self._original()
        before = self.provider.get(original)
        self.provider.correct_memory(original, self._correction())
        after = self.provider.get(original)
        self.assertEqual(after.reference, before.reference)
        self.assertEqual(after.content, before.content)
        self.assertEqual(after.memory_origin, before.memory_origin)
        self.assertEqual(after.memory_status, before.memory_status)
        self.assertEqual(after.memory_confidence, before.memory_confidence)

    def test_correction_stored_and_linked_bidirectionally(self):
        original = self._original()
        correction_ref = self.provider.correct_memory(
            original, self._correction(content="修正后的认识")
        )
        self.assertNotEqual(correction_ref, original)
        c = self.provider.get(correction_ref)
        self.assertEqual(c.content, "修正后的认识")
        self.assertEqual(c.memory_status, MemoryStatus.REPORTED)
        # 显式引用链双向解析
        self.assertIn(
            correction_ref,
            [m.reference for m in self.provider.resolve_reference(original)],
        )
        self.assertIn(
            original,
            [m.reference for m in self.provider.resolve_reference(correction_ref)],
        )

    def test_insight_corrected_via_same_path(self):
        """ADR 0006 / INV-10：Insight 无独立存储——经 remember / correct_memory
        同一路径落库与修正。"""
        insight = self.provider.remember(
            content="一条洞见",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.SUPPORTED,
        )
        ref = self.provider.correct_memory(
            insight,
            Correction(
                content="修正洞见",
                memory_origin=MemoryOrigin.DERIVED,
                memory_status=MemoryStatus.VERIFIED,
                memory_confidence=MemoryConfidence.CONFIRMED,
            ),
        )
        self.assertEqual(self.provider.get(insight).content, "一条洞见")  # 原记录不变
        self.assertEqual(self.provider.get(ref).memory_status, MemoryStatus.VERIFIED)

    def test_insight_retired_via_correction_original_survives(self):
        """INV-10（M11 S4 B1）：Insight 可淘汰而不删除原记录——淘汰 =
        经 correct_memory 追加淘汰形态修正记录（显式双向引用键）；原
        Insight 原样留存。状态值集无 "retired" 值（test_status_values_
        exact 锁定 {observed, reported, verified}）：淘汰是修正形态，
        不是状态。"""
        insight = self.provider.remember(
            content="一条被判定不再采用的洞见",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.SUPPORTED,
        )
        retire_ref = self.provider.correct_memory(
            insight,
            Correction(
                content="淘汰：该洞见不再采用",
                memory_origin=MemoryOrigin.DERIVED,
                memory_status=MemoryStatus.REPORTED,
                memory_confidence=MemoryConfidence.CONFIRMED,
            ),
        )
        self.assertEqual(
            self.provider.get(insight).content, "一条被判定不再采用的洞见"
        )
        self.assertIs(
            self.provider.get(insight).memory_status, MemoryStatus.REPORTED
        )
        # 显式引用链双向可解析
        self.assertIn(
            retire_ref,
            [m.reference for m in self.provider.resolve_reference(insight)],
        )
        self.assertIn(
            insight,
            [m.reference for m in self.provider.resolve_reference(retire_ref)],
        )

    def test_missing_target_fails_loud(self):
        with self.assertRaises(ValueError):
            self.provider.correct_memory("nonexistent-reference", self._correction())

    def test_rejects_empty_correction_content(self):
        original = self._original()
        with self.assertRaises(ValueError):
            self.provider.correct_memory(original, self._correction(content="   "))

    def test_rejects_non_enum_dimensions(self):
        original = self._original()
        with self.assertRaises(ValueError):
            self.provider.correct_memory(
                original,
                Correction(
                    content="x",
                    memory_origin="derived",
                    memory_status=MemoryStatus.REPORTED,
                    memory_confidence=MemoryConfidence.CONFIRMED,
                ),
            )


class ReferenceTest(unittest.TestCase):
    """Seam 6：register_reference / resolve_reference = 显式有序对链接，
    两端必须存在（fail-loud）、同对幂等、双向解析、永不做内容匹配
    （显式引用优先，V0 行为形态）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.provider = SqliteMemoryProvider(Path(self._tmp.name) / "memory")
        self.addCleanup(self.provider.close)

    def _remember(self, content) -> str:
        return self.provider.remember(
            content=content,
            memory_origin=MemoryOrigin.CANONICAL,
            memory_status=MemoryStatus.OBSERVED,
            memory_confidence=MemoryConfidence.CONFIRMED,
        )

    def _refs(self, reference: str) -> list[str]:
        return [m.reference for m in self.provider.resolve_reference(reference)]

    def test_register_requires_both_ends_exist(self):
        a = self._remember("内容 A")
        with self.assertRaises(ValueError):
            self.provider.register_reference(a, "nonexistent-reference")
        with self.assertRaises(ValueError):
            self.provider.register_reference("nonexistent-reference", a)

    def test_register_same_pair_idempotent(self):
        a = self._remember("内容 A")
        b = self._remember("内容 B")
        self.provider.register_reference(a, b)
        self.provider.register_reference(a, b)
        self.assertEqual(self._refs(a), [b])

    def test_resolve_bidirectional(self):
        a = self._remember("内容 A")
        b = self._remember("内容 B")
        self.provider.register_reference(a, b)
        self.assertIn(b, self._refs(a))
        self.assertIn(a, self._refs(b))

    def test_resolve_never_matches_content(self):
        """显式引用优先：内容相同但无显式链接 → 解析为空（永不做内容匹配）。"""
        a = self._remember("相同内容")
        b = self._remember("相同内容")
        self.assertEqual(self._refs(a), [])
        self.assertEqual(self._refs(b), [])

    def test_resolve_missing_reference_fails_loud(self):
        with self.assertRaises(ValueError):
            self.provider.resolve_reference("nonexistent-reference")

    def test_resolve_order_follows_insertion(self):
        original = self._remember("原始")
        c1 = self._remember("修正一")
        c2 = self._remember("修正二")
        self.provider.register_reference(original, c1)
        self.provider.register_reference(original, c2)
        self.assertEqual(self._refs(original), [c1, c2])


class ProviderFormTest(unittest.TestCase):
    """Seam 7：Provider 载体形态（决定 ⑥）——memory_dir 内单 embedded
    SQLite 文件 + WAL；初始化不读外部存储（AC 7）；目录缺失 = 初始态
    （ADR 0007）；数据跨实例持久（WAL 落盘）。

    本类是对载体形态本身的核验（决定 ⑥ 的落位验证），不属于 6 方法行为
    测试——其余行为测试全部只经 Interface（interface = test surface）。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.mem_dir = Path(self._tmp.name) / "memory"

    def test_init_creates_single_db_file_in_memory_dir(self):
        p = SqliteMemoryProvider(self.mem_dir)
        self.addCleanup(p.close)
        self.assertEqual(
            [f.name for f in self.mem_dir.iterdir() if f.name.endswith(".db")],
            ["memory.db"],
        )

    def test_missing_directory_is_initial_state_empty_memory(self):
        """目录 / DB 缺失 = 初始态（新建个体，空记忆）——初始化不读 V0 存储
        （ADR 0007；参数面仅 memory_dir，无外部存储可传入，AC 7）。"""
        p = SqliteMemoryProvider(self.mem_dir)
        self.addCleanup(p.close)
        self.assertEqual(p.recall(RecallQuery()), [])

    def test_wal_journal_mode_active(self):
        """决定 ⑥ 载体形态：WAL 已启用（research E2；-wal / -shm 侧文件）。"""
        import sqlite3

        p = SqliteMemoryProvider(self.mem_dir)
        self.addCleanup(p.close)
        conn = sqlite3.connect(self.mem_dir / "memory.db")
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(mode, "wal")

    def test_data_persists_across_instances(self):
        p1 = SqliteMemoryProvider(self.mem_dir)
        ref = p1.remember(
            content="持久内容",
            memory_origin=MemoryOrigin.CANONICAL,
            memory_status=MemoryStatus.OBSERVED,
            memory_confidence=MemoryConfidence.CONFIRMED,
        )
        p1.close()
        p2 = SqliteMemoryProvider(self.mem_dir)
        self.addCleanup(p2.close)
        self.assertEqual(p2.get(ref).content, "持久内容")
        self.assertEqual(
            [m.reference for m in p2.recall(RecallQuery())], [ref]
        )


if __name__ == "__main__":
    unittest.main()
