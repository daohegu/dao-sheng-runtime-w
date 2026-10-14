"""Faculties 状态载体模块（读 / 严格校验 / 保护隐藏）— M03。

Seam（票 Comments 清单 6）：`FACULTY_ROOTS` 单一来源（Q3 初始 8 根）、
`parse_faculties` 严格"恰好 8 根"（未知根 / 缺根 / 重复 / 非字符串 /
顶层非数组 → 拒绝）、`Faculties` 冻结投影（AC 3）。

依据：spec-self-state.md §3（8 根初始集 Q3 USER_RATIFIED；增删根 =
Domain 决策，非实现层）、domain-invariants.md §1.2（Faculty ≠
Capability）、keep.md K-09（faculty 独立概念层）/ D-7（白名单双维护
收敛单一来源）、M03 决定 ④ 载体形态（单 JSON 文件；内容形态不预设
——规则 11）。
"""

import json
import unittest

from dao_sheng.faculties import FACULTY_ROOTS, Faculties, parse_faculties

EIGHT_ROOTS = (
    "intent",
    "choice",
    "stopping",
    "observation",
    "correction",
    "selection",
    "reflection",
    "continuity",
)


class FacultyRootsTest(unittest.TestCase):
    """Seam 6a：`FACULTY_ROOTS` 单一来源 = Q3 初始 8 根（无增无减）。"""

    def test_exactly_eight_roots(self):
        """AC 3 结构面：初始集 = 8 根，无增无减（Q3 USER_RATIFIED）。"""
        self.assertEqual(tuple(FACULTY_ROOTS), EIGHT_ROOTS)
        self.assertEqual(len(set(FACULTY_ROOTS)), 8)


class ParseFacultiesTest(unittest.TestCase):
    """Seam 6b：`parse_faculties` 严格"恰好 8 根"。"""

    def test_legal_carrier_to_frozen_projection(self):
        f = parse_faculties(json.dumps(EIGHT_ROOTS, ensure_ascii=False))
        self.assertEqual(f.roots, EIGHT_ROOTS)

    def test_root_order_in_carrier_is_ignored(self):
        """载体根序无意义——投影归一化为单一来源序（单一来源，D-7）。"""
        shuffled = list(reversed(EIGHT_ROOTS))
        f = parse_faculties(json.dumps(shuffled))
        self.assertEqual(f.roots, EIGHT_ROOTS)

    def test_non_array_top_level_rejected(self):
        for text in ("{}", "42", '"intent"', "null", "not json"):
            with self.assertRaises(ValueError, msg=text):
                parse_faculties(text)

    def test_non_string_element_rejected(self):
        roots = list(EIGHT_ROOTS)
        roots[0] = 1
        with self.assertRaises(ValueError):
            parse_faculties(json.dumps(roots))

    def test_unknown_root_rejected(self):
        roots = list(EIGHT_ROOTS)
        roots.append("capability")
        with self.assertRaises(ValueError) as ctx:
            parse_faculties(json.dumps(roots))
        self.assertIn("capability", str(ctx.exception))

    def test_missing_root_rejected(self):
        roots = EIGHT_ROOTS[:7]  # 缺 "continuity" 根
        with self.assertRaises(ValueError) as ctx:
            parse_faculties(json.dumps(roots))
        self.assertIn("continuity", str(ctx.exception))

    def test_duplicate_root_rejected(self):
        roots = list(EIGHT_ROOTS[:7]) + ["intent"]
        with self.assertRaises(ValueError):
            parse_faculties(json.dumps(roots))


class FrozenProjectionTest(unittest.TestCase):
    """Seam 6c：`Faculties` 冻结投影——无 mutation API，无增删根入口。"""

    def test_projection_is_frozen(self):
        f = parse_faculties(json.dumps(EIGHT_ROOTS))
        with self.assertRaises(AttributeError):
            f.roots = ()

    def test_no_mutation_api_on_class(self):
        """AC 3 结构面：增删根 = Domain 决策（非实现层）——类表面无
        mutation API；模块表面亦无 add / remove 根入口。"""
        import dao_sheng.faculties as mod

        mutators = [
            n
            for n in dir(Faculties)
            if n.startswith(("set_", "update_", "mutate", "write"))
            or n in ("replace", "save", "append", "extend", "add", "remove")
        ]
        self.assertEqual(mutators, [])
        for name in ("add_root", "remove_root", "add_faculty", "remove_faculty"):
            self.assertFalse(hasattr(mod, name))


if __name__ == "__main__":
    unittest.main()
