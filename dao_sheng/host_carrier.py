"""宿主侧载体通道 —— M09 S3（宿主层唯一 I/O 通道）。

依据：spec-adapters.md §1（import_session 经验回流的载体面）、
ADR 0002 决定 1（schema 知识正是 adapter 该持有的东西——宿主状态库
读取面 = messages 表必需列 session_id / content /
_compressed_summary / message_uid + id 物理行身份，本模块设计决定；
V0 逐列 schema = UNKNOWN，规则 11，票 Comments）、决定 2（中性形态：
宿主名不进本模块）、M03 / M05 通道纪律（合法内部 I/O 通道 = 模块
函数 + frozen dataclass，允许位棘轮固化）、ADR 0010 契约实施票
（D1 裁定 1–3 / 7–8：必需列 preflight + 派生摘要标记校验与排除 +
逻辑消息键）；D-056 跨 rotation 去重：新 key 版本 v4（不含
session_id / rowid），v3 降为 legacy 继续被识别——见
read_session_records。

- 宿主状态库 = 只读连接（mode=ro）：宿主进程数据永不被集成层改写
  （INV-7 单向：投影不回流；宿主库不是个体状态的写面）。
- 导入日志 = 宿主自有文件：每行一个幂等键（append-only，无 JSON
  形态——损坏形态不可表达；去重 / 幂等状态归宿主层，
  spec-individual.md §2.3）。
- 缺失 = 初始态（宿主未运行 / 首次导入）：记录读 = 空、日志读 = 空
  集——host 消失不影响个体状态（ADR 0002 Consequences）。
- 布局确保 = 本模块唯一布局副作用（导入日志父目录）；宿主状态库
  永不写。
- 本模块 = 宿主层 I/O 通道：宿主 adapter 逻辑模块自身零 I/O，一律
  经本通道（棘轮固化）。
- location digest 公式 = 本模块唯一声明位（`location_digest`，Candidate 4
  conformance correction）：key 合成知识归本模块，host adapter 层的
  collision guard 经函数引用复用同一公式，生产层不各自实现（locality
  不破坏，同决定 ㊷ 单一声明位纪律）。
- 裁定日志（D-058 / ADR 0010 修订 Decision 12 记录载体）= 独立
  append-only JSONL（`host/adjudications.jsonl` 形态，用户 2026-10-12
  裁定）：冲突组人工裁定记录，与导入日志完全分离——裁定记录不是
  导入记录、永不写入 imported.log、不冒充已导入；append-only，不重写
  不删除历史裁定，旧裁定失效经候选集合指纹不匹配表达。候选集合指纹
  与内容 SHA-256 公式 = 本模块唯一声明位（内容基，非 DB 文件哈希——
  实测 live DB 文件哈希漂移而候选集合不变）。`append_adjudication`
  永不被 host adapter 层引用（棘轮白名单固化 = 机器绝不自动裁定、
  裁定写入面与咨询面分离的结构保证）。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


#: 身份字段 integrity 守卫（P2；D-058 扩展至 message_uid）：含任何
#: `splitlines()` 切分字符的 session_id / message_uid = 损坏形态——
#: 导入日志 = 每行一个幂等键的 append-only 去重状态记录，切分字符进入
#: key 会把一条 key 拆成多行 / 与相邻 key 粘连（损坏不可表达）→
#: fail-loud，在 record 建立之前。message_uid 嵌入 v4 写入键
#: （`v4:<digest>:<uid>`）与 legacy v3 键，切分字符同样破坏日志行结构
#: （D-058 deferred finding 闭合）。字符全集 = Python str.splitlines()
#: 的切分集合。本守卫只查切分字符——普通空白 / ":" / 空身份字段不受
#: 本守卫限制（合格候选的资格与身份完整性裁定归 host adapter 层 D1
#: preflight，见 import_session 消费面）。
_LINE_SPLIT_CHARS = frozenset("\n\r\x0b\x0c\x1c\x1d\x1e\x85") | {chr(0x2028), chr(0x2029)}


#: messages 表必需列（D1 裁定 1）：候选身份（session_id / message_uid）
#: 与派生摘要标记（_compressed_summary）读取面所依赖的列全集。缺任一
#: 列 = 读取面不可建立 → fail-loud（不建候选、不导入、不写日志），
#: 在读取任何行之前。
_REQUIRED_MESSAGE_COLUMNS = frozenset(
    {"session_id", "content", "_compressed_summary", "message_uid"}
)


@dataclass(frozen=True)
class HostSessionRecord:
    """单条会话记录（中性形态，无宿主名；已过滤派生摘要 = 原始消息
    候选形态）：content = 记录内容；session_id / message_uid = 逻辑
    消息身份字段（缺失 / 空 / 非法 → host adapter 层身份 preflight
    fail-loud，载体不为其降级）；rowid = 物理行身份（宿主 clone /
    代际会产生新 rowid = 不稳定，D1 裁定 7——只用于组内代表版本选
    择，绝不进入新 key）；record_key = global import identity（v4
    形态 `v4:<location digest>:<message_uid>`——D-056 跨 rotation 去
    重：宿主 rotation child retarget 换 session_id 但保留
    message_uid，同一逻辑消息不得因跨 session 克隆建立多条独立
    Experience，逻辑消息身份 = (location digest, message_uid)，不含
    session_id / rowid；身份只在单库内唯一，key 必须含 canonical
    location digest；公式在本模块唯一声明位声明，其他模块复用
    record_key，不重复实现；opaque identity string，绝不按分隔符切
    分解析；身份字段含 ":" 的 injectivity 危险由 host adapter 层
    fail-loud 守卫）；
    legacy_record_keys = 旧键形态元组（v3
    `v3:<location digest>:<session_id>:<message_uid>` + v2
    `v2:<location digest>:<session_id>:<rowid>` + v1
    `session_id:rowid`）——导入日志 append-only 且不重写，已落盘的
    旧键必须继续被识别（组级多读判重，防升级后重复导入），新写入只
    使用 v4。"""

    content: str
    session_id: str | None
    message_uid: str | None
    rowid: int
    record_key: str
    legacy_record_keys: tuple[str, ...]


def location_digest(canonical: str) -> str:
    """canonical location 的 location digest（production 层唯一公式位）：
    SHA-256 over canonical resolved posix 字符串，64 hex 全量、不截断、
    不 lowercase、不新增 canonicalization、无 I/O。digest 提供 collision
    resistance 与 practical uniqueness，不提供 mathematical injectivity
    （固定长度摘要由鸽笼原理非单射）——runtime collision guard（host
    adapter 层）兜底 fail-loud。host adapter 层经本函数引用复用同一
    公式，不重复实现。"""
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read_session_records(state_db: Path) -> tuple[HostSessionRecord, ...]:
    """读宿主状态库全部会话记录（只读连接，行序 = rowid 序），并在
    record 建立之前完成候选资格 preflight（ADR 0010 实施票 D1 裁定
    1–3 / 6–8）——必需列 preflight、派生摘要标记校验、标记 = 1 排
    除，全部 fail-loud / 排除先于任何下游逻辑（较新摘要行绝不覆盖
    原始消息资格；无部分副作用）。

    缺失 = 宿主未运行（初始态）→ 空元组；库存在但不可读（非 SQLite
    形态 / 表缺失 / 必需列缺失）= 损坏 → fail-loud（import_session
    签名无降级面，降级不可表达）。
    """
    if not state_db.is_file():
        return ()
    canonical = state_db.resolve().as_posix()
    conn = sqlite3.connect(f"file:{canonical}?mode=ro", uri=True)
    try:
        # 必需列 preflight（D1 裁定 1）：零行 SELECT 取列名全集，在读
        # 任何行之前；缺必需列 = 候选身份 / 派生摘要标记读取面不可
        # 建立 → fail-loud（不建候选、不导入、不写日志）。
        columns = {
            column[0]
            for column in conn.execute("SELECT * FROM messages LIMIT 0").description
        }
        missing = sorted(_REQUIRED_MESSAGE_COLUMNS - columns)
        if missing:
            raise ValueError(
                "messages 表缺少必需列："
                + "、".join(missing)
                + "（候选身份 / 派生摘要标记读取面不可建立——"
                "fail-loud，不建候选、不导入、不写日志）"
            )
        rows = conn.execute(
            "SELECT rowid, session_id, content, _compressed_summary, "
            "message_uid FROM messages ORDER BY rowid"
        ).fetchall()
    finally:
        conn.close()
    # location digest = 本模块 location_digest()（production 层唯一公式位，
    # 不写 raw 原文进 key；collision guard 在 host adapter 层兜底）。
    digest = location_digest(canonical)
    records: list[HostSessionRecord] = []
    for rowid, session_id, content, summary_marker, message_uid in rows:
        # session_id integrity（P2）：切分字符 → fail-loud，在 record
        # 建立之前（损坏形态不可表达）。非 str session_id（NULL 列 =
        # UNKNOWN schema 领域，规则 11）不新增禁令、不新增崩溃。
        if isinstance(session_id, str) and any(
            ch in _LINE_SPLIT_CHARS for ch in session_id
        ):
            raise ValueError(
                "session_id 含行切分字符：导入日志（每行一个幂等键）"
                "去重状态记录形态不可表达（fail-loud，不建候选）"
            )
        # message_uid integrity（P2；D-058 deferred finding 闭合）：
        # message_uid 嵌入 v4 写入键与 legacy v3 键，切分字符同样把
        # 一条幂等键拆成多行 → 去重状态记录形态不可表达 → fail-loud。
        if isinstance(message_uid, str) and any(
            ch in _LINE_SPLIT_CHARS for ch in message_uid
        ):
            raise ValueError(
                "message_uid 含行切分字符：v4 写入键（嵌入 message_uid）"
                "与导入日志（每行一个幂等键）去重状态记录形态不可表达"
                "（fail-loud，不建候选）"
            )
        # 派生摘要标记校验（D1 裁定 2）：只接受合法 SQLite 整数 0 / 1；
        # NULL / 非整数 / 其他值 → fail-loud，绝不把未知值默认为 0。
        # bool 排除（True/False 非合法标记形态——严格判定，不默认）。
        if (
            isinstance(summary_marker, bool)
            or not isinstance(summary_marker, int)
            or summary_marker not in (0, 1)
        ):
            raise ValueError(
                f"派生摘要标记非法：_compressed_summary 只接受整数 0 / 1"
                f"（rowid {rowid} 标记形态不可表达资格裁定——"
                "fail-loud，不建候选、不导入、不写日志）"
            )
        # 派生摘要排除（D1 裁定 3 / 6 顺序要求）：标记 = 1 的记录不建
        # record——先于身份检查、分组与代表版本选择（摘要行绝不进入
        # 候选、绝不覆盖同 UID 原始消息资格；已导入的摘要旧键也因此
        # 绝不参与压制逻辑）。
        if summary_marker == 1:
            continue
        records.append(
            HostSessionRecord(
                content="" if content is None else content,
                session_id=session_id,
                message_uid=message_uid,
                rowid=rowid,
                # v4 键（D-056 跨 rotation 去重）：逻辑消息身份 =
                # (location digest, message_uid)——不含 session_id /
                # rowid（rotation child 换 session_id 保留 uid = 同一
                # 逻辑消息）；物理 rowid 不进新 key。身份缺失行的 key
                # 永不被咨询——host adapter 层身份 preflight 先行
                # fail-loud。
                record_key=f"v4:{digest}:{message_uid}",
                # legacy 键（v3 / v2 / v1 旧形态）：append-only 日志不
                # 重写，旧键必须继续可识别（host adapter 层组级多读
                # 判重：v3 旧键按组内成员真实 session_id 生成完整字符
                # 串精确比对，绝不按 ":" 切分解析）；新写入只用 v4。
                legacy_record_keys=(
                    f"v3:{digest}:{session_id}:{message_uid}",
                    f"v2:{digest}:{session_id}:{rowid}",
                    f"{session_id}:{rowid}",
                ),
            )
        )
    return tuple(records)


def read_imported_keys(log: Path) -> frozenset[str]:
    """读导入日志 = 已导入幂等键集合（每行一个键，append-only 宿主
    自有文件）。缺失 = 首次导入（初始态）→ 空集。"""
    if not log.is_file():
        return frozenset()
    return frozenset(
        line.strip()
        for line in log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def append_imported(log: Path, keys: Sequence[str]) -> None:
    """导入幂等键追加落盘（每行一个键，append-only）——宿主侧去重
    状态唯一持久点；布局确保 = 本模块唯一布局副作用（日志父目录）。
    空 = no-op（无新增不触碰载体）。"""
    if not keys:
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        for key in keys:
            f.write(f"{key}\n")


@dataclass(frozen=True)
class AdjudicationCandidate:
    """冲突组人工裁定记录中的单个候选（D-058 / 裁定方案 §2 字段表）：
    rowid = 定位证据（绝不用于自动择优）；session_id = 候选所在物理
    行的 session 身份（指纹组成字段）；content_sha256 = 候选内容
    SHA-256（人工按内容选择的唯一依据，不存私人全文）；content_len =
    内容长度（证据字段）。"""

    rowid: int
    session_id: str
    content_sha256: str
    content_len: int


@dataclass(frozen=True)
class AdjudicationRecord:
    """一个冲突组的一次人工裁定记录（ADR 0010 修订 Decision 12 记录
    载体，D-058；用户 2026-10-12 裁定采纳）：ts = 裁定时间（非空字符
    串；时间戳仅作记录，绝不作择优或生效依据——格式为实现级定义，不
    做机器格式校验，见实施票登记）；location_digest = 该裁定适用的导
    入源 canonical path 的 location digest（与 location_digest() 同一
    公式）；message_uid = 冲突组逻辑消息身份；candidate_set_fingerprint
    = 候选集合指纹（须与 candidates 重算一致——记录自一致性）；
    candidates = 候选集合（非空）；conclusion ∈ {A, B, C}（A = 同一逻
    辑消息且人工选定获准导入内容；B = 不同事件，v4 无法表达，停止提
    请再裁定；C = 证据不足，等同未裁定）；selected_content_sha256 =
    仅 A 必填且必须 ∈ candidates 的内容哈希集合（B / C 必须缺失）；
    reason = 人工理由；evidence_refs = 证据引用；adjudicated_by = 裁
    定来源（非空字符串；身份核验 = 无注册表 = UNKNOWN，规则 11，机器
    不核验身份，见实施票登记）。"""

    ts: str
    location_digest: str
    message_uid: str
    candidate_set_fingerprint: str
    candidates: tuple[AdjudicationCandidate, ...]
    conclusion: str
    selected_content_sha256: str | None
    reason: str
    evidence_refs: tuple[str, ...]
    adjudicated_by: str


def content_sha256(content: str) -> str:
    """候选内容 SHA-256（production 层唯一公式位）：SHA-256 over
    utf-8 编码，64 hex 全量。人工按内容 SHA-256 选定获准导入候选
    （ADR 0010 修订 Decision 11 / 裁定方案 §3 A 案）；host adapter 层
    经本函数引用复用同一公式，不重复实现。"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _fingerprint_from_tuples(candidates: Sequence[tuple[int, str, str, int]]) -> str:
    """候选集合指纹核心公式（唯一实现位）：对每个候选生成
    `rowid|content_sha256|content_len|session_id` 元组串（定形字段在
    前、自由形态 session_id 在最后 → 切分无歧义、序列化单射），排序
    后以换行连接，SHA-256 over utf-8。内容基指纹，不基于 DB 文件哈
    希（live DB 文件哈希漂移而候选集合不变——文件哈希作指纹会使裁定
    无谓失效，D-058 实测）。"""
    lines = sorted(
        f"{rowid}|{content_sha256_value}|{content_len}|{session_id}"
        for rowid, content_sha256_value, content_len, session_id in candidates
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def candidate_set_fingerprint(records: Sequence[HostSessionRecord]) -> str:
    """冲突组候选集合指纹（对外公式位，裁定方案 §2）：输入 = 该组过
    滤后的成员（空白 / 投影标记 / 摘要行已被排除）。成员 session_id
    必须为 str（host adapter 层身份 preflight 先行保证；违规 =
    fail-loud，指纹不可建立）。host adapter 层咨询面与未来人工裁定
    工具面均经本函数计算，保证指纹一致性。"""
    tuples: list[tuple[int, str, str, int]] = []
    for record in records:
        if not isinstance(record.session_id, str):
            raise ValueError(
                f"候选集合指纹不可建立：rowid {record.rowid} 的 session_id 非法"
                "（指纹组成字段必须是字符串——fail-loud，不建裁定依据）"
            )
        tuples.append(
            (record.rowid, content_sha256(record.content), len(record.content), record.session_id)
        )
    return _fingerprint_from_tuples(tuples)


def _is_hex64(value: object) -> bool:
    """64 位小写 hex 摘要形态判定（digest / 内容哈希 / 指纹共用）。"""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _parse_adjudication(payload: object, line_no: int) -> AdjudicationRecord:
    """单条裁定记录严格校验（fail-loud，损坏记录不可表达；记录本身不
    含私人全文——只含哈希 / 长度 / 定位证据）。"""

    def fail(field: str) -> None:
        raise ValueError(
            f"裁定日志第 {line_no} 行记录非法：{field}"
            "（裁定记录损坏形态不可表达——fail-loud，整批阻断）"
        )

    if not isinstance(payload, dict):
        fail("整条记录须为 JSON 对象")
    ts = payload.get("ts")
    if not isinstance(ts, str) or not ts:
        fail("ts 须为非空字符串（时间戳仅作记录，不作择优或生效依据）")
    digest = payload.get("location_digest")
    if not _is_hex64(digest):
        fail("location_digest 须为 64 hex 摘要")
    message_uid = payload.get("message_uid")
    if not isinstance(message_uid, str) or not message_uid:
        fail("message_uid 须为非空字符串")
    fingerprint = payload.get("candidate_set_fingerprint")
    if not _is_hex64(fingerprint):
        fail("candidate_set_fingerprint 须为 64 hex 摘要")
    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        fail("candidates 须为非空数组")
    candidates: list[AdjudicationCandidate] = []
    for index, item in enumerate(raw_candidates):
        if not isinstance(item, dict):
            fail(f"candidates[{index}] 须为 JSON 对象")
        rowid = item.get("rowid")
        if isinstance(rowid, bool) or not isinstance(rowid, int):
            fail(f"candidates[{index}].rowid 须为整数（定位证据）")
        session_id = item.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            fail(f"candidates[{index}].session_id 须为非空字符串")
        candidate_hash = item.get("content_sha256")
        if not _is_hex64(candidate_hash):
            fail(f"candidates[{index}].content_sha256 须为 64 hex 摘要")
        content_len = item.get("content_len")
        if isinstance(content_len, bool) or not isinstance(content_len, int) or content_len < 0:
            fail(f"candidates[{index}].content_len 须为非负整数")
        candidates.append(
            AdjudicationCandidate(
                rowid=rowid,
                session_id=session_id,
                content_sha256=candidate_hash,
                content_len=content_len,
            )
        )
    # 记录自一致性：声明指纹必须与 candidates 重算指纹一致（防篡改 /
    # 防候选集合与指纹脱节——不一致 = 损坏记录）。
    recomputed = _fingerprint_from_tuples(
        [
            (c.rowid, c.content_sha256, c.content_len, c.session_id)
            for c in candidates
        ]
    )
    if recomputed != fingerprint:
        fail(
            "candidate_set_fingerprint 与 candidates 重算指纹不一致"
            "（记录自一致性破坏——fail-loud）"
        )
    conclusion = payload.get("conclusion")
    if conclusion not in ("A", "B", "C"):
        fail("conclusion 须为 A / B / C")
    selected = payload.get("selected_content_sha256")
    if conclusion == "A":
        if not _is_hex64(selected):
            fail("selected_content_sha256 须为 64 hex 摘要（结论 A 必须明确选定候选内容）")
        if selected not in {c.content_sha256 for c in candidates}:
            fail("selected_content_sha256 必须属于该记录候选集合的内容哈希")
    elif selected is not None:
        fail("selected_content_sha256 在结论 B / C 下必须缺失（B / C 不授权导入）")
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason:
        fail("reason 须为非空字符串（人工理由）")
    evidence_refs = payload.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or not all(
        isinstance(ref, str) and ref for ref in evidence_refs
    ):
        fail("evidence_refs 须为字符串数组（可缺失 = 空）")
    adjudicated_by = payload.get("adjudicated_by")
    if not isinstance(adjudicated_by, str) or not adjudicated_by:
        fail("adjudicated_by 须为非空字符串（裁定来源；身份核验 = UNKNOWN，机器不核验）")
    return AdjudicationRecord(
        ts=ts,
        location_digest=digest,
        message_uid=message_uid,
        candidate_set_fingerprint=fingerprint,
        candidates=tuple(candidates),
        conclusion=conclusion,
        selected_content_sha256=selected,
        reason=reason,
        evidence_refs=tuple(evidence_refs),
        adjudicated_by=adjudicated_by,
    )


def read_adjudications(log: Path) -> tuple[AdjudicationRecord, ...]:
    """读裁定日志 = 人工裁定记录集合（JSONL，append-only，与导入日志
    完全分离）。缺失 = 无任何裁定（初始态）→ 空元组；任何非法行 =
    损坏 → fail-loud（整批阻断，先于任何导入）。记录语义（A / B / C
    咨询与指纹匹配）归 host adapter 层咨询面，本函数只做记录结构与
    自一致性校验。"""
    if not log.is_file():
        return ()
    records: list[AdjudicationRecord] = []
    for line_no, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"裁定日志第 {line_no} 行不是合法 JSON"
                "（裁定记录损坏形态不可表达——fail-loud，整批阻断）"
            ) from error
        records.append(_parse_adjudication(payload, line_no))
    return tuple(records)


def append_adjudication(log: Path, record: AdjudicationRecord) -> None:
    """裁定记录追加落盘（JSONL append-only，不重写不删除历史；布局确
    保经既有日志父目录 mkdir 通道）。裁定记录永不写入 imported.log、
    永不计入导入幂等状态。**本函数永不被 host adapter 层引用**（棘轮
    白名单固化）——机器不替人工裁定，写入面与咨询面分离。"""
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
