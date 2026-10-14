"""Identity 模块（加载 / 校验 / 保护隐藏）— M02。

Seam：`parse_identity`（载体文本 → 冻结只读投影；非法载体拒绝）、
`Identity` 冻结（运行时不存在改写路径）。

依据：spec-self-state.md §1/§4、data-ownership.md §2（Identity 行）、
constitution.md §3、CINV-3、INV-2 / 规则 2、4、K-11（历史形态参考，
非 KEEP 依据——规则 12）。
"""

import json
import unittest

from dao_sheng.identity import Identity, parse_identity


def _carrier(**overrides) -> str:
    """一份完整合法载体文档（测试 fixture；内容值仅为 fixture，非设计层内容）。"""
    doc = {
        "name": "DaoSheng",
        "self_appellation": "",
        "voice": "",
        "visual_image": "",
        "behavioral_habits": [],
        "past_experiences": [],
        "continuous_memory": [],
    }
    doc.update(overrides)
    return json.dumps(doc, ensure_ascii=False)


class ParseIdentityTest(unittest.TestCase):
    """Seam 1：合法载体文本 → 冻结只读投影。"""

    def test_parses_full_carrier_to_projection(self):
        i = parse_identity(
            _carrier(
                self_appellation="我",
                behavioral_habits=["h1", "h2"],
                past_experiences=["e1"],
                continuous_memory=["m1"],
            )
        )
        self.assertEqual(i.name, "DaoSheng")
        self.assertEqual(i.self_appellation, "我")
        self.assertEqual(i.behavioral_habits, ("h1", "h2"))
        self.assertEqual(i.past_experiences, ("e1",))
        self.assertEqual(i.continuous_memory, ("m1",))

    def test_empty_scalar_and_list_fields_allowed(self):
        """内容 = 设计层值，运行时不预设任何内容（规则 11）——空 = 设计层未定。"""
        i = parse_identity(_carrier())
        self.assertEqual(i.name, "DaoSheng")
        self.assertEqual(i.voice, "")
        self.assertEqual(i.behavioral_habits, ())


class RejectInvalidCarrierTest(unittest.TestCase):
    """Seam 2：非法载体一律显式拒绝（严格 schema：恰好 7 支撑项键）。"""

    def test_missing_key_rejected(self):
        doc = json.loads(_carrier())
        del doc["voice"]
        with self.assertRaises(ValueError):
            parse_identity(json.dumps(doc, ensure_ascii=False))

    def test_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            parse_identity(_carrier(extra_field="x"))

    def test_model_worker_host_keys_rejected(self):
        """AC 2/3：载体不得含 model / worker / host 字段（INV-2 / 规则 2、4）。"""
        for forbidden in ("model", "worker", "host"):
            with self.assertRaises(ValueError, msg=forbidden):
                parse_identity(_carrier(**{forbidden: "x"}))

    def test_name_must_be_nonempty_string(self):
        with self.assertRaises(ValueError):
            parse_identity(_carrier(name=""))
        with self.assertRaises(ValueError):
            parse_identity(_carrier(name=5))

    def test_scalar_type_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            parse_identity(_carrier(voice=3))

    def test_list_fields_must_be_string_lists(self):
        with self.assertRaises(ValueError):
            parse_identity(_carrier(behavioral_habits=["ok", 3]))
        with self.assertRaises(ValueError):
            parse_identity(_carrier(past_experiences="not-a-list"))

    def test_non_json_rejected(self):
        with self.assertRaises(ValueError):
            parse_identity("not a json document")


class IdentitySchemaTest(unittest.TestCase):
    """Seam 2/6（结构面）：载体 schema = B1-E6 恰好 7 支撑项，无外部依赖字段。"""

    def test_schema_is_exactly_the_seven_supporting_items(self):
        import dataclasses

        fields = {f.name for f in dataclasses.fields(Identity)}
        self.assertEqual(
            fields,
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

    def test_schema_has_no_external_dependency_fields(self):
        """AC 2 结构检查：schema 无 model / worker / host 字段（K-11 / INV-2）。"""
        import dataclasses

        fields = {f.name for f in dataclasses.fields(Identity)}
        for forbidden in ("model", "worker", "host"):
            self.assertNotIn(forbidden, fields)


class FrozenProjectionTest(unittest.TestCase):
    """Seam 3：投影冻结——运行时不存在改写路径（AC 1 行为面 / enforce 机制）。"""

    def test_projection_is_frozen(self):
        i = parse_identity(_carrier())
        with self.assertRaises(AttributeError):
            i.name = "other"
        with self.assertRaises(AttributeError):
            i.behavioral_habits = ()

    def test_no_mutation_api_on_class(self):
        """类表面除构造器外无 mutation API（写接口结构性不存在，enforce 决定 ②）。"""
        mutators = [
            n
            for n in dir(Identity)
            if n.startswith(("set_", "update_", "mutate", "write"))
            or n in ("replace",)
        ]
        self.assertEqual(mutators, [])


if __name__ == "__main__":
    unittest.main()
