"""Faculties 状态载体模块（读 / 严格校验 / 保护隐藏）— M03。

Seam：`FACULTY_ROOTS`（单一来源，Q3 初始 8 根）、`parse_faculties`
（严格"恰好 8 根"，非法载体拒绝）。

依据：spec-self-state.md §3（8 根初始集，Q3 USER_RATIFIED；增删根 =
Domain 决策，非实现层行为）、domain-invariants.md §1.2（Faculty ≠
Capability：先天倾向 vs 后天之"术"；Doctrine ≠ Faculty）、keep.md K-09
（faculty 独立概念层 KEEP）/ D-7（白名单双维护收敛单一来源）。

M03 决定 ④ 载体形态：单 JSON 文件 root/"faculties.json"，内容 = JSON
数组恰好 8 根根名。内容 = 域常量（USER_RATIFIED），设计层初始化（幼体
"出生"时，M12 验收域，同批 identity 载体）；运行时装配只读（缺失 →
fail-loud 不代建，M02 决定 ② 对齐）。per-root 状态内容形态（倾向强度
等）= 无已定值，不预设（规则 11）；倾向更新机制由实现该机制的票
（个体内部机制，data-ownership §2）显式决定并记录（文件位置与本票
形态不变）。V0 FacultyState（clarity / stability / activations）仅历史
形态参考，非 KEEP 依据（规则 12）。

本模块纯无 I/O（R-09）；M03 不提供 faculties 写 API（倾向更新机制
未实现前，写接口结构性不存在——同 M02 决定 ② 骨架）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final

# 单一来源（K-09 条件 1 / D-7 收敛）：Q3 USER_RATIFIED 初始 8 根。
# 增删根 = Domain 决策（spec-self-state.md §3）——此处变更须经域文档
# 先行，非实现层行为。
FACULTY_ROOTS: Final[tuple[str, ...]] = (
    "intent",
    "choice",
    "stopping",
    "observation",
    "correction",
    "selection",
    "reflection",
    "continuity",
)


@dataclass(frozen=True)
class Faculties:
    """Faculties 读投影：根序列（归一化为 `FACULTY_ROOTS` 单一来源序）。

    frozen 容器 —— 类表面无 mutation API、无增删根入口（增删根 =
    Domain 决策，非实现层，spec-self-state.md §3）。
    """

    roots: tuple[str, ...]


def parse_faculties(source_text: str) -> Faculties:
    """合法载体文本（JSON 数组，恰好 8 根根名）→ 冻结只读投影。

    严格校验：顶层非数组 / 元素非字符串 / 未知根 / 缺根 / 重复根 →
    显式拒绝（fail-loud，不静默跳过）。载体根序无意义——校验"恰好
    8 根"后归一化为 `FACULTY_ROOTS` 序（单一来源）。
    """
    try:
        data = json.loads(source_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Faculties 载体不是合法 JSON：{e}") from e
    if not isinstance(data, list):
        raise ValueError(
            f"Faculties 载体顶层必须是 JSON 数组，实际 {type(data).__name__}"
        )
    for root in data:
        if not isinstance(root, str):
            raise ValueError(
                f"Faculties 载体元素必须是字符串根名，实际 {type(root).__name__}"
            )
    for root in set(FACULTY_ROOTS) - set(data):
        raise ValueError(f"Faculties 载体缺根：{root}")
    for root in set(data) - set(FACULTY_ROOTS):
        raise ValueError(f"Faculties 载体含未知根：{root}")
    if len(set(data)) != len(data):
        dupes = sorted({r for r in data if data.count(r) > 1})
        raise ValueError(f"Faculties 载体根重复：{dupes}")
    return Faculties(roots=FACULTY_ROOTS)
