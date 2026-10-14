"""最小启动入口自动化测试（阶段 B，决定 D-053；阶段 D 接线，决定 D-055）。

覆盖入口行为：
- 运行配置读取（config/model-config.json → ModelConfig 槽位；缺失 = 未配置
  全 None，U-5 不预设）；
- host 部署配置读取（config/host-config.json → HostConfig 槽位，str → Path；
  缺失 = 未配置全 None → 不装配，U-5 不预设；阶段 D）；
- 实例根读取（config/install-state.json 现有约定；缺失 → fail-loud）；
- run_turn = act → persist 严格交替（决定 ⑬）；未配置模型 → 降级回合
  （action=None，决定 ⑯）但经历仍经 persist 路径落盘（决定 ⑮）；
- 坏 backend 在装配点 fail-loud（_build_model_client 规则）；
- run_observe = FileWorld 只读观察 → 观察事实经现有 M04 回合入口进入个体
  经验流（阶段 D，决定 D-055；逃逸 → ValueError fail-loud）；
- run_host_sync = 现有 host adapter sync() 一次（阶段 D；host 未装配 →
  诊断退出码 2；缺失状态库 = 初始态 → 0 新增；重复 sync = 0 新增）。

真实模型调用与真实宿主库不在本测试范围（真实运行证据见交接文件）。
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import run_dao_sheng
from dao_sheng.composition import (
    HostConfig,
    ModelConfig,
    OperationalDefaults,
    compose,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PRINCIPLES = REPO_ROOT / "docs" / "constitution" / "principles.md"

IDENTITY_TEXT = json.dumps(
    {
        "name": "测试个体",
        "self_appellation": "",
        "voice": "",
        "visual_image": "",
        "behavioral_habits": [],
        "past_experiences": [],
        "continuous_memory": [],
    },
    ensure_ascii=False,
)
FACULTIES_TEXT = json.dumps(
    ["intent", "choice", "stopping", "observation", "correction", "selection",
     "reflection", "continuity"]
)


def _init_carriers(root: Path) -> None:
    """设计层初始化两载体（compose fail-loud 前置；同 USER_GUIDE §6.2）。"""
    (root / "identity.json").write_text(IDENTITY_TEXT, encoding="utf-8")
    (root / "faculties.json").write_text(FACULTIES_TEXT, encoding="utf-8")


class LoadModelConfigTest(unittest.TestCase):
    def test_declared_slots_are_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "model-config.json").write_text(
                json.dumps(
                    {
                        "agent_backend": "llama_cpp",
                        "agent_endpoint": "http://127.0.0.1:8081",
                        "agent_model": "some-model-id",
                        "timeout_seconds": 900.0,
                        "retry_limit": 1,
                    }
                ),
                encoding="utf-8",
            )
            config = run_dao_sheng.load_model_config(root)
            self.assertEqual(config.agent_backend, "llama_cpp")
            self.assertEqual(config.agent_endpoint, "http://127.0.0.1:8081")
            self.assertEqual(config.agent_model, "some-model-id")
            self.assertEqual(config.timeout_seconds, 900.0)
            self.assertEqual(config.retry_limit, 1)
            # 未声明侧保持未设定（不预设）
            self.assertIsNone(config.reflection_backend)

    def test_missing_config_yields_unconfigured(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = run_dao_sheng.load_model_config(Path(tmp))
            self.assertIsNone(config.agent_backend)
            self.assertIsNone(config.agent_endpoint)
            self.assertIsNone(config.agent_model)
            self.assertIsNone(config.timeout_seconds)
            self.assertIsNone(config.retry_limit)


class LoadInstanceRootTest(unittest.TestCase):
    def test_instance_root_read_from_install_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "install-state.json").write_text(
                json.dumps({"instance_root": str(root / "instances" / "default")}),
                encoding="utf-8",
            )
            self.assertEqual(
                run_dao_sheng.load_instance_root(root),
                root / "instances" / "default",
            )

    def test_missing_install_state_fail_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                run_dao_sheng.load_instance_root(Path(tmp))


class RunTurnTest(unittest.TestCase):
    def _compose_unconfigured(self, root: Path):
        _init_carriers(root)
        return compose(
            principles_source_path=PRINCIPLES,
            individual_root=root,
            model_config=ModelConfig(),
            operational_defaults=OperationalDefaults(),
            host_config=HostConfig(),
        )

    def test_degraded_turn_still_persists_experience(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assembly = self._compose_unconfigured(root)
            self.assertIsNone(assembly.model)  # 未配置 → 两侧 None（U-5）
            outcome, reference = run_dao_sheng.run_turn(assembly, "测试任务内容")
            self.assertEqual(outcome.turn_number, 1)
            self.assertIsNone(outcome.action)  # 降级回合（决定 ⑯）
            # 经历经 persist 路径落盘：Memory 载体存在且记录可读回
            self.assertTrue((root / "memory" / "memory.db").is_file())
            record = assembly.memory.get(reference)
            self.assertEqual(
                record.content, "经历：测试任务内容\n行动：无"
            )  # 决定 ⑮ 两行形态
            assembly.memory.close()

    def test_unknown_backend_fail_loud_at_assembly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_carriers(root)
            with self.assertRaises(RuntimeError):
                compose(
                    principles_source_path=PRINCIPLES,
                    individual_root=root,
                    model_config=ModelConfig(
                        agent_backend="bogus",
                        agent_endpoint="http://127.0.0.1:1",
                        agent_model="m",
                        timeout_seconds=1.0,
                        retry_limit=0,
                    ),
                    operational_defaults=OperationalDefaults(),
                    host_config=HostConfig(),
                )


def _compose_unconfigured(root: Path):
    """未配置模型 / host 的最小装配（U-5：全 None，不预设）。"""
    _init_carriers(root)
    return compose(
        principles_source_path=PRINCIPLES,
        individual_root=root,
        model_config=ModelConfig(),
        operational_defaults=OperationalDefaults(),
        host_config=HostConfig(),
    )


class LoadHostConfigTest(unittest.TestCase):
    """阶段 D（决定 D-055）：host 部署配置读取（config/host-config.json）。"""

    def test_declared_slots_are_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "host-config.json").write_text(
                json.dumps(
                    {
                        "state_db": str(root / "host" / "state.db"),
                        "import_log": str(root / "host" / "imported.log"),
                    }
                ),
                encoding="utf-8",
            )
            config = run_dao_sheng.load_host_config(root)
            self.assertEqual(config.state_db, root / "host" / "state.db")
            self.assertIsNone(config.hermes_home)
            self.assertEqual(config.import_log, root / "host" / "imported.log")

    def test_missing_config_yields_unconfigured(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = run_dao_sheng.load_host_config(Path(tmp))
            self.assertIsNone(config.state_db)
            self.assertIsNone(config.hermes_home)
            self.assertIsNone(config.import_log)


class RunObserveTest(unittest.TestCase):
    """阶段 D（决定 D-055）：观察触发入口——FileWorld 只读观察经现有
    M04 回合入口进入个体经验流。观察目标 = 本仓入口文件自身（明确
    授权、内容无敏感信息；FileWorld 只取元数据，不读内容）。"""

    def test_observation_enters_experience_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assembly = _compose_unconfigured(root)
            observation, outcome, reference = run_dao_sheng.run_observe(
                assembly, "run_dao_sheng.py"
            )
            # 观察 = 只读元数据事实（K-08）
            self.assertTrue(observation.exists)
            self.assertTrue(observation.is_file)
            self.assertGreater(observation.size, 0)
            # 观察事实经现有回合入口落盘（决定 ⑬ 严格交替；未配置模型
            # → 降级回合决定 ⑯，但经历仍 persist，决定 ⑮ 两行形态）
            self.assertEqual(outcome.turn_number, 1)
            self.assertIsNone(outcome.action)
            record = assembly.memory.get(reference)
            self.assertIn("世界观察（FileWorld 只读元数据）", record.content)
            self.assertIn(f"size={observation.size}", record.content)
            self.assertTrue(record.content.startswith("经历：世界观察"))
            self.assertTrue(record.content.endswith("行动：无"))
            assembly.memory.close()

    def test_escape_path_fail_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assembly = _compose_unconfigured(root)
            with self.assertRaises(ValueError):
                run_dao_sheng.run_observe(assembly, "../outside")
            assembly.memory.close()


class RunHostSyncTest(unittest.TestCase):
    """阶段 D（决定 D-055）：Host 同步触发入口——部署层接线面（host 未
    装配 → 诊断退出码 2；host-config → compose 装配 → sync 经入口运行
    一次，缺失状态库 = 初始态 → 0 新增 → 退出码 0；幂等复跑同样 0）。

    宿主 adapter sync() 的导入语义（新增计数 / 派生摘要排除 / 重复导入
    0 新增 / legacy 双读 / collision guard）归 test_host_integration.py
    的文档化 fixture 位（ImportTest / S4SyncTest，K-10：本测试不触碰
    存储细节）。"""

    def test_host_not_assembled_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assembly = _compose_unconfigured(root)
            self.assertIsNone(assembly.host)  # HostConfig() 全 None → 不装配
            self.assertEqual(run_dao_sheng.run_host_sync(assembly), 2)
            assembly.memory.close()

    def test_load_host_config_wires_into_compose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "host-config.json").write_text(
                json.dumps(
                    {
                        "state_db": str(root / "host" / "state.db"),
                        "import_log": str(root / "host" / "imported.log"),
                    }
                ),
                encoding="utf-8",
            )
            host_config = run_dao_sheng.load_host_config(root)
            _init_carriers(root)
            assembly = compose(
                principles_source_path=PRINCIPLES,
                individual_root=root,
                model_config=ModelConfig(),
                operational_defaults=OperationalDefaults(),
                host_config=host_config,
            )
            self.assertIsNotNone(assembly.host)
            # 状态库缺失 = 初始态（宿主未运行）→ 0 新增，退出码 0
            self.assertEqual(run_dao_sheng.run_host_sync(assembly), 0)
            # 幂等复跑经入口同样 0 新增（导入语义本身见 test_host_integration）
            self.assertEqual(run_dao_sheng.run_host_sync(assembly), 0)
            assembly.memory.close()


if __name__ == "__main__":
    unittest.main()
