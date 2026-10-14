"""Capability 闸门机制 — M11 (a)（spec-capability.md §1/§2/§7 + ADR 0003）。

闸门 = active 的唯一可达路径（K-05 / INV-11）：实现 M08 的 `CapabilityGate`
契约位——`verify` 接收能力投影，返回布尔裁决（True = 放行，False = 拒绝）；
拒绝 ⇒ 不可达 active / 执行被阻（硬行为由 Manager 的 advance / execute
enforce，本模块只出裁决）。本模块是 V1 唯一闸门实现——无第二条验证路径、
无 legacy 旁路形态（D-03：`def verify(` 定义位全包仅契约位 + 本模块；
调用位仅 Manager 内部，棘轮固化）。

闸门判据（spec §7：细节 = 实现阶段；决定 ㊱）：规则式、model-free——V1
默认配置无 model（U-5 不预设），闸门必须在默认配置下可闭环（AC 6）；
三判据全部满足才放行：

1. 投影良构：name / content / source_reference 三字段均为非空 str，name
   不含路径分隔符、非 '.' / '..'（独立于 propose 的校验——闸门是 active
   前的最后一道防线，不依赖上游已校验）；
2. 源可解析：源记忆记录经注入 memory 的 get 可读——ValueError（记录缺失）
   → False（不可验证 = 不可信，INV-11）；其他异常透传（provider 故障 =
   fail-loud，不是静默拒绝）；
3. grounding：投影 content == 源记录 content（propose 从源记录读 content，
   记录此后永不改写 ⇒ 分歧 = 载体或记忆损坏）。

闸门只裁决——不写、不移动、不抛（provider 异常透传除外）；零 dao_sheng
import（memory 以 6 方法契约实例注入，鸭子类型；构造位仅 composition
root，R-09）。不引入新状态（spec §6：状态集扩展 = Domain 决策；本模块
是机制，不是形态）。

依据：spec-capability.md §1/§2/§7、ADR 0003 决定 1/2、审计 K-05 / D-03 /
K-10、INV-11、决定 ㊱–㊴。
"""

from __future__ import annotations


class CapabilityVerifier:
    """执行前闸门（K-05 / INV-11 的机制交付；M08 契约位的唯一实现）。

    构造注入 memory（MemoryStore 契约实例：闸门只经其 `get` 读源记录）；
    鸭子类型判定（零 import 纪律，同 capability_lifecycle.py 对 verifier
    的注入面）。
    """

    def __init__(self, *, memory: object) -> None:
        """1 项依赖构造注入（R-09），无默认值：memory（6 方法契约实例；
        闸门判据 2 / 3 的唯一读通道）。"""
        self._memory = memory

    def verify(self, capability: object) -> bool:
        """闸门裁决（CapabilityGate 契约位实现）：三判据全满足 → True
        （放行）；任一不满足 → False（拒绝 = 不可达 active / 执行被阻）。

        不抛（provider 的 ValueError 之外的异常透传 = fail-loud，决定
        ㊱）；不写、不移动（裁决无副作用）。"""
        name = getattr(capability, "name", None)
        content = getattr(capability, "content", None)
        reference = getattr(capability, "source_reference", None)
        # 判据 1：投影良构（三字段非空 str + name 路径安全）。
        if not all(
            isinstance(value, str) and value.strip()
            for value in (name, content, reference)
        ):
            return False
        if "/" in name or "\\" in name or name in (".", ".."):
            return False
        # 判据 2：源可解析（ValueError = 记录缺失 → 拒绝；其他异常透传）。
        try:
            source = self._memory.get(reference)
        except ValueError:
            return False
        # 判据 3：grounding（投影 content == 源记录 content）。
        source_content = getattr(source, "content", None)
        if not isinstance(source_content, str) or source_content != content:
            return False
        return True
