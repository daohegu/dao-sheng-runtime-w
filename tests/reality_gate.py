"""V1 Reality Gate —— STEP 15 Real Verification 执行器（真实运行验证）。

证据类别定位：本模块产出的证据 = Real Runtime Verification——真实磁盘
（repo 外持久 workspace）+ 真实进程边界（每个 phase = 独立 python 进程，
subprocess 启动）+ 真实 Model wire（Ollama 真实端点，两个不同真实模型）。
与既有证据类别的区分：
- Unit Test = 既有单测套件；
- Integration Test = 进程内装配组件测试（既有）；
- System Test = M12 永久演练模块 tests/test_acceptance_m12.py（进程内 +
  真实载体 + 真实 Provider，降级形态 = U-5 已定推论）；
- Real Runtime Verification = 本模块（真实 wire + 跨进程 + 真实持久位）。

本文件不匹配 unittest 默认发现模式（test*.py），不进入默认套件——执行
依赖真实 Ollama 端点与 repo 外 workspace；workspace 必须由使用者显式
提供（--workspace 参数或环境变量 DAO_SHENG_REALITY_GATE_WORKSPACE）——
无默认目录，缺失即 fail-loud，不会回退到任何既有实例：
    python tests/reality_gate.py --workspace <dir>              # 全量编排（P0→P9）
    python tests/reality_gate.py --workspace <dir> --phase p1   # 单 phase（子进程入口）

纪律：
- 唯一构造位 = composition.compose（R-09）；dao_sheng/ 业务代码零改动。
- P0 中 runner 扮演"设计层初始化"（data-ownership：Identity / Faculties
  载体仅设计层可写）——fixture 值 = 演练值，非生产设计值（报告中声明）。
- 宿主 state.db 由 P0 按宿主载体通道读取面建表（messages：session_id /
  content 列 + rowid 行身份——schema 知识归 host adapter 层，M09）。
- 每个 phase 结束显式 memory.close()（WAL 落盘；Windows 文件锁纪律）。
- 断言失败 → 该 phase 非零退出 → 编排器如实记录，不静默跳过。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dao_sheng import composition  # noqa: E402
from dao_sheng.continuity import load_continuity  # noqa: E402
from dao_sheng.faculties import FACULTY_ROOTS  # noqa: E402
from dao_sheng.individual import Turn  # noqa: E402
from dao_sheng.layout import IndividualFiles  # noqa: E402
from dao_sheng.memory import MemoryOrigin, RecallQuery  # noqa: E402

# -- 部署值（验证演练值；U-5 部署形态 UNKNOWN 不变——此处值只属于本次演练） --
# workspace 无默认值：必须由 --workspace 参数或环境变量显式提供（见 main()
# 解析）——不预设任何个人目录，缺失即 fail-loud，绝不回退到仓库内正式实例。
WORKSPACE_ENV = "DAO_SHENG_REALITY_GATE_WORKSPACE"
OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
# 模型对（时延探针实测，/api/chat 与 OllamaModel（Ollama adapter）完全相同 wire 形态）：
MODEL_A = "qwen3-coder:30b"    # 基线认知手段（实测 15.7s/call，MoE 3.3B active，默认非思考）
MODEL_B = "gpt-oss:20b"        # 更换后的认知手段（实测 41.3s/call，MoE 5.1B active——
# 与 A 不同家族（Qwen3-Coder vs OpenAI gpt-oss）、不同架构、行为形态不同；
# 原选 qwen3.6:27b（干净实测 611s/call）在负载下单调用超出实用 phase
# 预算，演练改选另一 MoE；公开使用者应按本机 Model 库存自行调整——详见
# 报告执行记录）
DEAD_ENDPOINT = "http://127.0.0.1:9"  # discard 端口：真实连接失败
TIMEOUT_SECONDS = 900.0        # 部署值：覆盖 B 实测单次调用（41.3s）+ 负载波动裕量
RETRY_LIMIT = 3
PHASE_TIMEOUT = 7200  # 单 phase 子进程超时（秒）：覆盖重试耗尽最坏形态（2 回合 × 3 次 × 900s）

PRINCIPLES = REPO_ROOT / "docs" / "constitution" / "principles.md"

# -- 回合内容（演练文本） --
TURNS_P1 = (
    "今日观察：重建工程的验收证据必须来自实际执行。",
    "今日观察：个体状态只由五项持久文件构成。",
    "今日观察：手段可换，个体不可换。",
)
HOST_SEED = (
    ("s1", "宿主侧回流记录一：一次外部会话经历。"),
    ("s1", "宿主侧回流记录二：又一次外部会话经历。"),
    ("s2", "[dao-sheng:projection] 投影内容不得回流为经历"),
    ("s2", "   "),
)
TURNS_P2 = (
    "更换认知手段后的第一回合：世界未变，手段已变。",
    "更换认知手段后的第二回合：继续观察。",
)
TURN_P4A = "手段故障演练回合：认知手段端点不可达。"
TURN_CRASH = "崩溃演练回合：进行中被终止。"
TURN_RECOVER = "崩溃恢复后回合：个体仍在。"
TURNS_P5 = (
    "外部世界变化一：一个新的问题出现——如何验证验证本身。",
    "外部世界变化二：验证证据需要跨进程稳定。",
)
TURNS_P7 = (
    "能力断开演练回合一：核心环路不受影响。",
    "能力断开演练回合二：核心环路不受影响。",
)


# ---------------------------------------------------------------- 公共工具

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(f"断言失败：{msg}")


@dataclass(frozen=True)
class MemorySnapshot:
    reference: str
    content: str
    origin: str
    status: str
    confidence: str


def snap(memory, reference: str) -> MemorySnapshot:
    m = memory.get(reference)
    return MemorySnapshot(
        reference=m.reference,
        content=m.content,
        origin=m.memory_origin.value,
        status=m.memory_status.value,
        confidence=m.memory_confidence.value,
    )


def snap_all(memory) -> list[MemorySnapshot]:
    return [
        MemorySnapshot(
            m.reference,
            m.content,
            m.memory_origin.value,
            m.memory_status.value,
            m.memory_confidence.value,
        )
        for m in memory.recall(RecallQuery())
    ]


def continuity_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def files_tree_hash(root: Path) -> dict[str, str]:
    """目录树文件哈希（相对路径 → sha256；缺失 = 空 dict）。"""
    if not root.is_dir():
        return {}
    return {
        str(p.relative_to(root)).replace("\\", "/"): sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def compose_ws(ws: Path, endpoint: str, model: str, *,
               timeout: float = TIMEOUT_SECONDS,
               retry: int = RETRY_LIMIT, host: bool = True):
    """真实装配（唯一构造位 composition.compose，R-09）。"""
    mc = composition.ModelConfig(
        agent_backend="ollama",
        agent_endpoint=endpoint,
        agent_model=model,
        reflection_backend="ollama",
        reflection_endpoint=endpoint,
        reflection_model=model,
        timeout_seconds=timeout,
        retry_limit=retry,
    )
    hc = composition.HostConfig(
        state_db=ws / "host" / "state.db" if host else None,
        import_log=ws / "host" / "imported.log" if host else None,
    )
    return composition.compose(
        principles_source_path=PRINCIPLES,
        individual_root=ws / "individual",
        model_config=mc,
        operational_defaults=composition.OperationalDefaults(),
        host_config=hc,
    )


def read_evidence(ws: Path, name: str) -> dict:
    return json.loads(
        (ws / "evidence" / f"{name}.json").read_text(encoding="utf-8")
    )


def write_evidence(ws: Path, name: str, evidence: dict) -> None:
    (ws / "evidence").mkdir(parents=True, exist_ok=True)
    (ws / "evidence" / f"{name}.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[{name}] evidence 已落盘", flush=True)


def do_turns(individual, contents: tuple[str, ...]) -> list[dict]:
    """逐个完整回合（act → persist，两阶段纪律），返回逐回合证据。"""
    out = []
    for content in contents:
        print(f"[turn] act 开始：{content[:24]}…", flush=True)
        t0 = time.monotonic()
        outcome = individual.act(Turn(content, MemoryOrigin.CANONICAL))
        print(f"[turn] act 完成（{time.monotonic() - t0:.1f}s），persist…", flush=True)
        ref = individual.persist()
        out.append(
            {
                "content": content,
                "turn_number": outcome.turn_number,
                "action": outcome.action,
                "reference": ref,
            }
        )
    return out


def projection_inputs(ws: Path, a) -> dict:
    """经公共表面重建投影输入（证据用：理解环节的输入面）。"""
    files = a.individual_files
    identity = a.identity
    return {
        "identity": {
            "name": identity.name,
            "self_appellation": identity.self_appellation,
            "voice": identity.voice,
            "visual_image": identity.visual_image,
            "behavioral_habits": list(identity.behavioral_habits),
            "past_experiences": list(identity.past_experiences),
            "continuous_memory": list(identity.continuous_memory),
        },
        "doctrine": [
            {"name": p.name, "text": p.text} for p in a.doctrine.principles
        ],
        "faculties": list(a.faculties.roots),
        "continuity_records": [dict(r) for r in load_continuity(files.continuity).records],
        "memory_contents": [m.content for m in a.memory.recall(RecallQuery())],
    }


# ---------------------------------------------------------------- P0 设计层

def phase_p0(ws: Path) -> dict:
    """设计层初始化（runner 扮演设计层）：identity / faculties 载体 +
    宿主 state.db 播种（2 有效 + 1 投影标记行 + 1 空白行——回流过滤
    面真实覆盖）。"""
    import sqlite3

    ind = ws / "individual"
    ind.mkdir(parents=True, exist_ok=True)
    host = ws / "host"
    host.mkdir(parents=True, exist_ok=True)

    identity_doc = {
        "name": "DaoSheng",
        "self_appellation": "我",
        "voice": "平静、克制",
        "visual_image": "无固定形象",
        "behavioral_habits": ["先观察，后行动"],
        "past_experiences": ["V1 重建：M01–M12 全部 resolved"],
        "continuous_memory": ["以不变应万变"],
    }
    (ind / "identity.json").write_text(
        json.dumps(identity_doc, ensure_ascii=False), encoding="utf-8"
    )
    (ind / "faculties.json").write_text(
        json.dumps(list(FACULTY_ROOTS), ensure_ascii=False), encoding="utf-8"
    )

    db = host / "state.db"
    if db.is_file():
        check(False, f"state.db 已存在（P0 幂等性破坏）：{db}")
    conn = sqlite3.connect(db)
    try:
        # 必需列读取面（host_carrier D1 裁定 1）：缺 _compressed_summary /
        # message_uid 列 = fail-loud，fixture 必须构造完整读取面；
        # message_uid = 确定性 uid-N，全部标记 = 0 非派生摘要。
        conn.execute(
            "CREATE TABLE messages ("
            "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
            "_compressed_summary INTEGER NOT NULL DEFAULT 0, message_uid TEXT)"
        )
        conn.executemany(
            "INSERT INTO messages (session_id, content, message_uid) "
            "VALUES (?, ?, ?)",
            [
                (session_id, content, f"uid-{index}")
                for index, (session_id, content) in enumerate(HOST_SEED, start=1)
            ],
        )
        conn.commit()
    finally:
        conn.close()

    manifest = {
        "workspace": str(ws),
        "identity_sha256": sha256(ind / "identity.json"),
        "faculties_sha256": sha256(ind / "faculties.json"),
        "identity_doc": identity_doc,
        "host_seed": [list(r) for r in HOST_SEED],
        "expected_imports": 2,  # 标记行 + 空白行须被源头过滤
        "models": {"A": MODEL_A, "B": MODEL_B},
        "endpoint": OLLAMA_ENDPOINT,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    write_evidence(ws, "P0", manifest)
    return manifest


# ---------------------------------------------------------------- P1 基线

def phase_p1(ws: Path) -> dict:
    """基线（Model A，真实 wire）：host 回流导入 + 3 真实回合 +
    digest/extract/reflect 全真实反思（continuity 首次有内容）。"""
    a = compose_ws(ws, OLLAMA_ENDPOINT, MODEL_A)
    try:
        session = a.host.open_session()
        import_refs = a.host.import_session(session)
        check(len(import_refs) == 2,
              f"回流导入应恰 2 条（标记/空白行被过滤），实际 {len(import_refs)}")

        turns = do_turns(a.individual, TURNS_P1)
        for t in turns:
            check(t["action"] is not None and t["action"].strip(),
                  f"真实 wire 回合作用不应为空：{t['content']}")

        r1 = turns[0]["reference"]
        derived_ref = a.growth.digest(r1)
        insight_ref = a.growth.extract(r1)
        reflection_ref = a.growth.reflect(r1)
        for name, ref in (("digest", derived_ref), ("extract", insight_ref),
                          ("reflect", reflection_ref)):
            check(ref is not None, f"真实反思 {name} 未产出（手段故障？）")

        ev = {
            "model": MODEL_A,
            "import_refs": list(import_refs),
            "turns": turns,
            "growth": {"digest": derived_ref, "extract": insight_ref,
                       "reflect": reflection_ref},
            "identity_sha256": sha256(a.individual_files.identity),
            "faculties_sha256": sha256(a.individual_files.faculties),
            "continuity_text": continuity_text(a.individual_files.continuity),
            "memory": [s.__dict__ for s in snap_all(a.memory)],
            "projection_inputs": projection_inputs(ws, a),
        }
    finally:
        a.memory.close()
    write_evidence(ws, "P1", ev)
    return ev


# ---------------------------------------------------------------- P2 更换 Model

def phase_p2(ws: Path) -> dict:
    """重点验证 ①：进程重启 + Model A→B——identity 字节不变、
    continuity 字节前缀（append-only）、全部旧记录 get() 逐字一致、
    新手段上回合照常。"""
    p1 = read_evidence(ws, "P1")
    files = IndividualFiles.layout(ws / "individual")
    check(sha256(files.identity) == p1["identity_sha256"],
          "identity 载体字节在 Model 更换后必须不变")
    check(sha256(files.faculties) == p1["faculties_sha256"],
          "faculties 载体字节必须不变")
    cont = continuity_text(files.continuity)
    check(cont.startswith(p1["continuity_text"]),
          "continuity 必须字节前缀保持（append-only，无重写）")

    a = compose_ws(ws, OLLAMA_ENDPOINT, MODEL_B)
    try:
        for s in p1["memory"]:
            got = a.memory.get(s["reference"])
            check(
                got.content == s["content"]
                and got.memory_origin.value == s["origin"]
                and got.memory_status.value == s["status"]
                and got.memory_confidence.value == s["confidence"],
                f"旧记忆记录跨 Model 更换后必须逐字一致：{s['reference']}",
            )
        turns = do_turns(a.individual, TURNS_P2)
        for t in turns:
            check(t["action"] is not None and t["action"].strip(),
                  f"新手段（{MODEL_B}）回合作用不应为空：{t['content']}")
        ev = {
            "model": MODEL_B,
            "identity_sha256": sha256(files.identity),
            "continuity_text": continuity_text(files.continuity),
            "turns": turns,
            "old_refs_verified": len(p1["memory"]),
            "memory": [s.__dict__ for s in snap_all(a.memory)],
            "projection_inputs": projection_inputs(ws, a),
        }
    finally:
        a.memory.close()
    write_evidence(ws, "P2", ev)
    return ev


# ---------------------------------------------------------------- P3 Hermes 重启

def phase_p3(ws: Path) -> dict:
    """重点验证 ②：Hermes 重启（新进程重开宿主会话）——重导入零新增
    （宿主侧跨进程幂等，import_log 持久）；sync 零新增；continuity
    不变（宿主重启对个体是 no-op）。"""
    p2 = read_evidence(ws, "P2")
    files = IndividualFiles.layout(ws / "individual")
    check(continuity_text(files.continuity) == p2["continuity_text"],
          "宿主重启前 continuity 不得有变")

    a = compose_ws(ws, OLLAMA_ENDPOINT, MODEL_A)
    try:
        log_before = (ws / "host" / "imported.log").read_text(encoding="utf-8")
        reimport_refs = a.host.import_session(a.host.open_session())
        sync = a.host.sync()
        check(reimport_refs == (), "跨进程重导入必须零新增（宿主侧幂等）")
        check(sync.new_references == (), "sync 必须零新增")
        check(
            (ws / "host" / "imported.log").read_text(encoding="utf-8")
            == log_before,
            "重导入零新增时导入日志不得被触碰",
        )
        cont = continuity_text(files.continuity)
        check(cont == p2["continuity_text"],
              "宿主重启对个体 continuity 必须是 no-op")
        for s in p2["memory"]:
            got = a.memory.get(s["reference"])
            check(got.content == s["content"],
                  f"宿主重启后旧记录必须可读且一致：{s['reference']}")
        ev = {
            "model": MODEL_A,
            "reimport_refs": list(reimport_refs),
            "sync": {"state_locations": [str(p) for p in sync.state_locations],
                     "new_references": list(sync.new_references),
                     "error": sync.error},
            "import_log_keys": [l for l in log_before.splitlines() if l.strip()],
            "identity_sha256": sha256(files.identity),
            "continuity_text": cont,
            "old_refs_verified": len(p2["memory"]),
        }
    finally:
        a.memory.close()
    write_evidence(ws, "P3", ev)
    return ev


# ---------------------------------------------------------------- P4 故障恢复

def phase_p4a(ws: Path) -> dict:
    """Failure Recovery (a)：真实连接失败（死端点，重试耗尽）→
    降级回合——行动 None、经历仍记录、不抛异常（INV-1：手段故障 ≠
    个体故障）。"""
    a = compose_ws(ws, DEAD_ENDPOINT, "none", timeout=2.0, retry=2, host=False)
    try:
        outcome = a.individual.act(Turn(TURN_P4A, MemoryOrigin.CANONICAL))
        ref = a.individual.persist()
        check(outcome.action is None, "手段不可达时行动必须为 None（降级回合）")
        m = a.memory.get(ref)
        check(m.content.endswith("行动：无"), f"降级回合记录形态不符：{m.content!r}")
        ev = {
            "endpoint": DEAD_ENDPOINT,
            "turn": {"content": TURN_P4A, "action": None, "reference": ref},
            "record": snap(a.memory, ref).__dict__,
            "identity_sha256": sha256(a.individual_files.identity),
            "continuity_text": continuity_text(a.individual_files.continuity),
        }
    finally:
        a.memory.close()
    write_evidence(ws, "P4a", ev)
    return ev


def phase_p4_crash(ws: Path) -> None:
    """崩溃子进程：act 之后、persist 之前进程消失（os._exit = 崩溃，
    无清理）。进行中回合不入库（回合原子性，真实进程边界）。"""
    a = compose_ws(ws, OLLAMA_ENDPOINT, MODEL_A)
    try:
        a.individual.act(Turn(TURN_CRASH, MemoryOrigin.CANONICAL))
    finally:
        # 不 persist、不 close——进程即死
        os._exit(1)


def phase_p4_post(ws: Path) -> dict:
    """Failure Recovery (b) 后验：崩溃代价 = 进行中该一回合——持久状态
    5 项完整、崩溃回合内容不入库、新进程无进行中回合（persist
    fail-loud）、恢复后新回合正常。"""
    p3 = read_evidence(ws, "P3")
    p2 = read_evidence(ws, "P2")
    p1 = read_evidence(ws, "P1")
    files = IndividualFiles.layout(ws / "individual")
    a = compose_ws(ws, OLLAMA_ENDPOINT, MODEL_A)
    try:
        try:
            a.individual.persist()
            check(False, "新进程无进行中回合，persist 必须 fail-loud")
        except ValueError:
            pass
        contents = [m.content for m in a.memory.recall(RecallQuery())]
        check(not any(TURN_CRASH in c for c in contents),
              "进行中崩溃回合不得入库")
        all_refs = [s["reference"] for s in p1["memory"] + p2["memory"]]
        for ref in all_refs:
            a.memory.get(ref)  # 缺失 → ValueError
        check(sha256(files.identity) == p1["identity_sha256"],
              "崩溃后 identity 载体必须不变")
        check(continuity_text(files.continuity) == p3["continuity_text"],
              "崩溃后 continuity 必须不变（崩溃回合未达任何持久面）")
        turns = do_turns(a.individual, (TURN_RECOVER,))
        check(turns[0]["turn_number"] == 1, "新进程 turn 计数从 1 起（C-2）")
        ev = {
            "model": MODEL_A,
            "crash_turn_absent": True,
            "persist_fail_loud": True,
            "refs_verified": len(all_refs),
            "recovery_turn": turns[0],
            "identity_sha256": sha256(files.identity),
            "continuity_text": continuity_text(files.continuity),
        }
    finally:
        a.memory.close()
    write_evidence(ws, "P4post", ev)
    return ev


# ---------------------------------------------------------------- P5 世界变化

def phase_p5(ws: Path) -> dict:
    """重点验证 ⑥：External World 变化（新经历内容）→ Growth 全管线
    按 Domain 工作——产出全部归位：阶段输出记忆（DERIVED / REPORTED /
    UNCERTAIN）、reflect → Memory + Continuity（恰 2 键 schema）、
    verify_insight → 修正形态（DERIVED / VERIFIED / CONFIRMED；INV-8
    原记录不变；显式引用链建立）。行为面 = 记录观察（真实模型非确定，
    INV-4 行为层判定不做语义猜测，规则 11）。"""
    p4 = read_evidence(ws, "P4post")
    files = IndividualFiles.layout(ws / "individual")
    check(continuity_text(files.continuity) == p4["continuity_text"],
          "P5 启动前 continuity 不得有变")

    a = compose_ws(ws, OLLAMA_ENDPOINT, MODEL_A)
    try:
        pre_actions = [t["action"] for t in do_turns(a.individual, TURNS_P5)]
        new_turn_ref = None
        for m in a.memory.recall(RecallQuery()):
            if m.content.startswith(f"经历：{TURNS_P5[0]}"):
                new_turn_ref = m.reference
        check(new_turn_ref is not None, "新回合记录未找到")
        digest_ref = a.growth.digest(new_turn_ref)
        insight_ref = a.growth.extract(new_turn_ref)
        reflection_ref = a.growth.reflect(new_turn_ref)
        verify_ref = a.growth.verify_insight(insight_ref)
        for name, ref in (("digest", digest_ref), ("extract", insight_ref),
                          ("reflect", reflection_ref), ("verify", verify_ref)):
            check(ref is not None, f"真实反思 {name} 未产出")

        d = snap(a.memory, digest_ref)
        e = snap(a.memory, insight_ref)
        r = snap(a.memory, reflection_ref)
        v = snap(a.memory, verify_ref)
        for name, s in (("digest", d), ("extract", e), ("reflect", r)):
            check((s.origin, s.status, s.confidence)
                  == ("derived", "reported", "uncertain"),
                  f"阶段输出三维归位错误（{name}）：{(s.origin, s.status, s.confidence)}")
        check((v.origin, v.status, v.confidence)
              == ("derived", "verified", "confirmed"),
              f"验证修正三维归位错误：{(v.origin, v.status, v.confidence)}")
        original = a.memory.get(insight_ref)
        check(original.content == e.content,
              "INV-8：被验证原记录 content 必须不变")
        chain = a.memory.resolve_reference(insight_ref)
        check(any(m.reference == verify_ref for m in chain),
              "verify_insight 必须建立显式引用链（原 ↔ 修正）")

        prev_count = len(p4["continuity_text"].splitlines())
        cont_records = [dict(x) for x in load_continuity(files.continuity).records]
        check(len(cont_records) == prev_count + 2,
              f"本轮 continuity 必须恰新增 2 条（reflect + verify），"
              f"实际 {len(cont_records) - prev_count}")
        reflect_record = cont_records[prev_count]
        verify_record = cont_records[prev_count + 1]
        check(set(reflect_record) == {"content", "reference"},
              f"continuity 记录须恰 2 键：{set(reflect_record)}")
        check(reflect_record["reference"] == reflection_ref,
              "reflect 的 continuity 记录须指向主体记忆记录")
        check(verify_record["reference"] == insight_ref,
              "verify 的 continuity 记录须指向被验证 insight")

        ev = {
            "model": MODEL_A,
            "world_change_turns": [
                {"content": TURNS_P5[0], "action": pre_actions[0]},
                {"content": TURNS_P5[1], "action": pre_actions[1]},
            ],
            "source_ref": new_turn_ref,
            "pipeline": {"digest": digest_ref, "extract": insight_ref,
                         "reflect": reflection_ref, "verify": verify_ref},
            "stage_outputs": {"digest": d.__dict__, "extract": e.__dict__,
                              "reflect": r.__dict__, "verify": v.__dict__},
            "inv8_original_unchanged": True,
            "reference_chain_built": True,
            "continuity_text": continuity_text(files.continuity),
            "memory": [s.__dict__ for s in snap_all(a.memory)],
            "projection_inputs_after": projection_inputs(ws, a),
        }
    finally:
        a.memory.close()
    write_evidence(ws, "P5", ev)
    return ev


# ---------------------------------------------------------------- P6 Provider 更换

def phase_p6(ws: Path) -> dict:
    """重点验证 ③：Memory Provider 更换（新进程 = 同载体目录新
    SqliteMemoryProvider 实例）→ DaoSheng Ontology 仍然成立：同一
    6 方法契约上，全部历次 phase 记录逐字可读、三维不变、修正显式
    引用链跨 Provider 实例可解析（Ontology 属个体不属 Provider，
    规则 5 / INV-3）。"""
    p5 = read_evidence(ws, "P5")
    p2 = read_evidence(ws, "P2")
    files = IndividualFiles.layout(ws / "individual")
    a = compose_ws(ws, OLLAMA_ENDPOINT, MODEL_A)
    try:
        all_snaps = {s["reference"]: s for s in p2["memory"] + p5["memory"]}
        for ref, s in all_snaps.items():
            got = a.memory.get(ref)
            check(
                got.content == s["content"]
                and got.memory_origin.value == s["origin"]
                and got.memory_status.value == s["status"]
                and got.memory_confidence.value == s["confidence"],
                f"Provider 更换后记录必须逐字一致：{ref}",
            )
        chain = a.memory.resolve_reference(p5["pipeline"]["extract"])
        check(
            any(m.reference == p5["pipeline"]["verify"] for m in chain),
            "修正引用链必须跨 Provider 实例可解析",
        )
        current = snap_all(a.memory)
        check(len(current) >= len(all_snaps),
              f"记录数不得减少：{len(current)} < {len(all_snaps)}")
        # Ontology 三维值域检查：全部记录三维值必须落在枚举值域内
        allowed = {
            "origin": {"canonical", "derived", "external", "echo"},
            "status": {"observed", "reported", "verified"},
            "confidence": {"confirmed", "supported", "uncertain"},
        }
        for s in current:  # MemorySnapshot 对象（属性访问，非 dict）
            check(s.origin in allowed["origin"], f"非法 origin：{s}")
            check(s.status in allowed["status"], f"非法 status：{s}")
            check(s.confidence in allowed["confidence"],
                  f"非法 confidence：{s}")
        ev = {
            "model": MODEL_A,
            "refs_verified": len(all_snaps),
            "total_records": len(current),
            "chain_across_provider": True,
            "ontology_value_domain_ok": True,
            "identity_sha256": sha256(files.identity),
            "continuity_text": continuity_text(files.continuity),
            "memory": [s.__dict__ for s in current],
        }
    finally:
        a.memory.close()
    write_evidence(ws, "P6", ev)
    return ev


# ---------------------------------------------------------------- P7 能力断开 + Worker

def phase_p7(ws: Path) -> dict:
    """重点验证 ⑤：Capability 断开后 Core 仍然成立——(a) 主根上回合
    环路运行时能力载体目录字节不变（环路不触碰能力子系统）；(b) 无
    capabilities/ 目录的最小根（初始态）照常装配且回合环路运转。
    重点验证 ④：Worker 消失后 Identity 仍然成立——全包零 worker 符号
    定义（M10 形态复验）、identity 载体恰 7 键且无 worker 字段、
    identity 哈希自 P0 至今不变。"""
    p0 = read_evidence(ws, "P0")
    ind = ws / "individual"
    files = IndividualFiles.layout(ind)

    a = compose_ws(ws, OLLAMA_ENDPOINT, MODEL_A)
    try:
        # 先建立真实能力（proposed 态，载体文件真实落盘）——随后回合
        # 环路运行时该目录必须字节不变（断开 = 环路不触碰能力子系统）
        source_ref = a.memory.recall(RecallQuery())[0].reference
        a.capability_manager.propose("真实演练能力", source_ref)
        check(
            (files.capabilities_dir / "proposed" / "真实演练能力.json").is_file(),
            "能力提案载体必须真实落盘（严格 3 键）",
        )
        caps_before = files_tree_hash(files.capabilities_dir)
        do_turns(a.individual, TURNS_P7)
    finally:
        a.memory.close()
    caps_after = files_tree_hash(files.capabilities_dir)
    check(bool(caps_before), "能力目录必须非空（真实能力已建立）")
    check(caps_before == caps_after,
          "回合环路运行时能力载体目录必须字节不变（断开 = 不触碰）")
    check(sha256(files.identity) == p0["identity_sha256"],
          "identity 哈希自 P0 至今必须不变")

    # (b) 最小根：无 capabilities/ 目录（初始态，无能力不代建）
    minimal = ws / "individual-minimal"
    if minimal.exists():
        check(False, "最小根已存在（重跑须先清理 workspace）")
    minimal.mkdir(parents=True)
    (minimal / "identity.json").write_text(
        (ind / "identity.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (minimal / "faculties.json").write_text(
        (ind / "faculties.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    check(not (minimal / "capabilities").is_dir(), "最小根不得有 capabilities/")
    a2 = composition.compose(
        principles_source_path=PRINCIPLES,
        individual_root=minimal,
        model_config=composition.ModelConfig(),  # 全未设定 = 不装配（U-5）
        operational_defaults=composition.OperationalDefaults(),
        host_config=composition.HostConfig(),
    )
    try:
        outcome = a2.individual.act(Turn("最小根降级回合：无手段无能力。",
                                         MemoryOrigin.CANONICAL))
        ref = a2.individual.persist()
        check(outcome.action is None, "无手段装配 → 降级回合（行动 None）")
        check(a2.memory.get(ref).content.endswith("行动：无"),
              "最小根回合记录形态不符")
        check(not (minimal / "capabilities").is_dir(),
              "初始态不得代建能力目录（ADR 0007 语义）")
        minimal_ok = {
            "assembled": True,
            "degraded_turn": {"action": None, "reference": ref},
            "capabilities_absent": True,
        }
    finally:
        a2.memory.close()

    # ④ Worker 形态扫描（M10 复验，真实执行非引用）
    worker_definitions = 0
    worker_token_files: dict[str, int] = {}
    pkg = REPO_ROOT / "dao_sheng"
    for path in sorted(pkg.rglob("*.py")):
        for line in path.read_text(encoding="utf-8").splitlines():
            low = line.lower()
            if re.search(r"^\s*(class|def)\s+\w*worker\w*", low):
                worker_definitions += 1
            if "worker" in low:
                worker_token_files[path.name] = worker_token_files.get(path.name, 0) + 1
    check(worker_definitions == 0,
          f"V1 不得出现 worker 符号定义，实际 {worker_definitions}")
    id_doc = json.loads(files.identity.read_text(encoding="utf-8"))
    check("worker" not in {k.lower() for k in id_doc},
          "identity 载体不得含 worker 字段")
    check(set(id_doc) == {
        "name", "self_appellation", "voice", "visual_image",
        "behavioral_habits", "past_experiences", "continuous_memory",
    }, "identity 载体必须恰 7 支撑项键")

    ev = {
        "model": MODEL_A,
        "capability_dir_unchanged": True,
        "capabilities_hash": caps_after,
        "minimal_root": minimal_ok,
        "worker": {
            "definitions_in_dao_sheng": worker_definitions,
            "token_files": worker_token_files,
            "identity_keys": sorted(id_doc),
            "identity_sha256": sha256(files.identity),
        },
        "continuity_text": continuity_text(files.continuity),
    }
    write_evidence(ws, "P7", ev)
    return ev


# ---------------------------------------------------------------- P9 汇总

def phase_p9(ws: Path) -> dict:
    """Persistence 终检：workspace 全文件哈希树 + 主根 5 项清单 +
    continuity 全链 append-only 前缀校验（P1⊑P2⊑P3⊑P4post⊑P5⊑P6⊑P7）
    + identity / faculties 哈希全链不变。"""
    p0 = read_evidence(ws, "P0")
    chain = ["P1", "P2", "P3", "P4post", "P5", "P6", "P7"]
    prev_cont = ""
    for name in chain:
        ev = read_evidence(ws, name)
        cont = ev["continuity_text"]
        check(cont.startswith(prev_cont),
              f"continuity append-only 全链校验失败于 {name}")
        prev_cont = cont
    files = IndividualFiles.layout(ws / "individual")
    check(sha256(files.identity) == p0["identity_sha256"],
          "identity 全链哈希不变")
    check(sha256(files.faculties) == p0["faculties_sha256"],
          "faculties 全链哈希不变")
    # 5 项清单（spec-individual.md §4）：清单之外任何文件都不是个体状态；
    # capabilities/ 缺失 = 合法初始态（不代建）——此处主根已含真实能力。
    five_present = {
        "identity.json": files.identity.is_file(),
        "continuity.jsonl": files.continuity.is_file(),
        "memory/": files.memory_dir.is_dir(),
        "capabilities/": files.capabilities_dir.is_dir(),
        "faculties.json": files.faculties.is_file(),
    }
    check(all(five_present.values()), f"主根 5 项清单不完整：{five_present}")
    allowed_prefixes = ("identity.json", "continuity.jsonl", "faculties.json",
                        "memory/", "capabilities/")
    out_of_list = [
        str(p.relative_to(files.root)).replace("\\", "/")
        for p in files.root.rglob("*")
        if p.is_file()
        and not str(p.relative_to(files.root)).replace("\\", "/").startswith(
            allowed_prefixes
        )
    ]
    check(not out_of_list,
          f"个体根出现清单外文件（非个体状态）：{out_of_list}")
    tree = {}
    for p in sorted(ws.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(ws)).replace("\\", "/")
            tree[rel] = sha256(p)
    records = load_continuity(files.continuity).records
    ev = {
        "five_items": five_present,
        "continuity_records": len(records),
        "workspace_tree": tree,
        "append_only_chain_ok": True,
        "identity_chain_ok": True,
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    write_evidence(ws, "P9", ev)
    return ev


# ---------------------------------------------------------------- 编排

PHASES = (
    ("P1", "p1", phase_p1),
    ("P2", "p2", phase_p2),
    ("P3", "p3", phase_p3),
    ("P4a", "p4a", phase_p4a),
    ("P4post", "p4post", phase_p4_post),
    ("P5", "p5", phase_p5),
    ("P6", "p6", phase_p6),
    ("P7", "p7", phase_p7),
)


def stop_models() -> None:
    """用完即卸载纪律：对本次演练用到的两个模型执行 `ollama stop`
    （幂等——未加载 = no-op，失败仅记录不中断）。防止大模型跨阶段 /
    跨运行常驻内存与机器争抢资源（2026-09-21 P2 超时根因 = P1 的 A
    未驱逐 + P2 的 B 同时驻留，调用实测慢 3 倍）。每阶段子进程自行
    按需加载所需模型，阶段间卸载安全。"""
    for model in (MODEL_A, MODEL_B):
        try:
            subprocess.run(["ollama", "stop", model], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"[hygiene] ollama stop {model} 失败：{e}", flush=True)


def run_child(ws: Path, phase: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(Path(__file__).resolve()),
           "--phase", phase, "--workspace", str(ws)]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    print(f"===== {phase}（子进程）===== " + " ".join(cmd), flush=True)
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        env=env, timeout=PHASE_TIMEOUT, cwd=str(REPO_ROOT),
    )


def run_crash_child(ws: Path) -> subprocess.CompletedProcess:
    """P4 崩溃子进程：act 后 os._exit(1)——真实进程消失（崩溃演练）。"""
    cmd = [sys.executable, str(Path(__file__).resolve()),
           "--phase", "p4-crash", "--workspace", str(ws)]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    print(f"===== p4-crash（崩溃子进程，预期 exit=1）=====", flush=True)
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        env=env, timeout=PHASE_TIMEOUT, cwd=str(REPO_ROOT),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=[c for _, c, _ in PHASES] + ["p4-crash"])
    parser.add_argument(
        "--workspace", type=Path, default=None,
        help=f"演练 workspace（必填，repo 外持久目录；也可经环境变量 {WORKSPACE_ENV} 提供）",
    )
    args = parser.parse_args()

    # workspace 显式解析：--workspace 参数 > 环境变量 > fail-loud（parser.error）。
    # 不预设默认目录，不因缺失配置回退任何既有实例——使用者必须自备 workspace。
    ws = args.workspace
    if ws is None:
        env_ws = os.environ.get(WORKSPACE_ENV)
        if env_ws:
            ws = Path(env_ws)
    if ws is None:
        parser.error(
            f"必须提供 workspace：--workspace <dir> 或环境变量 {WORKSPACE_ENV}；"
            "本脚本不预设默认目录，也不会回退到任何既有实例"
        )

    if args.phase:
        if args.phase == "p4-crash":
            phase_p4_crash(ws)
            return 1
        for _, choice, fn in PHASES:
            if choice == args.phase:
                fn(ws)
                return 0
        raise AssertionError(f"未知 phase：{args.phase}")

    print(f"== V1 Reality Gate 编排（workspace = {ws}）==", flush=True)
    stop_models()  # 干净起点：确保无上次运行残留的常驻模型
    p0 = phase_p0(ws)
    results: dict[str, object] = {"P0": "ok"}

    def fail(name: str, detail: str, r: object) -> int:
        """FAIL 统一出口：模型卸载（用完即卸载）+ FAIL SUMMARY 落盘 + exit 1。"""
        stop_models()
        print(f"===== {name} FAILED =====\n{detail}")
        if isinstance(r, subprocess.CompletedProcess):
            print(r.stdout[-3000:] if r.stdout else "")
            print(r.stderr[-3000:] if r.stderr else "")
        write_evidence(
            ws, "SUMMARY",
            {"gate": "FAIL", "failed_phase": name, "results": results,
             "p0": p0,
             "note": "停留于当前问题：Real Verification 未通过，"
                     "不得置 COMPLETE（STEP 15 纪律）"},
        )
        return 1

    for name, choice, _fn in PHASES:
        try:
            if name == "P4a":
                r = run_child(ws, choice)
            elif name == "P4post":
                crash = run_crash_child(ws)
                if crash.returncode != 1:
                    return fail(
                        name,
                        f"崩溃子进程必须 exit=1，实际 {crash.returncode}",
                        crash,
                    )
                results["P4crash"] = {"exit_code": crash.returncode}
                r = run_child(ws, choice)
            else:
                r = run_child(ws, choice)
        except subprocess.TimeoutExpired as te:
            # subprocess.run 在 kill 后会排空管道——异常自带子进程全部输出
            out = te.stdout or ""
            err = te.stderr or ""
            detail = f"{name} 子进程超过 {PHASE_TIMEOUT}s 未完成（超时）"
            if out:
                detail += f"\n--- 子进程 stdout（部分） ---\n{out[-3000:]}"
            if err:
                detail += f"\n--- 子进程 stderr（部分） ---\n{err[-3000:]}"
            return fail(name, detail, None)
        stop_models()  # 每阶段结束后卸载——防止跨阶段双模型常驻争抢内存
        if r.returncode != 0:
            return fail(name, f"exit={r.returncode}", r)
        results[name] = "ok"
        print(f"===== {name} PASS =====", flush=True)
    p9 = phase_p9(ws)
    summary = {
        "gate": "PASS",
        "results": results,
        "p0": p0,
        "p9": {k: v for k, v in p9.items() if k != "workspace_tree"},
        "note": "全部 phase 通过：真实 wire + 真实进程边界 + 真实持久位",
    }
    write_evidence(ws, "SUMMARY", summary)
    stop_models()  # 用完即卸载：全量运行结束，释放机器内存
    print("== V1 Reality Gate 结果：PASS ==", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
