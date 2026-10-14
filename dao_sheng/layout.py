"""个体持久文件清单（5 项）——DaoSheng Runtime 进程拥有的个体状态边界。

依据：spec-individual.md §4（5 项清单；清单之外的任何文件都不是个体状态）、
container-model.md §2/§3（Runtime 进程拥有个体持久文件；重启后个体状态
完全由本清单恢复）、spec-adapters.md §5（进程边界：host 进程不直接触碰）。

- 载体形态（存什么 / 怎么存）：Identity 已定 = 单 JSON 文件（M02 决定 ①）、
  Continuity 已定 = 单 append-only 日志文件（M03 决定 ③）、Faculties 已定 =
  单 JSON 文件（M03 决定 ④）、Memory 已定 = memory_dir 内单 embedded SQLite
  文件 + WAL 侧文件（M05 决定 ⑥），记录于各票 Comments /
  RECONSTRUCTION.md Decisions；Capability 已定 = 四目录 adapter 形态
  （M08 决定 ㉘：目录名 = 状态名；每能力 = 当前状态目录内单个 JSON 记录
  文件，严格 schema 恰好 3 键、无状态字段；转换 = 文件移动；见
  capability_lifecycle.py）。
- root = 部署层值，由 composition root 注入；本模块不预设任何绝对位置、
  不做 I/O、不 import 其他 V1 模块（R-09）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IndividualFiles:
    """个体持久文件清单（5 项）。

    - identity          Identity 载体 = root/"identity.json"（M02 决定 ①：单 JSON 文件，
                        严格 schema 恰好 7 支撑项键；校验/投影见 identity.py）
    - continuity        Continuity 单一载体 = root/"continuity.jsonl"（M03 决定 ③：
                        单 append-only 日志文件，每行 = 一条记录 = 一个 JSON 对象；
                        校验 / 投影 / 追加见 continuity.py；ADR 0004）
    - memory_dir        Memory 存储目录：单 embedded SQLite 文件 + WAL 侧文件
                        （M05 决定 ⑥；ADR 0001；形态/校验/投影见 memory 存储
                        provider 模块）
    - capabilities_dir  Capability 载体根 = root/"capabilities"（M08 决定 ㉘：
                        四目录 adapter 形态——目录名 = 状态名；形态 / 校验 /
                        投影见 capability_lifecycle.py；ADR 0003）
    - faculties         Faculties 状态载体 = root/"faculties.json"（M03 决定 ④：
                        单 JSON 文件，严格"恰好 8 根根名"；校验 / 投影见
                        faculties.py）
    """

    root: Path
    identity: Path
    continuity: Path
    memory_dir: Path
    capabilities_dir: Path
    faculties: Path

    @classmethod
    def layout(cls, root: Path) -> "IndividualFiles":
        """由部署层注入的 root 派生 5 项清单位置。"""
        return cls(
            root=root,
            identity=root / "identity.json",
            continuity=root / "continuity.jsonl",
            memory_dir=root / "memory",
            capabilities_dir=root / "capabilities",
            faculties=root / "faculties.json",
        )
