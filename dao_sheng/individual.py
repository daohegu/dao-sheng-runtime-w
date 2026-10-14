"""Individual 顶层聚合 —— 回合模型 + 经验回流（M04；spec-individual.md 全对象）。

依据：spec-individual.md §1–§6（双入口 R-01 / 单回合原子 §2 / 重启语义三事件
§3 / persistent vs runtime 分类 §4 / 投影纪律 §5 / 全部依赖构造注入 §6）、
R-08（无跨类私有调用）、R-09（依赖注入面）、INV-7（投影不回流）、
INV-1（手段故障 ≠ 个体故障）、Q2（三维语义层显式）、C-2（turn 计数 =
runtime，不持久）。

- 两阶段回合（决定 ⑬）：`act(turn)` 产出行动并暂存（runtime 状态，不持久）；
  `persist()` = 唯一提交点 —— 单条 Memory 记录原子写入（经注入的
  MemoryStore，本模块零直接 I/O）；生命周期严格交替 act → persist，
  违例 fail-loud（ValueError）。
- 回合输入（决定 ⑭）：`Turn(content, memory_origin)` 中性概念（ADR 0002
  无宿主名）；另两维 Core 规则固定：回合经历记录恒 status=OBSERVED /
  confidence=CONFIRMED。
- 记录形态（决定 ⑮）：content = 经历 / 行动 两行；不含 turn 计数（C-2）、
  不含投影文本（INV-7）；persist 返回的 reference = 该记录句柄（M09 幂等
  重导入去重依据）。
- 降级回合（决定 ⑯）：model 未装配或调用不可用 → 行动 None，经历仍记录，
  act 不抛异常（INV-1）。
- 投影装配（决定 ⑰）：messages = [(system, 投影), (user, 回合内容)]；
  投影 = 身份 / 道 / 行为倾向 / 经历（continuity 最近 32 条）/ 记忆
  （recall 全集 ≤32）节，空节省略；可裁剪、不得引入宿主 / 模型 / 存储细节
  （R-12 / INV-7 / M-05）。
- continuity 读通道（决定 ⑱）：每回合按需 load_continuity（不携带装配时
  快照）；本模块不追加 continuity（唯一调用方 = 成长管线，M07；引用源
  棘轮守卫）。
- 本模块零直接 I/O（全部持久化经注入的 MemoryStore 方法 + load_continuity
  纯读函数）→ 既有 I/O 棘轮无需放宽位；import 面 = 类型 / 枚举值 / 异常
  类型引用（白名单棘轮显式调整，决定 ⑲）；构造只发生在 composition root
  （棘轮固化）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from dao_sheng.continuity import load_continuity
from dao_sheng.doctrine import Doctrine
from dao_sheng.faculties import Faculties
from dao_sheng.identity import Identity
from dao_sheng.memory import MemoryConfidence, MemoryOrigin, MemoryStatus, MemoryStore, RecallQuery
from dao_sheng.model import Model, ModelUnavailable

#: 经历节投影上限（最近 N 条；可裁剪 = M-05 纪律）。
_CONTINUITY_PROJECTION_LIMIT = 32


@dataclass(frozen=True)
class Turn:
    """一个回合的输入（决定 ⑭）：内容 + 来源维度；另两维由 Core 规则固定。"""

    content: str
    memory_origin: MemoryOrigin

    def __post_init__(self) -> None:
        if not self.content or not self.content.strip():
            raise ValueError("Turn.content 不得为空（空内容无回合意义；fail-loud）")


@dataclass(frozen=True)
class TurnOutcome:
    """一个回合的结果：turn 计数（runtime，C-2）+ 行动（降级回合 = None）。"""

    turn_number: int
    action: str | None


class Individual:
    """Individual 顶层聚合（spec-individual.md §1）：唯一入口对
    act / persist（R-01）；顶层无内部 seam（K-10：interface = test
    surface）；全部依赖构造注入（R-09），构造只发生在装配点。"""

    def __init__(
        self,
        *,
        doctrine: Doctrine,
        identity: Identity,
        faculties: Faculties,
        continuity_file: Path,
        memory: MemoryStore,
        model: Model | None,
    ) -> None:
        """全部依赖注入、无默认值（R-09）；model = None → 全部回合降级
        （决定 ⑯，U-5 未装配态）。"""
        self._doctrine = doctrine
        self._identity = identity
        self._faculties = faculties
        self._continuity_file = continuity_file
        self._memory = memory
        self._model = model
        # runtime 状态（§4：不持久；C-2：turn 计数不是载体内容）
        self._turn_count = 0
        self._pending_turn: Turn | None = None
        self._pending_action: str | None = None

    def act(self, turn: Turn) -> TurnOutcome:
        """单回合入口（R-01）：产出行动并暂存为进行中回合（runtime 状态）。

        严格交替：已有未提交回合 → fail-loud（先 persist）。手段故障 →
        降级回合（行动 None，不抛异常，INV-1）。
        """
        if self._pending_turn is not None:
            raise ValueError("已有未提交的进行中回合：先 persist 再 act")
        self._turn_count += 1
        action = self._produce_action(turn)
        self._pending_turn = turn
        self._pending_action = action
        return TurnOutcome(turn_number=self._turn_count, action=action)

    def persist(self) -> str:
        """唯一提交点（决定 ⑬）：进行中回合 → 单条 Memory 记录（原子）。

        返回 reference（该记录句柄；M09 幂等重导入去重依据）。
        无进行中回合 → fail-loud。
        """
        if self._pending_turn is None:
            raise ValueError("没有进行中回合可提交：先 act 再 persist")
        turn, action = self._pending_turn, self._pending_action
        self._pending_turn = None
        self._pending_action = None
        return self._memory.remember(
            content=self._experience_content(turn, action),
            memory_origin=turn.memory_origin,
            memory_status=MemoryStatus.OBSERVED,
            memory_confidence=MemoryConfidence.CONFIRMED,
        )

    def _produce_action(self, turn: Turn) -> str | None:
        """行动产出（决定 ⑰ / ⑯）：经注入的 model chat 调用；手段未装配
        或不可用 → None（降级回合；INV-1）。"""
        if self._model is None:
            return None
        messages = [("system", self._assemble_projection()), ("user", turn.content)]
        try:
            return self._model.chat(messages)
        except ModelUnavailable:
            return None

    def _experience_content(self, turn: Turn, action: str | None) -> str:
        """回合经历记录内容（决定 ⑮）：经历 / 行动 两行；无 turn 计数
        （C-2）、无投影文本（INV-7）。"""
        action_text = "无" if action is None else action
        return f"经历：{turn.content}\n行动：{action_text}"

    def _assemble_projection(self) -> str:
        """投影装配（决定 ⑰；§5 纪律：可裁剪、可改写措辞、不得另立来源；
        不得引入宿主 / 模型 / 存储细节；内容不得回流为经历，INV-7）。"""
        sections: list[str] = []
        identity_lines = ["身份："]
        for label, value in (
            ("姓名", self._identity.name),
            ("自称", self._identity.self_appellation),
            ("声音", self._identity.voice),
            ("形象", self._identity.visual_image),
        ):
            if value:
                identity_lines.append(f"{label}：{value}")
        for label, values in (
            ("行为倾向", self._identity.behavioral_habits),
            ("过往经历", self._identity.past_experiences),
            ("持续记忆", self._identity.continuous_memory),
        ):
            if values:
                identity_lines.append(f"{label}：" + " / ".join(values))
        sections.append("\n".join(identity_lines))
        sections.append(
            "道：\n"
            + "\n".join(
                f"{i}. {p.name}：{p.text}"
                for i, p in enumerate(self._doctrine.principles, start=1)
            )
        )
        sections.append("行为倾向：" + " / ".join(self._faculties.roots))
        continuity = load_continuity(self._continuity_file).records
        if continuity:
            records = [dict(record) for record in continuity[-_CONTINUITY_PROJECTION_LIMIT:]]
            sections.append(
                "经历：\n"
                + "\n".join(
                    json.dumps(record, ensure_ascii=False, sort_keys=True)
                    for record in records
                )
            )
        memories = self._memory.recall(RecallQuery())
        if memories:
            sections.append("记忆：\n" + "\n".join(m.content for m in memories))
        return "\n\n".join(sections)
