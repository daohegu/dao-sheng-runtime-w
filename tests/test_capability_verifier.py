"""Capability 闸门机制行为测试 — M11 (a) S1（spec-capability.md §1/§2/§7
+ ADR 0003；决定 ㊱）。

K-10：经公共表面驱动——Verifier = 注入 6 方法 Memory 契约实例 + verify
方法；Manager 集成测试经四方法（propose / advance / retire / execute）。
fake memory = 契约最小 fake（M08 测试模块模式：各测试模块自有 fake）。
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from dao_sheng.capability_lifecycle import (
    Capability,
    CapabilityManager,
    CapabilityState,
)
from dao_sheng.capability_verifier import CapabilityVerifier
from dao_sheng.memory import (
    MemoryConfidence,
    MemoryOrigin,
    MemoryStatus,
)
from dao_sheng.memory_sqlite import SqliteMemoryProvider


class FakeMemory:
    """MemoryStore 契约的最小 fake（6 方法表面；Verifier 只用 get）。"""

    def __init__(self, records: dict[str, str] | None = None):
        self._records = dict(records or {})
        self._counter = 0

    def remember(self, *, content, memory_origin, memory_status, memory_confidence):
        self._counter += 1
        reference = f"mem-{self._counter}"
        self._records[reference] = content
        return reference

    def get(self, reference):
        if reference not in self._records:
            raise ValueError(f"memory 记录缺失：{reference}")
        return SimpleNamespace(content=self._records[reference])

    def recall(self, query):
        return []

    def correct_memory(self, target, correction):
        return target

    def register_reference(self, source, target):
        return None

    def resolve_reference(self, reference):
        return []


class VerifierDecisionTest(unittest.TestCase):
    """闸门判据（决定 ㊱）：规则式 model-free 三判据；只裁决——不写、
    不移动、不抛（provider 缺失异常除外，fail-loud 透传）。"""

    def setUp(self):
        self.memory = FakeMemory()
        self.verifier = CapabilityVerifier(memory=self.memory)

    def _ref(self, content="内容"):
        return self.memory.remember(
            content=content,
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.UNCERTAIN,
        )

    def test_accept_grounded_capability(self):
        """三判据全满足 → 放行。"""
        reference = self._ref("内容")
        capability = Capability(name="甲", content="内容", source_reference=reference)
        self.assertTrue(self.verifier.verify(capability))

    def test_reject_missing_source(self):
        """源记录不可解析（get → ValueError = 缺失）→ 拒绝
        （不可验证 = 不可信，INV-11）。"""
        capability = Capability(
            name="甲", content="内容", source_reference="不存在的引用"
        )
        self.assertFalse(self.verifier.verify(capability))

    def test_reject_content_divergence(self):
        """投影 content 与源记录 content 分歧 → 拒绝（grounding 判据）。"""
        reference = self._ref("源内容")
        capability = Capability(
            name="甲", content="分歧内容", source_reference=reference
        )
        self.assertFalse(self.verifier.verify(capability))

    def test_reject_malformed_projection(self):
        """投影良构判据：三字段非空 str、name 无路径分隔符、非 '.' / '..'。"""
        reference = self._ref("内容")
        cases = [
            Capability(name="", content="c", source_reference=reference),
            Capability(name="   ", content="c", source_reference=reference),
            Capability(name="a/b", content="c", source_reference=reference),
            Capability(name="a\\b", content="c", source_reference=reference),
            Capability(name=".", content="c", source_reference=reference),
            Capability(name="..", content="c", source_reference=reference),
            Capability(name="甲", content="", source_reference=reference),
            Capability(name="甲", content="c", source_reference=""),
            Capability(name="甲", content=5, source_reference=reference),  # type: ignore[arg-type]
            Capability(name=5, content="c", source_reference=reference),  # type: ignore[arg-type]
        ]
        for capability in cases:
            self.assertFalse(
                self.verifier.verify(capability),
                f"投影 {capability!r} 应被拒绝",
            )

    def test_reject_fieldless_projection(self):
        """无字段投影（畸形载体形态）→ False，不抛。"""
        self.assertFalse(self.verifier.verify(SimpleNamespace()))
        self.assertFalse(self.verifier.verify(object()))

    def test_broader_provider_exception_propagates(self):
        """provider 故障（非缺失异常）= fail-loud，不是静默拒绝（决定 ㊱）。"""

        class BrokenMemory:
            def get(self, reference):
                raise RuntimeError("provider 故障")

        verifier = CapabilityVerifier(memory=BrokenMemory())
        capability = Capability(name="甲", content="c", source_reference="r")
        with self.assertRaises(RuntimeError):
            verifier.verify(capability)


class VerifierManagerIntegrationTest(unittest.TestCase):
    """真实闸门 + 真实 Manager：advance / execute 均经闸门（AC 1 / AC 6
    行为面）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "capabilities"
        self.memory = FakeMemory()
        self.verifier = CapabilityVerifier(memory=self.memory)
        self.manager = CapabilityManager(
            capabilities_dir=self.root,
            memory=self.memory,
            verifier=self.verifier,
        )

    def _propose(self, name="甲", content="提案内容"):
        reference = self.memory.remember(
            content=content,
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.UNCERTAIN,
        )
        return self.manager.propose(name, reference)

    def test_accept_path_to_active_and_execute(self):
        """放行路径：propose → working → active（记录入 active/）→ execute
        返回投影。"""
        capability = self._propose()
        self.manager.advance("甲", CapabilityState.WORKING)
        self.manager.advance("甲", CapabilityState.ACTIVE)
        self.assertTrue((self.root / "active" / "甲.json").is_file())
        self.assertEqual(self.manager.execute("甲"), capability)

    def test_reject_blocks_active_on_carrier_divergence(self):
        """载体损坏形态（记录 content 与源记录分歧）→ 闸门拒绝，
        不可达 active（硬行为：不移动、不写）。"""
        self._propose()
        self.manager.advance("甲", CapabilityState.WORKING)
        record_path = self.root / "working" / "甲.json"
        doc = json.loads(record_path.read_text(encoding="utf-8"))
        doc["content"] = "被篡改的内容"
        record_path.write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaises(ValueError):
            self.manager.advance("甲", CapabilityState.ACTIVE)
        self.assertTrue((self.root / "working" / "甲.json").is_file())
        self.assertFalse((self.root / "active").exists())

    def test_reject_blocks_execute_on_unresolvable_source(self):
        """active 记录源引用不可解析（损坏形态）→ execute 被闸门阻。"""
        active_dir = self.root / CapabilityState.ACTIVE.value
        active_dir.mkdir(parents=True)
        (active_dir / "甲.json").write_text(
            json.dumps(
                {"name": "甲", "content": "内容", "source_reference": "不可解析"},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            self.manager.execute("甲")

    def test_e2e_real_provider(self):
        """组件级 e2e（AC 6 组件面）：真实 Memory Provider + 真实闸门 +
        真实 Manager：remember → propose → working → active → execute。"""
        provider = SqliteMemoryProvider(Path(self._tmp.name) / "memory")
        # LIFO：close 先于目录删除执行（cleanup 先注册，close 后注册）
        self.addCleanup(provider.close)
        manager = CapabilityManager(
            capabilities_dir=self.root,
            memory=provider,
            verifier=CapabilityVerifier(memory=provider),
        )
        reference = provider.remember(
            content="成长管线产出的一条提案记录",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.UNCERTAIN,
        )
        capability = manager.propose("e2e", reference)
        manager.advance("e2e", CapabilityState.WORKING)
        manager.advance("e2e", CapabilityState.ACTIVE)
        self.assertTrue((self.root / "active" / "e2e.json").is_file())
        self.assertEqual(manager.execute("e2e"), capability)


if __name__ == "__main__":
    unittest.main()
