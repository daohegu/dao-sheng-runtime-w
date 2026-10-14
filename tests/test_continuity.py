"""Continuity 模块（读 / 追加 / 保护隐藏）— M03。

Seam（票 Comments 清单 1–4）：`parse_continuity`（合法 → 冻结投影 /
非法拒绝）、`Continuity` 冻结（无 mutation API / 无计数器字段）、
`load_continuity` + `append_continuity`（缺失 = 空日志 / 唯一写入入口 /
追加后历史记录不变）。

依据：spec-self-state.md §2（单一载体 / append-only / 不是计数器）、
ADR 0004 决定 2–4、data-ownership.md §2（合法内部追加通道）、
spec-growth.md §4（唯一写入通道 = 成长管线，M07 闭环）、M02 决定 ②
的 M03 对齐声明、M03 决定 ③ 载体形态（单 append-only 日志文件；
记录内容 schema 不预设——规则 11）。
"""

import json
import tempfile
import unittest
from pathlib import Path

from dao_sheng.continuity import (
    Continuity,
    append_continuity,
    load_continuity,
    parse_continuity,
)


class ParseContinuityTest(unittest.TestCase):
    """Seam 1：合法 JSONL 载体文本 → 冻结只读投影（records 保序）。"""

    def test_legal_jsonl_to_frozen_projection(self):
        c = parse_continuity(
            json.dumps({"a": 1}, ensure_ascii=False) + "\n"
            + json.dumps({"note": "成长管线记录", "nested": {"x": [1, 2]}}) + "\n"
        )
        self.assertEqual(len(c.records), 2)
        self.assertEqual(c.records[0], {"a": 1})
        self.assertEqual(c.records[1]["note"], "成长管线记录")
        self.assertEqual(c.records[1]["nested"], {"x": [1, 2]})

    def test_empty_text_is_empty_log(self):
        """初始状态无已定内容（规则 11）——空文本 = 空日志，非错误。"""
        c = parse_continuity("")
        self.assertEqual(c.records, ())

    def test_trailing_newline_is_legal(self):
        """追加以换行结尾——尾随空行是合法形态，不得拒绝。"""
        c = parse_continuity(json.dumps({"a": 1}) + "\n")
        self.assertEqual(len(c.records), 1)

    def test_blank_lines_ignored(self):
        c = parse_continuity(json.dumps({"a": 1}) + "\n\n" + json.dumps({"b": 2}) + "\n")
        self.assertEqual(len(c.records), 2)
        self.assertEqual(c.records[0], {"a": 1})
        self.assertEqual(c.records[1], {"b": 2})


class RejectInvalidCarrierTest(unittest.TestCase):
    """Seam 2：非法载体一律显式拒绝（fail-loud，不静默跳过）。"""

    def test_non_json_line_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            parse_continuity("not a json line\n")
        self.assertIn("第 1 行", str(ctx.exception))

    def test_non_object_line_rejected(self):
        for line in ("42", '"x"', "[1, 2]", "null", "true"):
            with self.assertRaises(ValueError, msg=line):
                parse_continuity(line + "\n")

    def test_corrupt_line_after_legal_line_rejected(self):
        with self.assertRaises(ValueError):
            parse_continuity(json.dumps({"a": 1}) + "\nbroken\n")


class FrozenProjectionTest(unittest.TestCase):
    """Seam 3：投影冻结——运行时不存在改写路径（决定 ⑤ 行为面）。"""

    def test_projection_is_frozen(self):
        c = parse_continuity(json.dumps({"a": 1}) + "\n")
        with self.assertRaises(AttributeError):
            c.records = ()

    def test_no_mutation_api_on_class(self):
        """类表面除构造器外无 mutation API（写接口结构性不存在）。"""
        mutators = [
            n
            for n in dir(Continuity)
            if n.startswith(("set_", "update_", "mutate", "write"))
            or n in ("replace", "save", "append", "extend")
        ]
        self.assertEqual(mutators, [])

    def test_projection_has_no_counter_field(self):
        """不是计数器（C-2 处置）+ continuity_revision 不复存在（C-3 处置）：
        投影只有记录序列本身，无任何计数 / revision 字段。"""
        import dataclasses

        fields = {f.name for f in dataclasses.fields(Continuity)}
        self.assertEqual(fields, {"records"})


class ContinuityIOTest(unittest.TestCase):
    """Seam 4：load / append 行为面（tempdir 内真实文件）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.carrier = self.root / "continuity.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_missing_file_is_empty_log(self):
        """缺失文件 = 空日志（初始状态；首次追加创建文件）——非错误。"""
        c = load_continuity(self.carrier)
        self.assertEqual(c.records, ())
        self.assertFalse(self.carrier.exists())

    def test_load_legal_file_roundtrip(self):
        self.carrier.write_text(
            json.dumps({"a": 1}, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        c = load_continuity(self.carrier)
        self.assertEqual(c.records, ({"a": 1},))

    def test_load_corrupt_line_rejected(self):
        """损坏行 → fail-loud（装配面校验依据，决定 ⑤ 装配面）。"""
        self.carrier.write_text("not json\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_continuity(self.carrier)

    def test_append_creates_file_and_grows_log(self):
        append_continuity(self.carrier, {"source": "growth"})
        self.assertTrue(self.carrier.is_file())
        c = load_continuity(self.carrier)
        self.assertEqual(c.records, ({"source": "growth"},))

    def test_append_preserves_history(self):
        """AC 1 行为面：追加后历史记录不变（append-only）。"""
        append_continuity(self.carrier, {"seq": 1})
        first_line = self.carrier.read_text(encoding="utf-8")
        append_continuity(self.carrier, {"seq": 2})
        text = self.carrier.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(first_line))
        c = load_continuity(self.carrier)
        self.assertEqual(len(c.records), 2)
        self.assertEqual(c.records[0], {"seq": 1})
        self.assertEqual(c.records[1], {"seq": 2})

    def test_append_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            append_continuity(self.carrier, [1, 2, 3])
        self.assertFalse(self.carrier.exists())

    def test_append_only_writes_continuity_carrier(self):
        """AC 6 行为面：追加不触碰任何其他个体持久文件（无共享写路径，
        ADR 0004 决定 3）。"""
        identity = self.root / "identity.json"
        faculties = self.root / "faculties.json"
        identity.write_text("{}", encoding="utf-8")
        faculties.write_text("[]", encoding="utf-8")
        before_identity = identity.read_bytes()
        before_faculties = faculties.read_bytes()
        append_continuity(self.carrier, {"seq": 1})
        self.assertEqual(identity.read_bytes(), before_identity)
        self.assertEqual(faculties.read_bytes(), before_faculties)


if __name__ == "__main__":
    unittest.main()
