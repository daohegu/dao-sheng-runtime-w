"""装配函数 compose — M01（+ M02 identity 装配面 / M03 faculties +
continuity 装配面 / M04 individual 装配面 / M05 memory provider 装配面 /
M06 model 调用装配面 / M07 growth 装配面）。

Seam：`compose`（全部依赖注入 → RuntimeAssembly；R-09 accept don't create）；
M02：identity 载体装配时读取 + 校验 + 投影；载体缺失 / 非法 → fail-loud
（enforce 机制决定 ② 装配面：单一来源仅在 composition root 装配时读取）；
M03：faculties 载体读取 + 校验 + 投影（缺失 → fail-loud 不代建；非法 →
拒绝）+ continuity 载体装配时校验（缺失 = 空日志；损坏 → fail-loud；
投影不随装配结果携带）；
M05：Memory Provider 仅在装配点构造（R-09）并进入装配结果
（memory: MemoryStore）；目录 / DB 缺失 = 初始态（新建个体，空记忆，
ADR 0007）——Provider 自建载体，与 identity / faculties 载体的 fail-loud
语义不同；M09：host 集成声明位 HostConfig（U-5 全部未设定 →
host None；完整 → HermesHostAdapter 仅装配点构造并进入装配结果，
导入通道 = growth.import_experience；部分设定 → fail-loud）；
M11：闸门唯一实现 CapabilityVerifier 仅装配点构造（R-09）并注入
capability_manager（verifier 位由 M08 的 None 降级替换为真闸门，
决定 ㊱–㊴）——advance working → active 与 execute 均经闸门，默认
配置下端到端可闭环（AC 6）。

依据：spec-composition-root.md §1/§2（装配点 + "道"运行时单一来源注入）、
ADR 0004 决定 1（不设独立 life 层）/ 决定 3（三独立）、CINV-2（只读设计层
来源）、data-ownership.md §2（Identity / Faculties：仅设计层可写，Runtime
只读；Continuity：个体内部机制追加）。
"""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from dao_sheng import composition
from dao_sheng.capability_lifecycle import CapabilityState
from dao_sheng.faculties import FACULTY_ROOTS
from dao_sheng.growth import ExperienceCandidate, Growth
from dao_sheng.hermes_host import HermesHostAdapter
from dao_sheng.individual import Individual, Turn
from dao_sheng.model_llama_cpp import LlamaCppModel
from dao_sheng.model_ollama import OllamaModel
from dao_sheng.memory import (
    MemoryConfidence,
    MemoryOrigin,
    MemoryStatus,
    RecallQuery,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PRINCIPLES = REPO_ROOT / "docs" / "constitution" / "principles.md"


def _carrier_text(**overrides) -> str:
    """一份完整合法 identity 载体文档（fixture；内容值非设计层内容）。"""
    doc = {
        "name": "DaoSheng",
        "self_appellation": "",
        "voice": "",
        "visual_image": "",
        "behavioral_habits": [],
        "past_experiences": [],
        "continuous_memory": [],
    }
    doc.update(overrides)
    return json.dumps(doc, ensure_ascii=False)


def _faculties_text(roots) -> str:
    """faculties 载体文档（fixture；默认内容 = Q3 初始 8 根，域常量）。"""
    return json.dumps(list(roots), ensure_ascii=False)


def _make_host_state_db(path: Path, rows: tuple[tuple[str, str], ...]) -> None:
    """宿主状态库 fixture：messages 表必需列读取面（host_carrier D1 裁定
    1：session_id / content / _compressed_summary / message_uid——缺必需
    列 fail-loud，fixture 必须构造完整读取面；宿主 schema 知识归宿主层，
    fixture 只构造该读取面；message_uid = 确定性 uid-N，全部标记 = 0 非
    派生摘要）。"""
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE messages ("
            "id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, content TEXT, "
            "_compressed_summary INTEGER NOT NULL DEFAULT 0, message_uid TEXT)"
        )
        conn.executemany(
            "INSERT INTO messages (session_id, content, message_uid) "
            "VALUES (?, ?, ?)",
            [(session_id, content, f"uid-{index}") for index, (session_id, content) in enumerate(rows, start=1)],
        )
        conn.commit()
    finally:
        conn.close()


class ComposeTest(unittest.TestCase):
    def setUp(self):
        """部署层 fixture：临时个体 root + 合法 identity / faculties 载体
        （设计层初始化模拟；continuity 缺失 = 空日志，不建文件）。

        清理顺序（Windows：临时目录删除要求 memory.db 连接已关）：
        addCleanup 按 LIFO 执行——先登记 _tmp.cleanup，测试内绑定装配
        结果后登记 a.memory.close，则 close 先于目录删除执行。
        """
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self._write_identity()
        self._write_faculties()

    def _write_identity(self, **overrides) -> None:
        (self.root / "identity.json").write_text(
            _carrier_text(**overrides), encoding="utf-8"
        )

    def _write_faculties(self, roots=FACULTY_ROOTS) -> None:
        (self.root / "faculties.json").write_text(
            _faculties_text(roots), encoding="utf-8"
        )

    def test_all_inputs_required(self):
        """R-09：全部依赖必须注入——缺任何一个都不得装配。"""
        with self.assertRaises(TypeError):
            composition.compose()
        with self.assertRaises(TypeError):
            composition.compose(
                principles_source_path=PRINCIPLES,
                individual_root=self.root,
                model_config=composition.ModelConfig(),
                # operational_defaults 缺失
            )
        with self.assertRaises(TypeError):
            composition.compose(
                principles_source_path=PRINCIPLES,
                individual_root=self.root,
                model_config=composition.ModelConfig(),
                operational_defaults=composition.OperationalDefaults(),
                # host_config 缺失
            )

    def test_assembles_runtime_from_injected_inputs(self):
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        # "道"运行时唯一副本：当前成文子集 6 条
        self.assertEqual(len(a.doctrine.principles), 6)
        # 个体持久文件清单 5 项全部派生自注入 root
        self.assertEqual(a.individual_files.root, self.root)
        # M02 决定 ①：Identity 载体 = root/"identity.json"
        self.assertEqual(a.individual_files.identity, self.root / "identity.json")
        # M03 决定 ③：Continuity 载体 = root/"continuity.jsonl"
        self.assertEqual(a.individual_files.continuity, self.root / "continuity.jsonl")
        self.assertEqual(a.individual_files.memory_dir, self.root / "memory")
        self.assertEqual(
            a.individual_files.capabilities_dir, self.root / "capabilities"
        )
        # M03 决定 ④：Faculties 载体 = root/"faculties.json"
        self.assertEqual(a.individual_files.faculties, self.root / "faculties.json")
        # M02：identity 载体装配时读取 + 校验 + 投影为只读 Identity
        self.assertEqual(a.identity.name, "DaoSheng")
        self.assertEqual(a.identity.behavioral_habits, ())
        # M03：faculties 载体装配时读取 + 校验 + 投影为只读 Faculties
        self.assertEqual(a.faculties.roots, FACULTY_ROOTS)
        # 部署层注入的声明位原样进入装配结果
        cfg = composition.ModelConfig(timeout_seconds=30.0)
        a2 = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=cfg,
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a2.memory.close)
        self.assertIs(a2.model_config, cfg)

    def test_composition_result_immutable(self):
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        with self.assertRaises(AttributeError):
            a.doctrine = None
        with self.assertRaises(AttributeError):
            a.individual_files = None
        with self.assertRaises(AttributeError):
            a.identity = None
        with self.assertRaises(AttributeError):
            a.faculties = None
        with self.assertRaises(AttributeError):
            a.memory = None
        with self.assertRaises(AttributeError):
            a.individual = None
        with self.assertRaises(AttributeError):
            a.model = None
        with self.assertRaises(AttributeError):
            a.reflection_model = None
        with self.assertRaises(AttributeError):
            a.growth = None
        with self.assertRaises(AttributeError):
            a.host = None

    def test_identity_carrier_read_only(self):
        """data-ownership：装配只读 identity 载体，不得改写。"""
        before = (self.root / "identity.json").read_bytes()
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertEqual((self.root / "identity.json").read_bytes(), before)

    def test_design_source_read_only(self):
        """CINV-2：装配只读设计层来源，不得改写 principles.md。"""
        before = PRINCIPLES.read_bytes()
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertEqual(PRINCIPLES.read_bytes(), before)

    def test_missing_canonical_source_fails_loudly(self):
        """来源文件里没有成文清单 → 装配显式失败，不产出空 Doctrine。"""
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "principles.md"
            bad.write_text("# 空来源\n\n无清单。\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                composition.compose(
                    principles_source_path=bad,
                    individual_root=self.root,
                    model_config=composition.ModelConfig(),
                    operational_defaults=composition.OperationalDefaults(),
                    host_config=composition.HostConfig(),
                )

    def test_missing_identity_carrier_fails_loudly(self):
        """M02 决定 ② 装配面：identity 载体缺失 → 装配显式失败，不产出空 Identity。

        载体由设计层初始化（data-ownership：Identity 仅设计层可写）；
        Runtime 不预设、不代建（规则 11）。
        """
        (self.root / "identity.json").unlink()
        with self.assertRaises(RuntimeError):
            composition.compose(
                principles_source_path=PRINCIPLES,
                individual_root=self.root,
                model_config=composition.ModelConfig(),
                operational_defaults=composition.OperationalDefaults(),
                host_config=composition.HostConfig(),
            )

    def test_invalid_identity_carrier_rejected(self):
        """M02：非法载体（含 host 字段 = 外部依赖）→ 装配显式拒绝。"""
        self._write_identity(host="x")
        with self.assertRaises(ValueError):
            composition.compose(
                principles_source_path=PRINCIPLES,
                individual_root=self.root,
                model_config=composition.ModelConfig(),
                operational_defaults=composition.OperationalDefaults(),
                host_config=composition.HostConfig(),
            )

    def test_missing_faculties_carrier_fails_loudly(self):
        """M03 决定 ④ 装配面：faculties 载体缺失 → 装配显式失败，不代建
        （内容 = 域常量，设计层初始化；M02 决定 ② 对齐）。"""
        (self.root / "faculties.json").unlink()
        with self.assertRaises(RuntimeError):
            composition.compose(
                principles_source_path=PRINCIPLES,
                individual_root=self.root,
                model_config=composition.ModelConfig(),
                operational_defaults=composition.OperationalDefaults(),
                host_config=composition.HostConfig(),
            )

    def test_invalid_faculties_carrier_rejected(self):
        """M03：非法载体（含未知根）→ 装配显式拒绝。"""
        self._write_faculties(list(FACULTY_ROOTS) + ["capability"])
        with self.assertRaises(ValueError):
            composition.compose(
                principles_source_path=PRINCIPLES,
                individual_root=self.root,
                model_config=composition.ModelConfig(),
                operational_defaults=composition.OperationalDefaults(),
                host_config=composition.HostConfig(),
            )

    def test_faculties_carrier_read_only(self):
        """data-ownership：装配只读 faculties 载体，不得改写。"""
        before = (self.root / "faculties.json").read_bytes()
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertEqual((self.root / "faculties.json").read_bytes(), before)

    def test_missing_continuity_carrier_is_empty_log(self):
        """M03 决定 ⑤ 装配面：continuity 载体缺失 = 空日志（初始状态）
        → 装配成功，且装配不代建文件（装配无写入）。"""
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertFalse((self.root / "continuity.jsonl").exists())
        # 装配结果不携带 Continuity 投影（快照会陈旧——消费方按需读取）
        self.assertFalse(hasattr(a, "continuity"))

    def test_memory_provider_assembled_initial_state(self):
        """M05 决定 ⑥ 装配面：Memory Provider 仅在装配点构造（R-09）并
        进入装配结果；目录 / DB 缺失 = 初始态（新建个体，空记忆，
        ADR 0007）——Provider 自建载体（与 identity / faculties 载体的
        fail-loud 语义不同）。"""
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        # 初始态 = 空记忆（经 6 方法契约读取，interface = test surface）
        self.assertEqual(a.memory.recall(RecallQuery()), [])
        # 载体已自建：memory_dir 内单 embedded SQLite 文件（决定 ⑥）
        self.assertTrue((self.root / "memory" / "memory.db").is_file())

    def test_memory_roundtrip_through_assembled_provider(self):
        """M05：装配结果中的 Provider 满足 MemoryStore 契约（行为面经
        契约方法；三维显式，无推断行）。"""
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        ref = a.memory.remember(
            content="装配后写入的一条记忆",
            memory_origin=MemoryOrigin.CANONICAL,
            memory_status=MemoryStatus.OBSERVED,
            memory_confidence=MemoryConfidence.CONFIRMED,
        )
        self.assertEqual(a.memory.get(ref).content, "装配后写入的一条记忆")

    def test_individual_assembled_and_turn_e2e_degraded(self):
        """M04 装配面：Individual 仅装配点构造（R-09）并进入装配结果
        （individual）；接线 = doctrine / identity / faculties / memory /
        continuity 载体路径 + agent 侧 model（U-5 未装配 → None，全部
        回合降级，决定 ⑯）。行为接线经公共面验证（K-10）：完整回合
        act / persist 成环——action None，经历记录（经历 / 行动两行）
        落在装配结果的 memory（经 6 方法契约读取）。"""
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertIsInstance(a.individual, Individual)
        outcome = a.individual.act(Turn("装配接线验证回合", MemoryOrigin.CANONICAL))
        self.assertEqual(outcome.turn_number, 1)
        self.assertIsNone(outcome.action, "agent 侧 model 未装配（U-5）→ 降级回合")
        reference = a.individual.persist()
        self.assertTrue(reference)
        record = a.memory.get(reference)
        self.assertEqual(record.content, "经历：装配接线验证回合\n行动：无")
        self.assertEqual(len(a.memory.recall(RecallQuery())), 1)

    def test_model_clients_assembled_from_full_config(self):
        """M06 装配面：两侧配置完整（backend + endpoint + model + 共享
        timeout / retry）→ 两侧 OllamaModel 构造并进入装配结果
        （R-09：仅在装配点构造；注入值原样传递）。"""
        cfg = composition.ModelConfig(
            agent_backend="ollama",
            agent_endpoint="ep-agent",
            agent_model="m-agent",
            reflection_backend="ollama",
            reflection_endpoint="ep-reflection",
            reflection_model="m-reflection",
            timeout_seconds=30.0,
            retry_limit=2,
        )
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=cfg,
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertIsInstance(a.model, OllamaModel)
        self.assertEqual(a.model.endpoint, "ep-agent")
        self.assertEqual(a.model.model, "m-agent")
        self.assertEqual(a.model.timeout_seconds, 30.0)
        self.assertEqual(a.model.retry_limit, 2)
        self.assertIsInstance(a.reflection_model, OllamaModel)
        self.assertEqual(a.reflection_model.model, "m-reflection")

    def test_model_unset_is_none(self):
        """M06 装配面：全部未设定（U-5：部署形态 UNKNOWN）→ 两侧
        None——不代建、不预设（规则 11）。"""
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertIsNone(a.model)
        self.assertIsNone(a.reflection_model)

    def test_one_side_model_configured(self):
        """M06 装配面：单侧设定（共享 timeout / retry 齐备）→ 该侧
        构造、另一侧 None（两侧独立，不互相要求）。"""
        cfg = composition.ModelConfig(
            reflection_backend="ollama",
            reflection_endpoint="ep-reflection",
            reflection_model="m-reflection",
            timeout_seconds=30.0,
            retry_limit=1,
        )
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=cfg,
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertIsNone(a.model)
        self.assertIsInstance(a.reflection_model, OllamaModel)

    def test_mixed_backends_independent(self):
        """ADR 0008 裁定 ②：两侧允许异 backend 且独立构造（agent =
        Ollama，reflection = llama.cpp）——逐侧经自身 backend 名 dispatch
        到对应 adapter，注入值原样传递。"""
        cfg = composition.ModelConfig(
            agent_backend="ollama",
            agent_endpoint="ep-agent",
            agent_model="m-agent",
            reflection_backend="llama_cpp",
            reflection_endpoint="ep-reflection",
            reflection_model="m-reflection",
            timeout_seconds=30.0,
            retry_limit=2,
        )
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=cfg,
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertIsInstance(a.model, OllamaModel)
        self.assertIsInstance(a.reflection_model, LlamaCppModel)
        self.assertEqual(a.reflection_model.endpoint, "ep-reflection")

    def test_partial_model_config_fails_loudly(self):
        """M06 装配面：部分设定 = 坏配置 → 装配显式失败（fail-loud，
        不携带半配置运行；含 backend 缺失 / 未知 backend——ADR 0008，
        无默认 backend）。

        fail-before-allocation 顺序不变量测试锁（Candidate 1 裁定）：
        失败后 Memory Provider 不得被构造——memory.db 未自建
        （composition 注释约定「坏配置在分配任何资源前 fail-loud」
        的可执行化）。"""
        for bad in (
            composition.ModelConfig(  # agent 半设定
                agent_backend="ollama",
                agent_endpoint="e",
                agent_model="m",
                timeout_seconds=30.0,
                retry_limit=1,
                reflection_endpoint="e2",
            ),
            composition.ModelConfig(  # agent 齐但共享 timeout 缺
                agent_backend="ollama",
                agent_endpoint="e",
                agent_model="m",
                retry_limit=1,
            ),
            composition.ModelConfig(  # reflection 齐但共享 retry 缺
                reflection_backend="ollama",
                reflection_endpoint="e",
                reflection_model="m",
                timeout_seconds=30.0,
            ),
            composition.ModelConfig(  # endpoint / model 设定但 backend 缺失
                agent_endpoint="e",
                agent_model="m",
                timeout_seconds=30.0,
                retry_limit=1,
            ),
            composition.ModelConfig(  # 未知 backend
                agent_backend="bogus",
                agent_endpoint="e",
                agent_model="m",
                timeout_seconds=30.0,
                retry_limit=1,
            ),
        ):
            with self.assertRaises(RuntimeError):
                composition.compose(
                    principles_source_path=PRINCIPLES,
                    individual_root=self.root,
                    model_config=bad,
                    operational_defaults=composition.OperationalDefaults(),
                    host_config=composition.HostConfig(),
                )
            # 顺序不变量锁：Model 校验位于 Memory Provider 构造之前——
            # 失败路径不得已创建 memory.db（Provider 构造即自建载体）
            self.assertFalse((self.root / "memory" / "memory.db").exists())

    def test_mixed_backends_reverse_dispatch(self):
        """ADR 0008 裁定 ②：dispatch 以各侧自身 backend 槽为键（不以
        侧位置为键）——反向组合（agent = llama.cpp，reflection =
        Ollama）同进程独立装配，逐侧经自身 backend 到对应 adapter，
        注入值原样传递。"""
        cfg = composition.ModelConfig(
            agent_backend="llama_cpp",
            agent_endpoint="ep-agent",
            agent_model="m-agent",
            reflection_backend="ollama",
            reflection_endpoint="ep-reflection",
            reflection_model="m-reflection",
            timeout_seconds=30.0,
            retry_limit=2,
        )
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=cfg,
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertIsInstance(a.model, LlamaCppModel)
        self.assertEqual(a.model.endpoint, "ep-agent")
        self.assertEqual(a.model.model, "m-agent")
        self.assertIsInstance(a.reflection_model, OllamaModel)
        self.assertEqual(a.reflection_model.endpoint, "ep-reflection")
        self.assertEqual(a.reflection_model.model, "m-reflection")

    def test_backend_set_missing_endpoint_or_model_fails_loudly(self):
        """ADR 0008：backend 已设定但 endpoint / model 缺失 = 坏配置 →
        装配显式失败（与其余部分组合同一 fail-loud 表面；M06 决定
        ⑪「全部设定或全部不设定」，无默认 backend）。

        fail-before-allocation 顺序不变量测试锁（Candidate 1 裁定）：
        失败后 Memory Provider 不得被构造——memory.db 未自建。"""
        for bad in (
            composition.ModelConfig(  # agent：backend + model，缺 endpoint
                agent_backend="ollama",
                agent_model="m",
                timeout_seconds=30.0,
                retry_limit=1,
            ),
            composition.ModelConfig(  # agent：backend + endpoint，缺 model
                agent_backend="ollama",
                agent_endpoint="e",
                timeout_seconds=30.0,
                retry_limit=1,
            ),
            composition.ModelConfig(  # reflection：backend + endpoint，缺 model
                reflection_backend="llama_cpp",
                reflection_endpoint="e",
                timeout_seconds=30.0,
                retry_limit=1,
            ),
        ):
            with self.assertRaises(RuntimeError):
                composition.compose(
                    principles_source_path=PRINCIPLES,
                    individual_root=self.root,
                    model_config=bad,
                    operational_defaults=composition.OperationalDefaults(),
                    host_config=composition.HostConfig(),
                )
            # 顺序不变量锁：Model 校验位于 Memory Provider 构造之前——
            # 失败路径不得已创建 memory.db（Provider 构造即自建载体）
            self.assertFalse((self.root / "memory" / "memory.db").exists())

    def test_shared_slots_passed_to_both_adapters(self):
        """M06 决定 ⑪：timeout_seconds / retry_limit 为共享槽位——一次
        设定，两侧 adapter 构造均原样收到同一值（共享槽位行为不随
        backend dispatch 改变；两侧独立装配、值不串位）。"""
        cfg = composition.ModelConfig(
            agent_backend="ollama",
            agent_endpoint="ep-agent",
            agent_model="m-agent",
            reflection_backend="llama_cpp",
            reflection_endpoint="ep-reflection",
            reflection_model="m-reflection",
            timeout_seconds=45.5,
            retry_limit=3,
        )
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=cfg,
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertEqual(a.model.timeout_seconds, 45.5)
        self.assertEqual(a.model.retry_limit, 3)
        self.assertEqual(a.reflection_model.timeout_seconds, 45.5)
        self.assertEqual(a.reflection_model.retry_limit, 3)

    def test_growth_assembled_and_pipeline_degraded(self):
        """M07 装配面：Growth 成长管线仅装配点构造（R-09）并进入装配
        结果（growth，决定 ⑳–㉗：8 项依赖全部由装配点注入）。行为接线
        经公共面验证（K-10）：import_experience 经装配的 memory 写入
        （6 方法契约可读）；U-5 未装配（reflection 侧 model None）→
        digest 降级 None（决定 ㉕：不写、不追加、不抛异常，continuity
        载体不被代建）。"""
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertIsInstance(a.growth, Growth)
        (reference,) = a.growth.import_experience(
            (
                ExperienceCandidate(
                    content="装配接线验证经历",
                    memory_origin=MemoryOrigin.EXTERNAL,
                    idempotency_key="装配接线验证",
                ),
            )
        )
        self.assertEqual(a.memory.get(reference).content, "装配接线验证经历")
        self.assertIsNone(
            a.growth.digest(reference),
            "reflection 侧 model 未装配（U-5）→ 阶段降级",
        )
        # 降级不产生新记录、不追加（continuity 载体保持缺失 = 空日志）
        self.assertEqual(len(a.memory.recall(RecallQuery())), 1)
        self.assertFalse((self.root / "continuity.jsonl").exists())

    def test_corrupt_continuity_carrier_rejected(self):
        """M03 决定 ⑤ 装配面：continuity 载体损坏行 → 装配显式拒绝。"""
        (self.root / "continuity.jsonl").write_text("not json\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            composition.compose(
                principles_source_path=PRINCIPLES,
                individual_root=self.root,
                model_config=composition.ModelConfig(),
                operational_defaults=composition.OperationalDefaults(),
                host_config=composition.HostConfig(),
            )

    def test_host_unset_is_none(self):
        """M09 S5 装配面：host 配置全部未设定（U-5：宿主部署形态
        UNKNOWN）→ host = None——不构造、不预设（规则 11）。"""
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        self.assertIsNone(a.host)

    def test_host_assembled_from_full_config(self):
        """M09 S5 装配面：完整配置（显式状态库位置 + 导入日志）→
        HermesHostAdapter 仅装配点构造（R-09）并进入装配结果（host）；
        行为接线经公共面验证（K-10）：open_session → import_session →
        新建经历记录可经装配的 memory 读取（导入通道 =
        growth.import_experience 接成长管线，M07）。"""
        _make_host_state_db(
            self.root / "host_state.db", (("s1", "宿主会话经历"),)
        )
        cfg = composition.HostConfig(
            state_db=self.root / "host_state.db",
            import_log=self.root / "imported.txt",
        )
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=cfg,
        )
        self.addCleanup(a.memory.close)
        self.assertIsInstance(a.host, HermesHostAdapter)
        references = a.host.import_session(a.host.open_session())
        self.assertEqual(len(references), 1)
        self.assertEqual(a.memory.get(references[0]).content, "宿主会话经历")

    def test_host_both_locations_fail_loudly(self):
        """M09 S5 装配面：状态库位置与宿主根同时配置 = 坏配置 →
        装配显式失败（资源分配前 fail-loud）。

        fail-before-allocation 顺序不变量测试锁（Candidate 1 裁定）：
        失败后 Memory Provider 不得被构造——memory.db 未自建。"""
        cfg = composition.HostConfig(
            state_db=self.root / "a.db",
            hermes_home=self.root / "home",
            import_log=self.root / "imported.txt",
        )
        with self.assertRaises(RuntimeError):
            composition.compose(
                principles_source_path=PRINCIPLES,
                individual_root=self.root,
                model_config=composition.ModelConfig(),
                operational_defaults=composition.OperationalDefaults(),
                host_config=cfg,
            )
        # 顺序不变量锁：host 校验位于 Memory Provider 构造之前——
        # 失败路径不得已创建 memory.db（Provider 构造即自建载体）
        self.assertFalse((self.root / "memory" / "memory.db").exists())

    def test_host_partial_config_fail_loudly(self):
        """M09 S5 装配面：部分设定（位置缺导入日志 / 日志缺位置）=
        坏配置 → 装配显式失败（不携带半配置运行）。

        fail-before-allocation 顺序不变量测试锁（Candidate 1 裁定）：
        失败后 Memory Provider 不得被构造——memory.db 未自建。"""
        for bad in (
            composition.HostConfig(state_db=self.root / "a.db"),
            composition.HostConfig(hermes_home=self.root / "home"),
            composition.HostConfig(import_log=self.root / "imported.txt"),
        ):
            with self.assertRaises(RuntimeError):
                composition.compose(
                    principles_source_path=PRINCIPLES,
                    individual_root=self.root,
                    model_config=composition.ModelConfig(),
                    operational_defaults=composition.OperationalDefaults(),
                    host_config=bad,
                )
            # 顺序不变量锁：host 校验位于 Memory Provider 构造之前——
            # 失败路径不得已创建 memory.db（Provider 构造即自建载体）
            self.assertFalse((self.root / "memory" / "memory.db").exists())

    def test_capability_gate_wired_live(self):
        """M11 S2 装配面：闸门唯一实现仅装配点构造（R-09）并注入
        capability_manager——M08 的 verifier=None 降级位已替换为真闸门
        （决定 ㊱–㊴）。行为面经公共表面验证（K-10）：篡改载体记录
        （content 与源记录分歧）→ advance working → active 被闸门阻
        （ValueError）。若装配仍传 None，闸门操作降级、该 advance
        不失败——本测试即红（接线锁定）。"""
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        reference = a.memory.remember(
            content="装配接线验证的源记录",
            memory_origin=MemoryOrigin.CANONICAL,
            memory_status=MemoryStatus.OBSERVED,
            memory_confidence=MemoryConfidence.CONFIRMED,
        )
        a.capability_manager.propose("乙", reference)
        a.capability_manager.advance("乙", CapabilityState.WORKING)
        record_path = self.root / "capabilities" / "working" / "乙.json"
        doc = json.loads(record_path.read_text(encoding="utf-8"))
        doc["content"] = "与源记录分歧的内容"
        record_path.write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaises(ValueError):
            a.capability_manager.advance("乙", CapabilityState.ACTIVE)
        self.assertTrue(record_path.is_file())
        self.assertFalse((self.root / "capabilities" / "active").exists())

    def test_capability_advance_to_active_e2e(self):
        """M11 S5 AC 6：M08 端到端 advance → active 闭环（真实 Verifier
        验收；默认配置 = 无 model / 无 host，U-5）：remember → propose →
        advance working → advance active（记录入 active/）→ execute 返回
        投影——真闸门 + 真 Provider + 真 Manager 全闭环。fake Verifier
        验收面 = M08 既有 FakeGate 测试（test_capability_lifecycle.py）。"""
        a = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(a.memory.close)
        reference = a.memory.remember(
            content="端到端闭环验证的源记录",
            memory_origin=MemoryOrigin.DERIVED,
            memory_status=MemoryStatus.REPORTED,
            memory_confidence=MemoryConfidence.UNCERTAIN,
        )
        capability = a.capability_manager.propose("丙", reference)
        a.capability_manager.advance("丙", CapabilityState.WORKING)
        a.capability_manager.advance("丙", CapabilityState.ACTIVE)
        self.assertTrue(
            (self.root / "capabilities" / "active" / "丙.json").is_file()
        )
        self.assertEqual(a.capability_manager.execute("丙"), capability)


if __name__ == "__main__":
    unittest.main()
