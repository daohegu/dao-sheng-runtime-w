"""Doctrine（"道"文本）运行时 typed 投影 — M01。

Seam：`parse_doctrine`（纯函数：注入的来源文本 → 只读 typed 投影）；
`Doctrine` / `Principle` 不可变（CINV-2 / K-11）。

依据：ADR 0005、spec-composition-root.md §2、M-05/D-6。
"""

import unittest
from pathlib import Path

from dao_sheng.doctrine import Doctrine, Principle, parse_doctrine

REPO_ROOT = Path(__file__).resolve().parents[1]
PRINCIPLES = REPO_ROOT / "docs" / "constitution" / "principles.md"

# 独立期望来源 = 设计层成文单一来源（principles.md 头注"六条文本"，
# STEP 10 已核验与 V0 两仓库逐字一致）。以下为已知良好字面量。
EXPECTED = (
    ("不妄动", "没有必要与依据，不主动行动。"),
    ("知止", "知道什么时候应该停止，而不是为了完成而无限执行。"),
    ("顺势", "优先利用现有环境、工具与条件，而不是强行改造世界。"),
    ("反思", "经历产生反馈，反馈应进入后续学习。"),
    ("海纳百川", "外部知识、模型、工具与观点可以进入，但必须保留来源。"),
    (
        "道心稳固",
        "外部输入可以改变知识与能力，但不能直接改写 Identity / Continuity / Core Doctrine。",
    ),
)


class ParseDoctrineTest(unittest.TestCase):
    def test_projects_current_written_subset(self):
        """当前成文子集（Q1：六条）被完整、按序投影。"""
        doctrine = parse_doctrine(PRINCIPLES.read_text(encoding="utf-8"))
        self.assertIsInstance(doctrine, Doctrine)
        self.assertEqual(
            [(p.name, p.text) for p in doctrine.principles], list(EXPECTED)
        )
        for p in doctrine.principles:
            self.assertIsInstance(p, Principle)

    def test_each_text_traceable_to_source(self):
        """验收 2：运行时副本可溯源——每条全文（名：文）逐字出现在设计层来源中。"""
        source = PRINCIPLES.read_text(encoding="utf-8")
        for p in parse_doctrine(source).principles:
            self.assertIn(f"{p.name}：{p.text}", source)

    def test_only_canonical_numbered_lines_are_projected(self):
        """正文各条的"成文文本"行不带名、不参与投影——只取头注编号清单。"""
        doctrine = parse_doctrine(PRINCIPLES.read_text(encoding="utf-8"))
        self.assertEqual(len(doctrine.principles), len(EXPECTED))
        self.assertEqual(
            [p.name for p in doctrine.principles], [n for n, _ in EXPECTED]
        )

    def test_missing_canonical_list_raises(self):
        """来源中没有成文清单时显式失败，不静默产出空 Doctrine。"""
        with self.assertRaises(ValueError):
            parse_doctrine("# 空文件\n\n没有任何成文文本。\n")

    def test_doctrine_immutable(self):
        """CINV-2 / K-11：运行时任何路径不可改写 Core Doctrine。"""
        doctrine = parse_doctrine(PRINCIPLES.read_text(encoding="utf-8"))
        with self.assertRaises(AttributeError):
            doctrine.principles = ()
        first = doctrine.principles[0]
        with self.assertRaises(AttributeError):
            first.text = "篡改"
        with self.assertRaises(AttributeError):
            first.name = "篡改"


if __name__ == "__main__":
    unittest.main()
