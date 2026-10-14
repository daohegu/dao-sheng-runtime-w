"""Model Interface —— Model 调用两级调用面的显式类型（ADR 0008 决定 1）。

依据：ADR 0008（决定 1/2/5，裁定 2）、M06 决定 ⑨/⑩、INV-1、K-11、U-5。

- 契约 = 两级调用面：`complete(prompt) -> str`（补全）与
  `chat(messages) -> str`（会话），仅暴露此两级（M06 决定 ⑨：
  interface = test surface，表面不变；wire / 重试 / 退避 / 超时 / 契约
  校验细节 = depth，全部内化于各具体实现模块，M06 决定 ⑩）。
- Interface 中性：不含具体实现名、不含部署位置、不含任何实现专属
  参数（ADR 0002 决定 2 同款中性纪律）；Core 调用方（agent /
  reflection 两侧）只依赖本 interface，不依赖任何具体实现类（ADR
  0008 决定 1）；Agent / Reflection 结构上允许使用不同具体实现
  （ADR 0008 裁定 2）——本 interface 不预设任何具体实现，实现名
  不进入 Domain / Identity / Doctrine（K-11 / 裁定 2）。
- `ModelUnavailable` = 手段故障的 fail-loud 信号（M06 决定 ⑩ /
  INV-1：手段故障 ≠ 个体故障）：语义不变；唯一定义位 = 本模块，
  全部具体实现模块与 Core 调用方共享此异常类型（仅类型引用，互不
  构造，R-09）。
- 具体 Python 形态 = Protocol（结构化类型；实现阶段决定项，ADR
  0008 决定 1）：符合性由两级调用面判定，不要求继承关系。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class Model(Protocol):
    """Model 调用两级调用面（Core 与 Model 调用之间唯一的契约）。

    - `complete`：补全——prompt → 模型续写；
    - `chat`：会话——(role, content) 序列 → 模型回复。

    手段故障时由具体实现抛出 `ModelUnavailable`（INV-1）；Core
    调用方捕获后降级（手段故障 ≠ 个体故障，降级路径不变，M04
    决定 ⑯ / M07 决定 ㉕）。
    """

    def complete(self, prompt: str) -> str:
        """补全调用：prompt → 模型续写。"""
        ...

    def chat(self, messages: Sequence[tuple[str, str]]) -> str:
        """会话调用：(role, content) 序列 → 模型回复。

        调用方以 `(role, content)` 二元组给出完整消息序列（含最后一
        轮 user 消息）；不预设任何 system 前缀——上下文组织是 Core
        的事，具体实现不代 Core 做判断（手段不得定义个体，INV-1
        同一纪律）。
        """
        ...


class ModelUnavailable(RuntimeError):
    """Model 调用不可用：重试耗尽 / 服务端拒绝 / 响应不合契约。

    调用方（M04 起）对此的处理属 Core 决定；本异常只是手段边界的
    fail-loud 信号（INV-1：手段故障不等于个体故障）。
    """
