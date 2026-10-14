"""init-role / configure-role 设计层入口测试（角色初始化与修改）。

依据：docs/deployment/INSTALLATION_CONTRACT.md（install 不写任何 inventory
项；设计层初始化 = 独立入口）、dao_sheng/identity.py（严格 7 键 schema）、
dao_sheng/faculties.py（FACULTY_ROOTS 恰 8 根，单一来源）、
dao_sheng/composition.py（载体缺失 fail-loud；装配只读）。

覆盖（票面 §3 九项）：
  ① 首次初始化生成 schema 合法 identity + faculties（参数模式 / 交互模式）
  ② 用户输入的名称 / 自称 / 声音 / 形象 / 行为倾向正确保存，不注入默认人格
  ③ 缺失必需名称 / 取消输入 / 非法输入 → 清晰反馈，不留无效 JSON
  ④ 任一载体已存在 → 拒绝覆盖，现有数据逐字节不变
  ⑤ configure-role 修改指定字段并保留全部未修改字段（含 list 字段 / 清空）
  ⑥ 修改后新 composition 读取新身份
  ⑦ 修改前后 memory 数据与 Continuity 记录逐字节不变
  ⑧ install 幂等性不变，install 不创建 inventory
  ⑨ 写入失败 / 非法现有载体 → 不破坏原始配置，无半成品残留
  ⑩ 自定义角色注入运行时回归（RoleChatInjectionTest）：CLI 角色经真实
     compose() / Individual → model.chat() 实际收到的 system 消息含姓名 /
     声音 / 至少一项行为习惯、不注入默认人格、两个实例根互不串用；
     configure-role 后旧 composition 保持已加载身份、新 composition 读新身份

测试纪律：经 powershell.exe 子进程真实调用 dao-sheng.ps1（真实临时实例
根，绝不触碰 instances/default）；断言 = exit code + Python 以 UTF-8 读
真实 JSON 载体 + stdout ASCII 标记（[OK]/[FAIL]）。交互输入用 ASCII
（PS 5.1 管道 stdin 按控制台代码页解码）；非 ASCII 值经参数模式测试
（CreateProcess 以 UTF-16 传参，无代码页问题）。Continuity 真实记录经
测试内构造的 Growth（注入 stub reflection_model——growth 降级规则：
reflection_model=None 不追加）经真实 append_continuity 通道写入。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dao_sheng import composition
from dao_sheng.continuity import append_continuity, parse_continuity
from dao_sheng.faculties import FACULTY_ROOTS, parse_faculties
from dao_sheng.growth import ExperienceCandidate, Growth
from dao_sheng.identity import parse_identity
from dao_sheng.individual import Turn
from dao_sheng.memory import Correction, MemoryConfidence, MemoryOrigin, MemoryStatus
from dao_sheng.model import ModelUnavailable

REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRY = REPO_ROOT / "dao-sheng.ps1"
PRINCIPLES = REPO_ROOT / "docs" / "constitution" / "principles.md"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


def _run_entry(args, instance_root, stdin_text="", entry=ENTRY, env=None):
    """真实调用 dao-sheng.ps1：子进程 powershell.exe，显式 -InstanceRoot
    指向临时目录（永不触碰正式实例）。返回 CompletedProcess（text，
    stdout/stderr 已捕获；stdout 中 CJK 可能因控制台代码页而失真——断言
    只依赖 ASCII 标记与载体文件本身）。"""
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(entry), *args, "-InstanceRoot", str(instance_root)],
        input=stdin_text, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300, env=env,
    )


def _dir_digest(directory: Path) -> str:
    """目录内容指纹（相对路径 + 文件字节）：memory 载体逐字节不变判据。"""
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(directory)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


class _StubReflectionModel:
    """测试 stub：为 Growth 认知阶段提供非空输出（决定 ㉕ 降级规则的
    反面——有模型时 reflect 真实写记忆并追加 Continuity）。"""

    def chat(self, messages):
        return "stub reflection output for role-init test"


class _RoleEntryTest(unittest.TestCase):
    """共享基座：临时实例根 + 载体读写辅助（addCleanup LIFO：先关
    memory 连接再删临时目录——Windows 上 memory.db 须先关连接）。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root = self.tmp / "instance"
        self.root.mkdir(parents=True)

    def _identity_path(self) -> Path:
        return self.root / "identity.json"

    def _faculties_path(self) -> Path:
        return self.root / "faculties.json"

    def _seed_identity(self, **overrides) -> None:
        doc = {
            "name": "林晚",
            "self_appellation": "晚",
            "voice": "低沉",
            "visual_image": "青衫",
            "behavioral_habits": ["谨慎", "好奇"],
            "past_experiences": ["幼年丧父"],
            "continuous_memory": ["记得雨夜"],
        }
        doc.update(overrides)
        self._identity_path().write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8"
        )

    def _seed_faculties(self) -> None:
        self._faculties_path().write_text(
            json.dumps(list(FACULTY_ROOTS), ensure_ascii=False), encoding="utf-8"
        )

    def _compose(self):
        assembly = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(assembly.memory.close)
        return assembly

    def _assert_ok(self, proc) -> None:
        self.assertEqual(
            proc.returncode, 0,
            f"exit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
        )

    def _assert_fail(self, proc) -> None:
        self.assertEqual(
            proc.returncode, 1,
            f"exit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
        )
        self.assertIn("[FAIL]", proc.stdout)

    def _assert_no_tmp_residue(self) -> None:
        self.assertEqual([p.name for p in self.root.glob("*.tmp")], [])


class InitRoleTest(_RoleEntryTest):
    """init-role：仅当 identity 与 faculties 均不存在时初始化。"""

    def test_parameter_mode_creates_schema_valid_carriers(self):
        """①②：参数模式（含 CJK 值）→ exit 0；identity 逐字段 = 输入；
        faculties = FACULTY_ROOTS 恰 8 根；无临时残留。"""
        proc = _run_entry(
            ["init-role",
             "-Name", "林晚",
             "-SelfAppellation", "晚",
             "-Voice", "低沉",
             "-VisualImage", "青衫",
             "-BehavioralHabits", "谨慎", "好奇",
             "-PastExperiences", "幼年丧父",
             "-ContinuousMemory", "记得雨夜"],
            self.root,
        )
        self._assert_ok(proc)
        identity = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        self.assertEqual(identity.name, "林晚")
        self.assertEqual(identity.self_appellation, "晚")
        self.assertEqual(identity.voice, "低沉")
        self.assertEqual(identity.visual_image, "青衫")
        self.assertEqual(identity.behavioral_habits, ("谨慎", "好奇"))
        self.assertEqual(identity.past_experiences, ("幼年丧父",))
        self.assertEqual(identity.continuous_memory, ("记得雨夜",))
        faculties = parse_faculties(self._faculties_path().read_text(encoding="utf-8"))
        self.assertEqual(faculties.roots, FACULTY_ROOTS)
        self._assert_no_tmp_residue()

    def test_name_only_leaves_other_fields_empty_no_persona_injection(self):
        """②：仅提供名称 → 其余字段 = schema 允许的空值（""/[]），
        载体文本不含任何默认人格内容（"道生" / "DaoSheng"）。"""
        proc = _run_entry(["init-role", "-Name", "TestRole"], self.root)
        self._assert_ok(proc)
        text = self._identity_path().read_text(encoding="utf-8")
        self.assertNotIn("道生", text)
        self.assertNotIn("DaoSheng", text)
        identity = parse_identity(text)
        self.assertEqual(identity.name, "TestRole")
        self.assertEqual(identity.self_appellation, "")
        self.assertEqual(identity.voice, "")
        self.assertEqual(identity.visual_image, "")
        self.assertEqual(identity.behavioral_habits, ())
        self.assertEqual(identity.past_experiences, ())
        self.assertEqual(identity.continuous_memory, ())
        self._assert_no_tmp_residue()

    def test_interactive_mode_saves_input(self):
        """①②：交互模式（ASCII 输入；list 字段 = 单行逗号分隔）→
        逐字段保存；空行 = 空值。"""
        stdin = "Aria\nme\nsoft voice\ntall silhouette\ncalm, curious\n\norphan\n"
        proc = _run_entry(["init-role"], self.root, stdin_text=stdin)
        self._assert_ok(proc)
        identity = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        self.assertEqual(identity.name, "Aria")
        self.assertEqual(identity.self_appellation, "me")
        self.assertEqual(identity.voice, "soft voice")
        self.assertEqual(identity.visual_image, "tall silhouette")
        self.assertEqual(identity.behavioral_habits, ("calm", "curious"))
        self.assertEqual(identity.past_experiences, ())
        self.assertEqual(identity.continuous_memory, ("orphan",))
        self._assert_no_tmp_residue()

    def test_interactive_empty_name_fails_without_writing(self):
        """③：交互模式必需名称为空（取消）→ exit 1 + [FAIL] 反馈；
        不创建任何载体、无临时残留。"""
        proc = _run_entry(["init-role"], self.root, stdin_text="\n\n\n\n\n\n\n")
        self._assert_fail(proc)
        self.assertFalse(self._identity_path().exists())
        self.assertFalse(self._faculties_path().exists())
        self._assert_no_tmp_residue()

    def test_blank_name_parameter_fails_without_writing(self):
        """③：参数模式空白名称 → exit 1 + [FAIL]；先于任何写入，无载体。"""
        proc = _run_entry(["init-role", "-Name", "   "], self.root)
        self._assert_fail(proc)
        self.assertFalse(self._identity_path().exists())
        self.assertFalse(self._faculties_path().exists())
        self._assert_no_tmp_residue()

    def test_refuses_when_identity_already_exists(self):
        """④：identity 已存在（faculties 缺失）→ 拒绝；identity 逐字节
        不变；faculties 不被创建。"""
        self._seed_identity()
        before = self._identity_path().read_bytes()
        proc = _run_entry(["init-role", "-Name", "另一个"], self.root)
        self._assert_fail(proc)
        self.assertEqual(self._identity_path().read_bytes(), before)
        self.assertFalse(self._faculties_path().exists())
        self._assert_no_tmp_residue()

    def test_refuses_when_faculties_already_exists(self):
        """④：faculties 已存在（identity 缺失）→ 拒绝；faculties 逐字节
        不变；identity 不被创建。"""
        self._seed_faculties()
        before = self._faculties_path().read_bytes()
        proc = _run_entry(["init-role", "-Name", "另一个"], self.root)
        self._assert_fail(proc)
        self.assertEqual(self._faculties_path().read_bytes(), before)
        self.assertFalse(self._identity_path().exists())
        self._assert_no_tmp_residue()

    def test_refuses_when_both_exist(self):
        """④：两载体均已存在 → 拒绝并提示 configure-role；均逐字节不变。"""
        self._seed_identity()
        self._seed_faculties()
        before_id = self._identity_path().read_bytes()
        before_fac = self._faculties_path().read_bytes()
        proc = _run_entry(["init-role", "-Name", "另一个"], self.root)
        self._assert_fail(proc)
        self.assertEqual(self._identity_path().read_bytes(), before_id)
        self.assertEqual(self._faculties_path().read_bytes(), before_fac)
        self._assert_no_tmp_residue()


class ConfigureRoleTest(_RoleEntryTest):
    """configure-role：仅修改 identity 载体；faculties / memory /
    Continuity 绝不触碰。"""

    def test_requires_existing_identity(self):
        """identity 缺失 → exit 1 + [FAIL]（提示 init-role）；不创建载体。"""
        proc = _run_entry(["configure-role", "-Voice", "清亮"], self.root)
        self._assert_fail(proc)
        self.assertFalse(self._identity_path().exists())
        self._assert_no_tmp_residue()

    def test_changes_only_given_field(self):
        """⑤：-Voice 修改 → 该字段更新；其余 6 字段逐一相等；faculties
        载体逐字节不变；无临时残留。"""
        self._seed_identity()
        self._seed_faculties()
        before = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        faculties_before = self._faculties_path().read_bytes()
        proc = _run_entry(["configure-role", "-Voice", "清亮"], self.root)
        self._assert_ok(proc)
        after = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        self.assertEqual(after.voice, "清亮")
        self.assertEqual(after.name, before.name)
        self.assertEqual(after.self_appellation, before.self_appellation)
        self.assertEqual(after.visual_image, before.visual_image)
        self.assertEqual(after.behavioral_habits, before.behavioral_habits)
        self.assertEqual(after.past_experiences, before.past_experiences)
        self.assertEqual(after.continuous_memory, before.continuous_memory)
        self.assertEqual(self._faculties_path().read_bytes(), faculties_before)
        self._assert_no_tmp_residue()

    def test_replaces_list_field(self):
        """⑤：list 字段按 list[str] 保存——-BehavioralHabits 整表替换，
        其余字段保留。"""
        self._seed_identity()
        before = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        proc = _run_entry(
            ["configure-role", "-BehavioralHabits", "读书", "散步"], self.root
        )
        self._assert_ok(proc)
        after = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        self.assertEqual(after.behavioral_habits, ("读书", "散步"))
        self.assertEqual(after.name, before.name)
        self.assertEqual(after.voice, before.voice)
        self.assertEqual(after.past_experiences, before.past_experiences)
        self._assert_no_tmp_residue()

    def test_clear_field(self):
        """⑤：-Clear voice → 显式清空为 ""；其余字段保留。"""
        self._seed_identity()
        before = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        proc = _run_entry(["configure-role", "-Clear", "voice"], self.root)
        self._assert_ok(proc)
        after = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        self.assertEqual(after.voice, "")
        self.assertEqual(after.name, before.name)
        self.assertEqual(after.behavioral_habits, before.behavioral_habits)
        self._assert_no_tmp_residue()

    def test_cannot_clear_name(self):
        """name 为必需字段：-Clear name → exit 1 + [FAIL]；原载体不变。"""
        self._seed_identity()
        before = self._identity_path().read_bytes()
        proc = _run_entry(["configure-role", "-Clear", "name"], self.root)
        self._assert_fail(proc)
        self.assertEqual(self._identity_path().read_bytes(), before)
        self._assert_no_tmp_residue()

    def test_interactive_empty_input_keeps_values(self):
        """⑤：交互模式空输入 = 保留原值；提供值 = 更新。"""
        self._seed_identity(
            name="Aria", self_appellation="me", voice="low",
            visual_image="tall", behavioral_habits=["calm"],
            past_experiences=["x"], continuous_memory=["y"],
        )
        stdin = "\n\nNewVoice\n\n\n\n\n"
        proc = _run_entry(["configure-role"], self.root, stdin_text=stdin)
        self._assert_ok(proc)
        after = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        self.assertEqual(after.name, "Aria")
        self.assertEqual(after.self_appellation, "me")
        self.assertEqual(after.voice, "NewVoice")
        self.assertEqual(after.visual_image, "tall")
        self.assertEqual(after.behavioral_habits, ("calm",))
        self.assertEqual(after.past_experiences, ("x",))
        self.assertEqual(after.continuous_memory, ("y",))
        self._assert_no_tmp_residue()

    def test_interactive_dash_clears_optional_field(self):
        """⑤：交互模式 '-' token = 显式清空可选字段。"""
        self._seed_identity(
            name="Aria", self_appellation="me", voice="low",
            visual_image="tall", behavioral_habits=["calm"],
            past_experiences=["x"], continuous_memory=["y"],
        )
        stdin = "\n\n-\n\n\n\n\n"
        proc = _run_entry(["configure-role"], self.root, stdin_text=stdin)
        self._assert_ok(proc)
        after = parse_identity(self._identity_path().read_text(encoding="utf-8"))
        self.assertEqual(after.voice, "")
        self.assertEqual(after.name, "Aria")
        self._assert_no_tmp_residue()

    def test_refuses_invalid_identity_without_damage(self):
        """⑨：现有 identity 非法（含未知键 model）→ exit 1 + [FAIL]；
        原文件逐字节不变；无临时残留。"""
        bad = {
            "name": "X", "self_appellation": "", "voice": "", "visual_image": "",
            "behavioral_habits": [], "past_experiences": [], "continuous_memory": [],
            "model": "llama",
        }
        self._identity_path().write_text(
            json.dumps(bad, ensure_ascii=False), encoding="utf-8"
        )
        before = self._identity_path().read_bytes()
        proc = _run_entry(["configure-role", "-Voice", "y"], self.root)
        self._assert_fail(proc)
        self.assertEqual(self._identity_path().read_bytes(), before)
        self._assert_no_tmp_residue()

    def test_blank_name_update_rejected(self):
        """③⑨：-Name 空白 → exit 1 + [FAIL]；原载体不变。"""
        self._seed_identity()
        before = self._identity_path().read_bytes()
        proc = _run_entry(["configure-role", "-Name", "   "], self.root)
        self._assert_fail(proc)
        self.assertEqual(self._identity_path().read_bytes(), before)
        self._assert_no_tmp_residue()


class RoleCompositionTest(_RoleEntryTest):
    """⑥⑦：configure-role 与真实 composition / memory / Continuity 的交互。"""

    def test_configure_role_visible_to_next_composition(self):
        """⑥：configure-role 改名 → 新 composition 读取新身份。"""
        self._seed_identity()
        self._seed_faculties()
        first = self._compose()
        self.assertEqual(first.identity.name, "林晚")
        first.memory.close()
        proc = _run_entry(["configure-role", "-Name", "林晓"], self.root)
        self._assert_ok(proc)
        second = self._compose()
        self.assertEqual(second.identity.name, "林晓")

    def test_configure_role_preserves_memory_and_continuity_bytes(self):
        """⑦：真实 Individual 回合写 memory + 真实 Growth.reflect 经
        append_continuity 写 Continuity → 关闭连接 → 指纹 → configure-role
        → 指纹逐字节不变（memory 目录与 continuity.jsonl）。"""
        self._seed_identity()
        self._seed_faculties()
        assembly = self._compose()
        assembly.individual.act(
            Turn(content="测试回合：角色初始化验收", memory_origin=MemoryOrigin.EXTERNAL)
        )
        assembly.individual.persist()
        growth = Growth(
            memory=assembly.memory,
            append_continuity=partial(
                append_continuity, assembly.individual_files.continuity
            ),
            reflection_model=_StubReflectionModel(),
            origin=MemoryOrigin,
            status=MemoryStatus,
            confidence=MemoryConfidence,
            correction=Correction,
            unavailable=ModelUnavailable,
        )
        (reference,) = growth.import_experience([
            ExperienceCandidate(
                content="一段可导入的经历",
                memory_origin=MemoryOrigin.EXTERNAL,
                idempotency_key="role-init-acceptance-1",
            )
        ])
        self.assertIsNotNone(growth.reflect(reference))
        assembly.memory.close()
        # 真实 Continuity 记录已存在（恰 1 条，schema 恰 2 键）。
        records = parse_continuity(
            assembly.individual_files.continuity.read_text(encoding="utf-8")
        ).records
        self.assertEqual(len(records), 1)
        self.assertEqual(set(records[0]), {"content", "reference"})
        memory_before = _dir_digest(assembly.individual_files.memory_dir)
        continuity_before = assembly.individual_files.continuity.read_bytes()
        proc = _run_entry(["configure-role", "-Voice", "清亮"], self.root)
        self._assert_ok(proc)
        self.assertEqual(
            _dir_digest(assembly.individual_files.memory_dir), memory_before
        )
        self.assertEqual(
            assembly.individual_files.continuity.read_bytes(), continuity_before
        )
        self._assert_no_tmp_residue()


class InstallContractTest(unittest.TestCase):
    """⑧：install 契约不变——幂等、不创建 inventory；隔离副本上
    install → init-role → composition → configure-role → composition 全链。

    个人运行时数据（install-state、实例载体）经 DAO_SHENG_DATA_HOME 写入
    副本之外的外部数据根——Git worktree（副本）内不出现任何个人数据。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.copy = self.tmp / "repo-copy"
        shutil.copytree(
            REPO_ROOT, self.copy,
            ignore=shutil.ignore_patterns(
                ".venv", "instances", "config", "log", "__pycache__", ".git",
                "*.pyc", ".scratch",
            ),
        )
        # dao_sheng 无外部依赖（pyproject：仅标准库）→ 副本内新建 venv 即可
        # 满足 install 的 Python 探测（不依赖 PATH 上是否有 python）。
        subprocess.run(
            [sys.executable, "-m", "venv", str(self.copy / ".venv")],
            check=True, timeout=300,
        )
        # 外部数据根：位于副本（Git worktree）之外
        self.data_home = self.tmp / "data-home"
        self.env = dict(os.environ)
        self.env["DAO_SHENG_DATA_HOME"] = str(self.data_home)
        self.instance = self.data_home / "instances" / "default"
        self.entry = self.copy / "dao-sheng.ps1"

    def test_install_idempotent_then_role_entries_end_to_end(self):
        # —— install 两次：均 exit 0；不创建任何 inventory 项 ——
        first = _run_entry(["install"], self.instance, entry=self.entry, env=self.env)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertFalse((self.instance / "identity.json").exists())
        self.assertFalse((self.instance / "faculties.json").exists())
        second = _run_entry(["install"], self.instance, entry=self.entry, env=self.env)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertFalse((self.instance / "identity.json").exists())
        self.assertFalse((self.instance / "faculties.json").exists())
        # install-state 写入外部数据根，Git worktree（副本）内不出现
        self.assertTrue((self.data_home / "config" / "install-state.json").is_file())
        self.assertFalse((self.copy / "config" / "install-state.json").exists())

        # —— init-role：设计层初始化（独立入口）——
        proc = _run_entry(
            ["init-role", "-Name", "副本角色", "-Voice", "温和"],
            self.instance, entry=self.entry, env=self.env,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        identity = parse_identity(
            (self.instance / "identity.json").read_text(encoding="utf-8")
        )
        self.assertEqual(identity.name, "副本角色")
        faculties = parse_faculties(
            (self.instance / "faculties.json").read_text(encoding="utf-8")
        )
        self.assertEqual(faculties.roots, FACULTY_ROOTS)

        # —— 真实 composition（无模型：降级装配）——
        assembly = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.instance,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.assertEqual(assembly.identity.name, "副本角色")
        assembly.individual.act(
            Turn(content="副本冒烟回合", memory_origin=MemoryOrigin.EXTERNAL)
        )
        assembly.individual.persist()
        growth = Growth(
            memory=assembly.memory,
            append_continuity=partial(
                append_continuity, assembly.individual_files.continuity
            ),
            reflection_model=_StubReflectionModel(),
            origin=MemoryOrigin, status=MemoryStatus,
            confidence=MemoryConfidence, correction=Correction,
            unavailable=ModelUnavailable,
        )
        (reference,) = growth.import_experience([
            ExperienceCandidate(
                content="副本经历", memory_origin=MemoryOrigin.EXTERNAL,
                idempotency_key="copy-smoke-1",
            )
        ])
        self.assertIsNotNone(growth.reflect(reference))
        assembly.memory.close()
        memory_before = _dir_digest(assembly.individual_files.memory_dir)
        continuity_before = assembly.individual_files.continuity.read_bytes()

        # —— configure-role 修改 → 重新 composition 读取新身份 ——
        proc = _run_entry(
            ["configure-role", "-Name", "副本角色改", "-Voice", "清亮"],
            self.instance, entry=self.entry, env=self.env,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        assembly2 = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=self.instance,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.assertEqual(assembly2.identity.name, "副本角色改")
        self.assertEqual(assembly2.identity.voice, "清亮")
        assembly2.memory.close()

        # —— memory 与 Continuity 逐字节不变 ——
        self.assertEqual(
            _dir_digest(assembly.individual_files.memory_dir), memory_before
        )
        self.assertEqual(
            assembly.individual_files.continuity.read_bytes(), continuity_before
        )
        self.assertEqual([p.name for p in self.instance.glob("*.tmp")], [])


class _ChatCaptureHandler(BaseHTTPRequestHandler):
    """模拟模型服务：记录服务端实际收到的 /api/chat payload（= 传给
    model.chat() 的消息捕获位；wire 形态同 tests/test_model_ollama.py）。"""

    def do_POST(self):
        srv = self.server
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        srv.chat_bodies.append(body)
        payload = {"message": {"content": "chat:" + str(len(body["messages"]))}}
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class RoleChatInjectionTest(_RoleEntryTest):
    """自定义角色注入正式回归（任务项 1-6；项 7「角色更新不改写 Memory 与
    Continuity」已由 RoleCompositionTest ⑦ 完整覆盖，不重复）。

    真实路径：dao-sheng.ps1 init-role / configure-role（CLI 写载体）→
    composition.compose()（ModelConfig 指向本地 mock 模型服务 → 真实
    OllamaModel → 真实 HTTP POST /api/chat）→ Individual.act() → 服务端
    捕获实际消息。全部临时实例根 + 合成角色，绝不触碰 instances/default。
    """

    def setUp(self) -> None:
        super().setUp()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _ChatCaptureHandler)
        self.server.chat_bodies = []
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        # addCleanup LIFO：shutdown 先执行（serve_forever 退出后再关 socket，
        # 避免 Windows 竞态），最后才是 super().setUp 的 tmp.cleanup
        # （先关 memory 连接再删临时目录——_RoleEntryTest 同一纪律）。
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        host, port = self.server.server_address[:2]
        self.endpoint = f"http://{host}:{port}"

    def _compose_with_model(self, root):
        """真实装配：ModelConfig 全字段注入指向 mock 模型服务（R-09 注入面），
        compose() 产出携带真实 OllamaModel 的 RuntimeAssembly。"""
        assembly = composition.compose(
            principles_source_path=PRINCIPLES,
            individual_root=root,
            model_config=composition.ModelConfig(
                agent_endpoint=self.endpoint,
                agent_model="test-model",
                agent_backend="ollama",
                timeout_seconds=5.0,
                retry_limit=0,
            ),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        self.addCleanup(assembly.memory.close)
        return assembly

    def _last_chat_messages(self):
        """mock 模型服务端最近一次 /api/chat 实际收到的 (system, user) 消息。"""
        body = self.server.chat_bodies[-1]
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        return body["messages"][0]["content"], body["messages"][1]["content"]

    def test_cli_role_appears_in_actual_chat_system_message(self):
        """项 1-4：CLI 创建自定义角色经真实 compose()/Individual；model.chat()
        实际收到的 system 消息含姓名 / 声音 / 至少一项行为习惯，且不含任何
        硬编码 DaoSheng 默认人格。"""
        proc = _run_entry(
            ["init-role",
             "-Name", "沈默",
             "-SelfAppellation", "默",
             "-Voice", "沙哑",
             "-VisualImage", "玄衣",
             "-BehavioralHabits", "观察", "克制",
             "-PastExperiences", "独行多年",
             "-ContinuousMemory", "记得雪夜"],
            self.root,
        )
        self._assert_ok(proc)

        assembly = self._compose_with_model(self.root)
        outcome = assembly.individual.act(
            Turn(content="今日檐下听雨", memory_origin=MemoryOrigin.EXTERNAL)
        )
        assembly.individual.persist()
        # 模型已装配 → 非降级回合（行动来自 mock 服务真实回复）
        self.assertIsNotNone(outcome.action)

        system, user = self._last_chat_messages()
        self.assertEqual(user, "今日檐下听雨")
        self.assertIn("姓名：沈默", system)
        self.assertIn("声音：沙哑", system)
        self.assertIn("行为倾向：观察 / 克制", system)  # 至少一项行为习惯（此处两项）
        self.assertNotIn("DaoSheng", system)
        self.assertNotIn("道生", system)
        self._assert_no_tmp_residue()

    def test_two_instance_roots_do_not_cross_inject(self):
        """项 5：两个 InstanceRoot 分别注入不同角色，system 消息互不串用。"""
        proc_a = _run_entry(
            ["init-role", "-Name", "沈默", "-Voice", "沙哑",
             "-BehavioralHabits", "观察"],
            self.root,
        )
        self._assert_ok(proc_a)
        root_b = self.tmp / "instance-b"
        root_b.mkdir()
        proc_b = _run_entry(
            ["init-role", "-Name", "白露", "-Voice", "清越",
             "-BehavioralHabits", "追问"],
            root_b,
        )
        self._assert_ok(proc_b)

        assembly_a = self._compose_with_model(self.root)
        assembly_b = self._compose_with_model(root_b)
        self.assertEqual(assembly_a.identity.name, "沈默")
        self.assertEqual(assembly_b.identity.name, "白露")

        assembly_a.individual.act(
            Turn(content="A 实例回合", memory_origin=MemoryOrigin.EXTERNAL)
        )
        assembly_a.individual.persist()
        system_a, _ = self._last_chat_messages()
        self.assertIn("姓名：沈默", system_a)
        self.assertIn("声音：沙哑", system_a)
        self.assertIn("行为倾向：观察", system_a)
        self.assertNotIn("白露", system_a)
        self.assertNotIn("清越", system_a)
        self.assertNotIn("追问", system_a)

        assembly_b.individual.act(
            Turn(content="B 实例回合", memory_origin=MemoryOrigin.EXTERNAL)
        )
        assembly_b.individual.persist()
        system_b, _ = self._last_chat_messages()
        self.assertIn("姓名：白露", system_b)
        self.assertIn("声音：清越", system_b)
        self.assertIn("行为倾向：追问", system_b)
        self.assertNotIn("沈默", system_b)
        self.assertNotIn("沙哑", system_b)
        self.assertNotIn("观察", system_b)

    def test_configure_role_old_composition_keeps_loaded_identity(self):
        """项 6：configure-role 后旧 composition 保持已加载身份（投影仍用旧
        姓名），新 composition 读取更新后的身份。"""
        proc = _run_entry(
            ["init-role", "-Name", "旧名", "-SelfAppellation", "沉",
             "-Voice", "低缓", "-BehavioralHabits", "静观"],
            self.root,
        )
        self._assert_ok(proc)

        assembly = self._compose_with_model(self.root)
        assembly.individual.act(
            Turn(content="第一回合", memory_origin=MemoryOrigin.EXTERNAL)
        )
        assembly.individual.persist()
        system, _ = self._last_chat_messages()
        self.assertIn("姓名：旧名", system)

        proc2 = _run_entry(["configure-role", "-Name", "新名"], self.root)
        self._assert_ok(proc2)

        # 旧 composition（identity 构造时注入）→ 投影仍用旧姓名
        assembly.individual.act(
            Turn(content="第二回合", memory_origin=MemoryOrigin.EXTERNAL)
        )
        assembly.individual.persist()
        system_old, _ = self._last_chat_messages()
        self.assertIn("姓名：旧名", system_old)
        self.assertNotIn("新名", system_old)

        # 新 composition → 读取更新后的身份
        assembly2 = self._compose_with_model(self.root)
        self.assertEqual(assembly2.identity.name, "新名")
        assembly2.individual.act(
            Turn(content="第三回合", memory_origin=MemoryOrigin.EXTERNAL)
        )
        assembly2.individual.persist()
        system_new, _ = self._last_chat_messages()
        self.assertIn("姓名：新名", system_new)
        self.assertNotIn("旧名", system_new)
        self._assert_no_tmp_residue()


if __name__ == "__main__":
    unittest.main()
