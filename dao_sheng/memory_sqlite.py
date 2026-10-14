"""embedded SQLite Memory Provider — M05（决定 ⑥⑦⑧）。

依据：ADR 0001（单文件 embedded SQLite + WAL；recall = 结构化过滤 +
FTS5 trigram / LIKE 通道），docs/research/memory-architecture.md（E1
内置可用 / E2 WAL 侧文件 / E3 单写者 / E5 trigram ≥3 字符 / E7 vector
不随 V1），spec-memory.md §2/§3（Interface 实现列：通道选择 / 排序 /
上限 = 对调用方隐藏），ADR 0007（初始化不读 V0 存储；目录 / DB 缺失 =
初始态），R-09（仅装配点构造并注入）。

载体形态（决定 ⑥）：memory_dir 内单 embedded SQLite 文件 + WAL 侧文件。
reference 形态（决定 ⑦）：reference = 行 rowid 的十进制字符串，无语义
内容，生成对调用方隐藏；引用链 = 独立 memory_references 表有序对；无
`kind` 判别列（三维语义层是唯一语义载体，ADR 0006 单一表示）。隐藏
排序（决定 ⑧）：插入序倒序（最新优先），通道无关，≤32 上限（Interface
固化）。

调用方只见到 MemoryStore 契约的 6 方法（interface = test surface）：表
结构 / FTS 索引 / id 生成 / 通道选择 / 排序 / 上限形态皆为本模块实现
细节，不出现在契约上（component-model.md §3 实现隐藏列）。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from dao_sheng.memory import (
    Correction,
    Memory,
    MemoryConfidence,
    MemoryOrigin,
    MemoryStatus,
    RecallQuery,
)

# recall 结果上限：Interface 固化（spec-memory.md §2），非可调参数（决定 ⑧）。
RECALL_CAP = 32

# 关键词通道切换长度：trigram 分词器最小可查长度 = 3 字符（research E5）；
# <3 字符走 LIKE 通道。通道选择 = 实现细节，对调用方隐藏。
_TRIGRAM_MIN_LEN = 3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    content TEXT NOT NULL,
    memory_origin TEXT NOT NULL,
    memory_status TEXT NOT NULL,
    memory_confidence TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memory_references (
    source INTEGER NOT NULL,
    target INTEGER NOT NULL,
    PRIMARY KEY (source, target)
);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    tokenize = 'trigram'
);
"""


def _require_non_empty(content: str, field: str) -> None:
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"{field} 必须为非空字符串（空内容无记忆意义；fail-loud）：{content!r}")


def _require_enum(value: object, enum_cls: type, field: str) -> None:
    if not isinstance(value, enum_cls):
        raise ValueError(
            f"{field} 必须显式传入 {enum_cls.__name__} 枚举实例"
            f"（三维语义层无推断行，Q2 / H-4）：实际 = {value!r}"
        )


class SqliteMemoryProvider:
    """embedded SQLite 适配器（单一物理形态，ADR 0001）：实现 MemoryStore
    6 方法契约。仅装配点构造（R-09）；初始化不读任何外部存储——目录 /
    DB 缺失 = 初始态（新建个体，空记忆，ADR 0007 不默认迁移 V0 数据）。"""

    def __init__(self, memory_dir: Path) -> None:
        # 初始态自建（ADR 0007）：目录 / DB 缺失 = 新建个体，空记忆。
        # 参数面仅 memory_dir——无外部存储参数可传入（AC 7 结构面）。
        memory_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(memory_dir / "memory.db")
        # 决定 ⑥ 载体形态：WAL（research E2 侧文件）；未启用 = 载体形态
        # 破坏 → fail-loud。
        mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if mode != "wal":
            raise RuntimeError(f"载体形态破坏：journal_mode = {mode!r}（决定 ⑥ 要求 wal）")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def remember(
        self,
        *,
        content: str,
        memory_origin: MemoryOrigin,
        memory_status: MemoryStatus,
        memory_confidence: MemoryConfidence,
    ) -> str:
        """写入一条记忆：三维显式（枚举实例，无推断行）+ content 非空。

        返回 reference（决定 ⑦：rowid 十进制字符串，生成对调用方隐藏）。
        """
        _require_non_empty(content, "content")
        _require_enum(memory_origin, MemoryOrigin, "memory_origin")
        _require_enum(memory_status, MemoryStatus, "memory_status")
        _require_enum(memory_confidence, MemoryConfidence, "memory_confidence")
        cur = self._conn.execute(
            "INSERT INTO memories (content, memory_origin, memory_status, memory_confidence)"
            " VALUES (?, ?, ?, ?)",
            (content, memory_origin.value, memory_status.value, memory_confidence.value),
        )
        rowid = cur.lastrowid
        self._conn.execute(
            "INSERT INTO memories_fts (rowid, content) VALUES (?, ?)", (rowid, content)
        )
        self._conn.commit()
        return str(rowid)

    def recall(self, query: RecallQuery) -> list[Memory]:
        """结构化过滤（三维任意子集）+ 可选关键词；隐藏排序 = 插入序倒序
        （决定 ⑧）；≤32 条（上限 Interface 固化）。"""
        clauses: list[str] = []
        params: list[object] = []
        for field, enum_cls in (
            ("memory_origin", MemoryOrigin),
            ("memory_status", MemoryStatus),
            ("memory_confidence", MemoryConfidence),
        ):
            value = getattr(query, field)
            if value is not None:
                _require_enum(value, enum_cls, f"RecallQuery.{field}")
                clauses.append(f"memories.{field} = ?")
                params.append(value.value)
        if query.keyword is not None:
            kw = query.keyword.strip()
            if len(kw) >= _TRIGRAM_MIN_LEN:
                # trigram 通道（research E5：CJK ≥3 字符子串）；引号按 FTS5
                # 短语语法转义；trigram 默认大小写不敏感（与 LIKE 通道 ASCII
                # 行为一致，环境核验）。
                phrase = '"' + kw.replace('"', '""') + '"'
                clauses.append(
                    "memories.rowid IN"
                    " (SELECT rowid FROM memories_fts WHERE memories_fts MATCH ?)"
                )
                params.append(phrase)
            else:
                # LIKE 通道（<3 字符 = trigram 最小可查长度之下）；ESCAPE 禁用
                # 关键词内的 LIKE 通配符。
                escaped = kw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                clauses.append("memories.content LIKE ? ESCAPE '\\'")
                params.append(f"%{escaped}%")
        sql = (
            "SELECT rowid, content, memory_origin, memory_status, memory_confidence"
            " FROM memories"
        )
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        # 决定 ⑧：隐藏排序 = 插入序倒序（通道无关，确定性）；上限 Interface 固化。
        sql += " ORDER BY memories.rowid DESC LIMIT ?"
        params.append(RECALL_CAP)
        rows = self._conn.execute(sql, params).fetchall()
        return [self._to_memory(row) for row in rows]

    def get(self, reference: str) -> Memory:
        """按 reference 精确取回；缺失 → fail-loud（不返回空对象）。"""
        row = self._conn.execute(
            "SELECT rowid, content, memory_origin, memory_status, memory_confidence"
            " FROM memories WHERE rowid = ?",
            (reference,),
        ).fetchone()
        if row is None:
            raise ValueError(f"记忆缺失（reference = {reference!r}）：fail-loud，不返回空对象")
        return self._to_memory(row)

    def correct_memory(self, target: str, correction: Correction) -> str:
        """追加修正记录 + 建立 (original → correction) 显式引用链（INV-8）。

        原记录 content / 三维 / identity 不变；修正 = 普通记忆行（决定 ⑦：
        无 kind 判别列）；返回 correction 的 reference。
        """
        if self._conn.execute("SELECT 1 FROM memories WHERE rowid = ?", (target,)).fetchone() is None:
            raise ValueError(f"修正目标记忆缺失（target = {target!r}）：fail-loud")
        _require_non_empty(correction.content, "Correction.content")
        _require_enum(correction.memory_origin, MemoryOrigin, "Correction.memory_origin")
        _require_enum(correction.memory_status, MemoryStatus, "Correction.memory_status")
        _require_enum(
            correction.memory_confidence, MemoryConfidence, "Correction.memory_confidence"
        )
        ref = self.remember(
            content=correction.content,
            memory_origin=correction.memory_origin,
            memory_status=correction.memory_status,
            memory_confidence=correction.memory_confidence,
        )
        self._conn.execute(
            "INSERT INTO memory_references (source, target) VALUES (?, ?)",
            (target, ref),
        )
        self._conn.commit()
        return ref

    def register_reference(self, source: str, target: str) -> None:
        """显式登记引用链（source → target）：两端必须存在（fail-loud），
        同一有序对幂等（主键 + INSERT OR IGNORE）。"""
        for ref in (source, target):
            if self._conn.execute("SELECT 1 FROM memories WHERE rowid = ?", (ref,)).fetchone() is None:
                raise ValueError(
                    f"引用端点记忆缺失（reference = {ref!r}）：显式链接两端必须存在，fail-loud"
                )
        self._conn.execute(
            "INSERT OR IGNORE INTO memory_references (source, target) VALUES (?, ?)",
            (source, target),
        )
        self._conn.commit()

    def resolve_reference(self, reference: str) -> list[Memory]:
        """按显式引用解析：与 reference 双向显式链接的全部记忆（指向的 +
        指向 reference 的）。永不做内容匹配（显式引用优先）；缺失 →
        fail-loud。返回按插入序（先插入在前）。"""
        if self._conn.execute("SELECT 1 FROM memories WHERE rowid = ?", (reference,)).fetchone() is None:
            raise ValueError(f"记忆缺失（reference = {reference!r}）：fail-loud")
        rows = self._conn.execute(
            "SELECT m.rowid, m.content, m.memory_origin, m.memory_status, m.memory_confidence"
            " FROM memories AS m"
            " WHERE m.rowid IN ("
            "   SELECT target FROM memory_references WHERE source = ?"
            "   UNION"
            "   SELECT source FROM memory_references WHERE target = ?"
            " )"
            " ORDER BY m.rowid ASC",
            (reference, reference),
        ).fetchall()
        return [self._to_memory(row) for row in rows]

    def close(self) -> None:
        """关闭存储连接（WAL 侧文件已落盘，决定 ⑥）。"""
        self._conn.close()

    @staticmethod
    def _to_memory(row: sqlite3.Row) -> Memory:
        """映射方向 Ontology → schema（INV-3）：存储行 → Ontology 类型化
        投影；reference = rowid 十进制字符串（决定 ⑦）。"""
        return Memory(
            reference=str(row["rowid"]),
            content=row["content"],
            memory_origin=MemoryOrigin(row["memory_origin"]),
            memory_status=MemoryStatus(row["memory_status"]),
            memory_confidence=MemoryConfidence(row["memory_confidence"]),
        )
