"""Capability 生命周期 — M08（spec-capability.md 全对象 + ADR 0003）。

状态机 `proposed → working → active → retired` = Core Domain 概念（ADR 0003
决定 1）：生命周期语义在状态机，不是目录结构的副产品（K-04 反例纠正——V0
用目录当生命周期，V1 用状态机当生命周期）。四目录 = 状态机的一个合法
adapter 形态（ADR 0003 决定 3）：目录名与状态名对齐；四目录是状态的物理
表达，记录文件不带状态字段（D-5 单一表示——状态 = 记录的目录位置；状态
转换 = 文件移动，记录内容永不改写）。状态集扩展 = Domain 决策（§6
Re-evaluation Trigger → 复审 ADR 0003，棘轮固化状态集恰好 4 值）。

active 的唯一可达路径 = Verifier 执行前闸门（K-05 / INV-11）：闸门 = 本票
契约位——`CapabilityGate` 协议（verify 接收能力投影 → 布尔裁决），Verifier
经 composition root 构造注入（R-09）；闸门机制本身由 M11 实现。无旁路、
无手动提升、无 legacy 通道（D-03：legacy 验证旁路形态不存在——V1 中验证
只有闸门一处形态）。reject ⇒ 不可达 active / 执行被阻（硬行为，不是软
约束）；闸门未装配（verifier = None）⇒ 闸门操作降级 None（INV-1：手段未
装配 ≠ 个体故障，不写、不抛）。

Capability Manager 四方法 = 唯一权威生命周期（ADR 0003 决定 2/3）：
propose（登记 proposed；提案来源 = M07 经 Memory 的提案记录，决定 ㉖：
content 承载提案语义；源记录经注入的 memory 6 方法契约 get 读取——单一
事实来源，调用方不拷贝 content）/ advance（状态推进；working → active
必经闸门）/ retire（移入 retired 保留，不删除，K-06——记录文件字节不变，
历史可查）/ execute（执行前闸门，INV-11：执行同样受 Verifier 约束；非
active 状态全隔离，K-04；执行体 = 能力投影供给，执行语义集成属 M09 /
M12 域，规则 11 不臆造）。

A-7 反例禁止：本模块是唯一触碰能力载体目录的组件——载体根经 composition
root 注入（accept don't create），内部路径全部由注入根 + 状态名 + 能力名
派生；任何其他组件不得直接构造 `root/"active"/name` 路径"提升"能力
（棘轮固化：`capabilities_dir` 引用位仅 layout / composition / 本模块）。

fail-loud 面（决定 ㉙）：能力不存在 / 双重物理放置（同名记录出现在多个
状态目录 = 载体损坏）/ 记录 schema 非法 / 名称与文件名不交叉 / 非法状态
转换（无后退、无跳过、retired 终态）/ 闸门 reject → ValueError；proposal
reference 缺失 → ValueError（M05 get 契约）；name 空白 / 含路径分隔符 →
ValueError。载体缺失（目录不存在）= 初始状态 = 无能力，不代建根目录
（首个 propose / 转换创建所需状态目录，ADR 0007 初始态语义对齐）。

依据：spec-capability.md §1–§7、ADR 0003 决定 1–4、spec-individual.md §4
（清单项 4）、审计 K-04 / K-05 / K-06 / A-7 / D-03 / R-04、INV-1 /
INV-11。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol


class CapabilityState(Enum):
    """能力生命周期状态（ADR 0003 决定 1：4 状态，无新增——状态集扩展 =
    Domain 决策，棘轮固化）。值 = 四目录 adapter 形态的目录名（决定 ㉘）。"""

    PROPOSED = "proposed"
    WORKING = "working"
    ACTIVE = "active"
    RETIRED = "retired"


#: 状态机转换表（ADR 0003 决定 1）：合法转换的全部集合——
#: proposed → working → active 正向推进（working → active 必经闸门，
#: 闸门在 advance / execute 内 enforce，不在本表）；任意非终态 → retired
#: （retire 保留不删除，K-06）；retired = 终态（无出边）；无后退、
#: 无跳过（proposed 不可直达 active）。
_TRANSITIONS: frozenset[tuple[CapabilityState, CapabilityState]] = frozenset(
    {
        (CapabilityState.PROPOSED, CapabilityState.WORKING),
        (CapabilityState.WORKING, CapabilityState.ACTIVE),
        (CapabilityState.PROPOSED, CapabilityState.RETIRED),
        (CapabilityState.WORKING, CapabilityState.RETIRED),
        (CapabilityState.ACTIVE, CapabilityState.RETIRED),
    }
)


@dataclass(frozen=True)
class Capability:
    """能力投影（D-5 单一表示）：name + content + 源记忆记录 reference。

    载体记录文件不带状态字段——状态 = 记录所在目录位置（由 Manager 判定，
    调用方经方法语义获知）；投影本身无状态。
    """

    name: str
    content: str
    source_reference: str


class CapabilityGate(Protocol):
    """闸门契约位（K-05 / INV-11；机制由 M11 交付）。

    `verify` 接收能力投影，返回裁决：True = 放行，False = 拒绝（拒绝 ⇒
    不可达 active / 执行被阻——硬行为）。本票只交付契约位 + 注入位 + 硬
    行为；无任何其他验证形态（D-03：legacy 验证旁路不复存在）。
    """

    def verify(self, capability: Capability) -> bool:
        ...


class CapabilityManager:
    """能力生命周期唯一权威（ADR 0003 决定 2/3）：四方法
    propose / advance / retire / execute 是全部生命周期操作——无旁路
    方法、无直接状态写（棘轮固化公共表面）。

    载体形态（决定 ㉘，四目录 adapter 形态）：每个能力 = 当前状态目录下
    单 JSON 记录文件 `<name>.json`，严格 schema 恰好 3 键
    {"name", "content", "source_reference"}；name 四目录全局唯一（一个
    name = 一个生命周期，再次提案 = 新 name）；状态转换 = 文件移动
    （原子）；retire = 移入 retired/ 保留不删除（K-06，字节不变）。
    """

    def __init__(
        self,
        *,
        capabilities_dir: Path,
        memory: object,
        verifier: object | None,
    ) -> None:
        """3 项依赖全部构造注入（R-09），无默认值：capabilities_dir
        （能力载体根 = 个体持久文件清单项 4；唯一载体触碰点，A-7 棘轮）、
        memory（MemoryStore 契约实例：提案源记录读通道）、verifier
        （闸门契约位实例；None = M11 闸门机制未交付 → 闸门操作降级，
        INV-1，决定 ㉙）。"""
        self._capabilities_dir = capabilities_dir
        self._memory = memory
        self._verifier = verifier

    # -- 四方法（唯一权威生命周期，ADR 0003 决定 2/3） --

    def propose(self, name: str, reference: str) -> Capability:
        """登记 proposed（提案来源 = M07 经 Memory 的提案记录，决定 ㉖ /
        ADR 0003 决定 4）：content 经注入 memory 的 get 从源记录读取
        （单一事实来源，调用方不拷贝 content）。

        校验（fail-loud）：name 非空白、不含路径分隔符、非 "." / ".."；
        reference 存在（M05 get 契约）；源记录 content 非空；name 四目录
        全局唯一（已存在于任一状态 → 拒绝）。"""
        if not name or not name.strip():
            raise ValueError("能力名不得为空白")
        if "/" in name or "\\" in name or name in (".", ".."):
            raise ValueError(f"能力名不得含路径分隔符或为 '.' / '..'：{name}")
        content = self._memory.get(reference).content
        if not content or not content.strip():
            raise ValueError(f"源记忆记录 content 不得为空：{reference}")
        current, _ = self._locate(name)
        if current is not None:
            raise ValueError(f"能力名已存在（状态 {current.value}）：{name}")
        state_dir = self._capabilities_dir / CapabilityState.PROPOSED.value
        state_dir.mkdir(parents=True, exist_ok=True)
        record = Capability(name=name, content=content, source_reference=reference)
        self._write_record(state_dir / f"{name}.json", record)
        return record

    def advance(self, name: str, to: CapabilityState) -> Capability | None:
        """状态推进（合法转换 = 状态机表：无后退、无跳过、retired 终态）。

        working → active 必经闸门（active 唯一可达路径，K-05 / INV-11）：
        闸门未装配（verifier = None）→ 返回 None（降级，INV-1：不写、
        不抛）；reject → ValueError（硬行为：不可达 active）；放行 → 文件
        移动 + 返回能力投影。非法转换 / 能力不存在 → ValueError。"""
        current, capability = self._load(name)
        if (current, to) not in _TRANSITIONS:
            raise ValueError(
                f"非法状态转换：{current.value} → {to.value}（{name}）"
            )
        if to is CapabilityState.ACTIVE:
            if self._verifier is None:
                return None
            if not self._verifier.verify(capability):
                raise ValueError(f"闸门拒绝，不可达 active（INV-11）：{name}")
        self._move(name, current, to)
        return capability

    def retire(self, name: str) -> Capability:
        """退役（K-06 保留不删除）：记录文件移入 retired/，内容字节
        不变——历史可查。retired = 终态：对已退役能力再 retire →
        ValueError（终态无出边）。"""
        current, capability = self._load(name)
        if (current, CapabilityState.RETIRED) not in _TRANSITIONS:
            raise ValueError(f"非法状态转换：{current.value} → retired（{name}）")
        self._move(name, current, CapabilityState.RETIRED)
        return capability

    def execute(self, name: str) -> Capability | None:
        """执行前闸门（INV-11）：执行同样受 Verifier 约束——能力必须处于
        active（其余状态全隔离，K-04：非 active 不可执行），再过闸门：
        闸门未装配（verifier = None）→ None（降级，INV-1）；reject →
        ValueError；放行 → 返回能力投影（执行体 = 投影供给；执行语义
        集成属 M09 / M12 域，规则 11 不臆造）。"""
        current, capability = self._load(name)
        if current is not CapabilityState.ACTIVE:
            raise ValueError(
                f"仅 active 状态能力可执行（K-04）：当前 {current.value}（{name}）"
            )
        if self._verifier is None:
            return None
        if not self._verifier.verify(capability):
            raise ValueError(f"闸门拒绝，执行被阻（INV-11）：{name}")
        return capability

    # -- 载体内部机制（决定 ㉘：四目录 adapter 形态） --

    def _locate(self, name: str) -> tuple[CapabilityState | None, Path | None]:
        """按 name 定位当前状态：扫描 4 个状态目录。不存在 → (None,
        None)；双重物理放置（同名记录出现在多个状态目录 = 载体损坏）→
        ValueError（fail-loud，不猜哪个是真的）。"""
        hits = [
            (state, self._capabilities_dir / state.value / f"{name}.json")
            for state in CapabilityState
            if (self._capabilities_dir / state.value / f"{name}.json").is_file()
        ]
        if not hits:
            return None, None
        if len(hits) > 1:
            states = "、".join(state.value for state, _ in hits)
            raise ValueError(
                f"能力双重物理放置（载体损坏，出现于状态 {states}）：{name}"
            )
        return hits[0]

    def _load(self, name: str) -> tuple[CapabilityState, Capability]:
        """取能力当前状态 + 解析记录（不存在 / 损坏 → ValueError）。"""
        state, path = self._locate(name)
        if state is None or path is None:
            raise ValueError(f"能力不存在：{name}")
        return state, self._parse_record(path, name)

    def _parse_record(self, path: Path, name: str) -> Capability:
        """解析记录文件（决定 ㉘ 严格 schema）：恰好 3 键
        {"name", "content", "source_reference"}，全部非空 str，且文件内
        name 与文件名交叉一致（不一致 = 载体损坏，fail-loud）。"""
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"能力记录文件不可读或非法 JSON：{path}") from exc
        if not isinstance(doc, dict) or set(doc) != {
            "name",
            "content",
            "source_reference",
        }:
            raise ValueError(f"能力记录文件 schema 非法（恰好 3 键）：{path}")
        values = (doc["name"], doc["content"], doc["source_reference"])
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError(f"能力记录文件字段必须为非空字符串：{path}")
        if doc["name"] != name:
            raise ValueError(
                f"能力记录 name 与文件名不一致（载体损坏）：{path}"
            )
        return Capability(
            name=doc["name"],
            content=doc["content"],
            source_reference=doc["source_reference"],
        )

    def _write_record(self, path: Path, record: Capability) -> None:
        """写记录文件（决定 ㉘ 严格 3 键）。写入后永不改写——状态转换
        只移动文件（D-5 单一表示）。"""
        path.write_text(
            json.dumps(
                {
                    "name": record.name,
                    "content": record.content,
                    "source_reference": record.source_reference,
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    def _move(
        self, name: str, from_state: CapabilityState, to_state: CapabilityState
    ) -> None:
        """状态转换 = 文件移动（Path 原子移动语义；记录内容字节不变——
        retire 保留不删除 K-06 / D-5）。目标状态目录缺失 = 初始态，
        本次转换创建。"""
        source = self._capabilities_dir / from_state.value / f"{name}.json"
        target_dir = self._capabilities_dir / to_state.value
        target_dir.mkdir(parents=True, exist_ok=True)
        source.rename(target_dir / f"{name}.json")
