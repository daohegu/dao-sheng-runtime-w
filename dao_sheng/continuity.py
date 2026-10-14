"""Continuity 模块（读 / 追加 / 保护隐藏）— M03。

Seam：`parse_continuity`（载体文本 → 冻结只读投影；非法载体拒绝）、
`load_continuity`（缺失文件 = 空日志）、`append_continuity`（唯一写入
入口 = 合法内部追加通道，data-ownership §2；唯一调用方 = 成长管线，
spec-growth.md §4，M07 交付后闭环）。

依据：spec-self-state.md §2（单一载体 / append-only / 三独立 / 不是计数器）、
ADR 0004 决定 2–4、data-ownership.md §2（continuity 行：个体内部机制可
追加；覆写 / 删除 / host / model / 外部直写绝对不可）、spec-growth.md §4、
M02 决定 ② 的 M03 对齐声明（复用同一 enforce 骨架；唯一差异 = 本模块的
合法内部追加通道）。

M03 决定 ③ 载体形态：单 append-only 日志文件 root/"continuity.jsonl"，
每行 = 一条记录 = 一个 JSON 对象（stdlib json）。记录内容 schema 不预设
（无已定值，规则 11；内容 = 成长管线输出，内容形态 M07 与管线输出一起
决定）。载体物理 / 逻辑独立于 Identity 载体 / Memory / Runtime State
（ADR 0004 决定 3；C-4：Continuity 不是 Memory 的一种 kind）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Continuity:
    """Continuity 读投影：单一载体的全部记录序列（append-only）。

    frozen 容器 —— 类表面无 mutation API、无 save API（写接口结构性
    不存在，决定 ⑤；内存中记录的改动不达载体）。记录内容 = JSON 对象
    （内容 schema 不预设，规则 11）。"不是计数器"（C-2 处置）：投影
    只有记录序列本身，无任何计数 / revision 字段（C-3 处置）。
    """

    records: tuple[Mapping[str, object], ...]


def parse_continuity(source_text: str) -> Continuity:
    """合法载体文本（JSONL：每行 = 一条记录 = 一个 JSON 对象）→ 冻结只读投影。

    空文本 = 空日志（初始状态）；空行忽略（追加换行产生的合法形态）；
    任何非空行不是 JSON 对象 → 显式拒绝（fail-loud，不静默跳过）。
    """
    records: list[dict[str, object]] = []
    for line_no, line in enumerate(source_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Continuity 载体第 {line_no} 行不是合法 JSON：{e}"
            ) from e
        if not isinstance(record, dict):
            raise ValueError(
                f"Continuity 载体第 {line_no} 行必须是 JSON 对象，"
                f"实际 {type(record).__name__}"
            )
        records.append(record)
    return Continuity(records=tuple(records))


def load_continuity(path: Path) -> Continuity:
    """读 Continuity 载体：缺失文件 = 空日志（初始状态，无已定内容，规则 11；
    首次追加创建文件）；损坏行 → 显式拒绝（fail-loud，装配面校验依据）。"""
    if not path.is_file():
        return Continuity(records=())
    return parse_continuity(path.read_text(encoding="utf-8"))


def append_continuity(path: Path, record: Mapping[str, object]) -> None:
    """唯一写入入口：追加一条记录（一行 = 一个 JSON 对象，append 模式）。

    合法内部追加通道（data-ownership §2）；唯一调用方 = 成长管线
    （spec-growth.md §4，M07 交付后闭环；引用源结构棘轮保护）。
    追加不改动历史记录（append-only，ADR 0004 决定 2）。record 必须是
    JSON 对象（内容 = 成长管线输出；本模块不预设内容 schema，规则 11）。
    """
    if not isinstance(record, Mapping):
        raise ValueError("Continuity 记录必须是 JSON 对象（mapping）")
    line = json.dumps(record, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
