"""Hermes 宿主 adapter —— M09 S2/S3/S4（open_session：状态位置解析 +
钉定；import_session：经验回流 R-12 源头过滤 + 中性候选 + 宿主侧
幂等；sync：V0 同步形态收敛位——重新解析 + 重导入）。

依据：spec-adapters.md §1（open_session / import_session；V0 漂移形态
收敛 M-01/M-02/M-03）、ADR 0002 决定 1/4（唯一允许知道宿主名的层 =
本模块；解析输入 = 装配期注入的声明位配置，无 env 读、无系统默认
位置，U-5）、M-02（V0 进程间桥形态在 V1 无对应形态）、M-03（状态位置
三位置 fallback 形态收敛到本层内部解析——布局知识只属于本模块；宿主
未运行 = 初始态，空位置不 fail-loud）；ADR 0010 契约实施票 D1 裁定
1–8 + D-056 身份冲突保护（同 message_uid 不同 content → 无有效人工裁
定则任何写入之前 fail-loud；跨 session clone 按逻辑消息身份去重）+
ADR 0010 §Revision 修订 Decision 12 人工裁定通道（D-058：冲突组唯一
放行路径 = 指纹匹配的有效人工裁定记录——见 import_session /
_consult_adjudication）。

- 本模块 = 宿主 adapter 层：I/O 一律经宿主载体通道（S3
  `host_carrier`），本模块自身零 I/O、零宿主存储细节（棘轮固化）。
- import 面 = 白名单类型 / 通道函数引用（中性 Interface 句柄 / 报告 +
  Experience 候选类型 + 宿主载体通道函数），不构造任何组件（棘轮固化，
  同 individual.py 决定 ⑲ 先例）。
- 构造注入面（R-09 / U-5）：全部 keyword-only、无默认值——坏配置
  （显式位置与宿主根同时配置 / 两者皆缺）fail-loud。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from dao_sheng.growth import ExperienceCandidate
from dao_sheng.host_carrier import append_imported, candidate_set_fingerprint, content_sha256, location_digest, read_adjudications, read_imported_keys, read_session_records
from dao_sheng.host_integration import HostSession, SyncReport

#: R-12 源头过滤标记（rebuild.md 方向 ①：标记 + 过滤在源头）——投影
#: 内容 = "被告诉"，不是"经历"：带此标记的会话记录不建立为
#: Experience。标记施用 = 投影发出点（V1 未建——individual 投影目前
#: 仅进 Model 进程内通道，决定 ⑰）；识别 = 本层回流点（INV-7 单向：
#: 宁漏跳不泄漏）。中性协议常量：DaoSheng 侧投影概念（决定 2），非
#: 宿主名。
_PROJECTION_MARKER = "[dao-sheng:projection]"


class HermesHostAdapter:
    """Hermes 宿主 adapter（ADR 0002 决定 1：进程内 adapter 层，宿主名 /
    宿主布局知识只属于本层；Interface = host_integration 中性三方法，
    本模块是其唯一实现，seam = hypothetical，§4）。"""

    def __init__(
        self,
        *,
        state_db: Path | None,
        hermes_home: Path | None,
        import_log: Path,
        adjudication_log: Path | None,
        import_channel: Callable[
            [Sequence[ExperienceCandidate]], tuple[str, ...]
        ],
        candidate: type[ExperienceCandidate],
        origin: object,
    ) -> None:
        """装配点构造（R-09）：状态位置声明位（二选一，互斥）+ 导入
        通道 / 日志 / 裁定日志 / 候选与 origin 类型注入——全部无默认
        值，缺失即 TypeError（未装配不得静默运行，U-5）。

        adjudication_log（D-058 / ADR 0010 修订 Decision 12）= 人工裁
        定日志位置（`host/adjudications.jsonl` 形态，append-only，与
        导入日志完全分离）；显式 None = 未配置裁定日志 → 冲突组永远
        fail-loud（最严格缺省：无裁定即无导入）。"""
        if state_db is not None and hermes_home is not None:
            raise ValueError(
                "状态库位置与宿主根互斥：只可配置其一（坏配置不得进 adapter）"
            )
        if state_db is None and hermes_home is None:
            raise ValueError(
                "状态位置未配置：须注入显式状态库位置或宿主根（U-5：无 env 读、无默认位置）"
            )
        self._state_db = state_db
        self._hermes_home = hermes_home
        self._import_log = import_log
        self._adjudication_log = adjudication_log
        self._import_channel = import_channel
        self._candidate = candidate
        self._origin = origin

    def open_session(self) -> HostSession:
        """建立 / 打开 host 会话：解析状态位置并钉定句柄。

        解析输入 = 构造注入的声明位配置：显式状态库位置 → 单一位置；
        宿主根 → 宿主布局发现（根状态库 + profiles/*/状态库，布局知识
        由本模块持有，M-01/M-03 收敛）。缺失 = 宿主未运行（初始态）→
        空位置，不 fail-loud。frozen 句柄钉定后，重解析是 sync 的
        职责（S4）。
        """
        return HostSession(state_locations=self._resolve_state_locations())

    def import_session(self, session: HostSession) -> tuple[str, ...]:
        """经验回流（spec-adapters.md §1 / R-12 源头过滤 / ADR 0010 契约
        实施票 D1 / D-056 身份冲突保护）：钉定的状态位置逐一读会话记
        录（经宿主载体通道，只读；派生摘要排除与标记校验已在载体
        preflight 完成）→ 源头过滤（空白 / 投影标记）→ 候选身份
        preflight → 逻辑消息分组去重 → 已导入判重（v4 + 旧键组级多
        读）→ 身份冲突预检与人工裁定咨询（同 message_uid 不同 content
        → 无有效裁定则 fail-loud）
        → 中性候选（origin = EXTERNAL，宿主名不进枚举，
        spec-memory.md §1）→ 导入通道（成长管线），返回新建经历记录
        引用（空 = 无新增）。

        候选资格与身份（D1 裁定 3–8 / D-056）：派生摘要
        （`_compressed_summary` = 1）已被载体在分组与代表版本选择之前
        排除——较新摘要行绝不覆盖原始消息资格；合格原始消息按
        (location, message_uid) 分组——逻辑消息身份不含 session_id
        （Hermes rotation child retarget 换 session_id 保留 message_uid
        = 同一逻辑消息的跨 session clone，按已验证逻辑身份去重）；同
        组多物理版本（clone / 代际）只产生一个候选，代表 = 组内最大
        物理 rowid（rowid 不稳定，只用于同 content 组内确定性代表选
        择，绝不进入 key，绝不作为不同 content 之间的权威）；合格候
        选缺失 / 空 session_id 或 message_uid → fail-loud（D1 裁定 5
        冻结契约，不因 v4 不含 session_id 而放松），绝不回退 rowid /
        content / timestamp 生成身份；`absorbed_message_uids` 不读取、
        不用于合并或删除原始消息候选。

        身份冲突预检与人工裁定咨询（D-056 fail-loud 保护 + D-058 / ADR
        0010 修订 Decision 12 人工裁定通道）：同 message_uid 出现不同
        content（真实宿主库核验形态：original vs demoted-stub、full-
        output vs display-head / persisted-output）→ active / compacted
        标记与 rowid 均无一致权威性，机器绝不自动裁定权威版本。唯一放
        行路径 = 有效人工裁定记录（独立 append-only 裁定日志
        `host/adjudications.jsonl` 形态，与导入日志完全分离）：按
        (location digest, message_uid) 定位、对过滤后的完整候选组重算
        指纹，只有指纹准确匹配当前候选集合的追加顺序最后一条记录生效
        （候选集合任何变化 → 旧裁定失效 → fail-loud，须人工逐组重新裁
        定后整批重跑；较早记录 = 被取代历史，绝不覆盖较新有效裁定）；
        结论 A 按明确选定的 content SHA-256 定位导入候选（同哈希多行
        不构成权威择优，rowid 仅作同内容代表定位）；结论 B（不同事件，
        当前 v4 身份契约无法表达 → 停止并要求进一步裁定）/ 结论 C（未
        知，等同未裁定）/ 无裁定 / 指纹失效 / 未配置裁定日志 → 在该库
        任何候选进入导入通道、任何键写入 imported log 之前整批
        fail-loud ValueError（消息含 message_uid、组内 rowid 与 content
        长度，不 dump 全文）。绝不静默吞掉任一版本，绝不凭 active /
        compacted / rowid 选择代表，绝不过滤冲突行绕开冲突。组处理顺
        序 = 已导入判重（v4 + legacy 多读命中 → 跳过整组，append-only
        幂等契约不回溯重裁）先于冲突预检——无有效人工裁定时含冲突组的
        库导入必 fail-loud（UNKNOWN 保持，机器不发明代表选择规则）。

        单库完整 preflight（D1 §三，无部分副作用）：每个状态库的分组
        与身份裁定全部完成于该库记录进入候选流之前；导入写入（导入通
        道 + 日志追加）只在全部位置裁定完成后才发生——不会先写部分候
        选再发现后续坏记录。

        宿主侧幂等（spec-individual.md §2.3）：导入日志（每行一个幂等
        键，append-only）= 去重状态，跨实例 / 跨进程稳定。判重：v4 键
        （`v4:<location digest>:<message_uid>`，逻辑消息身份，不随物
        理 rowid 或 session_id 变化）+ 旧键组级多读（组内任一物理版本
        已有 v3 / v2 / legacy 键 = 逻辑消息在升级前已导入 → 跳过整组，
        防升级后重复导入；append-only 日志不重写，旧键按完整键字符串
        精确匹配继续可识别，绝不按 ":" 切分解析），新写入只使用 v4。
        顺序 = 先导入后落日志——两者之间崩溃 = in-flight 批可重放重复
        （管线侧幂等协作方承接，M07 决定 ㉑）；日志先落则经历永久丢失
        ——前者优先（票 Comments 记录）。

        Runtime collision guard（Candidate 4 / Q4 裁定 1b）：产生任何
        副作用之前，基于 session 的完整 canonical location 集合建立
        digest → canonical 映射（digest 计算 = `host_carrier.location_digest`
        函数引用——production 层唯一公式位归 host_carrier，本层不重复
        实现）——相同 digest + 不同 canonical location
        = location digest 碰撞（SHA-256 不提供 mathematical injectivity，
        碰撞时 v4 键会把不同库的独立经历错误去重）→ fail-loud
        ValueError：不建立候选、不触发导入、不写 imported log。相同
        canonical location 的重复 Path = 同一位置的重复表示，不算
        collision。
        """
        digest_to_canonical: dict[str, str] = {}
        for location in session.state_locations:
            canonical = location.resolve().as_posix()
            digest = location_digest(canonical)
            seen = digest_to_canonical.get(digest)
            if seen is not None and seen != canonical:
                raise ValueError(
                    "location digest 碰撞：两个不同 canonical 位置产生相同"
                    "摘要（v4 幂等键不可区分不同库的经历，fail-loud——"
                    "不建候选、不导入、不写日志）"
                )
            digest_to_canonical[digest] = canonical
        imported = read_imported_keys(self._import_log)
        # 裁定日志一次性读取（D-058 / ADR 0010 修订 Decision 12）：损坏
        # 裁定日志在任何候选建立 / 任何写入之前 fail-loud（载体读校验
        # 严格）；未配置（None）= 冲突组永远 fail-loud。
        adjudications = (
            read_adjudications(self._adjudication_log)
            if self._adjudication_log is not None
            else ()
        )
        candidates: list[ExperienceCandidate] = []
        for location in session.state_locations:
            # 单库完整 preflight（D1 §三）：分组与身份裁定全部完成于
            # 该库记录进入候选流之前；导入写入在全部位置裁定完成后才
            # 发生（无部分候选 / 日志副作用）。
            canonical_location = location.resolve().as_posix()
            location_digest_value = location_digest(canonical_location)
            groups: dict[str, list] = {}
            for record in read_session_records(location):
                if not record.content.strip():
                    continue
                if _PROJECTION_MARKER in record.content:
                    continue
                # 候选身份 preflight（D1 裁定 5）：合格原始消息缺失 /
                # 空 / 不可用 session_id 或 message_uid → fail-loud，
                # 不得回退 rowid / content / timestamp 生成身份。
                if not isinstance(record.session_id, str) or not record.session_id:
                    raise ValueError(
                        "合格候选缺失 session_id：逻辑消息身份不可建立"
                        "（不得回退 rowid / content / timestamp——"
                        "fail-loud，不建候选、不导入、不写日志）"
                    )
                if not isinstance(record.message_uid, str) or not record.message_uid:
                    raise ValueError(
                        "合格候选缺失 message_uid：逻辑消息身份不可建立"
                        "（不得回退 rowid / content / timestamp——"
                        "fail-loud，不建候选、不导入、不写日志）"
                    )
                # legacy 键 injectivity 守卫（D1 裁定 8 延伸 / D-056 更
                # 新理由）：v4 键因 digest 定长对含 ":" 的身份字段单射，
                # 但 legacy v3 / v2 / v1 键 = 身份字段字符串拼接，身份含
                # ":" 时不同 (session_id, message_uid) / (session_id,
                # rowid) 对会编码为同一旧键（("a:b","c") 与 ("a","b:c")
                # 同键）→ 组级旧键多读静默错误跳过（原始资格被吞 = 违反
                # 契约 2b）→ fail-loud（与载体 P2 integrity 守卫同族；
                # 不是去重规则）。
                if ":" in record.session_id or ":" in record.message_uid:
                    raise ValueError(
                        "合格候选身份含 key 分隔符 ':'：legacy 幂等键不"
                        "可区分不同逻辑消息（静默错误去重不可接受——"
                        "fail-loud，不建候选、不导入、不写日志）"
                    )
                # 逻辑消息分组键（D-056）：(location, message_uid)——不
                # 含 session_id（rotation child retarget 换 session_id 保
                # 留 uid = 同一逻辑消息的跨 session clone，必须落同组去
                # 重）。
                groups.setdefault(record.message_uid, []).append(record)
            for members in groups.values():
                # 组处理顺序（D-056 裁定）：已导入判重先于冲突预检——
                # append-only 幂等契约不回溯重裁，已导入组再出现冲突成
                # 员 = 跳过零新增（不 fail-loud）。v4 键组内全等（同
                # location 同 uid），任一成员命中即整组已导入。
                if any(member.record_key in imported for member in members):
                    continue
                # 旧键兼容（组级多读）：组内任一物理版本已有 v3 / v2 /
                # legacy 导入键 = 逻辑消息在升级前已导入 → 跳过整组（防
                # 升级后重复导入；旧键按完整键字符串精确匹配，绝不按
                # ":" 切分解析；摘要旧键已被载体排除，绝不压制同 UID 原
                # 始消息）。
                if any(
                    key in imported
                    for member in members
                    for key in member.legacy_record_keys
                ):
                    continue
                # 身份冲突预检 + 人工裁定咨询（D-056 fail-loud 保护 +
                # D-058 / ADR 0010 修订 Decision 12，先于任何写入）：同
                # message_uid 不同 content → active / compacted / rowid
                # 均无一致权威性，机器绝不自动裁定权威版本；唯一放行路
                # 径 = 指纹匹配的有效人工裁定记录（无裁定 / 指纹失效 /
                # 结论 B / 结论 C → fail-loud，绝不静默吞任一版本、绝不
                # 部分导入）。
                distinct_contents = {member.content for member in members}
                if len(distinct_contents) > 1:
                    selected_hash = self._consult_adjudication(
                        location_digest_value, members, adjudications
                    )
                    # 结论 A（Decision 12）：以裁定明确选定的 content
                    # SHA-256 定位导入候选。多个候选内容哈希相同 = 同一
                    # 内容（候选内容与 v4 键全等），rowid 仅作同内容内
                    # 代表定位，绝不构成权威择优。
                    selected_members = [
                        member
                        for member in members
                        if content_sha256(member.content) == selected_hash
                    ]
                    representative = max(
                        selected_members, key=lambda member: member.rowid
                    )
                    candidates.append(
                        self._candidate(
                            content=representative.content,
                            memory_origin=self._origin.EXTERNAL,
                            idempotency_key=representative.record_key,
                        )
                    )
                    continue
                # 代表 = 组内最大物理 rowid（D1 裁定 7：rowid 不稳定，
                # 只用于同 content 组内确定性代表选择——摘要行已被载体
                # 在分组之前排除，较新摘要行绝不覆盖原始资格）。
                representative = max(members, key=lambda member: member.rowid)
                candidates.append(
                    self._candidate(
                        content=representative.content,
                        memory_origin=self._origin.EXTERNAL,
                        idempotency_key=representative.record_key,
                    )
                )
        if not candidates:
            return ()
        references = self._import_channel(tuple(candidates))
        append_imported(
            self._import_log, tuple(c.idempotency_key for c in candidates)
        )
        return tuple(references)

    def _consult_adjudication(
        self,
        location_digest_value: str,
        members: list,
        adjudications: tuple,
    ) -> str:
        """冲突组人工裁定咨询（D-058 / ADR 0010 修订 Decision 12）。

        定位 = (location digest, message_uid)；候选集合指纹 = 对该组过
        滤后的完整候选组重算 `candidate_set_fingerprint`（内容基指纹，
        tuple 覆盖 rowid / content SHA-256 / content 长度 / session_id
        ——rowid 只作定位与候选集合变化证据，不是权威排序；marker 或
        session_id 变化 → 指纹变化 → 旧裁定失效）。只有指纹准确匹配当
        前候选集合的裁定记录才生效；同一组的多条追加式记录中，追加顺
        序最后一条 = 生效裁定（较早记录 = 被取代的历史，绝不覆盖较新
        有效裁定；时间戳从不作为选择依据）。

        任何不通过的情形一律 fail-loud（不得默认放行）：未配置裁定日志
        / 无匹配记录（未裁定，或候选集合已变化 → 旧裁定失效须重新裁
        定）/ 结论 B（不同事件，当前 v4 身份契约无法表达 → 停止并要求
        进一步裁定）/ 结论 C（未知 / 证据不足，等同未裁定）/ 选定内容
        哈希不在当前候选集合中（裁定与候选集合不一致 = 记录损坏或指纹
        碰撞）。返回生效结论 A 的 selected_content_sha256。
        """
        identity_evidence = (
            "同 message_uid 不同 content（身份冲突）：message_uid "
            + str(members[0].message_uid)
            + "，组内 rowid "
            + "、".join(str(member.rowid) for member in members)
            + "，content 长度 "
            + "、".join(str(len(member.content)) for member in members)
        )
        if not adjudications:
            raise ValueError(
                identity_evidence
                + " —— 未配置裁定日志，人工裁定无从咨询（权威版本不可机"
                "器裁定；不得凭 active / compacted / rowid 选择代表——"
                "fail-loud，不建候选、不导入、不写日志）"
            )
        fingerprint = candidate_set_fingerprint(members)
        matching = [
            record
            for record in adjudications
            if record.location_digest == location_digest_value
            and record.message_uid == members[0].message_uid
            and record.candidate_set_fingerprint == fingerprint
        ]
        if not matching:
            raise ValueError(
                identity_evidence
                + " —— 无有效裁定记录：未裁定，或候选集合指纹不符（候选"
                "集合已变化 → 旧裁定失效，须人工逐组重新裁定后整批重跑"
                "——fail-loud，不建候选、不导入、不写日志）"
            )
        # 追加顺序最后一条 = 生效裁定（较早记录 = 被取代历史，不得覆盖
        # 较新有效裁定；ts 从不作为选择依据——Decision 12 有效记录选择
        # 规则）。
        effective = matching[-1]
        if effective.conclusion == "B":
            raise ValueError(
                identity_evidence
                + " —— 人工裁定结论 B：不同事件，当前 v4 身份契约无法表"
                "达 → 停止并要求进一步裁定（不建候选、不导入、不写日志）"
            )
        if effective.conclusion == "C":
            raise ValueError(
                identity_evidence
                + " —— 人工裁定结论 C：未知 / 证据不足，等同未裁定（权威"
                "版本不可机器裁定——fail-loud，不建候选、不导入、不写日"
                "志）"
            )
        # 结论 A：选定内容哈希必须位于当前候选集合（防御性核验：记录
        # 损坏或指纹碰撞不得默认放行）。
        selected_hash = effective.selected_content_sha256
        if selected_hash not in {
            content_sha256(member.content) for member in members
        }:
            raise ValueError(
                identity_evidence
                + " —— 裁定选定内容哈希不在当前候选集合中（裁定与候选集"
                "合不一致 = 记录损坏或指纹碰撞，不得默认放行——fail-"
                "loud，不建候选、不导入、不写日志）"
            )
        return selected_hash

    def sync(self) -> SyncReport:
        """同步（V0 宿主同步形态收敛位——`sync_hermes` 移除非改名，
        ADR 0002 决定 5：同步属本层，不属 Growth 核）：重新解析状态
        位置（open_session 钉定后宿主布局可能变化——新增 profile 等，
        M-03 三位置 fallback 形态收敛位）+ 重导入新增内容（经
        import_session：共享宿主侧导入日志 = 同一幂等状态，
        spec-individual.md §2.3），返回 SyncReport。

        error = 降级说明（降级面，INV-1 纪律）——当前无可表达降级形态
        （缺失 = 初始态 → 空位置不 fail-loud；损坏 = fail-loud 非
        降级），恒 None；字段保留供未来降级形态（票 Comments 记录）。
        """
        locations = self._resolve_state_locations()
        references = self.import_session(HostSession(state_locations=locations))
        return SyncReport(state_locations=locations, new_references=references)

    def _resolve_state_locations(self) -> tuple[Path, ...]:
        """状态位置解析（M-03 收敛位）：resolve + 去重 + 确定性排序；
        布局中无任何状态库 = 初始态，空元组。"""
        if self._state_db is not None:
            return (self._state_db.resolve(),)
        home = self._hermes_home
        candidates = [home / "state.db", *sorted(home.glob("profiles/*/state.db"))]
        found = {p.resolve() for p in candidates if p.is_file()}
        return tuple(sorted(found, key=lambda p: str(p).lower()))
