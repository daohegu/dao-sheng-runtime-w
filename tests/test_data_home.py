"""外部数据根专项测试（Git 升级安全修复；全部临时目录 + 合成数据）。

覆盖（任务规格 §四 六项 + 迁移安全语义）：
  ① PS CLI 与 Python Runtime 默认数据根解析一致
  ② DAO_SHENG_DATA_HOME 覆盖（绝对 / 相对）两侧解析一致
  ③ 角色（identity/faculties）、Continuity、Memory、Capability 记录、
     install-state 全部写入外部数据根（Git worktree 之外）
  ④ 位于 worktree 内的数据根 / 显式 -InstanceRoot 被拒绝（PS exit 1 +
     [FAIL]；Python fail-loud RuntimeError）
  ⑤ 临时 Git 仓库模拟源码升级：上游开始跟踪旧个人数据路径时，
     git pull 退出 0 覆盖 worktree 文件，但外部数据根哨兵字节级不变；
     跟踪守卫对被跟踪路径返回失败
  ⑥ 跟踪守卫在临时仓库检测被强制跟踪的个人数据路径并使检查失败
     （完整守卫矩阵见 tests/test_repo_tracking_guard.py）
  迁移安全：无遗留 → 明确报告无需迁移（不创建空白实例）；遗留 → 目标
  逐文件 SHA-256 一致后删除源；目标已存在 → 拒绝覆盖、源与目标均不变；
  重复执行幂等；Python 入口对遗留数据 fail-loud（绝不静默启动空白实例）。
  迁移中途失败（受控故障注入 = 目标目录 Deny ACE → Copy-Item 被拒）：
  未迁移源完好留原位、已迁移文件留数据根、无 partial 残留、install 与
  Python 入口均拒绝静默空白启动、故障移除后重跑安全续迁且哈希逐项一致
  （MigrateDataMidFailureTest）。

测试纪律：绝不触碰真实实例 / 真实 Hermes 数据 / 真实用户数据根的写入；
① 的 PS 侧为只读 status（不写任何文件）。需要 install 的测试在仓库临时
副本 + 副本内独立 venv 上进行。Git 模拟全部在临时目录。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from functools import partial
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRY = REPO_ROOT / "dao-sheng.ps1"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
DATA_HOME_ENV = "DAO_SHENG_DATA_HOME"

sys.path.insert(0, str(REPO_ROOT))
import run_dao_sheng  # noqa: E402

from dao_sheng import composition  # noqa: E402
from dao_sheng.continuity import append_continuity  # noqa: E402
from dao_sheng.faculties import FACULTY_ROOTS, parse_faculties  # noqa: E402
from dao_sheng.growth import ExperienceCandidate, Growth  # noqa: E402
from dao_sheng.identity import parse_identity  # noqa: E402
from dao_sheng.individual import Turn  # noqa: E402
from dao_sheng.memory import (  # noqa: E402
    Correction,
    MemoryConfidence,
    MemoryOrigin,
    MemoryStatus,
)
from dao_sheng.model import ModelUnavailable  # noqa: E402

_guard_spec = importlib.util.spec_from_file_location(
    "repo_tracking_guard", REPO_ROOT / "tools" / "repo_tracking_guard.py"
)
guard = importlib.util.module_from_spec(_guard_spec)
assert _guard_spec.loader is not None
_guard_spec.loader.exec_module(guard)

GIT = shutil.which("git")


def _env(**overrides) -> dict[str, str]:
    """os.environ 完整副本 + 覆盖（值为 None 表示删除该变量）。"""
    env = dict(os.environ)
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def _run_ps(args, cwd=None, env=None, stdin_text="", entry=ENTRY):
    """真实调用 dao-sheng.ps1 子进程。stdout 中 CJK 可能因控制台代码页
    失真——断言只依赖 ASCII 标记（[OK]/[FAIL]）、ASCII 标签行与载体文件。"""
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(entry), *args],
        cwd=str(cwd) if cwd is not None else None,
        env=env, input=stdin_text,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300,
    )


def _parse_data_home(stdout: str) -> str:
    match = re.search(r"^data home\s*:\s*(.+?)\s*$", stdout, re.MULTILINE)
    assert match is not None, f"status 输出缺少 'data home :' 行:\n{stdout}"
    return match.group(1)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_repo(dest: Path, *, with_venv: bool) -> None:
    shutil.copytree(
        REPO_ROOT, dest,
        ignore=shutil.ignore_patterns(
            ".venv", "instances", "config", "log", "__pycache__", ".git",
            "*.pyc", ".scratch",
        ),
    )
    if with_venv:
        subprocess.run(
            [sys.executable, "-m", "venv", str(dest / ".venv")],
            check=True, timeout=600,
        )


class _StubReflectionModel:
    """测试 stub：使 Growth.reflect 真实追加 Continuity（同 test_role_init
    先例——growth 降级规则的反面）。"""

    def chat(self, messages):
        return "stub reflection output for data-home test"


class DefaultDataHomeParityTest(unittest.TestCase):
    """①：默认数据根——PS 与 Python 解析一致（PS 侧只读 status）。"""

    def test_default_data_home_parity(self) -> None:
        env = _env(**{DATA_HOME_ENV: None})
        proc = _run_ps(["status"], env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ps_home = _parse_data_home(proc.stdout)

        py_home = run_dao_sheng.resolve_data_home(env=env)
        self.assertEqual(
            os.path.normcase(ps_home), os.path.normcase(str(py_home)),
            "PS 与 Python 默认数据根解析不一致",
        )
        # 默认数据根必须位于仓库 worktree 之外
        self.assertFalse(run_dao_sheng._is_inside_repo(py_home, REPO_ROOT))
        # 默认值 = %LOCALAPPDATA%\DaoSheng（Windows）
        localappdata = env.get("LOCALAPPDATA", "")
        if localappdata:
            self.assertEqual(
                os.path.normcase(str(py_home)),
                os.path.normcase(os.path.join(localappdata, "DaoSheng")),
            )


class OverrideParityTest(unittest.TestCase):
    """②：DAO_SHENG_DATA_HOME 覆盖——绝对 / 相对路径两侧解析一致。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_absolute_override_parity(self) -> None:
        home = self.tmp / "dh-abs"
        env = _env(**{DATA_HOME_ENV: str(home)})
        proc = _run_ps(["status"], env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ps_home = _parse_data_home(proc.stdout)
        py_home = run_dao_sheng.resolve_data_home(env=env)
        self.assertEqual(os.path.normcase(ps_home), os.path.normcase(str(py_home)))
        self.assertEqual(os.path.normcase(str(py_home)), os.path.normcase(str(home)))

    def test_relative_override_parity_cross_process(self) -> None:
        """相对覆盖值：PS 按当前工作目录解析；Python 经独立子进程
        （chdir 到同一临时目录）解析——跨进程一致。"""
        proc = _run_ps(
            ["status"], cwd=self.tmp, env=_env(**{DATA_HOME_ENV: "dh-rel"}),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ps_home = _parse_data_home(proc.stdout)

        code = (
            "import sys, os; "
            f"sys.path.insert(0, {str(REPO_ROOT)!r}); "
            f"os.chdir({str(self.tmp)!r}); "
            "import run_dao_sheng; print(run_dao_sheng.resolve_data_home())"
        )
        sub = subprocess.run(
            [sys.executable, "-c", code],
            env=_env(**{DATA_HOME_ENV: "dh-rel"}),
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        self.assertEqual(sub.returncode, 0, sub.stdout + sub.stderr)
        py_home = sub.stdout.strip()
        self.assertEqual(os.path.normcase(ps_home), os.path.normcase(py_home))
        self.assertEqual(
            os.path.normcase(py_home),
            os.path.normcase(str(self.tmp / "dh-rel")),
        )


class RejectionTest(unittest.TestCase):
    """④：worktree 内的数据根 / InstanceRoot 被拒绝（PS + Python）。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_ps_rejects_instance_root_inside_repo(self) -> None:
        inside = REPO_ROOT / "instances" / "default"
        proc = _run_ps(["status", "-InstanceRoot", str(inside)])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("[FAIL] instance root", proc.stdout + proc.stderr)

        inside2 = REPO_ROOT / "config" / "nested"
        proc2 = _run_ps(["doctor", "-InstanceRoot", str(inside2)])
        self.assertEqual(proc2.returncode, 1)
        self.assertIn("[FAIL] instance root", proc2.stdout + proc2.stderr)

    def test_ps_rejects_data_home_inside_repo(self) -> None:
        env = _env(**{DATA_HOME_ENV: str(REPO_ROOT / "data-home-inside")})
        proc = _run_ps(["status"], env=env)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("[FAIL] data home", proc.stdout + proc.stderr)

    def test_python_rejects_data_home_inside_repo(self) -> None:
        with self.assertRaises(RuntimeError):
            run_dao_sheng.resolve_data_home(
                env={DATA_HOME_ENV: str(REPO_ROOT / "dh-inside")},
                repo_root=REPO_ROOT,
            )

    def test_python_rejects_recorded_instance_root_inside_repo(self) -> None:
        fake_repo = self.tmp / "repo"
        fake_repo.mkdir()
        data_home = self.tmp / "data-home"
        state_dir = data_home / "config"
        state_dir.mkdir(parents=True)
        (state_dir / "install-state.json").write_text(
            json.dumps({"instance_root": str(fake_repo / "instances" / "default")}),
            encoding="utf-8",
        )
        with self.assertRaises(RuntimeError) as ctx:
            run_dao_sheng.load_instance_root(data_home, repo_root=fake_repo)
        self.assertIn("migrate-data", str(ctx.exception))


class LegacyFailLoudTest(unittest.TestCase):
    """迁移/兼容边界：Python 入口对遗留数据 fail-loud，绝不静默空白实例。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.data_home = self.tmp / "data-home"

    def test_missing_state_with_legacy_data_points_to_migrate_data(self) -> None:
        legacy = self.repo / "instances" / "default"
        legacy.mkdir(parents=True)
        (legacy / "identity.json").write_text(
            json.dumps({"name": "synthetic-legacy"}), encoding="utf-8"
        )
        with self.assertRaises(RuntimeError) as ctx:
            run_dao_sheng.load_instance_root(self.data_home, repo_root=self.repo)
        message = str(ctx.exception)
        self.assertIn("migrate-data", message)
        self.assertIn("空白实例", message)
        # 只读检测：遗留数据不被覆盖 / 删除 / 自动重置
        self.assertTrue((legacy / "identity.json").is_file())
        self.assertFalse(self.data_home.exists())

    def test_missing_state_without_legacy_points_to_install(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            run_dao_sheng.load_instance_root(self.data_home, repo_root=self.repo)
        self.assertIn("install", str(ctx.exception))


class MigrateDataSafetyTest(unittest.TestCase):
    """迁移安全语义（临时仓库副本 + 合成数据，逐文件 SHA-256）：
    无遗留 → 无需迁移；遗留 → 哈希一致后移动；目标已存在 → 拒绝覆盖；
    重复执行 → 幂等。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.copy = cls.tmp / "repo-copy"
        _copy_repo(cls.copy, with_venv=False)  # migrate-data 不探测 Python
        cls.entry = cls.copy / "dao-sheng.ps1"
        cls.data_home = cls.tmp / "data-home"
        cls.env = _env(**{DATA_HOME_ENV: str(cls.data_home)})

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _migrate(self):
        return _run_ps(["migrate-data"], env=self.env, entry=self.entry)

    def test_a_no_legacy_reports_nothing_to_migrate(self) -> None:
        proc = self._migrate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("no legacy personal data", proc.stdout)
        self.assertIn("nothing to migrate", proc.stdout)
        # 不得创建空白实例冒充迁移成功
        self.assertFalse((self.data_home / "instances").exists())
        self.assertFalse((self.data_home / "instances" / "default").exists())

    def test_b_legacy_moved_with_sha256_match(self) -> None:
        legacy_files = {
            Path("instances/default/identity.json"):
                json.dumps({"name": "synthetic-legacy-role"}),
            Path("instances/default/faculties.json"):
                json.dumps({"roots": list(FACULTY_ROOTS)}),
            Path("instances/default/continuity.jsonl"):
                json.dumps({"event": "synthetic-legacy"}) + "\n",
            Path("instances/default/memory/memory.db"):
                "SYNTHETIC-SQLITE-PLACEHOLDER-BYTES",
            Path("instances/default/capabilities/proposed/cap.json"):
                json.dumps(
                    {"name": "cap", "content": "x", "source_reference": "ref"}
                ),
            Path("config/install-state.json"):
                json.dumps(
                    {
                        "instance_root": str(self.copy / "instances" / "default"),
                        "python": "3.12",
                    }
                ),
            Path("log/runtime.log"): "synthetic legacy log line\n",
        }
        before: dict[Path, str] = {}
        for rel, content in legacy_files.items():
            path = self.copy / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            before[rel] = _sha256(path)

        proc = self._migrate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[OK]", proc.stdout)

        # install-state.json 是唯一被有意改写的文件（instance_root 键重写，
        # 见 dao-sheng.ps1 fix-up 段）；其余个人数据载体必须逐字节一致。
        state_rel = Path("config/install-state.json")
        for rel, expected_hash in before.items():
            dest = self.data_home / rel
            self.assertTrue(dest.is_file(), f"未迁移: {rel}")
            if rel != state_rel:
                self.assertEqual(
                    _sha256(dest), expected_hash, f"SHA-256 不一致: {rel}"
                )
            self.assertFalse((self.copy / rel).exists(), f"源未删除: {rel}")

        # install-state：除 instance_root 外的键原样保留；instance_root 由
        # 仓库内路径重写为数据根路径
        state = json.loads(
            (self.data_home / "config" / "install-state.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            os.path.normcase(state["instance_root"]),
            os.path.normcase(str(self.data_home / "instances" / "default")),
        )
        self.assertEqual(state["python"], "3.12")
        self.assertIn("instance_root updated", proc.stdout)

    def test_c_existing_target_refuses_overwrite_both_sides_unchanged(self) -> None:
        src = self.copy / "instances" / "default" / "identity.json"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(
            json.dumps({"name": "synthetic-CONFLICTING-new-legacy"}), encoding="utf-8"
        )
        src_hash_before = _sha256(src)
        dst = self.data_home / "instances" / "default" / "identity.json"
        dst_hash_before = _sha256(dst)
        self.assertNotEqual(src_hash_before, dst_hash_before)

        proc = self._migrate()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("[FAIL] migrate-data", proc.stdout)
        self.assertIn("target(s) already present", proc.stdout)
        self.assertIn("nothing was copied", proc.stdout)
        # 源与目标均保持不变
        self.assertEqual(_sha256(src), src_hash_before)
        self.assertEqual(_sha256(dst), dst_hash_before)

        # 清理本轮合成冲突源，使后续幂等检查针对真实剩余状态
        src.unlink()

    def test_d_rerun_is_idempotent(self) -> None:
        home_files = sorted(
            p for p in self.data_home.rglob("*") if p.is_file()
        )
        hashes_before = {p.relative_to(self.data_home): _sha256(p) for p in home_files}
        self.assertTrue(hashes_before, "数据根应已有 test_b 迁移后的文件")

        proc = self._migrate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("nothing to migrate", proc.stdout)

        home_files_after = sorted(
            p for p in self.data_home.rglob("*") if p.is_file()
        )
        hashes_after = {
            p.relative_to(self.data_home): _sha256(p) for p in home_files_after
        }
        self.assertEqual(hashes_before, hashes_after, "重复执行改变了数据根内容")


class MigrateDataMidFailureTest(unittest.TestCase):
    """迁移中途失败的受控故障注入（目标 memory 目录 Deny ACE →
    Copy-Item 创建 memory.db 被拒 → EAP Stop → Fail-Step "migrate-data
    copy"）。

    验证的安全不变量（每个遗留文件在失败时刻必须恰好处于两种状态之一：
    已迁移 = 数据根字节一致且源已删；未迁移 = 源字节一致且目标无残留）：
    未迁移数据安全留源位置；已迁移文件留数据根不丢；无 partial 残留；
    不静默启动空白新实例（install 拒绝 + Python 入口 fail-loud）；故障
    移除后重跑安全续迁剩余内容，关键角色 / Memory / Continuity /
    install-state 哈希与预期一致。

    最小 fake repo（仅 dao-sheng.ps1）：migrate-data 不探测 Python；
    install 的第 0 步遗留检测先于 OS / Python 探测 → 无需 pyproject.toml
    / venv。故障注入与全部写入只发生在临时目录，绝不触碰真实实例。
    """

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)  # LIFO：先注册 → 最后执行（ACL 移除之后）
        self.tmp = Path(tmp.name)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        shutil.copy2(ENTRY, self.repo / "dao-sheng.ps1")
        self.entry = self.repo / "dao-sheng.ps1"
        self.data_home = self.tmp / "data-home"
        self.env = _env(**{DATA_HOME_ENV: str(self.data_home)})

        legacy_files = {
            Path("instances/default/continuity.jsonl"):
                json.dumps(
                    {"content": "pre-migration experience", "reference": "ref-mid-1"}
                ) + "\n",
            Path("instances/default/faculties.json"):
                json.dumps({"roots": list(FACULTY_ROOTS)}),
            Path("instances/default/identity.json"):
                json.dumps(
                    {
                        "name": "mid-failure-role",
                        "self_appellation": "合成",
                        "voice": "低沉",
                        "visual_image": "青衫",
                        "behavioral_habits": ["谨慎"],
                        "past_experiences": [],
                        "continuous_memory": [],
                    },
                    ensure_ascii=False,
                ),
            Path("instances/default/memory/memory.db"):
                "SYNTHETIC-SQLITE-PLACEHOLDER-BYTES",
            Path("config/install-state.json"):
                json.dumps(
                    {
                        "instance_root": str(self.repo / "instances" / "default"),
                        "python": "3.12",
                        "installed_by": "mid-failure-test",
                    }
                ),
            Path("log/runtime.log"): "synthetic pre-migration log line\n",
        }
        self.expected: dict[Path, str] = {}
        for rel, content in legacy_files.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            self.expected[rel] = _sha256(path)

        # 故障注入点：预创建数据根的 memory 目标目录并加 Deny ACE。
        # Phase 1 碰撞预检不触发（Test-Path 目标文件为 False）；Phase 2
        # 跳过 New-Item，Copy-Item 在目录内创建 memory.db 被拒。
        self.blocked_dir = self.data_home / "instances" / "default" / "memory"
        self.blocked_dir.mkdir(parents=True)
        # LIFO：后注册 → 先执行（Deny 移除先于临时目录删除）
        self.addCleanup(self._acl, self.blocked_dir, "remove")

    def _acl(self, directory: Path, action: str) -> None:
        """目录上加 / 删 Deny ACE（CreateFiles,WriteData,AppendData）。
        只拒绝创建与写入子文件，保留 WRITE_DAC / DELETE → 清理始终能
        移除 ACE 并删除目录。"""
        verb = (
            "$acl.AddAccessRule($rule)" if action == "deny"
            else "$acl.RemoveAccessRuleAll($rule)"
        )
        script = (
            "$ErrorActionPreference = 'Stop'; "
            f"$path = '{directory}'; "
            "$acl = Get-Acl -LiteralPath $path; "
            "$who = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name; "
            "$rule = New-Object "
            "System.Security.AccessControl.FileSystemAccessRule("
            "$who, 'CreateFiles,WriteData,AppendData', "
            "'ContainerInherit,ObjectInherit', 'None', 'Deny'); "
            + verb + "; "
            "Set-Acl -LiteralPath $path -AclObject $acl"
        )
        proc = subprocess.run(
            [POWERSHELL, "-NoProfile", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"ACL {action} failed on {directory}:\n{proc.stdout}\n{proc.stderr}"
            )

    def _migrate(self):
        return _run_ps(["migrate-data"], env=self.env, entry=self.entry)

    def _digest(self, root: Path) -> dict[Path, str]:
        return {
            p.relative_to(root): _sha256(p)
            for p in sorted(root.rglob("*")) if p.is_file()
        }

    def test_mid_run_copy_failure_then_safe_resume(self):
        """中途失败 → 续迁：失败提示明确可恢复；每个遗留文件要么已迁移
        （数据根哈希一致 + 源已删）要么未迁移（源哈希一致 + 目标无
        partial）；移除故障后重跑完成剩余迁移，第三次幂等。"""
        self._acl(self.blocked_dir, "deny")
        proc = self._migrate()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("[FAIL] migrate-data copy", proc.stdout)
        self.assertIn("copy failed for:", proc.stdout)
        self.assertIn("memory.db", proc.stdout)
        self.assertIn("kept in place", proc.stdout)
        self.assertIn("re-run migrate-data", proc.stdout)

        # 不变量：每个遗留文件恰好处于"已迁移"或"未迁移"之一，字节一致
        migrated_any = False
        for rel, expected_hash in self.expected.items():
            src = self.repo / rel
            dst = self.data_home / rel
            src_ok = src.is_file() and _sha256(src) == expected_hash
            dst_ok = dst.is_file() and _sha256(dst) == expected_hash
            self.assertNotEqual(
                src_ok, dst_ok,
                f"{rel} 状态异常（src_ok={src_ok} dst_ok={dst_ok}）："
                "文件丢失、重复或 partial 残留",
            )
            if dst_ok:
                migrated_any = True
        self.assertTrue(migrated_any, "失败前应已有文件成功迁移（部分进度必须保留）")

        # 失败点本身：memory.db 完好留在源位置，目标无 partial 残留
        src_mem = self.repo / "instances/default/memory/memory.db"
        self.assertTrue(src_mem.is_file(), "copy 失败后 memory.db 仍被移动")
        self.assertEqual(
            _sha256(src_mem), self.expected[Path("instances/default/memory/memory.db")]
        )
        self.assertFalse(
            (self.data_home / "instances/default/memory/memory.db").exists(),
            "目标留下 partial 残留",
        )
        # install-state fix-up 只在全循环完成后运行 → 中途失败不得写数据根 config
        self.assertFalse((self.data_home / "config" / "install-state.json").exists())

        # 移除故障 → 重跑安全续迁剩余内容
        self._acl(self.blocked_dir, "remove")
        proc2 = self._migrate()
        self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)
        self.assertIn("migrate-data complete", proc2.stdout)

        dest_mem = self.data_home / "instances/default/memory/memory.db"
        self.assertTrue(dest_mem.is_file(), "续迁后 memory.db 未迁入数据根")
        self.assertEqual(
            _sha256(dest_mem), self.expected[Path("instances/default/memory/memory.db")]
        )
        self.assertFalse(src_mem.exists(), "续迁后 memory.db 源未删除")
        self.assertEqual(
            _sha256(self.data_home / "log/runtime.log"),
            self.expected[Path("log/runtime.log")],
        )
        self.assertFalse((self.repo / "log/runtime.log").exists())

        # install-state：迁入后 fix-up 仅重写 instance_root 键（仓库内路径 →
        # 数据根路径），其余键原样保留
        state = json.loads(
            (self.data_home / "config" / "install-state.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            os.path.normcase(state["instance_root"]),
            os.path.normcase(str(self.data_home / "instances" / "default")),
        )
        self.assertEqual(state["python"], "3.12")
        self.assertEqual(state["installed_by"], "mid-failure-test")
        self.assertIn("instance_root updated", proc2.stdout)

        # 已迁移文件跨续迁字节不变
        for rel, expected_hash in self.expected.items():
            if rel == Path("config/install-state.json"):
                continue  # 唯一被有意改写的文件（instance_root 键）
            self.assertEqual(
                _sha256(self.data_home / rel), expected_hash,
                f"跨续迁字节变化: {rel}",
            )

        # 第三次执行：已完成部分被安全识别 → 明确 nothing to migrate
        proc3 = self._migrate()
        self.assertEqual(proc3.returncode, 0, proc3.stdout + proc3.stderr)
        self.assertIn("nothing to migrate", proc3.stdout)

    def test_partial_failure_refuses_blank_instance_start(self):
        """中途失败后不得静默启动空白新实例：install 拒绝（遗留数据仍在
        仓库内）且不写任何字节；Python 入口 fail-loud 指向 migrate-data。"""
        self._acl(self.blocked_dir, "deny")
        proc = self._migrate()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("[FAIL] migrate-data copy", proc.stdout)

        home_before = self._digest(self.data_home)
        repo_before = self._digest(self.repo)
        self.assertTrue(home_before, "部分迁移应在数据根留下已迁移文件")

        proc2 = _run_ps(["install"], env=self.env, entry=self.entry)
        self.assertEqual(proc2.returncode, 1, proc2.stdout + proc2.stderr)
        self.assertIn("[FAIL] legacy personal data in repository", proc2.stdout)

        # install 拒绝不写任何文件：数据根与仓库字节级不变
        self.assertEqual(self._digest(self.data_home), home_before,
                         "install 拒绝改写了数据根")
        self.assertEqual(self._digest(self.repo), repo_before,
                         "install 拒绝改写了仓库")
        self.assertFalse((self.data_home / "config" / "install-state.json").exists())

        # Python 入口 fail-loud：绝不静默在新数据根启动空白实例
        with self.assertRaises(RuntimeError) as ctx:
            run_dao_sheng.load_instance_root(self.data_home, repo_root=self.repo)
        self.assertIn("migrate-data", str(ctx.exception))

        # 未迁移的 memory.db 仍完好留在源位置
        src_mem = self.repo / "instances/default/memory/memory.db"
        self.assertTrue(src_mem.is_file())
        self.assertEqual(
            _sha256(src_mem), self.expected[Path("instances/default/memory/memory.db")]
        )


class ExternalDataHomeEndToEndTest(unittest.TestCase):
    """③：install / init-role / Runtime 写入全部落在外部数据根。
    仓库临时副本 + 副本内独立 venv；真实仓库不被写入。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.copy = cls.tmp / "repo-copy"
        _copy_repo(cls.copy, with_venv=True)
        cls.entry = cls.copy / "dao-sheng.ps1"
        cls.data_home = cls.tmp / "data-home"
        cls.env = _env(**{DATA_HOME_ENV: str(cls.data_home)})
        install = _run_ps(["install"], cwd=cls.copy, env=cls.env, entry=cls.entry)
        if install.returncode != 0:
            raise AssertionError(install.stdout + install.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_install_state_lives_in_data_home_not_worktree(self) -> None:
        state = self.data_home / "config" / "install-state.json"
        self.assertTrue(state.is_file())
        self.assertFalse((self.copy / "config" / "install-state.json").exists())
        doc = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(
            os.path.normcase(doc["instance_root"]),
            os.path.normcase(str(self.data_home / "instances" / "default")),
        )

    def test_all_personal_data_carriers_written_outside_worktree(self) -> None:
        proc = _run_ps(
            ["init-role", "-Name", "DataHomeRole", "-Voice", "calm"],
            cwd=self.copy, env=self.env, entry=self.entry,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        instance_root = self.data_home / "instances" / "default"
        identity = parse_identity(
            (instance_root / "identity.json").read_text(encoding="utf-8")
        )
        self.assertEqual(identity.name, "DataHomeRole")
        faculties = parse_faculties(
            (instance_root / "faculties.json").read_text(encoding="utf-8")
        )
        self.assertEqual(faculties.roots, FACULTY_ROOTS)

        # 真实 composition + 回合 + 成长（stub reflection 追加 Continuity）
        # + capability propose —— 全部经数据根实例根
        assembly = composition.compose(
            principles_source_path=self.copy / "docs" / "constitution" / "principles.md",
            individual_root=instance_root,
            model_config=composition.ModelConfig(),
            operational_defaults=composition.OperationalDefaults(),
            host_config=composition.HostConfig(),
        )
        try:
            assembly.individual.act(
                Turn(content="data-home smoke turn", memory_origin=MemoryOrigin.EXTERNAL)
            )
            turn_reference = assembly.individual.persist()

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
            (experience_reference,) = growth.import_experience([
                ExperienceCandidate(
                    content="data-home experience",
                    memory_origin=MemoryOrigin.EXTERNAL,
                    idempotency_key="data-home-smoke-1",
                )
            ])
            self.assertIsNotNone(growth.reflect(experience_reference))

            self.assertIsNotNone(
                assembly.capability_manager.propose("test-cap", turn_reference)
            )
        finally:
            assembly.memory.close()

        files = assembly.individual_files
        # 5 项个体载体 + install-state 全部位于数据根之下
        for path in (
            files.identity, files.faculties, files.continuity,
            files.memory_dir / "memory.db",
            files.capabilities_dir / "proposed" / "test-cap.json",
        ):
            self.assertTrue(path.is_file(), f"载体缺失: {path.relative_to(self.data_home)}")
            self.assertTrue(
                run_dao_sheng._is_inside_repo(path, self.data_home),
                f"载体不在数据根内: {path}",
            )
            self.assertFalse(
                run_dao_sheng._is_inside_repo(path, self.copy),
                f"载体落在 Git worktree 内: {path}",
            )
        # worktree 内不得出现任何个人数据文件
        legacy_in_copy = run_dao_sheng.find_legacy_repo_data(self.copy)
        self.assertEqual(legacy_in_copy, [], f"副本 worktree 内出现个人数据: {legacy_in_copy}")


@unittest.skipIf(GIT is None, "git executable not available")
class GitPullSimulationTest(unittest.TestCase):
    """⑤+⑥：临时 Git 仓库模拟源码升级——上游开始跟踪旧个人数据路径时
    git pull 覆盖 worktree 文件（exit 0），但外部数据根哨兵字节级不变；
    守卫对被跟踪路径返回失败。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.git_env = _env(
            **{
                "GIT_AUTHOR_NAME": "sim", "GIT_AUTHOR_EMAIL": "sim@example.com",
                "GIT_COMMITTER_NAME": "sim", "GIT_COMMITTER_EMAIL": "sim@example.com",
            }
        )

    def _git(self, *args, cwd: Path) -> None:
        subprocess.run(
            ["git", *args], cwd=str(cwd), env=self.git_env,
            capture_output=True, text=True, check=True, timeout=120,
        )

    def test_upstream_tracking_same_path_cannot_touch_external_data(self) -> None:
        upstream = self.tmp / "upstream"
        upstream.mkdir()
        self._git("init", "-q", cwd=upstream)
        # 初始上游：只有源码，无个人数据路径
        (upstream / "app.py").write_text("VERSION = 1\n", encoding="utf-8")
        self._git("add", "app.py", cwd=upstream)
        self._git("commit", "-q", "-m", "v1 source only", cwd=upstream)

        work = self.tmp / "work"
        self._git("clone", "-q", str(upstream), str(work), cwd=self.tmp)
        # 干净仓库：守卫通过
        self.assertEqual(guard.main(["--repo", str(work)]), 0)

        # 外部数据根：合成个人数据哨兵
        data_home = self.tmp / "data-home"
        personal = data_home / "instances" / "default"
        personal.mkdir(parents=True)
        sentinel = personal / "identity.json"
        sentinel.write_text(
            json.dumps({"name": "MY-PERSONAL-ROLE", "voice": "mine"}), encoding="utf-8"
        )
        memory = personal / "memory" / "memory.db"
        memory.parent.mkdir(parents=True)
        memory.write_text("MY-PERSONAL-MEMORY-BYTES", encoding="utf-8")
        sentinel_hash_before = _sha256(sentinel)
        memory_hash_before = _sha256(memory)

        # 上游开始跟踪旧个人数据路径 + 正常源码更新
        tracked = upstream / "instances" / "default"
        tracked.mkdir(parents=True)
        (tracked / "identity.json").write_text(
            json.dumps({"name": "UPSTREAM-PLACEHOLDER"}), encoding="utf-8"
        )
        (upstream / "app.py").write_text("VERSION = 2\n", encoding="utf-8")
        self._git("add", "-A", cwd=upstream)
        self._git("commit", "-q", "-m", "upstream starts tracking identity path", cwd=upstream)

        # 普通源码升级：git pull 退出 0（worktree 内同名文件被上游覆盖——
        # 这正是危险本身；外部数据根必须毫发无损）
        pull = subprocess.run(
            ["git", "pull", "-q"], cwd=str(work), env=self.git_env,
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(pull.returncode, 0, pull.stdout + pull.stderr)
        worktree_copy = work / "instances" / "default" / "identity.json"
        self.assertTrue(worktree_copy.is_file())
        self.assertIn("UPSTREAM-PLACEHOLDER", worktree_copy.read_text(encoding="utf-8"))

        # 外部哨兵字节级不变
        self.assertEqual(_sha256(sentinel), sentinel_hash_before)
        self.assertEqual(_sha256(memory), memory_hash_before)

        # 守卫必须对工作仓库的跟踪状态返回失败
        self.assertEqual(guard.main(["--repo", str(work)]), 1)


if __name__ == "__main__":
    unittest.main()
