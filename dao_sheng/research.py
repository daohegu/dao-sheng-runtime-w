"""Research seam 契约 —— 观察 ≠ 判断（M06；spec-adapters §3 / K-08 / D-04）。

依据：spec-adapters.md §3（Research adapter 契约 + 后端经装配注入）、
§4（Research seam = hypothetical，单 adapter、不预设第二个）、K-08
（`ResearchResult` 必须携带 sources + confidence = invariant；web.py
scraping 脆弱属 REBUILD 项，不影响本契约 KEEP）、D-04（`ResearchService`
47 行 pass-through 壳 DELETE：空查询校验逻辑归 seam 契约，见
`ResearchProvider` docstring）、M-6（后端在 composition root 注入，
adapter 接受依赖不创建）。

- 本模块 = 纯类型 + Protocol（无 I/O、无后端客户端）——与 memory.py
  Ontology / Provider 分离同一形态先例：具体后端是装配决定，未定、
  不预设（spec-adapters §6）；引入具体后端或第二个 adapter 使 seam
  转 real → 按规则 8 立 ADR（票 Required ADRs 触发条件）。
- 不 import 其他 V1 模块。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ResearchSource:
    """一条观察来源（观察的溯源单元；K-08：观察必须可溯源）。"""

    title: str
    url: str
    source_type: str = "web"
    publisher: str | None = None
    retrieved_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchResult:
    """一次 Research 的产物 = 带来源的观察，不是个体的判断（K-08 纪律）。

    invariant（K-08，缺任一即违规，fail-loud）：
    - `sources` 非空：无来源的观察不得存在（V0 `sources=[]` 默认值形态废止）；
    - `confidence` 为 [0, 1] 内实数且必给（V0 `confidence=0.5` 默认值形态
      废止——默认置信度正是"未评估也能存在"的通道；bool 虽为 int 子类
      但非置信度语义，一并拒绝）。
    消费侧（M04 / M07）须保持"观察 = 带来源输入"语义，不得当个体判断消费
    （票 Risks 第 3 条）。
    """

    query: str
    findings: str
    sources: tuple[ResearchSource, ...]
    provider: str
    confidence: float
    retrieved_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.sources:
            raise ValueError(
                "ResearchResult 必须携带非空 sources（K-08：观察必须有来源）"
            )
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence, (int, float)
        ):
            raise ValueError("confidence 必须为实数（K-08 invariant）")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence 必须在 [0, 1] 内（K-08 invariant）")


class ResearchProvider(Protocol):
    """Research seam 契约（interface = test surface）。

    - seam 契约（D-04 归位：原 `ResearchService` 壳的校验逻辑）：
      `query` 去除首尾空白后为空 → `research` 必须 fail-loud（ValueError）；
      原壳的 `isinstance` 运行期类型检查废止（类型系统 + `ResearchResult`
      frozen invariant 承接）。
    - `name`：后端名（观察溯源 / 装配诊断用）。
    - 本票不实现任何后端客户端：具体后端未定、不预设（spec-adapters §6），
      后端实例由 composition root 构造并注入（M-6 / R-09）。
    """

    name: str

    def research(self, query: str) -> ResearchResult:
        ...
