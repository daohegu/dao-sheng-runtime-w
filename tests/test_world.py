"""World 观察 adapter — M06（EXTERNAL WORLD 边界；K-07 / spec-adapters §2 相邻）。

Seam：`FileWorld.observe(relative_path) -> FileObservation`（world seam，
接近 real：单 adapter、不预设第二个观察类型）；
观察结果进个体经验流的通道 = M04 回合入口，本模块只提供观察手段，
不写个体状态（INV-7：投影 / 观察不回流）。

依据：spec-adapters.md §4（world seam 状态）、K-07（model/ + world/ seam
位置正确；保留条件：root 等部署值 → 注入，R-09；FileObservation 的
Domain 定位待 Domain 建模确认——本模块不预设为 Domain 概念）、
K-08 纪律（观察 = 带来源的事实，不是判断）；
V0 形态参考：dao_sheng/world/file.py（只读 stat/exists + 路径逃逸守卫）。
"""

import tempfile
import unittest
from pathlib import Path

from dao_sheng.world import FileObservation, FileWorld


class FileWorldTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "note.txt").write_text("观察对象", encoding="utf-8")
        (self.root / "sub").mkdir()
        self.world = FileWorld(self.root)

    def test_observe_existing_file(self):
        """存在文件：path / exists / is_file / size 全部如实报告（观察 ≠ 判断）。"""
        obs = self.world.observe("note.txt")
        self.assertIsInstance(obs, FileObservation)
        self.assertTrue(obs.exists)
        self.assertTrue(obs.is_file)
        self.assertEqual(obs.path, str(self.root / "note.txt"))
        self.assertEqual(obs.size, len("观察对象".encode("utf-8")))

    def test_observe_missing_file(self):
        """不存在：exists=False，is_file=False，size=None——不猜测。"""
        obs = self.world.observe("nope.txt")
        self.assertFalse(obs.exists)
        self.assertFalse(obs.is_file)
        self.assertIsNone(obs.size)

    def test_observe_directory(self):
        """目录：exists=True 但 is_file=False、size=None。"""
        obs = self.world.observe("sub")
        self.assertTrue(obs.exists)
        self.assertFalse(obs.is_file)
        self.assertIsNone(obs.size)

    def test_observe_nested_path(self):
        (self.root / "sub" / "deep.txt").write_text("x", encoding="utf-8")
        obs = self.world.observe("sub/deep.txt")
        self.assertTrue(obs.is_file)
        self.assertEqual(obs.size, 1)

    def test_path_escape_rejected(self):
        """路径逃逸守卫：越过 root 的相对路径 → fail-loud（ValueError）。"""
        with self.assertRaises(ValueError):
            self.world.observe("../outside.txt")

    def test_observe_is_read_only(self):
        """观察不产生任何写入：root 内容在 observe 前后不变（INV-7 无回流通道的
        行为面——本模块根本没有写通道）。"""
        before = sorted(p.name for p in self.root.iterdir())
        self.world.observe("note.txt")
        self.world.observe("nope.txt")
        after = sorted(p.name for p in self.root.iterdir())
        self.assertEqual(before, after)

    def test_root_is_injected_not_defaulted(self):
        """R-09：root = 部署层值，注入；无默认值（结构面）。"""
        import inspect

        sig = inspect.signature(FileWorld.__init__)
        self.assertIs(
            sig.parameters["root"].default, inspect.Parameter.empty
        )
        # 注入的 root 被 resolve 后公开（可检查，非隐藏状态）
        self.assertEqual(self.world.root, self.root.resolve())


if __name__ == "__main__":
    unittest.main()
