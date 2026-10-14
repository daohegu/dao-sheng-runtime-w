"""Research seam 契约 — M06（spec-adapters §3 / K-08 / D-04）。

Seam：`ResearchProvider`（Protocol：`name` + `research(query) -> ResearchResult`，
hypothetical，单 adapter；具体后端未定、不预设——本票只固化 seam 形态与
`ResearchResult` invariant，不实现任何后端客户端；M-6：后端在 composition
root 注入，不在 Research 包内硬建）。

K-08 invariant（数据结构强制项）：`ResearchResult` 必须携带 sources +
confidence——缺任一即违规，fail-loud（V0 的 `sources=[]` / `confidence=0.5`
默认值形态被废止：默认值正是"无来源观察也能存在"的通道）。

依据：spec-adapters.md §3、K-08（保留条件：service.py 壳 DELETE → D-04；
birth() 硬建 → composition root → M-6）、D-04（空查询校验归 seam 契约）；
V0 形态参考：dao_sheng/research/models.py + protocol.py。
"""

import unittest
from dataclasses import FrozenInstanceError
from typing import get_protocol_members

from dao_sheng.research import ResearchProvider, ResearchResult, ResearchSource


class ResearchResultInvariantTest(unittest.TestCase):
    """K-08 invariant：缺 sources 或 confidence = 违规（fail-loud）。"""

    def _kwargs(self, **overrides):
        kwargs = dict(
            query="某问题",
            findings="观察到的内容",
            sources=(ResearchSource(title="来源一", url="u1"),),
            provider="某后端",
            confidence=0.7,
        )
        kwargs.update(overrides)
        return kwargs

    def test_missing_sources_rejected(self):
        """sources 缺省（V0 默认 [] 形态）→ 构造失败，不得存在无来源观察。"""
        with self.assertRaises(TypeError):
            ResearchResult(**{k: v for k, v in self._kwargs().items() if k != "sources"})

    def test_empty_sources_rejected(self):
        """sources 显式空 → ValueError（fail-loud）。"""
        with self.assertRaises(ValueError):
            ResearchResult(**self._kwargs(sources=()))

    def test_missing_confidence_rejected(self):
        """confidence 缺省（V0 默认 0.5 形态）→ 构造失败。"""
        with self.assertRaises(TypeError):
            ResearchResult(
                **{k: v for k, v in self._kwargs().items() if k != "confidence"}
            )

    def test_confidence_none_rejected(self):
        with self.assertRaises(ValueError):
            ResearchResult(**self._kwargs(confidence=None))

    def test_confidence_out_of_range_rejected(self):
        for bad in (-0.1, 1.5):
            with self.assertRaises(ValueError):
                ResearchResult(**self._kwargs(confidence=bad))

    def test_confidence_bool_rejected(self):
        """bool 是 int 子类但非置信度语义 → 拒绝（fail-loud 不放宽）。"""
        with self.assertRaises(ValueError):
            ResearchResult(**self._kwargs(confidence=True))

    def test_valid_result_constructs(self):
        r = ResearchResult(**self._kwargs())
        self.assertEqual(r.query, "某问题")
        self.assertEqual(len(r.sources), 1)
        self.assertEqual(r.confidence, 0.7)
        self.assertEqual(r.provider, "某后端")
        # 默认槽位：retrieved_at 自动 UTC ISO 串、metadata 空 dict
        self.assertTrue(r.retrieved_at)
        self.assertEqual(r.metadata, {})

    def test_result_is_frozen(self):
        """frozen：观察产物不可变（invariant 不被事后改写）。"""
        r = ResearchResult(**self._kwargs())
        with self.assertRaises(FrozenInstanceError):
            r.confidence = 0.9
        with self.assertRaises(FrozenInstanceError):
            r.sources = ()


class ResearchSourceTest(unittest.TestCase):
    def test_source_shape(self):
        s = ResearchSource(title="来源一", url="u1")
        self.assertEqual(s.source_type, "web")
        self.assertIsNone(s.publisher)
        self.assertTrue(s.retrieved_at)
        self.assertEqual(s.metadata, {})

    def test_source_is_frozen(self):
        s = ResearchSource(title="t", url="u")
        with self.assertRaises(FrozenInstanceError):
            s.url = "other"


class ResearchProviderProtocolTest(unittest.TestCase):
    """seam 契约 = test surface：Protocol 成员恰为 name + research。"""

    def test_protocol_members(self):
        """与 M05 MemoryStore 棘轮同一验证手法（V1 先例：非 runtime_checkable，
        用 get_protocol_members 验证契约表面）。"""
        members = get_protocol_members(ResearchProvider)
        self.assertEqual(members, {"name", "research"})


if __name__ == "__main__":
    unittest.main()
