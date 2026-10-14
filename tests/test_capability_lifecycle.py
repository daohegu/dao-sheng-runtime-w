"""Capability 生命周期行为测试 — M08（spec-capability.md + ADR 0003）。

K-10：经公共接口（四方法）驱动；载体文件断言 = 四目录 adapter 形态的
物理表达检查（决定 ㉘）。fake 闸门 = 闸门契约位的最小实现（机制 M11
交付；本票验收契约位 + 硬行为）。
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
from dao_sheng.memory import (
    MemoryConfidence,
    MemoryOrigin,
    MemoryStatus,
)
from dao_sheng.memory_sqlite import SqliteMemoryProvider

RECORD_KEYS = {"name", "content", "source_reference"}


class FakeMemory:
    """MemoryStore 契约的最小 fake（6 方法表面；Manager 只用 get）。"""

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


class FakeGate:
    """闸门契约位 fake：预置裁决 + 记录每次 verify 调用的能力投影。"""

    def __init__(self, verdict: bool):
        self.verdict = verdict
        self.calls: list[Capability] = []

    def verify(self, capability: Capability) -> bool:
        self.calls.append(capability)
        return self.verdict


class CapabilityLifecycleTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "capabilities"
        self.memory = FakeMemory()
        self.gate = FakeGate(True)
        self.manager = CapabilityManager(
            capabilities_dir=self.root,
            memory=self.memory,
            verifier=self.gate,
        )

    def _propose(self, name="甲", content="提案内容"):
        reference = self.memory.remember(
            content=content,
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.UNCERTAIN,
        )
        return self.manager.propose(name, reference)

    def _to_working(self, name="甲"):
        self.manager.advance(name, CapabilityState.WORKING)

    def _to_active(self, name="甲"):
        self._to_working(name)
        return self.manager.advance(name, CapabilityState.ACTIVE)

    # -- 载体形态（决定 ㉘：四目录 adapter 形态） --

    def test_carrier_not_precreated(self):
        """载体不代建：构造后目录不存在；首个 propose 创建所需状态目录。"""
        self.assertFalse(self.root.exists())
        self._propose()
        self.assertTrue((self.root / "proposed" / "甲.json").is_file())
        self.assertFalse((self.root / "active").exists())

    def test_propose_registers_record(self):
        """propose 登记 proposed：投影返回 + 记录文件严格 3 键 schema。"""
        capability = self._propose()
        self.assertEqual(capability.name, "甲")
        self.assertEqual(capability.content, "提案内容")
        self.assertTrue(capability.source_reference.startswith("mem-"))
        doc = json.loads(
            (self.root / "proposed" / "甲.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(doc), RECORD_KEYS)
        self.assertEqual(doc["content"], "提案内容")
        self.assertNotIn("state", doc, "记录文件不得带状态字段（D-5）")

    def test_advance_proposed_to_working(self):
        """advance proposed → working：记录文件移入 working/。"""
        capability = self._propose()
        result = self.manager.advance("甲", CapabilityState.WORKING)
        self.assertEqual(result, capability)
        self.assertTrue((self.root / "working" / "甲.json").is_file())
        self.assertFalse((self.root / "proposed" / "甲.json").exists())

    def test_working_to_active_through_gate(self):
        """working → active 经放行闸门：记录入 active/，闸门收到投影。"""
        capability = self._propose()
        self._to_active()
        self.assertTrue((self.root / "active" / "甲.json").is_file())
        self.assertEqual(self.gate.calls, [capability])

    def test_gate_reject_blocks_active(self):
        """闸门 reject ⇒ 不可达 active（硬行为，INV-11）：不移动、不写。"""
        self._propose()
        self._to_working()
        self.gate.verdict = False
        with self.assertRaises(ValueError):
            self.manager.advance("甲", CapabilityState.ACTIVE)
        self.assertTrue((self.root / "working" / "甲.json").is_file())
        self.assertFalse((self.root / "active").exists())
        self.assertEqual(len(self.gate.calls), 1)

    def test_verifier_none_advance_degrades(self):
        """闸门未装配（verifier = None）→ advance 至 active 降级 None
        （INV-1：不写、不抛）。"""
        manager = CapabilityManager(
            capabilities_dir=self.root,
            memory=self.memory,
            verifier=None,
        )
        reference = self.memory.remember(
            content="内容",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.UNCERTAIN,
        )
        manager.propose("甲", reference)
        manager.advance("甲", CapabilityState.WORKING)
        self.assertIsNone(manager.advance("甲", CapabilityState.ACTIVE))
        self.assertTrue((self.root / "working" / "甲.json").is_file())
        self.assertFalse((self.root / "active").exists())

    # -- 状态机（ADR 0003 决定 1：无后退、无跳过、retired 终态） --

    def test_invalid_transitions_rejected(self):
        """非法转换 → ValueError：跳跃（proposed → active）、后退
        （→ proposed）、能力不存在。"""
        self._propose()
        with self.assertRaises(ValueError):
            self.manager.advance("甲", CapabilityState.ACTIVE)
        with self.assertRaises(ValueError):
            self.manager.advance("甲", CapabilityState.PROPOSED)
        with self.assertRaises(ValueError):
            self.manager.advance("不存在", CapabilityState.WORKING)
        # 未发生任何转换
        self.assertTrue((self.root / "proposed" / "甲.json").is_file())

    def test_retire_preserves_record_bytes(self):
        """retire 保留不删除（K-06）：记录文件移入 retired/，字节不变。"""
        self._propose()
        self._to_working()
        before = (self.root / "working" / "甲.json").read_bytes()
        self.manager.retire("甲")
        retired_path = self.root / "retired" / "甲.json"
        self.assertTrue(retired_path.is_file())
        self.assertFalse((self.root / "working" / "甲.json").exists())
        self.assertEqual(retired_path.read_bytes(), before)

    def test_retire_from_proposed_and_active(self):
        """retire 自任意非终态合法：proposed → retired；active → retired。"""
        self._propose("甲")
        self._propose("乙", content="另一条提案")
        self._to_active("乙")
        self.manager.retire("甲")
        self.assertTrue((self.root / "retired" / "甲.json").is_file())
        self.manager.retire("乙")
        self.assertTrue((self.root / "retired" / "乙.json").is_file())
        self.assertFalse((self.root / "active" / "乙.json").exists())

    def test_retired_is_terminal(self):
        """retired = 终态：重复 retire → ValueError（终态无出边）。"""
        self._propose()
        self._to_active()
        self.manager.retire("甲")
        with self.assertRaises(ValueError):
            self.manager.retire("甲")
        self.assertTrue((self.root / "retired" / "甲.json").is_file())

    # -- propose 校验（fail-loud） --

    def test_name_validation(self):
        """name 校验：空白 / 路径分隔符 / '.' / '..' → ValueError。"""
        reference = self.memory.remember(
            content="内容",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.UNCERTAIN,
        )
        for bad in ("", "   ", "a/b", "a\\b", ".", ".."):
            with self.assertRaises(ValueError, msg=f"name={bad!r} 应被拒绝"):
                self.manager.propose(bad, reference)
        self.assertFalse(self.root.exists())

    def test_reference_missing_fail_loud(self):
        """reference 缺失 → ValueError（M05 get 契约）。"""
        with self.assertRaises(ValueError):
            self.manager.propose("甲", "missing-reference")

    def test_empty_source_content_rejected(self):
        """源记录 content 为空 → ValueError（提案须承载语义）。"""
        reference = self.memory.remember(
            content="   ",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.UNCERTAIN,
        )
        with self.assertRaises(ValueError):
            self.manager.propose("甲", reference)

    def test_duplicate_name_rejected_global(self):
        """name 四目录全局唯一：同状态 / 跨状态重复提案 → ValueError。"""
        self._propose()
        with self.assertRaises(ValueError):
            self._propose()
        self._to_working()
        with self.assertRaises(ValueError):
            self._propose()

    # -- execute（INV-11 执行前闸门） --

    def test_execute_requires_active(self):
        """仅 active 可执行（K-04 隔离）：proposed / working / retired
        → ValueError。"""
        self._propose("甲")
        self._propose("乙", content="另一条提案")
        self._propose("丙", content="再一条提案")
        self._to_working("乙")
        self.manager.retire("丙")
        for name in ("甲", "乙", "丙"):
            with self.assertRaises(ValueError, msg=f"{name} 不可执行"):
                self.manager.execute(name)

    def test_execute_gate_reject(self):
        """active 能力执行同样经闸门：reject → ValueError，执行被阻。"""
        self._propose()
        self._to_active()
        self.gate.verdict = False
        with self.assertRaises(ValueError):
            self.manager.execute("甲")
        self.assertEqual(len(self.gate.calls), 2)  # advance 一次 + execute 一次

    def test_execute_active_returns_projection(self):
        """active + 放行 → 返回能力投影（执行体 = 投影供给）。"""
        capability = self._propose()
        self._to_active()
        result = self.manager.execute("甲")
        self.assertEqual(result, capability)
        self.assertEqual(self.gate.calls[-1], capability)

    def test_execute_verifier_none_degrades(self):
        """闸门未装配 → execute 降级 None（INV-1：不写、不抛）。"""
        active_dir = self.root / CapabilityState.ACTIVE.value
        active_dir.mkdir(parents=True)
        (active_dir / "甲.json").write_text(
            json.dumps(
                {"name": "甲", "content": "内容", "source_reference": "r"},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        manager = CapabilityManager(
            capabilities_dir=self.root,
            memory=self.memory,
            verifier=None,
        )
        self.assertIsNone(manager.execute("甲"))

    # -- 载体损坏检测（fail-loud） --

    def test_corrupt_record_detected(self):
        """记录损坏 → ValueError：多键 / 缺键 / 类型不符 / name 与文件名
        不交叉 / 非法 JSON。"""
        proposed_dir = self.root / "proposed"
        proposed_dir.mkdir(parents=True)
        base = {"name": "甲", "content": "内容", "source_reference": "r"}

        cases = [
            {**base, "extra": "x"},  # 多键
            {k: v for k, v in base.items() if k != "source_reference"},  # 缺键
            {**base, "content": 5},  # 类型不符
            {**base, "name": "乙"},  # name 与文件名不交叉
        ]
        for i, doc in enumerate(cases):
            path = proposed_dir / "甲.json"
            path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError, msg=f"case {i} 应被检出"):
                self.manager.advance("甲", CapabilityState.WORKING)
        (proposed_dir / "甲.json").write_text("not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.manager.advance("甲", CapabilityState.WORKING)

    def test_double_physical_placement(self):
        """双重物理放置（同名记录出现在多个状态目录 = 载体损坏）→
        ValueError（fail-loud，不猜哪个是真的）。"""
        for state in (CapabilityState.PROPOSED, CapabilityState.WORKING):
            state_dir = self.root / state.value
            state_dir.mkdir(parents=True)
            (state_dir / "甲.json").write_text(
                json.dumps(
                    {"name": "甲", "content": "内容", "source_reference": "r"},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        with self.assertRaises(ValueError):
            self.manager.advance("甲", CapabilityState.WORKING)
        with self.assertRaises(ValueError):
            self.manager.retire("甲")

    # -- 持久化（个体持久文件清单项 4） --

    def test_cross_instance_persistence(self):
        """跨实例持久化：实例 1 推进至 active，实例 2 同目录可直接
        execute（载体 = 个体状态，重启后由载体恢复）。"""
        capability = self._propose()
        self._to_active()
        manager2 = CapabilityManager(
            capabilities_dir=self.root,
            memory=FakeMemory(),
            verifier=FakeGate(True),
        )
        result = manager2.execute("甲")
        self.assertEqual(result, capability)

    def test_e2e_real_memory_provider(self):
        """提案通道 e2e（决定 ㉖）：真实 Memory Provider remember →
        propose 经 6 方法契约 get 读源记录，content = 单一事实来源。"""
        provider = SqliteMemoryProvider(Path(self._tmp.name) / "memory")
        # LIFO：close 先于目录删除执行（cleanup 先注册，close 后注册）
        self.addCleanup(provider.close)
        manager = CapabilityManager(
            capabilities_dir=self.root,
            memory=provider,
            verifier=self.gate,
        )
        reference = provider.remember(
            content="成长管线产出的一条提案记录",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.UNCERTAIN,
        )
        capability = manager.propose("e2e", reference)
        self.assertEqual(capability.content, "成长管线产出的一条提案记录")
        self.assertEqual(capability.source_reference, reference)


if __name__ == "__main__":
    unittest.main()
