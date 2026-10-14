"""World 观察 adapter —— EXTERNAL WORLD 边界的只读观察手段（M06）。

依据：spec-adapters.md §4（world seam = real 接近：单 adapter、hypothetical、
不预设第二个观察类型）、K-07（保留条件 1：root 等部署值 → 注入，R-09；
保留条件 2：`FileObservation` 的 Domain 定位待 Domain 建模确认——本模块
不预设其为 Domain 概念，仅为观察产物）、K-08 纪律（观察 = 带来源的事实，
不是判断）；V0 形态参考：dao_sheng/world/file.py（只读 + 路径逃逸守卫）。

- `observe(relative_path) -> FileObservation`：只读 stat/exists，不做任何写入、
  删除、创建（INV-7：观察 / 投影产物不得回流为个体经历——本模块没有写个体
  状态的通道；观察结果进个体经验流的通道 = M04 回合入口，由 M04 决定）。
- root = 部署层值，由调用方注入（R-09：本模块不预设任何绝对位置）。
- 本模块不 import 其他 V1 模块。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileObservation:
    """一次文件观察的产物（带来源的事实：path 即来源）。

    观察 ≠ 判断（K-08 纪律）：这里只有如实报告的存在性 / 类型 / 大小，
    不含任何解释或评估。
    """

    path: str
    exists: bool
    is_file: bool
    size: int | None = None


class FileWorld:
    """只读文件观察 adapter（world seam 的当前唯一 adapter）。

    观察范围被 root 边界限定：越过 root 的路径 → fail-loud（ValueError），
    不静默越界（V0 形态保留；守卫在 resolve 后执行，符号链接 / ".." 均被
    拦下）。
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def observe(self, relative_path: str) -> FileObservation:
        """观察 root 下的一条相对路径，返回 FileObservation（只读）。"""
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Path escapes DaoSheng world root.") from exc
        is_file = candidate.is_file()
        return FileObservation(
            path=str(candidate),
            exists=candidate.exists(),
            is_file=is_file,
            size=candidate.stat().st_size if is_file else None,
        )
