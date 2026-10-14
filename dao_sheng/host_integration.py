"""Host 集成层 —— 中性 Interface（M09；spec-adapters.md §1）。

依据：spec-adapters.md §1（中性三方法 Interface、无宿主名，ADR 0002
决定 2）、§4（seam = hypothetical，单 adapter 如实记录；Interface 不随
adapter 变化）、§5（进程边界：host 进程不直接触碰个体持久文件，一切
交互经本层）、ADR 0002 决定 1–6。

- Interface = 恰三方法（棘轮固化）：`open_session` / `import_session` /
  `sync`——无宿主名（决定 2）。
- 经验回流 = "导入会话 → [Experience 候选]"；去重 / 幂等 = 本层职责
  （spec-individual.md §2.3）；origin 中性标注（三维 origin 枚举，宿主名
  不进枚举，spec-memory.md §1）在本层完成。
- 本模块 = seam 契约：纯类型定义，零宿主知识、零内部模块 import、零
  I/O（同 memory.py Ontology 模块纪律，棘轮固化）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class HostSession:
    """Host 会话句柄：open 时钉定的状态位置。

    - state_locations = open_session 时解析钉定的宿主状态数据库位置
      元组——宿主布局知识由宿主 adapter 层持有，句柄只携带解析结果，
      无宿主名。
    - frozen：会话建立后位置不再解析（重解析是 sync 的职责）。
    """

    state_locations: tuple[Path, ...]


@dataclass(frozen=True)
class SyncReport:
    """sync 结果：重新解析后的状态位置 + 本次同步新导入的经历记录
    引用（空 = 无新增）；error = 降级说明（降级面，INV-1 纪律）。"""

    state_locations: tuple[Path, ...]
    new_references: tuple[str, ...] = ()
    error: str | None = None


class HostIntegration(Protocol):
    """Host 集成层 Interface（ADR 0002 决定 2：中性概念，无宿主名；
    seam = hypothetical，单 adapter 如实记录——Interface 即其契约，
    不随 adapter 变化）。"""

    def open_session(self) -> HostSession:
        """建立 / 打开 host 会话：解析状态位置并钉定句柄（宿主布局
        知识由 adapter 层持有；解析输入 = 装配期注入的声明位配置）。"""
        ...

    def import_session(self, session: HostSession) -> tuple[str, ...]:
        """经验回流："导入会话 → [Experience 候选]"→ 进入成长管线，
        返回新建经历记录的引用（空 = 无新增）。

        去重 / 幂等 = 本层职责（spec-individual.md §2.3）：同一会话
        幂等重导入不产生新候选；origin 中性标注（宿主名不进枚举）
        在本层完成（spec-memory.md §1）。
        """
        ...

    def sync(self) -> SyncReport:
        """同步（V0 宿主同步形态收敛位——移除非改名，ADR 0002 决定 5：
        同步属本层，不属 Growth 核）：重新解析状态位置 + 重导入新增
        内容，返回结果。"""
        ...
