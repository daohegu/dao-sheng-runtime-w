"""Growth 成长管线 — M07（spec-growth.md 全对象 + data-ownership.md §1）。

双通道模型的允许通道（data-ownership §1）：经历 → 消化 → 提取 → 记忆 →
复用。成长判据 INV-4 = 行为变化，不是知识增长；管线产出必须归位
（记忆记录 / Continuity 记录 / 提案记录），报告不是终点。

依赖纪律（M03 决定 ⑤ / 决定 ㉒）：本模块零 `dao_sheng` import；8 项
依赖全部由 composition 构造注入（函数值 + 类型）：memory（MemoryStore
契约实例）、append_continuity（M03 唯一写入口绑定载体路径的函数值）、
reflection_model（认知手段；None = 全部阶段降级）、三维枚举类型
（origin / status / confidence）、correction（修正记录类型）、
unavailable（手段不可用异常类型）。

全部 Memory 写只经 6 方法契约（R-08 A-1 / ADR 0006 决定 2）：无直接
记录构造、无直接存储接触。verify_insight = 域操作（INV-10），修正
形态：correct_memory（原记录不变 INV-8；修正记录 DERIVED / VERIFIED /
CONFIRMED，决定 ㉓）。

降级（决定 ㉕ / INV-1）：手段未装配 / 不可用 / 输出为空 → None——不写、
不追加、不抛异常。reference 缺失 → ValueError（M05 get 契约 fail-loud）。

Continuity 记录 schema（决定 ㉔）：JSON 对象恰 2 键
{"content": 阶段输出文本, "reference": 主体记忆记录 reference}，无判别
字段；append 仅经注入通道，唯一调用方 = 本管线（M03 决定 ⑤）。

能力提案 = reflection 阶段输出记忆记录的同款形态（决定 ㉖）：content
承载提案语义，M08 Manager 接管；本模块不触碰能力载体目录、不构造路径
（A-7 反例禁止）。

依据：spec-growth.md §1–§8、spec-memory.md §2、spec-self-state.md §2、
data-ownership.md §1、ADR 0002 / 0003 / 0006、审计 R-01…R-04 / D-06 /
A-1 / A-7、INV-1 / INV-4 / INV-8 / INV-10。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ExperienceCandidate:
    """经验回流候选（spec-growth §6 / 决定 ⑳）：中性三元
    (content, memory_origin, idempotency_key)——无宿主名（U-5 / ADR
    0002；origin 中性标注在 M09 host 层完成，本票接收中性候选）。

    fail-loud：content / idempotency_key 空白 → 构造时 ValueError。
    memory_origin 的正确性由导入处以注入枚举类型校验（候选构造处不做
    类型检查——注入类型对候选不可见）。
    """

    content: str
    memory_origin: object
    idempotency_key: str

    def __post_init__(self) -> None:
        if not self.content or not self.content.strip():
            raise ValueError("ExperienceCandidate.content 不得为空白")
        if not self.idempotency_key or not self.idempotency_key.strip():
            raise ValueError("ExperienceCandidate.idempotency_key 不得为空白")


class Growth:
    """成长管线（接口纪律，非算法；阶段机制细节 = L4，消化 / 遗忘机制
    UNKNOWN，规则 11 不臆造）。公共表面恰 5 方法（决定 ㉗，棘轮固化）。"""

    def __init__(
        self,
        *,
        memory: object,
        append_continuity: object,
        reflection_model: object | None,
        origin: type,
        status: type,
        confidence: type,
        correction: type,
        unavailable: type,
    ) -> None:
        """8 项依赖全部构造注入（R-09 / 决定 ㉒），无默认值：
        memory（MemoryStore 契约实例）、append_continuity（M03 唯一写
        入口绑定载体路径的函数值）、reflection_model（认知手段；None =
        全部阶段降级）、origin / status / confidence（三维枚举类型）、
        correction（修正记录类型）、unavailable（手段不可用异常类型）。"""
        self._memory = memory
        self._append_continuity = append_continuity
        self._reflection_model = reflection_model
        self._origin = origin
        self._status = status
        self._confidence = confidence
        self._correction = correction
        self._unavailable = unavailable
        # 管线侧幂等映射（决定 ㉑）：runtime 持有，不持久；跨进程去重
        # 协作方 = M09 host 层。
        self._imported: dict[str, str] = {}

    def import_experience(
        self, candidates: Sequence[ExperienceCandidate]
    ) -> tuple[str, ...]:
        """经验回流导入（双通道模型的允许通道，data-ownership §1）：
        候选按 Core 规则写入记忆——三维 = candidate.origin / OBSERVED /
        CONFIRMED（决定 ㉓，与 M04 回合经历记录一致）。

        管线侧幂等（决定 ㉑）：同 idempotency_key 重导入返回原
        reference、不产生新记忆。origin 非注入枚举值 → ValueError
        （中性标注必须来自 host 层）。
        """
        for candidate in candidates:
            if not isinstance(candidate.memory_origin, self._origin):
                raise ValueError(
                    "候选 origin 非注入枚举类型的值（中性标注须来自 host 层）："
                    f"{candidate.memory_origin!r}"
                )
        references: list[str] = []
        for candidate in candidates:
            key = candidate.idempotency_key
            if key not in self._imported:
                self._imported[key] = self._memory.remember(
                    content=candidate.content,
                    memory_origin=candidate.memory_origin,
                    memory_status=self._status.OBSERVED,
                    memory_confidence=self._confidence.CONFIRMED,
                )
            references.append(self._imported[key])
        return tuple(references)

    def _cognitive_output(self, reference: str, instruction: str) -> str | None:
        """认知阶段公共路径（决定 ㉕）：读源记录（M05 get 契约，
        reference 缺失 → ValueError fail-loud）→ chat 调用（会话形态：
        单条 user 消息 = 指令 + 源内容；两级调用面 seam 内的用法选择，
        M06 决定 ⑨ / ADR 0008——取值 = 模型最终回答内容，thinking 文本
        不进入回答、不作为阶段结论）→ 手段未装配 / 不可用 / 输出为空
        → None（不写、不追加、不抛异常，INV-1）；否则返回阶段输出文本
        （落库形态由各自阶段决定，决定 ㉓）。"""
        source = self._memory.get(reference).content
        model = self._reflection_model
        if model is None:
            return None
        try:
            output = model.chat([("user", f"{instruction}\n{source}")])
        except self._unavailable:
            return None
        if not output or not output.strip():
            return None
        return output

    def _remember_stage_output(self, output: str) -> str:
        """阶段输出 → 派生记忆（决定 ㉓：DERIVED / REPORTED /
        UNCERTAIN——未验证输出 = reported + uncertain，INV-10）。"""
        return self._memory.remember(
            content=output,
            memory_origin=self._origin.DERIVED,
            memory_status=self._status.REPORTED,
            memory_confidence=self._confidence.UNCERTAIN,
        )

    def digest(self, reference: str) -> str | None:
        """消化阶段：经历 → 派生记忆，返回派生记录 reference。本阶段不
        追加 continuity（只有 reflection / verify_insight 追加，决定 ㉔）。"""
        output = self._cognitive_output(
            reference, "将以下经历内容整理为适合长期记忆的一条记录："
        )
        if output is None:
            return None
        return self._remember_stage_output(output)

    def extract(self, reference: str) -> str | None:
        """提取阶段：消化 → insight 记忆（insight = Memory 的一种，
        ADR 0006：无独立存储），返回派生记录 reference。本阶段不追加
        continuity（决定 ㉔）。"""
        output = self._cognitive_output(
            reference, "从以下内容中提取一条可验证的、能指导未来行为的 insight："
        )
        if output is None:
            return None
        return self._remember_stage_output(output)

    def reflect(self, reference: str) -> str | None:
        """reflection 阶段：→ 记忆记录 + Continuity 记录（决定 ㉔ schema：
        {"content": 阶段输出, "reference": 主体记忆记录 reference}；append
        仅经注入通道，唯一调用方 = 本管线）。能力提案 = 本阶段输出记忆
        记录的同款形态（决定 ㉖：content 承载提案语义，M08 Manager
        接管）。降级 → 不写、不追加（决定 ㉕）。"""
        output = self._cognitive_output(
            reference, "基于以下内容，输出一段能改变未来行为的结论："
        )
        if output is None:
            return None
        reference_out = self._remember_stage_output(output)
        self._append_continuity({"content": output, "reference": reference_out})
        return reference_out

    def verify_insight(self, reference: str) -> str | None:
        """验证（域操作，INV-10）：insight → Memory 修正形态
        （correct_memory：原记录不变 INV-8；修正记录 DERIVED / VERIFIED /
        CONFIRMED，决定 ㉓）+ Continuity 记录（{"content": 验证输出,
        "reference": 被验证的 insight reference}，决定 ㉔）。返回修正
        记录 reference。降级 → 不写、不追加（决定 ㉕）。"""
        output = self._cognitive_output(
            reference, "验证以下 insight 是否成立，输出验证结论："
        )
        if output is None:
            return None
        correction_reference = self._memory.correct_memory(
            target=reference,
            correction=self._correction(
                content=output,
                memory_origin=self._origin.DERIVED,
                memory_status=self._status.VERIFIED,
                memory_confidence=self._confidence.CONFIRMED,
            ),
        )
        self._append_continuity({"content": output, "reference": reference})
        return correction_reference
