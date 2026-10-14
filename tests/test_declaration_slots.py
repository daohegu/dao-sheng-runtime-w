"""composition root 声明位 — M01。

Seams：`ModelConfig`（Model 配置声明位，U-5 不预设）、
`OperationalDefaults`（L4 运营策略默认值声明位，当前无已定值）、
`HOST_RELATION_STATEMENT`（host 关系声明位：M-04 / ADR 0002 决定 4 / R-12）。

依据：spec-composition-root.md §1/§3、principles.md 四层模型 L4（各条均
"当前 V1 无已定参数值——均为部署层待设项，不预设"）。
"""

import unittest
from pathlib import Path

from dao_sheng import composition


class ModelConfigTest(unittest.TestCase):
    def test_no_preset_values(self):
        """U-5 不预设：全部槽位默认为未设定（None），无任何内置端点 / 超时 / 后端。"""
        cfg = composition.ModelConfig()
        self.assertIsNone(cfg.agent_endpoint)
        self.assertIsNone(cfg.agent_model)
        self.assertIsNone(cfg.agent_backend)
        self.assertIsNone(cfg.reflection_endpoint)
        self.assertIsNone(cfg.reflection_model)
        self.assertIsNone(cfg.reflection_backend)
        self.assertIsNone(cfg.timeout_seconds)
        self.assertIsNone(cfg.retry_limit)
        self.assertIsNone(cfg.research_backend)

    def test_explicit_deployment_values_are_held(self):
        cfg = composition.ModelConfig(
            agent_endpoint="example.invalid/agent",
            agent_model="example-model",
            reflection_endpoint="example.invalid/reflection",
            reflection_model="example-model",
            timeout_seconds=30.0,
            retry_limit=3,
            research_backend="example-backend",
        )
        self.assertEqual(cfg.agent_endpoint, "example.invalid/agent")
        self.assertEqual(cfg.agent_model, "example-model")
        self.assertEqual(cfg.reflection_endpoint, "example.invalid/reflection")
        self.assertEqual(cfg.reflection_model, "example-model")
        self.assertEqual(cfg.timeout_seconds, 30.0)
        self.assertEqual(cfg.retry_limit, 3)
        self.assertEqual(cfg.research_backend, "example-backend")

    def test_immutable(self):
        """运行时不可改写：Model 配置由部署层声明，运行时路径不得修改。"""
        cfg = composition.ModelConfig()
        with self.assertRaises(AttributeError):
            cfg.agent_endpoint = "example.invalid/other"


class OperationalDefaultsTest(unittest.TestCase):
    def test_default_is_unset(self):
        """L4 声明位默认为空 = 全部未设定（principles.md 各条 L4：当前无已定参数值）。"""
        self.assertEqual(composition.OperationalDefaults().entries, ())

    def test_explicit_entries_held_and_immutable(self):
        d = composition.OperationalDefaults(
            entries=(composition.OperationalValue("行动频率上限", 10),)
        )
        self.assertEqual(d.entries[0].name, "行动频率上限")
        self.assertEqual(d.entries[0].value, 10)
        with self.assertRaises(AttributeError):
            d.entries = ()


class HostRelationStatementTest(unittest.TestCase):
    def test_statement_exists_at_declaration_slot(self):
        """M-04：表述降格为启动配置描述——装配点内的普通字符串声明位。"""
        stmt = composition.HOST_RELATION_STATEMENT
        self.assertIsInstance(stmt, str)
        self.assertIn("Hermes Desktop", stmt)
        self.assertIn("不直接触碰", stmt)

    def test_statement_only_lives_in_composition_root(self):
        """R-12 / M-04 结构检查：'Hermes' 在整个 V1 代码中只出现于
        装配点模块 + Hermes 宿主 adapter 层（M09 / ADR 0002 决定 1：
        唯一允许知道宿主名的层；宿主名 token 的完整允许位由 M09 棘轮
        test_hermes_token_only_in_allowed_sites 固化，此处对齐）。
        宿主关系"表述"本身仍仅存在于装配点声明位（上方存在性检查）。"""
        pkg = Path(composition.__file__).resolve().parent
        allowed = {"composition.py", "hermes_host.py"}
        for py in sorted(pkg.rglob("*.py")):
            if "Hermes" in py.read_text(encoding="utf-8"):
                self.assertIn(
                    py.name,
                    allowed,
                    f"'Hermes' 不得出现于 {py.name}（仅装配点声明位 / 宿主 adapter 层）",
                )


if __name__ == "__main__":
    unittest.main()
