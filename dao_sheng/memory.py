"""Memory Ontology + Memory Interface（6 方法契约）— M05。

依据：spec-memory.md §1（三维语义层 + 修正引用键 + provenance 中性化）/
§2（6 方法契约；派生读不独立成方法；实现隐藏列），component-model.md §3，
Q2（三维语义层，用户追认）/ H-4（provenance 中性化）/ R-05（契约形态固化），
INV-3（Ontology 与 Storage 分离；映射方向 Ontology → schema），
INV-8（修正不重写），ADR 0006（Insight 无独立存储：单一 Memory 表示）。

本模块是 Ontology 模块：只定义类型与 Interface 契约，无 I/O、无存储
实现细节（那些属于 Provider，对调用方隐藏，spec-memory.md §2），不 import
任何 V1 模块——Ontology 依赖任何模块都不得存在（方向锁：adapter 单向
依赖 Ontology，INV-3 / 规则 5）。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class MemoryOrigin(Enum):
    """记忆来源（spec-memory.md §1 三维语义层第 1 维；Q2）。"""

    CANONICAL = "canonical"
    DERIVED = "derived"
    EXTERNAL = "external"
    ECHO = "echo"


class MemoryStatus(Enum):
    """记忆状态（spec-memory.md §1 三维语义层第 2 维；Q2）。"""

    OBSERVED = "observed"
    REPORTED = "reported"
    VERIFIED = "verified"


class MemoryConfidence(Enum):
    """记忆置信（spec-memory.md §1 三维语义层第 3 维；Q2）。"""

    CONFIRMED = "confirmed"
    SUPPORTED = "supported"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class Memory:
    """一条记忆的只读投影（唯一表示：Experience / 修正 / Insight 皆经此落库，ADR 0006）。

    无时间戳：排序 / 新旧键是 Provider 实现细节（spec-memory.md §2 实现隐藏列）。
    """

    reference: str
    content: str
    memory_origin: MemoryOrigin
    memory_status: MemoryStatus
    memory_confidence: MemoryConfidence


@dataclass(frozen=True)
class RecallQuery:
    """recall 结构化查询：三维过滤任意子集 + 可选关键词（spec-memory.md §2）。

    空查询（全 None）= 全集（隐藏排序 + ≤32 上限）。
    """

    memory_origin: MemoryOrigin | None = None
    memory_status: MemoryStatus | None = None
    memory_confidence: MemoryConfidence | None = None
    keyword: str | None = None

    def __post_init__(self) -> None:
        # 空关键词无查询意义 → fail-loud（不静默当"无关键词"处理）
        if self.keyword is not None and not self.keyword.strip():
            raise ValueError("RecallQuery.keyword 不得为空字符串（空关键词无查询意义；fail-loud）")


@dataclass(frozen=True)
class Correction:
    """修正内容（三维显式声明）；correct_memory 将其落为一条 Memory 并建引用链。

    修正不重写原记录（INV-8）：原记录 content / 三维 / identity 不变。
    """

    content: str
    memory_origin: MemoryOrigin
    memory_status: MemoryStatus
    memory_confidence: MemoryConfidence


class MemoryStore(Protocol):
    """Memory Interface（6 方法契约，R-05；component-model.md §3）。

    The interface is the test surface：调用方只依赖本契约，不知道 Provider 的
    表结构 / 索引 / id 生成 / 关键词通道选择 / 排序 / 上限形态（实现隐藏列）。
    方法集合 = 6 即契约——不得出现 5 方法浅层形态或 11 方法实现表形态。
    """

    def remember(
        self,
        *,
        content: str,
        memory_origin: MemoryOrigin,
        memory_status: MemoryStatus,
        memory_confidence: MemoryConfidence,
    ) -> str:
        """写入一条记忆：三维字段显式传入（Q2；无推断行），content 非空。

        返回 reference（该记忆的唯一句柄）。
        """
        ...

    def recall(self, query: RecallQuery) -> list[Memory]:
        """结构化过滤（三维任意子集）+ 可选关键词 / 子串；排序标准隐藏；结果 ≤32 条。"""
        ...

    def get(self, reference: str) -> Memory:
        """按 reference 精确取回；缺失 → fail-loud（ValueError，不返回空对象）。"""
        ...

    def correct_memory(self, target: str, correction: Correction) -> str:
        """追加修正记录 + 建立 (original → correction) 显式引用链（INV-8）。

        原记录 content / 三维 / identity 不变；返回 correction 的 reference。
        """
        ...

    def register_reference(self, source: str, target: str) -> None:
        """显式登记引用链：source 记忆携带指向 target 的引用键。

        无隐式匹配；两端必须存在（缺失 → fail-loud）；同一有序对幂等。
        """
        ...

    def resolve_reference(self, reference: str) -> list[Memory]:
        """按显式引用解析：与 reference 双向显式链接的全部记忆。

        显式引用优先（V0 行为形态）：只依据显式链接，永不做内容匹配。
        """
        ...
