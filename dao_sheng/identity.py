"""Identity（身份）运行时 typed 投影 —— 加载 / 校验 / 保护隐藏。

依据：spec-self-state.md §1/§4（immutable，V1 不得弱化）、
data-ownership.md §2（Identity 行：仅设计层可写，任何运行时路径绝对不可写）、
constitution.md §3、CINV-3（外部直接重写 Forbidden）、
INV-2 / 规则 2、4（载体无 model / worker / host 字段）、
K-11（历史形态参考，非 KEEP 依据——规则 12）。

- 只读投影：frozen dataclass，类表面不存在任何 mutation API
  （enforce 机制 = "写接口结构性不存在"）。
- 严格 schema：载体 = 恰好 7 个支撑项键（B1-E6）；未知键（含
  model / worker / host）/ 缺键 / 类型不符 / name 为空 → 显式拒绝。
- 延续判据（"仍然还是谁"）= UNKNOWN（Q5），本模块不提供（规则 11）。
- 纯值 + 纯解析，不做 I/O（I/O 归 composition root，R-09）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass

#: 载体 schema —— 恰好 7 个支撑项键（spec-self-state.md §1 / B1-E6）。
#: 顺序即 dataclass 字段顺序；任何增删由结构棘轮测试守护。
_SCALAR_FIELDS = ("name", "self_appellation", "voice", "visual_image")
_LIST_FIELDS = ("behavioral_habits", "past_experiences", "continuous_memory")
_FIELDS = _SCALAR_FIELDS + _LIST_FIELDS


@dataclass(frozen=True)
class Identity:
    """Identity 只读投影：7 个支撑项（B1-E6）。

    frozen —— 运行时不存在改写路径（immutable；constitution §3）。
    list 支撑项投影为 tuple（不可变）。
    """

    name: str
    self_appellation: str
    voice: str
    visual_image: str
    behavioral_habits: tuple[str, ...]
    past_experiences: tuple[str, ...]
    continuous_memory: tuple[str, ...]


def parse_identity(source_text: str) -> Identity:
    """解析合法载体文档文本 → 冻结只读投影；非法载体一律显式拒绝。

    严格 schema：恰好 7 个支撑项键，不多不少。载体内容 = 设计层值，
    本函数不预设、不改写任何内容（规则 11）。
    """
    try:
        doc = json.loads(source_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Identity 载体不是合法 JSON 文档：{e}") from e

    if not isinstance(doc, dict):
        raise ValueError(
            f"Identity 载体必须是 JSON 对象，实际为 {type(doc).__name__}"
        )

    unknown = set(doc) - set(_FIELDS)
    if unknown:
        raise ValueError(
            f"Identity 载体含未知键（严格 schema = 恰好 7 支撑项键）：{sorted(unknown)}"
        )
    missing = set(_FIELDS) - set(doc)
    if missing:
        raise ValueError(f"Identity 载体缺键：{sorted(missing)}")

    values: dict[str, object] = {}
    for field in _SCALAR_FIELDS:
        value = doc[field]
        if not isinstance(value, str):
            raise ValueError(
                f"Identity 载体字段 {field!r} 必须是 string，实际为 {type(value).__name__}"
            )
        values[field] = value
    if not values["name"]:
        raise ValueError("Identity 载体字段 'name' 不得为空")
    for field in _LIST_FIELDS:
        value = doc[field]
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError(
                f"Identity 载体字段 {field!r} 必须是 string 列表，实际为 {type(value).__name__}"
            )
        values[field] = tuple(value)

    return Identity(**values)  # type: ignore[arg-type]
