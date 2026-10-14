"""Doctrine（"道"文本）运行时 typed 投影。

依据：ADR 0005、spec-composition-root.md §2、M-05/D-6。

- 设计层成文单一来源 = `docs/constitution/principles.md`（只读）。
  本模块不含任何成文文本（无第二来源）——只从注入的来源文本投影。
- 投影为只读 typed 形态（frozen）：运行时任何路径不可改写（CINV-2 / K-11）。
- 投影可裁剪 / 改写措辞，不得另立来源（M-05/D-6）；M01 投影 = 逐字。
- 纯值 + 纯解析：不做 I/O、不 import 其他 V1 模块（R-09：来源文件由
  composition root 读取后以文本注入）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 来源文本中成文清单的行形制：blockquote 内的编号行（principles.md 头注"六条文本"）。
_CANONICAL_LINE = re.compile(r"^> (\d+)\. (.+?)\s*$")


@dataclass(frozen=True)
class Principle:
    """一条"道"原则的成文投影：名 + 成文文本。"""

    name: str
    text: str


@dataclass(frozen=True)
class Doctrine:
    """运行时"道"文本唯一副本（当前成文子集，Q1：六条，可增补非全部）。"""

    principles: tuple[Principle, ...]


def parse_doctrine(source_text: str) -> Doctrine:
    """从设计层来源文本投影出 Doctrine。

    只取来源中头注的编号清单行；每条按首个全角冒号分为名 / 文。
    正文各条的"成文文本"行不带名、不参与投影。
    来源文本由 composition root 读取后注入——本函数不触盘（R-09）。
    """
    principles: list[Principle] = []
    for line in source_text.splitlines():
        m = _CANONICAL_LINE.match(line)
        if m is None:
            continue
        name, sep, text = m.group(2).partition("：")
        if not sep or not name or not text:
            raise ValueError(f"无法解析成文文本行：{line!r}")
        principles.append(Principle(name=name.strip(), text=text.strip()))
    if not principles:
        raise ValueError("来源文本中未找到成文文本清单")
    return Doctrine(principles=tuple(principles))
