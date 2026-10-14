"""个体持久文件清单（5 项）— M01（清单定义）/ M02·M03（载体形态落位）。

Seam：`IndividualFiles.layout`（注入 root → 清单 5 项派生路径）。

依据：spec-individual.md §4（持久 vs 运行时判据 + 5 项清单；
清单之外的任何文件都不是个体状态）、container-model.md §2/§3
（Runtime 进程拥有个体持久文件）、spec-adapters.md §5（进程边界）。
"""

import inspect
import unittest
from pathlib import Path

from dao_sheng.layout import IndividualFiles


class IndividualFilesTest(unittest.TestCase):
    def test_layout_has_exactly_the_five_items_under_root(self):
        """5 项清单全部派生自注入 root（Memory / Capability 为目录，其余为文件）。"""
        root = Path("C:/daosheng/individual")
        f = IndividualFiles.layout(root)
        self.assertEqual(f.root, root)
        # M02 决定 ①：Identity 载体 = 单 JSON 文件 root/"identity.json"
        self.assertEqual(f.identity, root / "identity.json")
        # M03 决定 ③：Continuity 载体 = 单 append-only 日志文件
        self.assertEqual(f.continuity, root / "continuity.jsonl")
        self.assertEqual(f.memory_dir, root / "memory")
        self.assertEqual(f.capabilities_dir, root / "capabilities")
        # M03 决定 ④：Faculties 载体 = 单 JSON 文件
        self.assertEqual(f.faculties, root / "faculties.json")

    def test_layout_is_immutable(self):
        """清单是 Runtime 侧的只读边界，不得被运行时改写。"""
        f = IndividualFiles.layout(Path("C:/daosheng/individual"))
        with self.assertRaises(AttributeError):
            f.identity = Path("other")
        with self.assertRaises(AttributeError):
            f.memory_dir = Path("other")

    def test_root_is_injected_not_preset(self):
        """root = 部署层值（container-model：个体落位由部署层决定）——不得有默认值。"""
        sig = inspect.signature(IndividualFiles.layout)
        for p in sig.parameters.values():
            self.assertIs(
                p.default,
                inspect.Parameter.empty,
                f"layout 参数 {p.name} 不得有默认值（不预设个体落位）",
            )


if __name__ == "__main__":
    unittest.main()
