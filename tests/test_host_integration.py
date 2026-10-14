"""Host 集成层 — M09（S1 中性 Interface / S2 open_session /
S3 import_session / S4 sync）。

依据：spec-adapters.md §1（中性三方法 Interface、无宿主名，ADR 0002
决定 2）、§4（seam = hypothetical，单 adapter 如实记录；Interface 不随
adapter 变化）、§5（进程边界）、ADR 0002 决定 1–6。

S1：`dao_sheng/host_integration.py` = 中性 Interface 模块——
`HostIntegration` 协议恰三方法（open_session / import_session / sync）
+ `HostSession` 句柄；零宿主知识（无宿主名 token）、零内部模块 import、
零 I/O（同 memory.py Ontology 模块纪律，棘轮固化）。

S2：`dao_sheng/hermes_host.py` = Hermes 宿主 adapter（唯一允许知道宿主
名的层，ADR 0002 决定 1）——`open_session` = 状态位置解析 + 句柄 root
钉定；解析输入 = 装配期注入的声明位配置（显式状态库位置 与 宿主根布局
发现 二选一，坏配置 fail-loud；M-03 三位置 fallback 形态收敛：无 env
读、无系统默认路径，U-5）。

S3：`import_session` = 经验回流（R-12 源头过滤 + 中性候选 + 宿主侧
幂等 / ADR 0010 契约实施票 D1 + D-056 身份冲突保护）——读钉定位置的
会话记录（经 `dao_sheng/host_carrier.py` 宿主载体通道，只读连接；宿
主层唯一 I/O 通道；载体 preflight = 必需列检查 + 派生摘要标记校验 +
标记 = 1 排除）→ 源头过滤（空白 / 投影标记）→ 候选身份 preflight →
逻辑消息分组去重（(location, message_uid) 不含 session_id，rotation
clone 去重；代表 = 组内最大物理 rowid，只用于同 content 组内确定性
选择）→ 已导入判重（v4 键 + v3 / v2 / legacy 旧键组级多读）→ 身份冲
突预检（同 message_uid 不同 content → 任何写入之前 fail-loud）→ 中性
候选（origin = EXTERNAL，宿主名不进枚举）→ 导入通道（成长管线）；去
重状态 = 宿主自有导入日志（append-only，每行一个幂等键，跨实例 / 跨
进程稳定，spec-individual.md §2.3；新写入只使用 v4 键
`v4:<location digest>:<message_uid>`）。

S4：`sync` = V0 同步形态收敛位（`sync_hermes` 移除非改名，ADR 0002 决定
5：同步属本层不属 Growth 核）——重新解析状态位置（宿主布局可能在
open_session 后变化，M-03 三位置 fallback 形态收敛位）+ 重导入新增
内容（与 import_session 共享宿主侧导入日志 = 同一幂等状态）→
`SyncReport`（frozen；error = 降级面，当前无可表达降级形态）。
"""

import hashlib
import os
import sqlite3
import tempfile
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
from typing import get_protocol_members
from unittest import mock

from dao_sheng.growth import ExperienceCandidate
from dao_sheng.hermes_host import HermesHostAdapter
from dao_sheng.host_carrier import (
    AdjudicationCandidate,
    AdjudicationRecord,
    HostSessionRecord,
    append_adjudication,
    candidate_set_fingerprint,
    content_sha256,
    location_digest,
    read_adjudications,
    read_session_records,
)
from dao_sheng.host_integration import (
    HostIntegration,
    HostSession,
    SyncReport,
)
from dao_sheng.memory import MemoryOrigin

PKG = Path(__file__).resolve().parents[1] / "dao_sheng"


class S1NeutralInterfaceTest(unittest.TestCase):
    """AC 2 结构面（ADR 0002 决定 2）：Interface = 中性三方法，无宿主名。"""

    def test_protocol_exactly_three_methods(self):
        """契约形态固化（同 MemoryRatchetTest 6 方法先例）：恰三方法——
        无 V0 `sync_hermes` 形态（决定 5：移除非改名）、无宿主名成员。"""
        self.assertEqual(
            get_protocol_members(HostIntegration),
            frozenset({"open_session", "import_session", "sync"}),
        )

    def test_host_integration_module_zero_host_knowledge(self):
        """AC 1（H-1…H-9 收敛）：中性 Interface 模块零宿主名 token
        （大小写不敏感）——宿主名只属于宿主 adapter 层与装配点声明位
        （ADR 0002 决定 2）。"""
        src = (PKG / "host_integration.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("hermes", src)

    def test_host_session_is_frozen_handle(self):
        """S2 依据：`HostSession` = frozen dataclass 句柄——open 时钉定
        状态位置，会话建立后位置不可变（重解析是 sync 的职责）。"""
        self.assertTrue(is_dataclass(HostSession))
        self.assertTrue(HostSession.__dataclass_params__.frozen)

    def test_module_zero_internal_import_zero_io(self):
        """R-09 / M05 纪律（对齐 memory.py）：seam 契约 = 纯类型定义——
        不 import 任何内部模块、无 I/O 形态。"""
        src = (PKG / "host_integration.py").read_text(encoding="utf-8")
        self.assertNotIn("dao_sheng", src)
        self.assertNotIn("open(", src)
        self.assertNotIn("read_text", src)
        self.assertNotIn("write_text", src)


class S2OpenSessionTest(unittest.TestCase):
    """S2（spec-adapters.md §1 open_session / M-02·M-03 形态收敛）：
    open_session = 状态位置解析 + 句柄 root 钉定——解析输入全部来自
    构造注入（声明位），无 env 读、无默认位置、无宿主外发现。"""

    def _make_home(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        (home / "state.db").touch()
        for p in ("alpha", "beta"):
            d = home / "profiles" / p
            d.mkdir(parents=True)
            (d / "state.db").touch()
        return home

    def _adapter(self, **overrides) -> HermesHostAdapter:
        base = dict(
            state_db=None,
            hermes_home=None,
            import_log=Path("log") / "import.jsonl",
            adjudication_log=None,
            import_channel=lambda candidates: (),
            candidate=ExperienceCandidate,
            origin=MemoryOrigin,
        )
        base.update(overrides)
        return HermesHostAdapter(**base)

    def test_discovery_mode_resolves_root_and_profile_layout(self):
        """宿主根发现模式：根状态库 + profiles/*/状态库布局——宿主布局
        知识只属于宿主 adapter 层（M-01/M-03 收敛位）；结果 resolve +
        去重 + 确定性排序。"""
        home = self._make_home()
        session = self._adapter(hermes_home=home).open_session()
        expected = tuple(
            sorted(
                {
                    (home / "state.db").resolve(),
                    (home / "profiles" / "alpha" / "state.db").resolve(),
                    (home / "profiles" / "beta" / "state.db").resolve(),
                },
                key=lambda p: str(p).lower(),
            )
        )
        self.assertEqual(session.state_locations, expected)

    def test_explicit_state_db_single_location(self):
        """显式状态库位置 = 单一位置，不做布局发现。"""
        home = self._make_home()
        session = self._adapter(state_db=home / "state.db").open_session()
        self.assertEqual(
            tuple(session.state_locations),
            ((home / "state.db").resolve(),),
        )

    def test_empty_discovery_is_initial_state(self):
        """宿主根存在但布局中无任何状态库 = 宿主未运行（初始态）——
        空位置元组，不 fail-loud（对齐 continuity 缺失 = 空日志先例）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        session = self._adapter(hermes_home=Path(tmp.name)).open_session()
        self.assertEqual(session.state_locations, ())

    def test_both_locations_set_fail_loud(self):
        """显式位置 与 宿主根 同时配置 = 坏配置（歧义）——fail-loud，
        不得静默取一方（对齐 _build_model_client 部分配置即失败先例）。"""
        home = self._make_home()
        with self.assertRaises(ValueError):
            self._adapter(state_db=home / "state.db", hermes_home=home)

    def test_no_location_configured_fail_loud(self):
        """两个位置槽位均未注入 = 未装配（U-5：无 env 读、无默认
        位置）——fail-loud。"""
        with self.assertRaises(ValueError):
            self._adapter()


class S3ImportSessionTest(unittest.TestCase):
    """S3（spec-adapters.md §1 import_session / R-12 源头过滤 /
    spec-individual.md §2.3 宿主侧幂等）：经验回流 = 读宿主状态库会话
    记录（经宿主载体通道，只读）→ 源头过滤（空白 / 投影标记——"被告诉"
    ≠"经历"，INV-7 单向）→ 中性候选（origin = EXTERNAL，宿主名不进
    枚举）→ 导入通道（成长管线）；幂等状态 = 宿主侧导入日志。"""

    MARKER = "[dao-sheng:projection]"

    def _state_db_into(self, path: Path, rows: list[tuple[str, str, str | None]]) -> Path:
        """建真实宿主状态库（V1 载体读取面：messages 表必需列 session_id /
        content / _compressed_summary / message_uid + id 物理行身份 +
        absorbed 元数据列——schema 知识归宿主载体通道，ADR 0002 决定 1；
        V0 逐列 schema = UNKNOWN，票 Comments）。rows = (session_id,
        content, message_uid)；标记默认 0（原始消息形态）。"""
        conn = sqlite3.connect(path)
        try:
            conn.execute(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
                "_compressed_summary INTEGER NOT NULL DEFAULT 0, message_uid TEXT, "
                "absorbed_message_uids TEXT)"
            )
            conn.executemany(
                "INSERT INTO messages (session_id, content, message_uid) "
                "VALUES (?, ?, ?)",
                rows,
            )
            conn.commit()
        finally:
            conn.close()
        return path

    def _state_db(self, rows: list[tuple[str, str, str | None]]) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return self._state_db_into(Path(tmp.name) / "state.db", rows)

    def _state_db_full_into(
        self,
        path: Path,
        rows: list[tuple[int, str, str, int, str | None, str | None]],
    ) -> Path:
        """显式物理行身份 + 派生摘要标记 + absorbed 列的完整形态（clone /
        摘要 / 身份测试需要精确控制 rowid、标记与 absorbed 元数据）。
        rows = (id, session_id, content, _compressed_summary, message_uid,
        absorbed_message_uids)。"""
        conn = sqlite3.connect(path)
        try:
            conn.execute(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
                "_compressed_summary INTEGER NOT NULL DEFAULT 0, message_uid TEXT, "
                "absorbed_message_uids TEXT)"
            )
            conn.executemany(
                "INSERT INTO messages (id, session_id, content, "
                "_compressed_summary, message_uid, absorbed_message_uids) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        finally:
            conn.close()
        return path

    def _state_db_full(
        self, rows: list[tuple[int, str, str, int, str | None, str | None]]
    ) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return self._state_db_full_into(Path(tmp.name) / "state.db", rows)

    def _state_db_marker_relaxed(self, marker: object) -> Path:
        """标记列无 NOT NULL / DEFAULT（NULL 可插入）——非法标记形态
        fail-loud 测试专用（其余列保持必需形态）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "state.db"
        conn = sqlite3.connect(path)
        try:
            conn.execute(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
                "_compressed_summary INTEGER, message_uid TEXT)"
            )
            conn.execute(
                "INSERT INTO messages (id, session_id, content, "
                "_compressed_summary, message_uid) VALUES (1, 's1', '原始经历', ?, 'u1')",
                (marker,),
            )
            conn.commit()
        finally:
            conn.close()
        return path

    def _adapter(
        self,
        log: Path,
        channel,
        adjudication_log: Path | None = None,
        **locations,
    ) -> HermesHostAdapter:
        return HermesHostAdapter(
            state_db=locations.get("state_db"),
            hermes_home=locations.get("hermes_home"),
            import_log=log,
            adjudication_log=adjudication_log,
            import_channel=channel,
            candidate=ExperienceCandidate,
            origin=MemoryOrigin,
        )

    def _channel(self, calls: list):
        def channel(candidates):
            calls.append(tuple(candidates))
            return tuple(f"ref:{c.idempotency_key}" for c in candidates)

        return channel

    def _log_path(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name) / "imported.log"

    @staticmethod
    def _v2(db: Path, session_id: str, rowid: int) -> str:
        """期望 v2 旧键形态（升级前落盘的 legacy 键，含物理 rowid）：
        digest 由测试侧对 fixture 路径独立施加 spec 算法（SHA-256 over
        `resolve().as_posix()`，64 hex 全量）得出，不手抄 hex。"""
        digest = hashlib.sha256(db.resolve().as_posix().encode("utf-8")).hexdigest()
        return f"v2:{digest}:{session_id}:{rowid}"

    @staticmethod
    def _v3(db: Path, session_id: str, message_uid: str) -> str:
        """期望 v3 legacy 键（D1 裁定 8 形态，D-056 起降为 legacy）：
        `v3:<location digest>:<session_id>:<message_uid>`——D-056 之前生
        产落盘形态，日志 append-only 不重写，升级后仍须被组级多读识别；
        digest 由测试侧独立施加 spec 算法得出，不手抄 hex。"""
        digest = hashlib.sha256(db.resolve().as_posix().encode("utf-8")).hexdigest()
        return f"v3:{digest}:{session_id}:{message_uid}"

    @staticmethod
    def _v4(db: Path, message_uid: str) -> str:
        """期望 v4 幂等键（D-056 跨 rotation 去重）：
        `v4:<location digest>:<message_uid>`——逻辑消息身份不含
        session_id / rowid（rotation child retarget 换 session_id 保留
        message_uid = 同一逻辑消息的跨 session clone）；digest 由测试侧
        独立施加 spec 算法得出，不手抄 hex。"""
        digest = hashlib.sha256(db.resolve().as_posix().encode("utf-8")).hexdigest()
        return f"v4:{digest}:{message_uid}"

    def test_import_produces_neutral_candidates(self):
        """导入产出中性候选：内容 / origin = EXTERNAL（宿主名不进
        枚举，spec-memory.md §1）/ 幂等键 = global import identity（v4
        形态 `v4:<location digest>:<message_uid>`，逻辑消息身份不含
        session_id / rowid、跨崩溃 / 跨 rowid / 跨 rotation session 变
        化稳定，§2.3 / D1 裁定 8 / D-056）；返回新建经历记录引用；导
        入日志落盘（宿主侧去重状态持久点）。"""
        db = self._state_db(
            [("s1", "first", "u1"), ("s1", "second", "u2"), ("s2", "third", "u3")]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        # key = v4 含 location digest + 逻辑消息身份（不含 session_id / rowid）
        self.assertEqual(
            refs,
            (
                f"ref:{self._v4(db, 'u1')}",
                f"ref:{self._v4(db, 'u2')}",
                f"ref:{self._v4(db, 'u3')}",
            ),
        )
        self.assertEqual(
            calls,
            [
                (
                    ExperienceCandidate(
                        content="first",
                        memory_origin=MemoryOrigin.EXTERNAL,
                        idempotency_key=self._v4(db, "u1"),
                    ),
                    ExperienceCandidate(
                        content="second",
                        memory_origin=MemoryOrigin.EXTERNAL,
                        idempotency_key=self._v4(db, "u2"),
                    ),
                    ExperienceCandidate(
                        content="third",
                        memory_origin=MemoryOrigin.EXTERNAL,
                        idempotency_key=self._v4(db, "u3"),
                    ),
                ),
            ],
        )
        self.assertEqual(
            log.read_text(encoding="utf-8"),
            f"{self._v4(db, 'u1')}\n{self._v4(db, 'u2')}\n{self._v4(db, 'u3')}\n",
        )

    def test_reimport_same_instance_zero_new(self):
        """AC 3：同一会话重复导入（同实例）→ 零新候选、零新引用、
        导入通道不再触发——宿主侧幂等（§2.3）。"""
        db = self._state_db([("s1", "first", "u1"), ("s2", "second", "u2")])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        session = adapter.open_session()
        self.assertEqual(len(adapter.import_session(session)), 2)
        self.assertEqual(adapter.import_session(session), ())
        self.assertEqual(len(calls), 1)

    def test_reimport_new_instance_cross_process_zero_new(self):
        """AC 3 最强形态：崩溃 / 重启后新实例（同导入日志）重导入 →
        零新候选——幂等状态在宿主侧载体，不在实例内。"""
        db = self._state_db([("s1", "first", "u1")])
        log = self._log_path()
        first = self._adapter(log, self._channel([]), state_db=db)
        self.assertEqual(len(first.import_session(first.open_session())), 1)
        calls: list = []
        second = self._adapter(log, self._channel(calls), state_db=db)
        self.assertEqual(second.import_session(second.open_session()), ())
        self.assertEqual(calls, [])

    def test_legacy_key_recognized_and_preserved(self):
        """legacy + v2 组级双读（迁移兼容，D1 裁定 8 / 旧键兼容）：导入
        日志中既有 legacy 键（`session_id:rowid` 旧形态）必须继续被识别
        = 已导入——组内任一物理版本的旧键命中即跳过整组，不得因 key
        格式变更而重导入既有经历；新导入只写 v4 键；append-only 日志不
        重写——legacy 行原样保留。"""
        db = self._state_db([("s1", "first", "u1"), ("s1", "second", "u2")])
        log = self._log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("s1:1\n", encoding="utf-8")  # legacy 键（旧形态，覆盖 rowid 1）
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        # (s1,u1) 组（rowid 1）已被 legacy 键覆盖 → 不重导入；
        # (s1,u2) 组（rowid 2）以 v4 键新导入
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u2')}",))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 1)
        self.assertEqual(calls[0][0].idempotency_key, self._v4(db, "u2"))
        # append-only：legacy 行原样保留，新 v4 行追加
        self.assertEqual(
            log.read_text(encoding="utf-8").splitlines(),
            ["s1:1", self._v4(db, "u2")],
        )
        # 再导入：v4 键已落日志 → 零新增（多读幂等稳定）
        self.assertEqual(adapter.import_session(adapter.open_session()), ())

    def test_projection_marker_filtered_at_source(self):
        """R-12 源头过滤：带投影标记的记录不建立为 Experience 候选
        （"被告诉"≠"经历"，rebuild.md 方向 ①；INV-7 单向：宁漏跳不
        泄漏）；标记记录不落导入日志（每次导入仍被过滤，不占去重
        状态）。"""
        db = self._state_db(
            [
                ("s1", f"{self.MARKER} projection text", "u1"),
                ("s1", "real experience", "u2"),
            ]
        )
        log = self._log_path()
        adapter = self._adapter(log, self._channel([]), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u2')}",))
        self.assertEqual(
            log.read_text(encoding="utf-8"), f"{self._v4(db, 'u2')}\n"
        )

    def test_blank_records_skipped(self):
        """空白记录源头跳过（无内容 = 无经历可建；候选空白 fail-loud
        契约归 M07，本层在源头滤掉，不进管线）。"""
        db = self._state_db([("s1", "   \n", "u1"), ("s1", "real", "u2")])
        log = self._log_path()
        adapter = self._adapter(log, self._channel([]), state_db=db)
        self.assertEqual(
            adapter.import_session(adapter.open_session()),
            (f"ref:{self._v4(db, 'u2')}",),
        )

    def test_missing_state_db_is_initial_state(self):
        """宿主状态库缺失 = 宿主未运行（初始态）→ 空引用、导入通道
        不触发、导入日志不创建、不 fail-loud（host 消失不影响个体
        状态，ADR 0002 Consequences）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "state.db"  # 不存在
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        self.assertEqual(adapter.import_session(adapter.open_session()), ())
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_missing_log_first_import_creates_layout(self):
        """导入日志缺失（父目录也不存在）= 首次导入（初始态）→ 正常
        导入；布局确保 = 日志父目录创建（宿主载体通道唯一布局副作用）。"""
        db = self._state_db([("s1", "first", "u1")])
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        log = Path(tmp.name) / "deep" / "nested" / "imported.log"
        adapter = self._adapter(log, self._channel([]), state_db=db)
        self.assertEqual(
            adapter.import_session(adapter.open_session()),
            (f"ref:{self._v4(db, 'u1')}",),
        )
        self.assertTrue(log.is_file())

    def test_discovery_mode_imports_all_locations(self):
        """宿主根发现模式：钉定的多个状态位置逐一回流（布局知识归
        宿主 adapter 层，S2 解析结果直接消费，位置按路径确定性排序）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        root_db = self._state_db_into(
            home / "state.db", [("s-root", "root-row", "u-root")]
        )
        alpha = home / "profiles" / "alpha"
        alpha.mkdir(parents=True)
        alpha_db = self._state_db_into(
            alpha / "state.db", [("s-alpha", "profile-row", "u-alpha")]
        )
        log = self._log_path()
        adapter = self._adapter(log, self._channel([]), hermes_home=home)
        # 排序：profiles/… 路径先于根 state.db（'p' < 's'）
        self.assertEqual(
            adapter.import_session(adapter.open_session()),
            (
                f"ref:{self._v4(alpha_db, 'u-alpha')}",
                f"ref:{self._v4(root_db, 'u-root')}",
            ),
        )

    def test_same_row_identity_across_locations_imports_both(self):
        """P1 regression（Candidate 4）：不同宿主状态库（不同 canonical
        location）出现相同 session_id + 相同 message_uid → 两条记录是两
        条独立经历，必须都被导入。逻辑消息身份只在单库内唯一，旧形态
        不含 location digest 时跨库碰撞 → 第二条被错误去重（经验永久丢
        失）。record_key = global import identity：v4 形态含 location
        digest，不同库的同 message_uid 产生不同幂等键。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        for sub, content in (("a", "from-a"), ("b", "from-b")):
            d = home / "profiles" / sub
            d.mkdir(parents=True)
            self._state_db_into(d / "state.db", [("s1", content, "u1")])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), hermes_home=home)
        refs = adapter.import_session(adapter.open_session())
        # 两条都必须导入：两个候选、两个不同幂等键、两条日志行
        self.assertEqual(len(refs), 2)
        self.assertEqual(len(calls), 1)
        keys = tuple(c.idempotency_key for c in calls[0])
        self.assertEqual(len(keys), 2)
        self.assertEqual(len(set(keys)), 2)
        self.assertEqual(
            sorted(log.read_text(encoding="utf-8").splitlines()), sorted(keys)
        )

    def test_malformed_session_id_fail_loud(self):
        """P2（session_id integrity）：session_id 含任何 `splitlines()`
        切分字符（全集逐一验证）→ fail-loud ValueError——在
        HostSessionRecord / 候选建立之前失败；导入通道不触发、导入日志
        不落盘。理由：导入日志 = 每行一个幂等键的 append-only 去重状态
        记录，切分字符进入 key 会把一条 key 拆成多行 / 与相邻 key 粘连
        = 损坏形态不可表达。本守卫只查切分字符——普通空白不受本守卫限
        制；":" / 空 session_id 的合格候选资格裁定归 host adapter 层
        D1 身份 preflight / injectivity 守卫（fail-loud，见
        test_missing_or_empty_session_id_fail_loud /
        test_identity_colon_injectivity_guard_fail_loud）。"""
        for bad in (
            "\n", "\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e",
            "\x85", chr(0x2028), chr(0x2029),
        ):
            with self.subTest(bad=repr(bad)):
                db = self._state_db([(f"s{bad}1", "content", "u1")])
                log = self._log_path()
                calls: list = []
                adapter = self._adapter(log, self._channel(calls), state_db=db)
                with self.assertRaises(ValueError):
                    adapter.import_session(adapter.open_session())
                self.assertEqual(calls, [])
                self.assertFalse(log.exists())

    def test_malformed_message_uid_fail_loud(self):
        """P2 扩展（D-058 deferred finding 闭合）：message_uid 含任何
        `splitlines()` 切分字符（全集逐一验证）→ fail-loud ValueError——
        在 HostSessionRecord / 候选建立之前失败；导入通道不触发、导入日志
        不落盘。理由：message_uid 嵌入 v4 写入键（`v4:<digest>:<uid>`）与
        legacy v3 键，切分字符同样把一条幂等键拆成多行 / 与相邻 key 粘连
        = 去重状态记录形态不可表达。":" / 空 message_uid 的裁定归 host
        adapter 层 injectivity 守卫（见
        test_identity_colon_injectivity_guard_fail_loud）。"""
        for bad in (
            "\n", "\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e",
            "\x85", chr(0x2028), chr(0x2029),
        ):
            with self.subTest(bad=repr(bad)):
                db = self._state_db([("s1", "content", f"u{bad}1")])
                log = self._log_path()
                calls: list = []
                adapter = self._adapter(log, self._channel(calls), state_db=db)
                with self.assertRaises(ValueError):
                    adapter.import_session(adapter.open_session())
                self.assertEqual(calls, [])
                self.assertFalse(log.exists())

    def test_location_digest_collision_guard_fail_loud(self):
        """Runtime collision guard（Candidate 4 / Q4 裁定 1b）：SHA-256
        不提供 mathematical injectivity（固定长度摘要，鸽笼原理）——两个
        不同 canonical location 产生相同 digest 时 v4 键碰撞（不同库的独立
        经历被错误去重）。guard = import_session 产生任何副作用之前，基于
        session 的完整 canonical location 集合建立 digest → canonical
        映射：相同 digest + 不同 canonical → fail-loud ValueError——不建立
        候选、不触发导入、不写 imported log。测试侧 patch
        `dao_sheng.hermes_host.location_digest`（= hermes_host 经 import
        绑定的 `host_carrier.location_digest` 函数引用——from-import 绑定
        在 hermes_host 命名空间，patch 该命名空间名即 patch 该引用；
        Candidate 4 conformance correction 后 hermes_host 无本地 digest
        helper）制造两个不同 canonical location 的相同 digest（真实
        SHA-256 碰撞无法制造；patch 目标不是全局 hashlib）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        for sub, content in (("a", "from-a"), ("b", "from-b")):
            d = home / "profiles" / sub
            d.mkdir(parents=True)
            self._state_db_into(d / "state.db", [("s1", content, "u1")])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), hermes_home=home)
        with mock.patch(
            "dao_sheng.hermes_host.location_digest", return_value="0" * 64
        ):
            with self.assertRaises(ValueError):
                adapter.import_session(adapter.open_session())
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_repeated_same_canonical_location_not_collision(self):
        """Collision guard 边界：相同 canonical location 的重复 Path =
        不算 collision（digest → canonical 映射：相同 digest + 相同
        canonical = 同一位置的重复表示，不是两个位置碰撞）→ guard 不
        误触发，导入正常进行。"""
        db = self._state_db([("s1", "content", "u1")])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        adapter.import_session(HostSession(state_locations=(db, db.resolve())))
        self.assertEqual(len(calls), 1)
        self.assertIn(
            self._v4(db, "u1"), log.read_text(encoding="utf-8").splitlines()
        )

    def test_record_key_digest_uses_host_carrier_location_digest(self):
        """digest formula 唯一归属（Candidate 4 conformance correction）：
        `host_carrier.location_digest` = production 层唯一 location digest
        公式位——(1) 函数输出 = 测试侧独立施加 spec 算法（SHA-256 over
        canonical posix 形态，64 hex 全量）的结果，不手抄 hex；(2) v4
        record_key 与 legacy 键（v3 / v2 / v1）经该函数构造：patch
        `dao_sheng.host_carrier.location_digest` 为哨兵摘要后
        `read_session_records` 的 record_key / legacy_record_keys 随之改
        变（若 key 内联独立公式，patch 不会生效——本断言正是「同一实
        现」的直接证明）。"""
        db = self._state_db([("s1", "content", "u1")])
        canonical = db.resolve().as_posix()
        self.assertEqual(
            location_digest(canonical),
            hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        )
        sentinel = "f" * 64
        with mock.patch(
            "dao_sheng.host_carrier.location_digest", return_value=sentinel
        ):
            records = read_session_records(db)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].record_key, f"v4:{sentinel}:u1")
        self.assertEqual(
            records[0].legacy_record_keys,
            (f"v3:{sentinel}:s1:u1", f"v2:{sentinel}:s1:1", "s1:1"),
        )

    def test_derived_summary_marker_excluded_from_candidates(self):
        """派生摘要排除（D1 裁定 3 / 契约 2a）：`_compressed_summary` = 1
        的记录不建立为 Experience 候选——载体在身份检查与分组之前就不为
        它建 record（读取面直接不出现摘要行）；原始消息（标记 = 0）正常
        回流（原始消息按既有 Experience Definition 保持候选资格，契约
        2b）。"""
        db = self._state_db_full(
            [
                (1, "s1", "原始经历", 0, "u1", None),
                (2, "s1", "[CONTEXT COMPACTION — REFERENCE ONLY] 派生摘要", 1, "u2", None),
            ]
        )
        self.assertEqual(
            tuple(record.message_uid for record in read_session_records(db)),
            ("u1",),
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u1')}",))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 1)
        self.assertEqual(
            log.read_text(encoding="utf-8").splitlines(),
            [self._v4(db, "u1")],
        )

    def test_summary_never_overrides_original_same_uid(self):
        """顺序保证（D1 裁定 3 / 6）：摘要行先于分组与代表版本选择被排
        除——同 (session_id, message_uid) 原始行（rowid 1）+ 较新摘要行
        （rowid 2，标记 = 1）→ 唯一候选 = 原始消息，content 与 v4 键都归
        原始；代表 = 组内最大 rowid 只在原始行之间起作用，摘要行绝不参
        与代表选择。"""
        db = self._state_db_full(
            [
                (1, "s1", "原始经历", 0, "u1", None),
                (2, "s1", "[CONTEXT COMPACTION — REFERENCE ONLY] 派生摘要", 1, "u1", None),
            ]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u1')}",))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 1)
        self.assertEqual(calls[0][0].content, "原始经历")
        self.assertEqual(calls[0][0].idempotency_key, self._v4(db, "u1"))

    def test_missing_summary_column_fail_loud(self):
        """必需列 preflight（D1 裁定 1 / 契约 3）：缺 `_compressed_summary`
        列 = 派生摘要标记读取面不可建立 → fail-loud ValueError，在读任何
        行之前；不得把缺标记静默当作"全部非派生摘要"静默导入——导入通
        道不触发、导入日志不落盘。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "state.db"
        conn = sqlite3.connect(db)
        try:
            conn.execute(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
                "message_uid TEXT)"
            )
            conn.execute(
                "INSERT INTO messages (id, session_id, content, message_uid) "
                "VALUES (1, 's1', '原始经历', 'u1')"
            )
            conn.commit()
        finally:
            conn.close()
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        with self.assertRaises(ValueError):
            read_session_records(db)
        with self.assertRaises(ValueError):
            adapter.import_session(adapter.open_session())
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_uninterpretable_marker_fail_loud(self):
        """标记校验（D1 裁定 2 / 契约 3）：`_compressed_summary` 只接受整
        数 0 / 1——NULL / 越界整数 / 非整数 → fail-loud，绝不把未知值默认
        为 0 静默放行（标记缺失不得静默当作非派生摘要）。说明：Python
        bool 经 SQLite round-trip 绑定为整数 0 / 1，bool 形态不可经 DB
        round-trip 构造——不伪造 fixture 语义；载体严格 bool 排除是代码
        事实（host_carrier 裁定 2），DB 侧验证 NULL / 2 / -1 / 'x'（
        INTEGER affinity 列无损转换失败 → 'x' 以 TEXT 存回读为 str）。"""
        for bad in (None, 2, -1, "x"):
            with self.subTest(bad=repr(bad)):
                db = self._state_db_marker_relaxed(bad)
                log = self._log_path()
                calls: list = []
                adapter = self._adapter(log, self._channel(calls), state_db=db)
                with self.assertRaises(ValueError):
                    read_session_records(db)
                with self.assertRaises(ValueError):
                    adapter.import_session(adapter.open_session())
                self.assertEqual(calls, [])
                self.assertFalse(log.exists())

    def test_clone_new_rowid_same_uid_single_candidate(self):
        """逻辑消息去重（D1 裁定 6 / 7；Research Gate rowid 不稳定证据导
        出；D-056 同 content 形态）：clone / 代际产生新 rowid——同
        message_uid 同 content 多物理版本只产生一个候选（代表 = 组内最
        大 rowid，同 content 间的确定性选择无可观察差异）；rowid 不进
        v4 键。第三行（同 content、不同 uid）证明身份判别 = message_uid
        而非 (session_id, content, timestamp)——同内容不同逻辑消息必须
        分别建立，不得仅凭同内容去重。注：同 uid 不同 content = 身份冲
        突，D-056 下 fail-loud（见
        test_identity_conflict_same_uid_different_content_fail_loud），
        本测试只固化同 content clone 去重形态。"""
        db = self._state_db_full(
            [
                (1, "s1", "同一经历", 0, "u1", None),
                (2, "s1", "同一经历", 0, "u1", None),
                (3, "s1", "同一经历", 0, "u2", None),
            ]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(
            refs,
            (f"ref:{self._v4(db, 'u1')}", f"ref:{self._v4(db, 'u2')}"),
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 2)
        by_key = {candidate.idempotency_key: candidate for candidate in calls[0]}
        self.assertEqual(by_key[self._v4(db, "u1")].content, "同一经历")
        self.assertEqual(by_key[self._v4(db, "u2")].content, "同一经历")
        # 重复扫描幂等：再导入 → 零新增
        self.assertEqual(adapter.import_session(adapter.open_session()), ())
        self.assertEqual(len(calls), 1)

    def test_clone_added_after_import_no_duplicate_candidate(self):
        """v4 键不随 rowid / session_id 变化（D1 裁定 7 / 8 / D-056）：
        导入后宿主 clone 产生新 rowid 物理版本（同一逻辑消息）→ 重导入
        零新候选——v2 键（含 rowid）会因新 rowid 产生新键 = 重复候选
        （Research Gate 证据导出 = 本票处理对象），v4 键不变 → 正确去
        重；clone content 与原始不同（身份冲突形态），但组已命中 v4 键
        = 已导入判重先于冲突预检（D-056 组处理顺序，append-only 幂等契
        约不回溯重裁）→ 跳过整组零新增、不 fail-loud；日志仍只有一条
        v4 行。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = self._state_db_full_into(
            Path(tmp.name) / "state.db", [(1, "s1", "原始经历", 0, "u1", None)]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        self.assertEqual(
            adapter.import_session(adapter.open_session()),
            (f"ref:{self._v4(db, 'u1')}",),
        )
        conn = sqlite3.connect(db)
        try:
            conn.execute(
                "INSERT INTO messages (id, session_id, content, "
                "_compressed_summary, message_uid) "
                "VALUES (2, 's1', '原始经历 clone', 0, 'u1')"
            )
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(adapter.import_session(adapter.open_session()), ())
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            log.read_text(encoding="utf-8").splitlines(), [self._v4(db, "u1")]
        )

    def test_legacy_v2_key_group_dual_read_skips_clone_group(self):
        """旧键兼容组级双读（D1 裁定 8）：逻辑消息在升级前已导入（v2 键
        含旧 rowid 落盘）→ 升级后同组出现新物理版本（clone，新 rowid）→
        组内任一物理版本旧键命中 = 跳过整组，不因 rowid 变化重复导入。"""
        db = self._state_db_full(
            [
                (1, "s1", "原始经历", 0, "u1", None),
                (2, "s1", "原始经历 clone", 0, "u1", None),
            ]
        )
        log = self._log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"{self._v2(db, 's1', 1)}\n", encoding="utf-8")  # v2 旧键（rowid 1）
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        self.assertEqual(adapter.import_session(adapter.open_session()), ())
        self.assertEqual(calls, [])

    def test_imported_summary_legacy_key_does_not_suppress_original(self):
        """摘要旧键不压制原始（D1 裁定 3 延伸）：升级前摘要行曾以 v2 键
        导入 → 升级后摘要行被载体在分组之前排除，其 legacy 键绝不被咨询；
        同库原始消息（不同 uid）正常回流为候选，不被摘要旧键压制。"""
        db = self._state_db_full(
            [
                (1, "s1", "原始经历", 0, "u1", None),
                (2, "s1", "[CONTEXT COMPACTION — REFERENCE ONLY] 派生摘要", 1, "u2", None),
            ]
        )
        log = self._log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"{self._v2(db, 's1', 2)}\n", encoding="utf-8")  # 摘要行旧 v2 键
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u1')}",))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0].content, "原始经历")

    def test_absorbed_message_uids_not_read_or_used(self):
        """`absorbed_message_uids` 不读取、不用于合并或删除原始消息候选
        （D1 显式）：三条原始消息（第一条 absorbed 元数据指向第二条、第
        三条指向不存在的 uid）全部独立回流为候选——无合并、无压制。"""
        db = self._state_db_full(
            [
                (1, "s1", "原始经历一", 0, "u1", "u2"),
                (2, "s1", "原始经历二", 0, "u2", None),
                (3, "s1", "原始经历三", 0, "u3", "u-gone"),
            ]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(
            refs,
            (
                f"ref:{self._v4(db, 'u1')}",
                f"ref:{self._v4(db, 'u2')}",
                f"ref:{self._v4(db, 'u3')}",
            ),
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 3)

    def test_missing_message_uid_fail_loud(self):
        """身份 preflight（D1 裁定 5）：合格原始消息（非空白 / 无投影标记）
        缺失 / 空 message_uid → fail-loud ValueError，不得回退 rowid /
        content / timestamp 生成身份。单库完整 preflight（D1 §三，无部分
        副作用）：坏行与合格行同库 → 整体失败，合格行不被先导入（导入
        通道不触发、导入日志不落盘）。"""
        for bad_uid in (None, ""):
            with self.subTest(bad_uid=repr(bad_uid)):
                db = self._state_db_full(
                    [
                        (1, "s1", "合格经历", 0, "u1", None),
                        (2, "s1", "缺身份经历", 0, bad_uid, None),
                    ]
                )
                log = self._log_path()
                calls: list = []
                adapter = self._adapter(log, self._channel(calls), state_db=db)
                with self.assertRaises(ValueError):
                    adapter.import_session(adapter.open_session())
                self.assertEqual(calls, [])
                self.assertFalse(log.exists())

    def test_missing_or_empty_session_id_fail_loud(self):
        """身份 preflight（D1 裁定 5）：合格候选空 session_id → fail-loud。
        载体 P2 守卫只查切分字符（空串不含切分字符，载体不新增禁令——
        NULL session_id = UNKNOWN schema 领域，规则 11）；空 session_id 的
        合格候选资格裁定归 host adapter 层 preflight，不得回退 rowid /
        content / timestamp。"""
        db = self._state_db_full([(1, "", "合格经历", 0, "u1", None)])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        with self.assertRaises(ValueError):
            adapter.import_session(adapter.open_session())
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_identity_colon_injectivity_guard_fail_loud(self):
        """legacy 键 injectivity 守卫（D1 裁定 8 延伸 / D-056 更新理由）：
        v4 键因 digest 定长对含 ':' 的身份字段单射；但 legacy v3 / v2 /
        v1 键 = 身份字段字符串拼接——身份字段含 key 分隔符 ':' → 不同
        (session_id, message_uid) / (session_id, rowid) 对编码为同一 opaque
        旧键（("a:b","c") 与 ("a","b:c") 同键）→ 组级旧键多读静默错误跳
        过（原始资格被吞 = 违反契约 2b）→ fail-loud（不是去重规则）。碰
        撞对库（两行理论同旧键）同样 fail-loud，不建候选、不导入、不写
        日志。"""
        for session_id, message_uid in (("a:b", "c"), ("a", "b:c")):
            with self.subTest(session_id=session_id, message_uid=message_uid):
                db = self._state_db_full(
                    [(1, session_id, "经历", 0, message_uid, None)]
                )
                log = self._log_path()
                calls: list = []
                adapter = self._adapter(log, self._channel(calls), state_db=db)
                with self.assertRaises(ValueError):
                    adapter.import_session(adapter.open_session())
                self.assertEqual(calls, [])
                self.assertFalse(log.exists())
        db = self._state_db_full(
            [
                (1, "a:b", "经历一", 0, "c", None),
                (2, "a", "经历二", 0, "b:c", None),
            ]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        with self.assertRaises(ValueError):
            adapter.import_session(adapter.open_session())
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_cross_session_clone_same_uid_single_candidate(self):
        """跨 session clone 去重（D-056）：Hermes rotation child retarget
        换 session_id 但保留 message_uid = 同一逻辑消息的跨 session 克隆。
        分组键 (location, message_uid) 不含 session_id → 跨 session 多物理
        行只产生一个候选（v4 键不随 session_id 变化），日志单行。"""
        db = self._state_db_full(
            [
                (1, "s1", "同一经历", 0, "u1", None),
                (2, "s2-child", "同一经历", 0, "u1", None),
            ]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u1')}",))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 1)
        self.assertEqual(calls[0][0].content, "同一经历")
        self.assertEqual(
            log.read_text(encoding="utf-8").splitlines(), [self._v4(db, "u1")]
        )

    def test_cross_session_clone_after_import_zero_new(self):
        """导入后 rotation clone（D-056）：逻辑消息已按 v4 键导入后，宿主
        rotation 产生新 session_id 克隆（同 uid 同 content）→ 再导入零新增
        候选（v4 键命中 = 已导入判重），日志仍只有一条 v4 行。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = self._state_db_full_into(
            Path(tmp.name) / "state.db", [(1, "s1", "同一经历", 0, "u1", None)]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        self.assertEqual(
            adapter.import_session(adapter.open_session()),
            (f"ref:{self._v4(db, 'u1')}",),
        )
        conn = sqlite3.connect(db)
        try:
            conn.execute(
                "INSERT INTO messages (id, session_id, content, "
                "_compressed_summary, message_uid) "
                "VALUES (2, 's2-child', '同一经历', 0, 'u1')"
            )
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(adapter.import_session(adapter.open_session()), ())
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            log.read_text(encoding="utf-8").splitlines(), [self._v4(db, "u1")]
        )

    def test_identity_conflict_same_uid_different_content_fail_loud(self):
        """身份冲突 fail-loud（D-056）：同 message_uid 不同 content（真实宿
        主库核验形态：original vs demoted-stub）→ 权威版本不可裁定 → 任何
        导入 / 日志写入之前 ValueError。消息含 message_uid、组内 rowid 与
        content 长度，不 dump 全文；导入通道不触发、导入日志不落盘。"""
        db = self._state_db_full(
            [
                (1857, "s1", "完整原始经历内容", 0, "u-conflict", None),
                (1880, "s1", "降级 stub", 0, "u-conflict", None),
            ]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        message = str(ctx.exception)
        self.assertIn("同 message_uid 不同 content", message)
        self.assertIn("u-conflict", message)
        self.assertIn("1857", message)
        self.assertIn("1880", message)
        self.assertIn(str(len("完整原始经历内容")), message)
        self.assertIn(str(len("降级 stub")), message)
        self.assertNotIn("完整原始经历内容", message)
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_conflict_blocks_whole_import_no_partial_side_effects(self):
        """无部分副作用（D1 §三单库完整 preflight / D-056）：发现模式（宿
        主根 = profiles/* 多库）下冲突库与干净库并存 → 冲突库裁定时
        fail-loud，干净库不被先导入：导入通道不触发、导入日志不落盘
        （不会先写部分候选再发现后续坏库）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        (home / "profiles" / "a").mkdir(parents=True)
        self._state_db_full_into(
            home / "profiles" / "a" / "state.db",
            [(1, "s1", "干净经历", 0, "u-clean", None)],
        )
        (home / "profiles" / "b").mkdir(parents=True)
        self._state_db_full_into(
            home / "profiles" / "b" / "state.db",
            [
                (1, "s1", "原始版本", 0, "u-conflict", None),
                (2, "s1", "冲突版本", 0, "u-conflict", None),
            ],
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), hermes_home=home)
        with self.assertRaises(ValueError):
            adapter.import_session(adapter.open_session())
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_imported_group_with_conflicting_member_skips_not_fail_loud(self):
        """组处理顺序固化（D-056 裁定）：已导入判重先于冲突预检——日志已
        有 v4 键命中该组，组内再出现不同 content 成员（冲突形态）→ 跳过
        整组零新增、不 fail-loud（append-only 幂等契约不回溯重裁）。"""
        db = self._state_db_full(
            [
                (1, "s1", "原始经历", 0, "u1", None),
                (2, "s1", "冲突版本", 0, "u1", None),
            ]
        )
        log = self._log_path()
        log.write_text(f"{self._v4(db, 'u1')}\n", encoding="utf-8")  # 组已导入
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        self.assertEqual(adapter.import_session(adapter.open_session()), ())
        self.assertEqual(calls, [])
        self.assertEqual(
            log.read_text(encoding="utf-8").splitlines(), [self._v4(db, "u1")]
        )

    def test_legacy_v3_key_group_multi_read_skips_import(self):
        """v3 legacy 键识别（D-056 迁移兼容）：D-056 之前生产日志落盘的是
        v3 键（`v3:<location digest>:<session_id>:<message_uid>`）——升级后
        同组必须被 v3 旧键组级多读识别为已导入 → 零新增、日志 append-only
        不变（旧键按完整键字符串精确匹配，绝不按 ":" 切分解析）。"""
        db = self._state_db_full([(1, "s1", "原始经历", 0, "u1", None)])
        log = self._log_path()
        log.write_text(f"{self._v3(db, 's1', 'u1')}\n", encoding="utf-8")  # 升级前 v3 键
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        self.assertEqual(adapter.import_session(adapter.open_session()), ())
        self.assertEqual(calls, [])
        self.assertEqual(
            log.read_text(encoding="utf-8").splitlines(), [self._v3(db, "s1", "u1")]
        )

    def test_same_uid_same_content_multiple_rowids_single_candidate(self):
        """多物理版本去重固化（D-056）：同 message_uid 同 content 跨
        rotation session 链（s1 → s2 → s3，三个物理 rowid）→ 单候选、单日
        志行；重复导入零新增（代表 = 组内最大 rowid，只用于同 content 组
        内确定性选择，同 content 间无可观察差异）。"""
        db = self._state_db_full(
            [
                (1, "s1", "同一经历", 0, "u1", None),
                (2, "s2", "同一经历", 0, "u1", None),
                (3, "s3", "同一经历", 0, "u1", None),
            ]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u1')}",))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 1)
        self.assertEqual(
            log.read_text(encoding="utf-8").splitlines(), [self._v4(db, "u1")]
        )
        self.assertEqual(adapter.import_session(adapter.open_session()), ())
        self.assertEqual(len(calls), 1)

    def test_real_host_conflict_groups_fail_loud(self):
        """真实宿主库冲突保护（D-056 真实数据核验）：真实 Hermes 状态库
        （2026-10-11 只读核验 = 28 组"同 message_uid 不同 content"冲突组）
        → import_session 必须在任何写入之前 fail-loud——冲突组不被静默跳
        过、不被部分导入、不被发明代表选择。只读纪律：导入前后库 size /
        mtime_ns / sha256 必须一致（宿主库永不被改写）；库缺失 = 环境不在
        场 → skip（UNKNOWN 不猜测，规则 11）。"""
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            self.skipTest("LOCALAPPDATA 缺失：真实宿主库位置不可得")
        db = Path(local_appdata) / "hermes" / "state.db"
        if not db.is_file():
            self.skipTest(f"真实宿主库不存在：{db}")
        before = (
            db.stat().st_size,
            db.stat().st_mtime_ns,
            hashlib.sha256(db.read_bytes()).hexdigest(),
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        self.assertIn("同 message_uid 不同 content", str(ctx.exception))
        # 无部分副作用：导入通道不触发、导入日志不落盘
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())
        after = (
            db.stat().st_size,
            db.stat().st_mtime_ns,
            hashlib.sha256(db.read_bytes()).hexdigest(),
        )
        self.assertEqual(after, before)  # 只读：宿主库未被触碰

    def test_corrupt_state_db_fail_loud(self):
        """宿主状态库存在但不可读（非 SQLite 形态）= 损坏 → fail-loud
        （import_session 签名无降级面——降级不可表达）；导入通道不
        触发、导入日志不落盘。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "state.db"
        db.write_text("not a sqlite database")
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        with self.assertRaises(sqlite3.DatabaseError):
            adapter.import_session(adapter.open_session())
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())


class AdjudicationCarrierTest(unittest.TestCase):
    """D-058 裁定日志载体面（host_carrier；ADR 0010 修订 Decision 12 记
    录载体，用户 2026-10-12 裁定采纳）：独立 append-only JSONL 裁定日
    志——数据模型 frozen、追加式读写、严格校验 fail-loud、记录自一致
    性（声明指纹 = candidates 重算指纹）、内容基候选集合指纹（非 DB
    文件哈希）、A 必须选定 ∈ 候选、B / C 不得携带选定哈希、裁定日志
    与导入日志完全分离。咨询语义（指纹匹配 / A 导入 / B / C 阻断）归
    host adapter 层咨询面，见 S3AdjudicationConsultTest。"""

    def _record(
        self, rowid: int, session_id: str | None, content: str, message_uid: str = "uid-1"
    ) -> HostSessionRecord:
        return HostSessionRecord(
            content=content,
            session_id=session_id,
            message_uid=message_uid,
            rowid=rowid,
            record_key=f"v4:digest:{message_uid}",
            legacy_record_keys=(
                f"v3:digest:{session_id}:{message_uid}",
                f"v2:digest:{session_id}:{rowid}",
                f"{session_id}:{rowid}",
            ),
        )

    def _log_path(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name) / "host" / "adjudications.jsonl"

    def _candidate_dicts(self, members: list[HostSessionRecord]) -> list[dict]:
        return [
            {
                "rowid": member.rowid,
                "session_id": member.session_id,
                "content_sha256": content_sha256(member.content),
                "content_len": len(member.content),
            }
            for member in members
        ]

    def _payload(
        self,
        members: list[HostSessionRecord],
        conclusion: str = "A",
        selected: str | None = None,
        fingerprint: str | None = None,
    ) -> dict:
        payload = {
            "ts": "2026-10-12T12:00:00",
            "location_digest": "a" * 64,
            "message_uid": "uid-1",
            "candidate_set_fingerprint": (
                fingerprint
                if fingerprint is not None
                else candidate_set_fingerprint(members)
            ),
            "candidates": self._candidate_dicts(members),
            "conclusion": conclusion,
            "reason": "fixture 裁定理由",
            "evidence_refs": ["docs/audit/d057-hermes-conflict-rederivation-20261012.md"],
            "adjudicated_by": "public-test-reviewer",
        }
        if selected is not None:
            payload["selected_content_sha256"] = selected
        return payload

    def _write_lines(self, log: Path, payloads: list[dict]) -> None:
        import json as _json

        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "".join(_json.dumps(payload, ensure_ascii=False) + "\n" for payload in payloads),
            encoding="utf-8",
        )

    def test_adjudication_dataclasses_are_frozen(self):
        """裁定数据模型 = frozen dataclass（记录不可被下游改写）。"""
        for cls in (AdjudicationCandidate, AdjudicationRecord):
            self.assertTrue(is_dataclass(cls))
            self.assertTrue(cls.__dataclass_params__.frozen)

    def test_missing_adjudication_log_reads_empty(self):
        """缺失 = 无任何裁定（初始态）→ 空元组（不猜测、不报错）。"""
        log = self._log_path()
        self.assertFalse(log.exists())
        self.assertEqual(read_adjudications(log), ())

    def test_content_sha256_formula_single_declaration_site(self):
        """内容 SHA-256 公式 = sha256(utf-8)，64 hex 全量（公式位核验）。"""
        value = content_sha256("道生 fixture 内容")
        self.assertEqual(value, hashlib.sha256("道生 fixture 内容".encode("utf-8")).hexdigest())
        self.assertEqual(len(value), 64)

    def test_fingerprint_order_independent_and_content_sensitive(self):
        """候选集合指纹：成员顺序无关（排序后哈希）；任何候选内容增
        删改 → 指纹变化（旧裁定自动失效，须重新人工裁定）。"""
        members = [
            self._record(10, "session-a", "内容甲"),
            self._record(11, "session-b", "内容乙"),
        ]
        forward = candidate_set_fingerprint(members)
        backward = candidate_set_fingerprint(list(reversed(members)))
        self.assertEqual(forward, backward)
        changed = [
            self._record(10, "session-a", "内容甲"),
            self._record(11, "session-b", "内容乙改"),
        ]
        self.assertNotEqual(candidate_set_fingerprint(changed), forward)
        added = members + [self._record(12, "session-c", "内容丙")]
        self.assertNotEqual(candidate_set_fingerprint(added), forward)
        # 内容基：同 rowid / session 但内容不同 → 指纹不同（非文件哈希）
        self.assertNotEqual(
            candidate_set_fingerprint([self._record(10, "session-a", "内容甲")]),
            candidate_set_fingerprint([self._record(10, "session-a", "内容甲改")]),
        )

    def test_fingerprint_requires_str_session_id(self):
        """指纹组成字段非法（session_id 非 str）→ fail-loud（裁定依据
        不可建立）。"""
        with self.assertRaises(ValueError):
            candidate_set_fingerprint([self._record(10, None, "内容甲")])

    def test_append_then_read_roundtrip(self):
        """追加落盘 → 读回 = 同一记录（字段逐一一致，JSONL 单行）。"""
        log = self._log_path()
        members = [self._record(10, "session-a", "内容甲"), self._record(11, "session-b", "内容乙")]
        selected = content_sha256("内容乙")
        record = AdjudicationRecord(
            ts="2026-10-12T12:00:00",
            location_digest="a" * 64,
            message_uid="uid-1",
            candidate_set_fingerprint=candidate_set_fingerprint(members),
            candidates=tuple(
                AdjudicationCandidate(
                    rowid=item["rowid"],
                    session_id=item["session_id"],
                    content_sha256=item["content_sha256"],
                    content_len=item["content_len"],
                )
                for item in self._candidate_dicts(members)
            ),
            conclusion="A",
            selected_content_sha256=selected,
            reason="fixture 裁定理由",
            evidence_refs=("docs/audit/d057-hermes-conflict-rederivation-20261012.md",),
            adjudicated_by="public-test-reviewer",
        )
        append_adjudication(log, record)
        read_back = read_adjudications(log)
        self.assertEqual(read_back, (record,))
        self.assertEqual(len(log.read_text(encoding="utf-8").splitlines()), 1)

    def test_append_only_preserves_history(self):
        """append-only：追加第二条不重写第一条（历史裁定不可被重写或
        删除；失效经指纹不匹配表达）。"""
        log = self._log_path()
        members = [self._record(10, "session-a", "内容甲"), self._record(11, "session-b", "内容乙")]
        first = self._payload(members, "C")
        second = self._payload(members, "A", selected=content_sha256("内容甲"))
        self._write_lines(log, [first])
        append_adjudication(
            log,
            AdjudicationRecord(
                ts="2026-10-12T13:00:00",
                location_digest="a" * 64,
                message_uid="uid-1",
                candidate_set_fingerprint=candidate_set_fingerprint(members),
                candidates=tuple(
                    AdjudicationCandidate(
                        rowid=item["rowid"],
                        session_id=item["session_id"],
                        content_sha256=item["content_sha256"],
                        content_len=item["content_len"],
                    )
                    for item in self._candidate_dicts(members)
                ),
                conclusion="A",
                selected_content_sha256=content_sha256("内容甲"),
                reason="fixture 追加裁定",
                evidence_refs=(),
                adjudicated_by="public-test-reviewer",
            ),
        )
        lines = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        records = read_adjudications(log)
        self.assertEqual([r.conclusion for r in records], ["C", "A"])
        self.assertEqual(records[0].reason, "fixture 裁定理由")

    def test_append_adjudication_never_touches_import_log(self):
        """裁定日志与导入日志完全分离：追加裁定不创建、不触碰导入日
        志路径。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        log = root / "host" / "adjudications.jsonl"
        import_log = root / "host" / "imported.log"
        members = [self._record(10, "session-a", "内容甲"), self._record(11, "session-b", "内容乙")]
        record = AdjudicationRecord(
            ts="2026-10-12T12:00:00",
            location_digest="a" * 64,
            message_uid="uid-1",
            candidate_set_fingerprint=candidate_set_fingerprint(members),
            candidates=tuple(
                AdjudicationCandidate(
                    rowid=item["rowid"],
                    session_id=item["session_id"],
                    content_sha256=item["content_sha256"],
                    content_len=item["content_len"],
                )
                for item in self._candidate_dicts(members)
            ),
            conclusion="A",
            selected_content_sha256=content_sha256("内容甲"),
            reason="fixture 裁定理由",
            evidence_refs=(),
            adjudicated_by="public-test-reviewer",
        )
        append_adjudication(log, record)
        self.assertTrue(log.is_file())
        self.assertFalse(import_log.exists())

    def test_malformed_json_line_fail_loud(self):
        """非法 JSON 行 = 损坏裁定记录 → fail-loud（含行号，整批阻
        断）。"""
        log = self._log_path()
        members = [self._record(10, "session-a", "内容甲"), self._record(11, "session-b", "内容乙")]
        import json as _json

        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            _json.dumps(self._payload(members, "C"), ensure_ascii=False)
            + "\n"
            + "这不是合法 JSON 行{{{\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError) as ctx:
            read_adjudications(log)
        self.assertIn("第 2 行", str(ctx.exception))

    def test_fingerprint_self_consistency_required(self):
        """声明指纹 ≠ candidates 重算指纹 = 记录自一致性破坏 →
        fail-loud。"""
        log = self._log_path()
        members = [self._record(10, "session-a", "内容甲"), self._record(11, "session-b", "内容乙")]
        self._write_lines(log, [self._payload(members, "C", fingerprint="f" * 64)])
        with self.assertRaises(ValueError) as ctx:
            read_adjudications(log)
        self.assertIn("自一致性", str(ctx.exception))

    def test_conclusion_a_requires_selected_hash_in_candidates(self):
        """结论 A 必须携带 selected_content_sha256 且 ∈ 候选内容哈希
        集合；缺失或不在集合 → fail-loud。"""
        log = self._log_path()
        members = [self._record(10, "session-a", "内容甲"), self._record(11, "session-b", "内容乙")]
        self._write_lines(log, [self._payload(members, "A")])
        with self.assertRaises(ValueError) as ctx:
            read_adjudications(log)
        self.assertIn("selected_content_sha256", str(ctx.exception))
        log2 = self._log_path()
        self._write_lines(log2, [self._payload(members, "A", selected="e" * 64)])
        with self.assertRaises(ValueError) as ctx:
            read_adjudications(log2)
        self.assertIn("候选集合", str(ctx.exception))

    def test_conclusion_bc_forbid_selected_hash(self):
        """结论 B / C 不得携带选定哈希（B / C 不授权导入）；缺失哈希
        的 B / C 记录合法可读。"""
        log = self._log_path()
        members = [self._record(10, "session-a", "内容甲"), self._record(11, "session-b", "内容乙")]
        self._write_lines(
            log,
            [
                self._payload(members, "B"),
                self._payload(members, "C"),
            ],
        )
        records = read_adjudications(log)
        self.assertEqual([r.conclusion for r in records], ["B", "C"])
        self.assertTrue(all(r.selected_content_sha256 is None for r in records))
        log2 = self._log_path()
        self._write_lines(log2, [self._payload(members, "B", selected=content_sha256("内容甲"))])
        with self.assertRaises(ValueError):
            read_adjudications(log2)

    def test_required_fields_fail_loud(self):
        """必需字段缺失 / 非法（ts / location_digest / message_uid /
        candidates 空 / conclusion 非法 / reason 空 / adjudicated_by
        空）→ fail-loud。"""
        members = [self._record(10, "session-a", "内容甲"), self._record(11, "session-b", "内容乙")]
        bad_variants = [
            {**self._payload(members, "C"), "ts": ""},
            {**self._payload(members, "C"), "location_digest": "short"},
            {**self._payload(members, "C"), "message_uid": ""},
            {**self._payload(members, "C"), "candidates": []},
            {**self._payload(members, "D")},
            {**self._payload(members, "C"), "reason": ""},
            {**self._payload(members, "C"), "adjudicated_by": ""},
            {**self._payload(members, "C"), "candidates": [{"rowid": 10}]},
        ]
        for index, payload in enumerate(bad_variants):
            log = self._log_path()
            self._write_lines(log, [payload])
            with self.subTest(variant=index):
                with self.assertRaises(ValueError):
                    read_adjudications(log)


class S3AdjudicationConsultTest(unittest.TestCase):
    """D-058 咨询面（hermes_host._consult_adjudication；ADR 0010 修订
    Decision 12；用户 2026-10-12 裁定采纳）：冲突组唯一放行路径 = 与当
    前候选集合重算指纹准确匹配的有效人工裁定记录。定位 = (location
    digest, message_uid)；指纹 = 过滤后完整候选组重算（内容基；候选集
    合任何变化 → 旧裁定失效 fail-loud）；同组多条追加式记录中追加顺序
    最后一条 = 生效裁定（较早记录 = 被取代历史，绝不覆盖较新有效裁定；
    ts 从不作为选择依据）。结论 A 按明确选定的 content SHA-256 定位导
    入候选——同哈希多行 = 同一内容，rowid 仅作同内容内代表定位，绝不
    构成权威择优。结论 B / 结论 C / 无裁定 / 指纹失效 / 裁定日志损坏 /
    未配置裁定日志 → 整批 fail-loud，先于任何候选建立 / 导入通道 / 日
    志写入（零部分副作用）。裁定日志对 adapter 层只读（append_adjudic
    ation 不入棘轮白名单）——机器永不写裁定。"""

    def _state_db_full(
        self, rows: list[tuple[int, str, str, int, str | None, str | None]]
    ) -> Path:
        """真实宿主状态库 fixture（rows = (id, session_id, content,
        _compressed_summary, message_uid, absorbed_message_uids)）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "state.db"
        conn = sqlite3.connect(path)
        try:
            conn.execute(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
                "_compressed_summary INTEGER NOT NULL DEFAULT 0, message_uid TEXT, "
                "absorbed_message_uids TEXT)"
            )
            conn.executemany(
                "INSERT INTO messages (id, session_id, content, "
                "_compressed_summary, message_uid, absorbed_message_uids) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        finally:
            conn.close()
        return path

    def _adapter(
        self,
        log: Path,
        channel,
        adjudication_log: Path | None = None,
        **locations,
    ) -> HermesHostAdapter:
        return HermesHostAdapter(
            state_db=locations.get("state_db"),
            hermes_home=locations.get("hermes_home"),
            import_log=log,
            adjudication_log=adjudication_log,
            import_channel=channel,
            candidate=ExperienceCandidate,
            origin=MemoryOrigin,
        )

    def _channel(self, calls: list):
        def channel(candidates):
            calls.append(tuple(candidates))
            return tuple(f"ref:{c.idempotency_key}" for c in candidates)

        return channel

    def _log_path(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name) / "imported.log"

    def _adjudication_path(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name) / "host" / "adjudications.jsonl"

    @staticmethod
    def _v4(db: Path, message_uid: str) -> str:
        digest = hashlib.sha256(db.resolve().as_posix().encode("utf-8")).hexdigest()
        return f"v4:{digest}:{message_uid}"

    @staticmethod
    def _record(
        rowid: int, session_id: str, content: str, message_uid: str
    ) -> HostSessionRecord:
        """指纹计算用合成候选（与载体读出的成员在指纹组成字段上全等：
        rowid / content / session_id / message_uid）。"""
        return HostSessionRecord(
            content=content,
            session_id=session_id,
            message_uid=message_uid,
            rowid=rowid,
            record_key=f"v4:digest:{message_uid}",
            legacy_record_keys=(
                f"v3:digest:{session_id}:{message_uid}",
                f"v2:digest:{session_id}:{rowid}",
                f"{session_id}:{rowid}",
            ),
        )

    def _payload(
        self,
        db: Path,
        members: list[HostSessionRecord],
        conclusion: str = "A",
        selected: str | None = None,
        ts: str = "2026-10-12T12:00:00",
        location_digest_value: str | None = None,
    ) -> dict:
        """合法裁定记录 payload（自一致性由载体校验保证：声明指纹 =
        candidates 重算指纹；candidates 与 members 组成字段全等）。"""
        payload = {
            "ts": ts,
            "location_digest": (
                location_digest_value
                if location_digest_value is not None
                else location_digest(db.resolve().as_posix())
            ),
            "message_uid": members[0].message_uid,
            "candidate_set_fingerprint": candidate_set_fingerprint(members),
            "candidates": [
                {
                    "rowid": member.rowid,
                    "session_id": member.session_id,
                    "content_sha256": content_sha256(member.content),
                    "content_len": len(member.content),
                }
                for member in members
            ],
            "conclusion": conclusion,
            "reason": "fixture 人工裁定理由（D-058 咨询面测试）",
            "evidence_refs": [
                "docs/adr/0010-host-adapter-experience-candidate-supply-contract.md"
            ],
            "adjudicated_by": "public-test-reviewer",
        }
        if selected is not None:
            payload["selected_content_sha256"] = selected
        return payload

    def _write_lines(self, log: Path, payloads: list[dict]) -> None:
        import json as _json

        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "".join(_json.dumps(payload, ensure_ascii=False) + "\n" for payload in payloads),
            encoding="utf-8",
        )

    def test_host_adapter_source_never_writes_adjudications(self):
        """结构保证（棘轮白名单同源断言）：host adapter 层源码不含
        `append_adjudication`——机器永不写裁定，写入面与咨询面分离。"""
        source = (PKG / "hermes_host.py").read_text(encoding="utf-8")
        self.assertNotIn("append_adjudication", source)

    def test_adjudication_a_imports_selected_content_only(self):
        """结论 A（Decision 12）：指纹匹配的有效裁定 → 以明确选定的
        content SHA-256 定位导入候选——导入 = 选定版本（非最大 rowid
        版本）；单候选、单 v4 键；裁定日志只读不被触碰（append-only 历
        史不变）。"""
        db = self._state_db_full(
            [
                (1857, "s1", "完整原始经历内容", 0, "u-conflict", None),
                (1880, "s1", "降级 stub", 0, "u-conflict", None),
            ]
        )
        members = [
            self._record(1857, "s1", "完整原始经历内容", "u-conflict"),
            self._record(1880, "s1", "降级 stub", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj,
            [self._payload(db, members, "A", selected=content_sha256("完整原始经历内容"))],
        )
        adj_before = adj.read_text(encoding="utf-8")
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u-conflict')}",))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 1)
        self.assertEqual(calls[0][0].content, "完整原始经历内容")
        self.assertEqual(calls[0][0].idempotency_key, self._v4(db, "u-conflict"))
        self.assertEqual(log.read_text(encoding="utf-8").splitlines(), [self._v4(db, "u-conflict")])
        self.assertEqual(adj.read_text(encoding="utf-8"), adj_before)  # 只读：裁定日志未被触碰

    def test_adjudication_a_selection_follows_hash_not_rowid(self):
        """A 案选定依据 = 内容哈希，不是 rowid / 长度 / 位置：裁定选定
        较小 rowid 版本 → 导入该版本（机器不得凭 rowid 择优）。"""
        db = self._state_db_full(
            [
                (1857, "s1", "完整原始经历内容", 0, "u-conflict", None),
                (1880, "s1", "降级 stub", 0, "u-conflict", None),
            ]
        )
        members = [
            self._record(1857, "s1", "完整原始经历内容", "u-conflict"),
            self._record(1880, "s1", "降级 stub", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj,
            [self._payload(db, members, "A", selected=content_sha256("降级 stub"))],
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        adapter.import_session(adapter.open_session())
        self.assertEqual(calls[0][0].content, "降级 stub")

    def test_adjudication_b_fail_loud_v4_cannot_express(self):
        """结论 B（不同事件，当前 v4 身份契约无法表达）→ 立即整批
        fail-loud，要求进一步裁定；导入通道不触发、导入日志不落盘；
        消息含身份证据（uid / rowid / 长度），不含私人全文。"""
        db = self._state_db_full(
            [
                (1857, "s1", "完整原始经历内容", 0, "u-conflict", None),
                (1880, "s1", "降级 stub", 0, "u-conflict", None),
            ]
        )
        members = [
            self._record(1857, "s1", "完整原始经历内容", "u-conflict"),
            self._record(1880, "s1", "降级 stub", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(adj, [self._payload(db, members, "B")])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        message = str(ctx.exception)
        self.assertIn("结论 B", message)
        self.assertIn("v4 身份契约无法表达", message)
        self.assertIn("u-conflict", message)
        self.assertNotIn("完整原始经历内容", message)
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_adjudication_c_fail_loud_equals_unadjudicated(self):
        """结论 C（未知 / 证据不足）等同未裁定 → fail-loud，零副作用。"""
        db = self._state_db_full(
            [
                (1, "s1", "版本甲", 0, "u-conflict", None),
                (2, "s1", "版本乙", 0, "u-conflict", None),
            ]
        )
        members = [
            self._record(1, "s1", "版本甲", "u-conflict"),
            self._record(2, "s1", "版本乙", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(adj, [self._payload(db, members, "C")])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        self.assertIn("结论 C", str(ctx.exception))
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_no_matching_adjudication_fail_loud(self):
        """裁定日志存在但无匹配记录（裁定的是其他 message_uid）→ 该冲
        突组未裁定 → fail-loud，零副作用（不得默认放行）。"""
        db = self._state_db_full(
            [
                (1, "s1", "版本甲", 0, "u-conflict", None),
                (2, "s1", "版本乙", 0, "u-conflict", None),
            ]
        )
        other = [
            self._record(9, "s1", "无关消息", "u-other"),
        ]
        adj = self._adjudication_path()
        self._write_lines(adj, [self._payload(db, other, "C")])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        self.assertIn("无有效裁定记录", str(ctx.exception))
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_unconfigured_adjudication_log_fail_loud(self):
        """未配置裁定日志（显式 None = 最严格缺省）→ 冲突组永远
        fail-loud（人工裁定无从咨询；不得凭 active / compacted / rowid
        选择代表）。"""
        db = self._state_db_full(
            [
                (1, "s1", "版本甲", 0, "u-conflict", None),
                (2, "s1", "版本乙", 0, "u-conflict", None),
            ]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)  # adjudication_log=None
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        self.assertIn("未配置裁定日志", str(ctx.exception))
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_candidate_set_change_invalidates_adjudication_fail_loud(self):
        """候选集合变化 → 旧裁定失效（裁定针对 {1857,1880} 两组，库中
        新增第三候选 1901 → 当前指纹不符 → fail-loud，须人工重新裁定
        后整批重跑；不得沿用旧裁定导入）。"""
        db = self._state_db_full(
            [
                (1857, "s1", "完整原始经历内容", 0, "u-conflict", None),
                (1880, "s1", "降级 stub", 0, "u-conflict", None),
                (1901, "s1", "新增第三版本", 0, "u-conflict", None),
            ]
        )
        stale_members = [
            self._record(1857, "s1", "完整原始经历内容", "u-conflict"),
            self._record(1880, "s1", "降级 stub", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj,
            [self._payload(db, stale_members, "A", selected=content_sha256("完整原始经历内容"))],
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        self.assertIn("指纹不符", str(ctx.exception))
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_append_order_last_adjudication_effective_ts_never_basis(self):
        """追加顺序最后一条 = 生效裁定：同组两条有效 A（先选甲、后选
        乙；后一条 ts 更早——ts 从不作为选择依据）→ 导入乙（较早记录 =
        被取代历史，绝不覆盖较新有效裁定）。"""
        db = self._state_db_full(
            [
                (1, "s1", "版本甲", 0, "u-conflict", None),
                (2, "s1", "版本乙", 0, "u-conflict", None),
            ]
        )
        members = [
            self._record(1, "s1", "版本甲", "u-conflict"),
            self._record(2, "s1", "版本乙", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj,
            [
                self._payload(db, members, "A", selected=content_sha256("版本甲"),
                              ts="2026-10-12T12:00:00"),
                self._payload(db, members, "A", selected=content_sha256("版本乙"),
                              ts="2020-01-01T00:00:00"),  # ts 更早，但追加在后 = 生效
            ],
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        adapter.import_session(adapter.open_session())
        self.assertEqual(calls[0][0].content, "版本乙")

    def test_append_order_later_b_supersedes_earlier_a_fail_loud(self):
        """追加顺序新旧裁定：先 A 后 B → 生效 = B → fail-loud（旧 A 不
        得覆盖较新裁定放行；零副作用）。"""
        db = self._state_db_full(
            [
                (1, "s1", "版本甲", 0, "u-conflict", None),
                (2, "s1", "版本乙", 0, "u-conflict", None),
            ]
        )
        members = [
            self._record(1, "s1", "版本甲", "u-conflict"),
            self._record(2, "s1", "版本乙", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj,
            [
                self._payload(db, members, "A", selected=content_sha256("版本甲")),
                self._payload(db, members, "B"),
            ],
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        self.assertIn("结论 B", str(ctx.exception))
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_append_order_later_a_supersedes_earlier_b(self):
        """追加顺序新旧裁定：先 B 后 A → 生效 = A → 导入选定版本（人工
        再裁定可推翻先前 B——Decision 12 追加式语义）。"""
        db = self._state_db_full(
            [
                (1, "s1", "版本甲", 0, "u-conflict", None),
                (2, "s1", "版本乙", 0, "u-conflict", None),
            ]
        )
        members = [
            self._record(1, "s1", "版本甲", "u-conflict"),
            self._record(2, "s1", "版本乙", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj,
            [
                self._payload(db, members, "B"),
                self._payload(db, members, "A", selected=content_sha256("版本甲")),
            ],
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        adapter.import_session(adapter.open_session())
        self.assertEqual(calls[0][0].content, "版本甲")

    def test_stale_invalid_record_cannot_override_newer_valid(self):
        """旧无效记录不得覆盖较新有效裁定：第一条指纹针对已变化候选集
        合（被匹配过滤排除，非损坏），第二条有效 A → 第二条生效 → 导
        入选定版本。"""
        db = self._state_db_full(
            [
                (1, "s1", "版本甲", 0, "u-conflict", None),
                (2, "s1", "版本乙", 0, "u-conflict", None),
            ]
        )
        stale_members = [
            self._record(1, "s1", "旧候选内容", "u-conflict"),
            self._record(2, "s1", "版本乙", "u-conflict"),
        ]
        current_members = [
            self._record(1, "s1", "版本甲", "u-conflict"),
            self._record(2, "s1", "版本乙", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj,
            [
                self._payload(db, stale_members, "A", selected=content_sha256("旧候选内容")),
                self._payload(db, current_members, "A", selected=content_sha256("版本乙")),
            ],
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        adapter.import_session(adapter.open_session())
        self.assertEqual(calls[0][0].content, "版本乙")

    def test_duplicate_content_hashes_single_candidate_rowid_not_authority(self):
        """同哈希多行不构成权威择优：组内两行内容全等（哈希相同）+ 一
        行不同 → 冲突组；A 选定该哈希 → 选定成员 = 同哈希两行，候选内
        容与 v4 键全等 → 单候选单日志行（rowid 仅作同内容内代表定位）。"""
        db = self._state_db_full(
            [
                (1, "s1", "同一版本", 0, "u1", None),
                (2, "s1", "同一版本", 0, "u1", None),
                (3, "s1", "另一版本", 0, "u1", None),
            ]
        )
        members = [
            self._record(1, "s1", "同一版本", "u1"),
            self._record(2, "s1", "同一版本", "u1"),
            self._record(3, "s1", "另一版本", "u1"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj, [self._payload(db, members, "A", selected=content_sha256("同一版本"))]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        refs = adapter.import_session(adapter.open_session())
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u1')}",))
        self.assertEqual(len(calls[0]), 1)
        self.assertEqual(calls[0][0].content, "同一版本")
        self.assertEqual(log.read_text(encoding="utf-8").splitlines(), [self._v4(db, "u1")])

    def test_cross_location_adjudication_not_applicable_fail_loud(self):
        """跨位置裁定不适用：裁定记录的 location_digest 属于另一导入源
        → 当前位置无匹配记录 → fail-loud（裁定不可跨位置挪用）。"""
        db = self._state_db_full(
            [
                (1, "s1", "版本甲", 0, "u-conflict", None),
                (2, "s1", "版本乙", 0, "u-conflict", None),
            ]
        )
        members = [
            self._record(1, "s1", "版本甲", "u-conflict"),
            self._record(2, "s1", "版本乙", "u-conflict"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj,
            [
                self._payload(
                    db,
                    members,
                    "A",
                    selected=content_sha256("版本甲"),
                    location_digest_value=location_digest("C:/other/host/state.db"),
                )
            ],
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        self.assertIn("无有效裁定记录", str(ctx.exception))
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_corrupt_adjudication_log_blocks_whole_batch_before_any_write(self):
        """裁定日志损坏（非法 JSON 行）→ 整批 fail-loud 先于任何候选
        建立 / 导入 / 日志写入：干净组也不被先导入（载体读校验严格，
        损坏记录不可表达）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        (home / "profiles" / "a").mkdir(parents=True)
        conn = sqlite3.connect(home / "profiles" / "a" / "state.db")
        conn.execute(
            "CREATE TABLE messages ("
            "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
            "_compressed_summary INTEGER NOT NULL DEFAULT 0, message_uid TEXT, "
            "absorbed_message_uids TEXT)"
        )
        conn.execute(
            "INSERT INTO messages (id, session_id, content, _compressed_summary, "
            "message_uid) VALUES (1, 's1', '干净经历', 0, 'u-clean')"
        )
        conn.commit()
        conn.close()
        (home / "profiles" / "b").mkdir(parents=True)
        conn = sqlite3.connect(home / "profiles" / "b" / "state.db")
        conn.execute(
            "CREATE TABLE messages ("
            "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
            "_compressed_summary INTEGER NOT NULL DEFAULT 0, message_uid TEXT, "
            "absorbed_message_uids TEXT)"
        )
        conn.executemany(
            "INSERT INTO messages (id, session_id, content, _compressed_summary, "
            "message_uid) VALUES (?, ?, ?, 0, ?)",
            [(1, "s1", "版本甲", "u-conflict"), (2, "s1", "版本乙", "u-conflict")],
        )
        conn.commit()
        conn.close()
        adj = self._adjudication_path()
        adj.parent.mkdir(parents=True, exist_ok=True)
        adj.write_text("这不是 JSON\n", encoding="utf-8")
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(
            log, self._channel(calls), adjudication_log=adj, hermes_home=home
        )
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        self.assertIn("不是合法 JSON", str(ctx.exception))
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_unadjudicated_group_blocks_adjudicated_group_whole_batch(self):
        """整批 precheck（先于任何 import_channel / append_imported）：
        同库两个冲突组，u-a 有有效 A、u-b 无裁定 → u-b fail-loud → 已
        裁定的 u-a 也不被部分导入（零候选、零通道、零日志）。"""
        db = self._state_db_full(
            [
                (1, "s1", "甲原始", 0, "u-a", None),
                (2, "s1", "甲冲突", 0, "u-a", None),
                (3, "s1", "乙原始", 0, "u-b", None),
                (4, "s1", "乙冲突", 0, "u-b", None),
            ]
        )
        members_a = [
            self._record(1, "s1", "甲原始", "u-a"),
            self._record(2, "s1", "甲冲突", "u-a"),
        ]
        adj = self._adjudication_path()
        self._write_lines(
            adj, [self._payload(db, members_a, "A", selected=content_sha256("甲原始"))]
        )
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), adjudication_log=adj, state_db=db)
        with self.assertRaises(ValueError) as ctx:
            adapter.import_session(adapter.open_session())
        self.assertIn("u-b", str(ctx.exception))
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_session_id_change_legacy_keys_non_reproducible_one_time_duplication(self):
        """一次性重复行为显式测试（D-058 实施票 D-fixture 判据 4；ADR
        0010 修订 Decision 13 一次性重复风险）：session_id 已变（历史
        日志键按旧 session s0 落盘，当前行为 s1）→ v3 / v2 / 裸旧键不
        可重现 → 组不被识别为已导入 → 产生一次性重复导入（新 v4 键追
        加，旧键 append-only 保留）；此后 v4 键识别 → 零新增。真实
        22 键场景证据另行报告，不在此混同。"""
        db = self._state_db_full([(1, "s1", "经历内容", 0, "u1", None)])
        log = self._log_path()
        legacy_lines = [
            f"v3:{location_digest(db.resolve().as_posix())}:s0:u1",
            f"v2:{location_digest(db.resolve().as_posix())}:s0:1",
            "s0:1",
        ]
        log.write_text("".join(line + "\n" for line in legacy_lines), encoding="utf-8")
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        refs = adapter.import_session(adapter.open_session())
        # 旧键不可重现 → 一次性重复导入发生（如实记录，不阻止）
        self.assertEqual(refs, (f"ref:{self._v4(db, 'u1')}",))
        self.assertEqual(len(calls), 1)
        lines = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[:3], legacy_lines)  # append-only：旧键保留
        self.assertEqual(lines[3], self._v4(db, "u1"))  # 新 v4 键追加
        # 此后 v4 键识别 → 零新增
        self.assertEqual(adapter.import_session(adapter.open_session()), ())
        self.assertEqual(len(calls), 1)


class S4SyncTest(unittest.TestCase):
    """S4（spec-adapters.md §1 sync / ADR 0002 决定 5：移除非改名）：
    sync = V0 同步形态收敛位——重新解析状态位置（open_session 钉定后
    宿主布局可能变化：新增 profile 状态库等）+ 重导入新增内容（与
    import_session 共享宿主侧导入日志 = 同一幂等状态，§2.3）→
    SyncReport。"""

    def _state_db_into(self, path: Path, rows: list[tuple[str, str, str | None]]) -> Path:
        conn = sqlite3.connect(path)
        try:
            conn.execute(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
                "_compressed_summary INTEGER NOT NULL DEFAULT 0, message_uid TEXT, "
                "absorbed_message_uids TEXT)"
            )
            conn.executemany(
                "INSERT INTO messages (session_id, content, message_uid) "
                "VALUES (?, ?, ?)",
                rows,
            )
            conn.commit()
        finally:
            conn.close()
        return path

    def _state_db(self, rows: list[tuple[str, str, str | None]]) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return self._state_db_into(Path(tmp.name) / "state.db", rows)

    def _adapter(
        self, log: Path, channel, **locations
    ) -> HermesHostAdapter:
        return HermesHostAdapter(
            state_db=locations.get("state_db"),
            hermes_home=locations.get("hermes_home"),
            import_log=log,
            adjudication_log=None,
            import_channel=channel,
            candidate=ExperienceCandidate,
            origin=MemoryOrigin,
        )

    def _channel(self, calls: list):
        def channel(candidates):
            calls.append(tuple(candidates))
            return tuple(f"ref:{c.idempotency_key}" for c in candidates)

        return channel

    def _log_path(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name) / "imported.log"

    @staticmethod
    def _v4(db: Path, message_uid: str) -> str:
        """期望 v4 幂等键（D-056 跨 rotation 去重）：
        `v4:<location digest>:<message_uid>`——digest 由测试侧对 fixture
        路径独立施加 spec 算法（SHA-256 over `resolve().as_posix()`，
        64 hex 全量）得出，不手抄 hex。"""
        digest = hashlib.sha256(db.resolve().as_posix().encode("utf-8")).hexdigest()
        return f"v4:{digest}:{message_uid}"

    def test_sync_re_resolves_new_layout_after_open(self):
        """重解析收敛位（M-03 三位置 fallback 形态 → sync 职责）：
        open_session 后宿主新增 profile 状态库 → sync 重新解析出的位置
        含新位置，且新位置内容被导入（句柄 frozen 钉定不含新位置）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        self._state_db_into(home / "state.db", [("s-root", "root-row", "u-root")])
        log = self._log_path()
        adapter = self._adapter(log, self._channel([]), hermes_home=home)
        handle = adapter.open_session()
        self.assertEqual(len(handle.state_locations), 1)
        # open 后宿主新建 profile
        beta = home / "profiles" / "beta"
        beta.mkdir(parents=True)
        self._state_db_into(beta / "state.db", [("s-beta", "profile-row", "u-beta")])
        report = adapter.sync()
        expected = tuple(
            sorted(
                {
                    (home / "state.db").resolve(),
                    (beta / "state.db").resolve(),
                },
                key=lambda p: str(p).lower(),
            )
        )
        self.assertEqual(report.state_locations, expected)
        # 排序：profiles/… 路径先于根 state.db（'p' < 's'）
        self.assertEqual(
            report.new_references,
            (
                f"ref:{self._v4(beta / 'state.db', 'u-beta')}",
                f"ref:{self._v4(home / 'state.db', 'u-root')}",
            ),
        )
        self.assertIsNone(report.error)

    def test_sync_idempotent_zero_new(self):
        """AC 3 延伸到 sync：同一 sync 连续两次 → 第二次零新引用、导入
        通道不再触发（宿主侧导入日志 = 去重状态）。"""
        db = self._state_db([("s1", "first", "u1")])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        self.assertEqual(
            adapter.sync().new_references, (f"ref:{self._v4(db, 'u1')}",)
        )
        self.assertEqual(adapter.sync().new_references, ())
        self.assertEqual(len(calls), 1)

    def test_sync_shares_idempotency_with_import_session(self):
        """import_session 与 sync 共享同一幂等状态（宿主侧导入日志，
        §2.3）：import_session 导入后，sync 无新增。"""
        db = self._state_db([("s1", "first", "u1")])
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        self.assertEqual(
            adapter.import_session(adapter.open_session()),
            (f"ref:{self._v4(db, 'u1')}",),
        )
        report = adapter.sync()
        self.assertEqual(report.new_references, ())
        self.assertEqual(len(calls), 1)

    def test_sync_report_is_frozen_result(self):
        """SyncReport = frozen 结果面：state_locations = 本次重新解析
        后的位置（非句柄钉定位置）；error = 降级说明（降级面，INV-1
        纪律）——当前无可表达降级形态（缺失 = 初始态不降级；损坏 =
        fail-loud 非降级），恒 None（票 Comments 记录）。"""
        db = self._state_db([("s1", "first", "u1")])
        log = self._log_path()
        adapter = self._adapter(log, self._channel([]), state_db=db)
        report = adapter.sync()
        self.assertTrue(is_dataclass(SyncReport))
        self.assertTrue(SyncReport.__dataclass_params__.frozen)
        self.assertEqual(report.state_locations, (db.resolve(),))
        self.assertIsNone(report.error)
        with self.assertRaises(FrozenInstanceError):
            report.error = "x"

    def test_sync_missing_state_db_is_initial_state(self):
        """宿主未运行（初始态）：显式位置指向不存在的库 → sync 不
        fail-loud、无新增、不触碰载体（日志不创建）；报告位置仍为
        解析出的声明位（显式模式无存在性检查，S2 契约）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "state.db"  # 不存在
        log = self._log_path()
        calls: list = []
        adapter = self._adapter(log, self._channel(calls), state_db=db)
        report = adapter.sync()
        self.assertEqual(report.state_locations, (db.resolve(),))
        self.assertEqual(report.new_references, ())
        self.assertIsNone(report.error)
        self.assertEqual(calls, [])
        self.assertFalse(log.exists())

    def test_sync_corrupt_state_db_fail_loud(self):
        """损坏状态库 = fail-loud——不经 error 字段吞入降级面（降级面
        不覆盖损坏：损坏 = 硬错误，同 import_session 纪律）。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "state.db"
        db.write_text("not a sqlite database")
        adapter = self._adapter(
            self._log_path(), self._channel([]), state_db=db
        )
        with self.assertRaises(sqlite3.DatabaseError):
            adapter.sync()


if __name__ == "__main__":
    unittest.main()
