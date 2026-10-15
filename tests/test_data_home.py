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
  Windows 8.3 短路径回归（ShortPathParityTest）：同一实际位置的短名 /
  长名文本表示两侧解析一致（PS GetFullPath 展开已存在组件的短名；
  Python _expand_short_names 经 GetLongPathNameW 对齐），仓库内拒绝跨
  表示一致生效，junction 不被解析。
  GetLongPathNameW 错误码分类回归（LongPathNameErrorTest）：仅本机实测
  确认的「组件不存在」码 2 / 3 允许向上回退；权限拒绝（5，经 fake API
  注入错误码模拟）与语法非法 123 及意外码一律 fail-loud OSError；回退
  到达根（盘符根 / UNC 共享根）仍无法验证根存在（不存在盘符的盘符根实测
  3）时 fail-loud，不把根不可用当成正常缺失。盘符根边界（DriveRootBoundaryTest）：盘符根仓库
  的仓库内判定正确（直接子路径不漏判），不同盘符路径互不误判。
  短名组件 + 不存在叶子分歧安全回归（ShortPathDivergenceSafetyTest）：
  PS 5.1 GetFullPath 对该形状的输出受同进程调用顺序影响，文本 parity
  不宣称；保证的是两侧「仓库内」判定一致——仓库内被拒（PS exit 1 +
  [FAIL] data home；Python RuntimeError），仓库外被正常接受且不存在
  叶子逐字保留（dao-sheng.ps1 经 Get-CanonicalPathForComparison 做与
  Python 相同的 walk-up 规范化）。
  PS 存在性探针 seam 回归（PsProbeSeamTest）：dao-sheng.ps1 的 walk-up 只
  回退 Test-PathExistsForComparison 判定为「确定不存在」（FNFE/DNFE）的
  组件；访问拒绝 / 意外 IO 错误 / 不可用驱动器或不可达 UNC 根 fail-loud，
  绝不当成不存在。测试经 DAO_SHENG_PS_LIB_ONLY=1 加载并直接调用生产
  helper，分两类证据：seam 注入（$DaoShengPathExistsProbe 模拟错误形状——
  缺失回退逐字保留 / 中途访问拒绝停止 / 叶子 IO 错误停止 / 驱动器根错误
  停止 / 根始终缺失停止）是模拟错误注入测试，不是真实 ACL 集成测试；真实
  Set-Acl Deny ACE（生产探针真实命中被拒路径，helper 级与中央守卫端到端
  各一条）是真实 ACL 集成测试。跨运行时统一根判定（本轮修复）：两侧
  walk-up 只越过「确定不存在」的组件，回退到达根而根仍报告缺失时一律
  fail-loud，不再原样返回——Python 侧不存在盘符（根实测 3）此前保持原
  样，现抛 OSError；PS 侧此前对不存在盘符逐字保留，现抛
  InvalidOperationException。不可用 UNC 根实测：Python 不可达主机 53、可
  达主机缺失共享 67、裸服务器名 161（均不属 2 / 3，本就 fail-loud）；PS
  对应形状 IOException / ArgumentException（本就 fail-loud）。本机没有可
  用的真实不可达 UNC 服务器：UNC 分类经 seam 注入验证，另以本机回环
  （127.0.0.1 上必然不存在的共享名）做 OS 级真实分类测试——两者都不是
  真实网络 / 远程 UNC 服务器集成测试。

测试纪律：绝不触碰真实实例 / 真实 Hermes 数据 / 真实用户数据根的写入；
① 的 PS 侧为只读 status（不写任何文件）。需要 install 的测试在仓库临时
副本 + 副本内独立 venv 上进行。Git 模拟全部在临时目录。直接启动
powershell.exe（5.1）的子进程统一经 _ps_safe_env / _strip_psmodulepath
去除复制环境中的 PSModulePath（Windows workflow 默认 PS7，Python 继承
其 PSModulePath 会使 5.1 错误发现 PS7 模块并加载失败；不修改
os.environ / 调用者 env / 机器与用户级变量）。
"""

from __future__ import annotations

import ctypes
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
from ctypes import wintypes
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


def _strip_psmodulepath(env: dict[str, str]) -> dict[str, str]:
    """返回移除 PSModulePath（按变量名不区分大小写）后的 env 副本。

    Windows workflow 默认 shell 是 PowerShell 7；Python 子进程继承 PS7 的
    PSModulePath，随后其启动 Windows PowerShell 5.1 时错误发现 PS7 的
    Microsoft.PowerShell.Security 7.0.0.0 模块——因重复 ObjectSecurity
    类型成员加载失败，Get-Acl / Get-FileHash 不可用。从子进程环境副本中
    移除该变量使 5.1 回退到自身默认模块搜索路径。不修改 os.environ、不
    修改调用者的原始 env、不触碰机器级 / 用户级环境变量。"""
    child = dict(env)
    for key in [k for k in child if k.lower() == "psmodulepath"]:
        del child[key]
    return child


def _ps_safe_env(**overrides) -> dict[str, str]:
    """直接启动 powershell.exe（5.1）时使用的子进程环境。"""
    return _strip_psmodulepath(_env(**overrides))


def _run_ps(args, cwd=None, env=None, stdin_text="", entry=ENTRY):
    """真实调用 dao-sheng.ps1 子进程。stdout 中 CJK 可能因控制台代码页
    失真——断言只依赖 ASCII 标记（[OK]/[FAIL]）、ASCII 标签行与载体文件。
    子进程环境统一经 _strip_psmodulepath（PS 5.1 模块发现污染，见其
    docstring）。"""
    child_env = _strip_psmodulepath(env) if env is not None else _ps_safe_env()
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(entry), *args],
        cwd=str(cwd) if cwd is not None else None,
        env=child_env, input=stdin_text,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300,
    )


def _run_ps_lib(body: str):
    """lib 模式 dot-source dao-sheng.ps1 后在同一作用域执行 body。

    DAO_SHENG_PS_LIB_ONLY=1 使 dao-sheng.ps1 只定义函数，在 usage 检查、
    中央守卫与命令 dispatch 之前 return——不读不写任何文件，测试因此可以
    覆盖 $DaoShengPathExistsProbe 并直接调用生产 helper（这满足「测试必须
    调用生产 helper，不得只测试独立复制的分类逻辑」）。入口路径经 -Command
    命令行（UTF-16）传入，dao-sheng.ps1 文件内容保持 ASCII（PS 5.1 按
    ANSI 读取无 BOM .ps1）。子进程环境经 _ps_safe_env。"""
    script = "$ErrorActionPreference = 'Stop'; " + f". '{ENTRY}'; " + body
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-Command", script],
        env=_ps_safe_env(**{"DAO_SHENG_PS_LIB_ONLY": "1"}),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300,
    )


def _parse_data_home(stdout: str) -> str:
    match = re.search(r"^data home\s*:\s*(.+?)\s*$", stdout, re.MULTILINE)
    assert match is not None, f"status 输出缺少 'data home :' 行:\n{stdout}"
    return match.group(1)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(path) -> str:
    """由 env / TEMP 构造的期望值的规范文本：Python _normalize_path
    （Windows 8.3 短名展开为长名，与 PS GetFullPath 的规范形一致）+
    normcase。runner 上 TEMP 本身可能是短形（C:\\Users\\RUNNER~1\\...），
    据此拼接的期望值必须先规范化才能与两侧运行时输出比较。跨运行时
    parity 断言仍比较两侧原始输出文本（normcase），不用本函数——
    那不是放宽：仍要求 PS 与 Python 都独立展开到同一规范形。"""
    return os.path.normcase(str(run_dao_sheng._normalize_path(Path(str(path)))))


def _short_path(path) -> str | None:
    """GetShortPathNameW：已存在路径的 8.3 短形文本（长名本身 8.3-valid
    时原样返回，大小写保留）；API 失败返回 None——含卷禁用 8.3 名称生成
    （该卷上没有短名）。测试专用 helper，用于在长形 TEMP 的本机上构造
    短形路径，覆盖 runner 的 RUNNER~1 场景。argtypes / restype 显式声明
    （同 run_dao_sheng._get_long_path_name 的理由：ctypes 默认 c_int 会
    误读返回的长度）。"""
    kernel32 = ctypes.windll.kernel32
    kernel32.GetShortPathNameW.argtypes = [
        wintypes.LPCWSTR,  # lpszPath
        wintypes.LPWSTR,   # lpBuffer（create_unicode_buffer 实例）
        wintypes.DWORD,    # cchBuffer
    ]
    kernel32.GetShortPathNameW.restype = wintypes.DWORD
    size = max(260, len(str(path)) + 1)
    while True:
        buffer = ctypes.create_unicode_buffer(size)
        written = kernel32.GetShortPathNameW(str(path), buffer, size)
        if 0 < written < size:
            return buffer.value
        if written == 0:
            return None  # 路径不存在 / 非法 / 卷禁用 8.3 生成
        size = written + 1  # 缓冲区不足：MSDN 返回所需长度（含 NUL）


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


class PsSafeEnvTest(unittest.TestCase):
    """环境辅助函数本身的测试：PSModulePath 移除按变量名大小写不敏感、
    经副本进行、不修改 os.environ / 调用者 env / 机器与用户级变量；并
    证明去除在真实 powershell.exe 子进程中确实生效。"""

    def test_strip_case_insensitive_and_copy_semantics(self) -> None:
        env = {
            "PSModulePath": r"C:\ps7-modules",
            "psmodulepath": r"C:\dup-lower",
            "PSMODULEPATH": r"C:\dup-upper",
            "PSModulePathExtra": "keep-me",
            "DAO_UNRELATED": "keep-me",
        }
        child = _strip_psmodulepath(env)
        self.assertFalse([k for k in child if k.lower() == "psmodulepath"])
        # 仅移除 PSModulePath 本身：PSModulePathExtra 等无关键保留
        self.assertEqual(child["PSModulePathExtra"], "keep-me")
        self.assertEqual(child["DAO_UNRELATED"], "keep-me")
        # 调用者的原始 env 字典不被修改
        self.assertEqual(env, {
            "PSModulePath": r"C:\ps7-modules",
            "psmodulepath": r"C:\dup-lower",
            "PSMODULEPATH": r"C:\dup-upper",
            "PSModulePathExtra": "keep-me",
            "DAO_UNRELATED": "keep-me",
        })

    def test_helpers_do_not_touch_os_environ(self) -> None:
        before = dict(os.environ)
        _ps_safe_env(**{"DAO_TEST_OVERRIDE": "1"})
        _strip_psmodulepath(dict(os.environ))
        _env(**{"DAO_TEST_OVERRIDE": "1", "DAO_TEST_DELETE": None})
        self.assertEqual(dict(os.environ), before)

    def test_ps_safe_env_strips_injected_psmodulepath(self) -> None:
        env = _ps_safe_env(
            **{"PSModulePath": "C:\\bogus-marker", "DAO_TEST": "1"},
        )
        self.assertFalse([k for k in env if k.lower() == "psmodulepath"])
        self.assertEqual(env["DAO_TEST"], "1")

    def test_child_powershell_actually_loses_injected_psmodulepath(self) -> None:
        """端到端：对照组证明注入的 PSModulePath 确实被子进程继承；
        经 _ps_safe_env 去除后子进程不再看到 marker——证明去除真实生效。"""
        marker = "bogus-psmodulepath-marker"
        polluted = _env(**{"PSModulePath": marker})
        safe = _ps_safe_env(**{"PSModulePath": marker})
        self.assertFalse([k for k in safe if k.lower() == "psmodulepath"])

        def _probe(env):
            return subprocess.run(
                [POWERSHELL, "-NoProfile", "-Command", "$env:PSModulePath"],
                env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=120,
            )

        control = _probe(polluted)
        self.assertEqual(control.returncode, 0, control.stdout + control.stderr)
        self.assertIn(marker, control.stdout.lower())
        stripped = _probe(safe)
        self.assertEqual(stripped.returncode, 0, stripped.stdout + stripped.stderr)
        self.assertNotIn(marker, stripped.stdout.lower())


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
                _canonical(os.path.join(localappdata, "DaoSheng")),
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
        self.assertEqual(os.path.normcase(str(py_home)), _canonical(str(home)))

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
            _canonical(str(self.tmp / "dh-rel")),
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
            _canonical(str(self.data_home / "instances" / "default")),
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
            env=_ps_safe_env(),
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
            _canonical(str(self.data_home / "instances" / "default")),
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
            _canonical(str(self.data_home / "instances" / "default")),
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


@unittest.skipIf(os.name != "nt", "Windows 8.3 短名 / GetFullPath 行为专用")
class ShortPathParityTest(unittest.TestCase):
    """Windows 8.3 短路径回归：同一实际位置的短名 / 长名文本表示，PS
    GetFullPath 与 Python _expand_short_names（GetLongPathNameW）解析一
    致；仓库内拒绝跨表示一致生效；junction 不被解析。

    GitHub Windows runner 的 TEMP 本身就是短形（C:\\Users\\RUNNER~1\\...），
    该场景在 runner 上由 DefaultDataHomeParityTest / OverrideParityTest 的
    _canonical 期望值覆盖。本机 TEMP 为长形时无法天然复现 RUNNER~1，故本
    类用 GetShortPathNameW（_short_path）从实际存在的长路径构造短形，
    在两侧运行时上验证同一展开行为。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # CI runner 的 TEMP 本身是短形（C:\\Users\\RUNNER~1\\...）：fixture
        # 根先经 _normalize_path 展开为长形（大小写保留；fixture 目录真实
        # 存在，其长形即 OS ground truth），使由 self.tmp 构造的期望值与
        # 运行时输出（同样展开已存在前缀）处于同一表示。短形子用例仍由
        # _short_path 从长形构造，真实展开语义不变。
        self.tmp = run_dao_sheng._normalize_path(Path(tmp.name))
        long_dir = self.tmp / "ShortPathParityLongName"
        long_dir.mkdir()
        short = _short_path(long_dir)
        if short is None or "~" not in Path(short).name:
            self.skipTest(
                "8.3 short-name generation is disabled on this volume "
                "(or the API failed) -- short/long parity cannot be "
                "exercised here; the GitHub Windows runner has it enabled"
            )
        self.long_dir = long_dir
        self.short_dir = short
        self.expected = _canonical(str(long_dir))

    def test_short_form_override_expanded_by_both_runtimes(self) -> None:
        """短形覆盖值：PS GetFullPath 与 Python GetLongPathNameW 各自独立
        展开到同一长形（修复前 Python 保持短形、PS 展开——必失败的真实
        回归）。"""
        env = _env(**{DATA_HOME_ENV: self.short_dir})
        proc = _run_ps(["status"], env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ps_home = _parse_data_home(proc.stdout)
        py_home = run_dao_sheng.resolve_data_home(env=env)
        # 跨运行时 parity：两侧原始输出文本一致
        self.assertEqual(
            os.path.normcase(ps_home), os.path.normcase(str(py_home)),
            "短形数据根：PS 与 Python 解析文本不一致",
        )
        # 且两侧都已展开到期望长形（不是保持短形）
        self.assertEqual(os.path.normcase(ps_home), self.expected)
        self.assertEqual(os.path.normcase(str(py_home)), self.expected)

    def test_long_form_override_parity(self) -> None:
        """长形覆盖值：两侧一致且保持不变（规范化不引入差异）。"""
        env = _env(**{DATA_HOME_ENV: str(self.long_dir)})
        proc = _run_ps(["status"], env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ps_home = _parse_data_home(proc.stdout)
        py_home = run_dao_sheng.resolve_data_home(env=env)
        self.assertEqual(os.path.normcase(ps_home), os.path.normcase(str(py_home)))
        self.assertEqual(os.path.normcase(str(py_home)), self.expected)

    def test_is_inside_repo_cross_representation(self) -> None:
        """仓库内拒绝在短名 / 长名混用时仍生效：短形仓库根能拒绝长形
        仓库内路径，长形仓库根能拒绝短形仓库内路径，反之亦然。"""
        repo = self.tmp / "RepoLongNameWorktree"
        (repo / "instances" / "default").mkdir(parents=True)
        outside = self.tmp / "OutsideLongName"
        outside.mkdir()
        short_repo = _short_path(repo)
        short_instances = _short_path(repo / "instances")
        short_outside = _short_path(outside)
        self.assertIsNotNone(short_repo)
        self.assertIsNotNone(short_instances)
        self.assertIsNotNone(short_outside)
        # 长形仓库内路径 vs 短形仓库根 → 拒绝
        self.assertTrue(
            run_dao_sheng._is_inside_repo(repo / "instances" / "default",
                                          Path(short_repo)))
        # 短形仓库内路径 vs 长形仓库根 → 拒绝
        self.assertTrue(
            run_dao_sheng._is_inside_repo(Path(short_instances), repo))
        # 短形仓库根本身 vs 长形仓库根 → 拒绝（等于仓库根即仓库内）
        self.assertTrue(
            run_dao_sheng._is_inside_repo(Path(short_repo), repo))
        # 短形仓库外路径 vs 长形仓库根 → 不拒绝（安全检查未被扩大）
        self.assertFalse(
            run_dao_sheng._is_inside_repo(Path(short_outside), repo))

    def test_resolve_data_home_rejects_short_form_inside_repo(self) -> None:
        """端到端：短形覆盖值指向仓库内时，Python 侧 fail-loud 拒绝
        （规范化一致使安全检查跨表示生效）。"""
        with self.assertRaises(RuntimeError):
            run_dao_sheng.resolve_data_home(
                env={DATA_HOME_ENV: self.short_dir}, repo_root=self.tmp,
            )

    def test_junction_not_resolved(self) -> None:
        """GetLongPathNameW 不解析 junction：返回链接条目自身的长名，
        绝不解析到 target——保留「不解析符号链接」的既有设计语义。"""
        target = self.tmp / "JunctionTargetLongName"
        target.mkdir()
        link = self.tmp / "JunctionLinkLongName"
        mk = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60,
        )
        if mk.returncode != 0:
            self.skipTest(
                f"junction creation failed on this machine:\n"
                f"{mk.stdout}\n{mk.stderr}"
            )
        short_link = _short_path(link)
        if short_link is None:
            self.skipTest("8.3 short-name generation unavailable")
        expanded = run_dao_sheng._expand_short_names(short_link)
        self.assertEqual(os.path.normcase(expanded), os.path.normcase(str(link)))
        self.assertNotIn("JunctionTargetLongName", os.path.normcase(expanded))
        # PS 侧同样不解析：data home 报告链接条目自身的长名
        proc = _run_ps(["status"], env=_env(**{DATA_HOME_ENV: short_link}))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ps_home = _parse_data_home(proc.stdout)
        self.assertEqual(os.path.normcase(ps_home), os.path.normcase(str(link)))

    def test_safe83_component_without_tilde(self) -> None:
        """8.3-valid 长名（无 ~）：其短名就是原名本身（大小写保留），
        GetLongPathNameW 返回同一文本——移除 ~ 门控后行为不变。只比较
        末组件：runner 上父组件可能本身是短形（RUNNER~1），那部分会被
        合法展开。"""
        safe = self.tmp / "Safe83"
        safe.mkdir()
        short = _short_path(safe)
        if short is None:
            self.skipTest("8.3 short-name generation unavailable")
        self.assertEqual(Path(short).name, safe.name)
        expanded = run_dao_sheng._expand_short_names(str(safe))
        self.assertEqual(Path(expanded).name, safe.name)
        self.assertNotIn("~", Path(expanded).name)
        self.assertEqual(os.path.normcase(expanded), _canonical(str(safe)))
        # 跨运行时 parity（原始输出文本）
        env = _env(**{DATA_HOME_ENV: str(safe)})
        proc = _run_ps(["status"], env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ps_home = _parse_data_home(proc.stdout)
        py_home = run_dao_sheng.resolve_data_home(env=env)
        self.assertEqual(os.path.normcase(ps_home), os.path.normcase(str(py_home)))


@unittest.skipIf(os.name != "nt", "GetLongPathNameW 错误码 / 盘符行为专用")
class LongPathNameErrorTest(unittest.TestCase):
    """_get_long_path_name 错误码分类（本机实测 Windows 11 26100，
    2026-10-15）：仅 2（ERROR_FILE_NOT_FOUND，缺失叶子组件）与 3
    （ERROR_PATH_NOT_FOUND，缺失中间组件 / 不存在盘符的盘符根及其子
    路径）属于「路径组件不存在」，允许调用方向上回退；不可用 UNC 根实测
    不落在 2 / 3——不可达主机 53（ERROR_BAD_NETPATH）、可达主机缺失共享
    67（ERROR_BAD_NAME）、裸服务器名 161（ERROR_BAD_PATH），本就
    fail-loud。注意 3 也出现在「根本身不可用」形状（不存在盘符），故回
    退本身不足以判定正常缺失，须由 _expand_short_names 的根终止判定
    fail-loud；5（ERROR_ACCESS_DENIED
    ——MSDN：GetLongPathNameW 需要对路径及其各父目录有 List Folder /
    Read Data / Read Attributes 权限）与 123（ERROR_INVALID_NAME，语法
    非法形状：非法字符 <>|*?、尾部点/空格、超长组件）及意外错误码一律
    fail-loud（OSError），绝不静默回退。实测结论：普通不存在路径绝不
    返回 123，故 123 不得归类为正常缺失。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # 同 ShortPathParityTest：CI runner 的 TEMP 为短形，fixture 根展开
        # 为长形后，期望值与 _expand_short_names 输出处于同一表示；短形
        # 输入子用例（self.short_dir）仍验证真实展开。
        self.tmp = run_dao_sheng._normalize_path(Path(tmp.name))
        self.long_dir = self.tmp / "LongPathNameErrorLongName"
        self.long_dir.mkdir()
        short = _short_path(self.long_dir)
        self.short_dir = short if short is not None and "~" in Path(short).name else None

    def test_missing_leaf_returns_none(self) -> None:
        """已存在目录 + 缺失叶子（实测 2）→ None，允许回退。"""
        self.assertIsNone(
            run_dao_sheng._get_long_path_name(str(self.long_dir / "MissingLeaf")))

    def test_missing_intermediate_returns_none(self) -> None:
        """缺失中间组件（实测 3）→ None，允许回退。"""
        self.assertIsNone(
            run_dao_sheng._get_long_path_name(
                str(self.tmp / "MissingInter" / "Deeper")))

    def test_expand_keeps_missing_leaf_verbatim(self) -> None:
        """回退语义：已存在前缀展开为长名，不存在的叶子逐字保留——
        待创建目录可正常规范化（短形前缀同样展开到同一长形）。"""
        expanded = run_dao_sheng._expand_short_names(
            str(self.long_dir / "MissingLeaf"))
        self.assertEqual(
            os.path.normcase(expanded),
            os.path.normcase(str(self.long_dir / "MissingLeaf")),
        )
        if self.short_dir is not None:
            expanded = run_dao_sheng._expand_short_names(
                self.short_dir + r"\MissingLeaf")
            self.assertEqual(
                os.path.normcase(expanded),
                os.path.normcase(str(self.long_dir / "MissingLeaf")),
            )

    def _fail_loud_with_code(self, err: int) -> OSError:
        """注入 fake GetLongPathNameW（返回 0 + 指定 last error），断言
        fail-loud 且 winerror 保留。本机无法可靠构造真实 Deny ACE 场景，
        故以 fake 模拟——错误码语义本身经 MSDN + 本机真实码实测确认。"""
        original = run_dao_sheng._long_path_name_w

        def fake(path, buffer, size):
            ctypes.set_last_error(err)
            return 0

        run_dao_sheng._long_path_name_w = fake
        try:
            with self.assertRaises(OSError) as ctx:
                run_dao_sheng._get_long_path_name(str(self.long_dir))
            self.assertEqual(ctx.exception.winerror, err)
            return ctx.exception
        finally:
            run_dao_sheng._long_path_name_w = original

    def test_access_denied_fails_loud(self) -> None:
        """权限拒绝（5）不是「组件不存在」信号：必须 fail-loud，不回退。"""
        exc = self._fail_loud_with_code(5)
        self.assertIn("only ERROR_FILE_NOT_FOUND/ERROR_PATH_NOT_FOUND",
                      str(exc))

    def test_unexpected_error_code_fails_loud(self) -> None:
        """意外错误码（53 = ERROR_BAD_NETPATH 形状）同样 fail-loud。"""
        self._fail_loud_with_code(53)

    def test_invalid_name_fails_loud(self) -> None:
        """真实 API 实测：语法非法形状返回 123——未经核实不得归类为
        正常缺失，fail-loud。"""
        with self.assertRaises(OSError) as ctx:
            run_dao_sheng._get_long_path_name(str(self.long_dir / "bad<>name"))
        self.assertEqual(ctx.exception.winerror, 123)

    def test_nonexistent_drive_root_fails_loud(self) -> None:
        """不存在盘符（盘符根与其子路径实测均为 3）：回退到达盘符根而
        根仍报告缺失 → 不可用根，不是正常缺失组件，_expand_short_names
        fail-loud（OSError），不再保持输入原样。与 PS 侧
        test_real_probe_nonexistent_drive_fails_loud 同决策。"""
        letter = None
        for candidate in "DEFGHIJKLMNOPQRSTUVWXYZ":
            if not os.path.exists(candidate + ":\\"):
                letter = candidate
                break
        if letter is None:
            self.skipTest("no free drive letter on this machine")
        value = letter + ":\\MissingDrivePath"
        self.assertIsNone(run_dao_sheng._get_long_path_name(value))
        self.assertIsNone(run_dao_sheng._get_long_path_name(letter + ":\\"))
        with self.assertRaises(OSError) as ctx:
            run_dao_sheng._expand_short_names(value)
        self.assertIn("could not be verified as existing", str(ctx.exception))

    def test_seam_unc_root_missing_fails_loud(self) -> None:
        """seam 注入（模拟错误注入，非真实网络集成测试）：UNC 共享根
        \\server\\share 报告 3（形状模拟）时回退到达共享根仍无法验证 →
        fail-loud，绝不原样返回。本机没有可用的真实不可达 UNC 服务器，
        分类逻辑以 fake _long_path_name_w 验证；真实 UNC 错误码分类见
        test_real_probe_unavailable_unc_share_fails_loud。"""
        original = run_dao_sheng._long_path_name_w

        def fake(path, buffer, size):
            ctypes.set_last_error(3)
            return 0

        run_dao_sheng._long_path_name_w = fake
        try:
            with self.assertRaises(OSError) as ctx:
                run_dao_sheng._expand_short_names(
                    "\\\\nonexistent-host-dao-probe\\share\\sub")
            self.assertIn("could not be verified as existing",
                          str(ctx.exception))
        finally:
            run_dao_sheng._long_path_name_w = original

    def test_real_probe_unreachable_unc_fails_loud(self) -> None:
        """本机 OS 级真实分类（回环主机上必然不存在的共享名，非远程
        UNC 服务器集成测试）：\\127.0.0.1\<缺失共享> 实测 67
        （ERROR_BAD_NAME；Afd 服务停止时 53），不属 2 / 3 →
        _get_long_path_name 与 _expand_short_names 均 fail-loud。"""
        value = "\\\\127.0.0.1\\dao-sheng-nonexistent-share-probe\\sub"
        with self.assertRaises(OSError) as ctx:
            run_dao_sheng._get_long_path_name(value)
        self.assertNotIn(ctx.exception.winerror,
                         run_dao_sheng._GLPN_NOT_FOUND_ERRORS)
        with self.assertRaises(OSError):
            run_dao_sheng._expand_short_names(value)


@unittest.skipIf(os.name != "nt", "盘符根 / 跨盘符判定专用")
class DriveRootBoundaryTest(unittest.TestCase):
    """_is_inside_repo 盘符根漏判回归：仓库根为盘符根（normcase 后为
    「盘符: + 单一尾分隔符」）时，边界必须经 root.rstrip(os.sep) +
    os.sep 构造为单一分隔符——直接 root + os.sep 产生「盘符: + 双分隔
    符」，盘符根仓库的直接子路径（C:\\Windows）不以其为前缀 → 漏判。
    不同盘符的路径盘符字符不同，不可能互为前缀，互不误判。根判定更新
    后：位于不存在盘符的候选路径或仓库根 fail-loud（OSError），绝不作
    为「仓库内 / 仓库外」文本误判通过。"""

    def setUp(self) -> None:
        self.drive = os.environ.get("SystemDrive", "C:").upper()
        self.root = Path(self.drive + "\\")

    def test_drive_root_itself_is_inside(self) -> None:
        self.assertTrue(run_dao_sheng._is_inside_repo(self.root, self.root))

    def test_direct_child_of_drive_root(self) -> None:
        self.assertTrue(
            run_dao_sheng._is_inside_repo(
                Path(self.drive + "\\Windows"), self.root))

    def test_deep_child_of_drive_root(self) -> None:
        self.assertTrue(
            run_dao_sheng._is_inside_repo(
                Path(self.drive + "\\Windows\\Temp"), self.root))

    def test_cross_drive_never_flagged(self) -> None:
        """跨盘符不误判：存在第二已存在盘符时直接验证前缀逻辑（不同盘
        符不可能互为前缀）。单盘符机器上以不存在盘符验证新的根判定——
        盘符根无法验证的候选路径 fail-loud 拒绝（绝不被接受为「仓库
        内」），反向以不可用盘符为仓库根同样 fail-loud。"""
        existing_other = None
        for candidate in "DEFGHIJKLMNOPQRSTUVWXYZ":
            if candidate != self.drive and os.path.exists(candidate + ":\\"):
                existing_other = candidate
                break
        if existing_other is not None:
            # 其他已存在盘符的路径不得被判为位于本盘符根仓库内
            self.assertFalse(
                run_dao_sheng._is_inside_repo(
                    Path(existing_other + ":\\Windows"), self.root))
            # 反向：以另一已存在盘符根为仓库根时，本盘符路径同样不误判
            self.assertFalse(
                run_dao_sheng._is_inside_repo(
                    Path(self.drive + "\\Windows"),
                    Path(existing_other + "\\")))
            return
        free = None
        for candidate in "DEFGHIJKLMNOPQRSTUVWXYZ":
            if candidate != self.drive and not os.path.exists(candidate + ":\\"):
                free = candidate
                break
        if free is None:
            self.skipTest("no drive letter available for cross-drive decision")
        # 不可验证的盘符根：fail-loud 拒绝，不是「仓库内」误判（与
        # test_nonexistent_drive_root_fails_loud 同决策）。
        with self.assertRaises(OSError):
            run_dao_sheng._is_inside_repo(Path(free + ":\\Windows"), self.root)
        with self.assertRaises(OSError):
            run_dao_sheng._is_inside_repo(
                Path(self.drive + "\\Windows"), Path(free + "\\"))


@unittest.skipIf(os.name != "nt", "8.3 短名组件 + 不存在叶子分歧专用")
class ShortPathDivergenceSafetyTest(unittest.TestCase):
    """已实测分歧形状「已存在 8.3 短名组件 + 不存在叶子」的安全回归。

    PS 5.1 GetFullPath 对该形状的输出文本受同进程调用顺序影响（先调用
    子路径 → 长形；先对父路径调用 GetFullPath → 短形），文本 parity 不
    能无条件宣称，本类也不断言显示文本相等。必须保证的是安全判定：两
    侧运行时对同一形状的「仓库内」决策一致——仓库内被拒（PS exit 1 +
    [FAIL] data home；Python fail-loud RuntimeError），仓库外被正常接受
    且不存在叶子逐字保留。dao-sheng.ps1 的 Test-PathInsideRepo 经
    Get-CanonicalPathForComparison 做与 Python _expand_short_names 相同
    的 walk-up 规范化（已存在组件一律展开，与调用顺序无关）；修复前
    raw GetFullPath 文本比较下，短形组件（REPO~1）不以长形仓库根为前缀
    → 仓库内路径漏判，本类的 PS 拒绝测试即该缺口的回归。

    副本仓库无 .venv：dao-sheng.ps1 的中央守卫先于命令 dispatch 执行，
    status 对 Python 缺失只报告不 Fail-Step，故拒绝 / 接受判定可在无
    venv 副本上端到端验证。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # 同 ShortPathParityTest：CI runner 的 TEMP 为短形，fixture 根展开
        # 为长形后期望值与运行时输出同表示；self.short_repo 仍由
        # _short_path 构造，短形 → 长形的真实展开语义不变。
        self.tmp = run_dao_sheng._normalize_path(Path(tmp.name))
        self.repo_copy = self.tmp / "RepoCopyDivergenceLongName"
        _copy_repo(self.repo_copy, with_venv=False)
        short = _short_path(self.repo_copy)
        if short is None or "~" not in Path(short).name:
            self.skipTest(
                "8.3 short-name generation is disabled on this volume "
                "(or the API failed) -- the divergent shape cannot be "
                "constructed here; the GitHub Windows runner has it enabled"
            )
        self.short_repo = short

    def test_ps_rejects_short_component_with_missing_leaf(self) -> None:
        value = self.short_repo + r"\instances\MissingLeaf"
        proc = _run_ps(
            ["status"], env=_env(**{DATA_HOME_ENV: value}),
            entry=self.repo_copy / "dao-sheng.ps1",
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("[FAIL] data home", proc.stdout + proc.stderr)

    def test_python_rejects_same_shape(self) -> None:
        value = self.short_repo + r"\instances\MissingLeaf"
        with self.assertRaises(RuntimeError):
            run_dao_sheng.resolve_data_home(
                env={DATA_HOME_ENV: value}, repo_root=self.repo_copy)

    def test_expand_expands_existing_component_keeps_leaf(self) -> None:
        """Python walk-up：短形已存在组件恒展开为长形，叶子逐字保留。"""
        expanded = run_dao_sheng._expand_short_names(
            self.short_repo + r"\MissingLeaf")
        self.assertEqual(
            os.path.normcase(expanded),
            os.path.normcase(str(self.repo_copy / "MissingLeaf")),
        )

    def test_is_inside_repo_detects_divergent_shape(self) -> None:
        self.assertTrue(
            run_dao_sheng._is_inside_repo(
                Path(self.short_repo + r"\instances\MissingLeaf"),
                self.repo_copy))

    def test_outside_missing_leaf_accepted_by_both_runtimes(self) -> None:
        """仓库外 + 不存在叶子：两侧正常接受（安全检查未被扩大），叶子
        逐字保留。已存在组件的显示文本可能短 / 长形不一致（PS GetFullPath
        调用顺序依赖）——不断言文本相等，断言 accept/reject 决策一致。"""
        outside = self.tmp / "OutsideDivergenceLongName"
        outside.mkdir()
        short_outside = _short_path(outside)
        if short_outside is None or "~" not in Path(short_outside).name:
            self.skipTest("8.3 short-name generation unavailable")
        value = short_outside + r"\MissingLeaf"
        proc = _run_ps(
            ["status"], env=_env(**{DATA_HOME_ENV: value}),
            entry=self.repo_copy / "dao-sheng.ps1",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ps_home = _parse_data_home(proc.stdout)
        self.assertEqual(Path(ps_home).name.lower(), "missingleaf")
        py_home = run_dao_sheng.resolve_data_home(
            env={DATA_HOME_ENV: value}, repo_root=self.repo_copy)
        self.assertEqual(py_home.name, "MissingLeaf")
        self.assertFalse(
            run_dao_sheng._is_inside_repo(py_home, self.repo_copy))


class PsProbeSeamTest(unittest.TestCase):
    """dao-sheng.ps1 存在性探针 seam 回归（直接调用生产 helper）。

    两类证据严格区分：
      - seam 注入（$DaoShengPathExistsProbe scriptblock 模拟错误形状）：
        验证「确定不存在 → 向上回退、缺失组件逐字保留」与「访问拒绝 /
        意外错误 / 回退到达根而根仍报告缺失 → 停止」。这是模拟错误注入
        测试，不是真实 ACL 集成测试。
      - 真实 Set-Acl Deny ACE（无任何注入，生产探针真实命中被拒路径）：
        helper 级与中央守卫端到端各一条，是真实 ACL 集成测试。
    本机实测分类（见 dao-sheng.ps1 注释）：FNFE/DNFE → 确定不存在，允许
    回退，但回退到达根（盘符根 / UNC 共享根）而根仍报告缺失 → 不可用根
    → 抛 InvalidOperationException fail-loud，不再逐字保留（与 Python
    _expand_short_names 根终止判定一致）；访问拒绝 / 意外 IO 错误 / 不可
    达 UNC（IOException）/ 裸服务器名（ArgumentException）→ 抛错。
    """

    # 只拒绝读取类权限（保留 WRITE_DAC / DELETE / 子项删除）→ 清理始终能
    # 移除 ACE 并删除临时目录（同 MigrateDataMidFailureTest._acl 的纪律）。
    DENY = "ReadData,ReadAttributes,ReadExtendedAttributes,ListDirectory"

    def setUp(self) -> None:
        # CI runner 的 TEMP 为短形（C:\\Users\\RUNNER~1\\...）：fixture 根
        # 经 _normalize_path 展开为长形（大小写保留，不用 _canonical 的
        # normcase 小写化——seam 断言是大小写敏感的 raw-text 比较）。
        # 生产 helper 先对输入做 GetFullPath（CI 上展开已存在短形前缀），
        # mock 的比较文本必须与 helper 实际收到的规范化形状一致，否则
        # seam 注入失配。长形输入经 GetFullPath 逐字保留 → 断言形状确定。
        self.tmp = run_dao_sheng._normalize_path(
            Path(tempfile.mkdtemp(prefix="dao-ps-probe-")))
        # LIFO：先注册 → 后执行（ACL 移除先于临时目录删除）
        self.addCleanup(shutil.rmtree, str(self.tmp), ignore_errors=True)

    def _acl(self, directory: Path, action: str) -> None:
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
            f"$who, '{self.DENY}', "
            "'ContainerInherit,ObjectInherit', 'None', 'Deny'); "
            + verb + "; "
            "Set-Acl -LiteralPath $path -AclObject $acl"
        )
        proc = subprocess.run(
            [POWERSHELL, "-NoProfile", "-Command", script],
            env=_ps_safe_env(),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"ACL {action} failed on {directory}:\n{proc.stdout}\n{proc.stderr}"
            )

    # ---- 真实 ACL 测试的前置自验证 ----

    def _deny_effective_for_current_identity(self, path: Path) -> bool:
        """前置自验证：直接执行生产探针的底层调用
        ([System.IO.File]::GetAttributes)，确认 Deny ACE 对「将要运行探针的
        同一身份」确实被 OS 强制执行。严格三分类：

        - 明确抛出 UnauthorizedAccessException → True（继续原有 ACL 断言）；
        - GetAttributes 正常返回 → False（允许明确 skip）；
        - 其他异常或无法解析的输出 → 直接失败本测试，不允许 skip
          （意外错误不得被误归类为「Deny ACE 未生效」而跳过断言）。

        真实 ACL fault-injection 的可重复性依赖这个前提，而前提本身是
        身份相关的：CI run 377cd2e 观察到 Deny ACE 应用成功（exit 0）、
        trustee 即探针进程当前身份（GetCurrent().Name），但同进程
        GetAttributes 仍成功读取属性；精确的 OS 原因尚未确定，因此测试
        直接检查前置条件，而不预设原因。前提不成立时显式 skip，而不是
        让 fail-loud 断言建立在不可靠的注入上。fail-loud 分类逻辑本身由
        seam 注入测试（确定性、全平台）与 test_real_probe_unavailable_unc_share_fails_loud
        （本机 OS 真实 IOException）覆盖。"""
        proc = _run_ps_lib(
            "try { [System.IO.File]::GetAttributes('" + str(path) + "') | Out-Null; "
            "Write-Host 'DENY-EFFECTIVE=False' } "
            "catch [System.UnauthorizedAccessException] { Write-Host 'DENY-EFFECTIVE=True' } "
            "catch { Write-Host ('DENY-EFFECTIVE=OTHER:' + $_.Exception.GetType().Name) }"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        if "DENY-EFFECTIVE=True" in out:
            return True
        if "DENY-EFFECTIVE=False" in out:
            return False
        self.fail(
            "deny-effectiveness probe produced no parseable result "
            "(unexpected error or malformed output); this is NOT treated as a "
            f"skip condition:\n{out}"
        )

    # ---- seam 注入（模拟错误形状，调用生产 Get-CanonicalPathForComparison）----

    def test_seam_definitively_missing_components_walk_up_verbatim(self) -> None:
        """注入「仅 tmp 存在」：生产 helper 回退到 tmp 后停止，缺失组件
        逐字保留（与 Python _expand_short_names 的 walk-up 决策一致）。"""
        tmp = str(self.tmp)
        proc = _run_ps_lib(
            "$DaoShengPathExistsProbe = { param($p) ($p -eq '" + tmp + "') }; "
            "$r = Get-CanonicalPathForComparison '" + tmp + "\\MissingInter\\MissingLeaf'; "
            "Write-Host ('RETURNED=' + $r)"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("RETURNED=" + tmp + "\\MissingInter\\MissingLeaf", out)

    def test_seam_access_denied_mid_path_stops(self) -> None:
        """注入模拟访问拒绝（中间组件）：helper 必须停止，不得回退、
        不得返回任何结果。注入的异常不经包装直接传播。"""
        tmp = str(self.tmp)
        proc = _run_ps_lib(
            "$DaoShengPathExistsProbe = { param($p) "
            "if ($p -eq ('" + tmp + "\\DeniedMid')) { "
            "throw [System.UnauthorizedAccessException]::new('simulated access denied') } "
            "return $false }; "
            "try { $r = Get-CanonicalPathForComparison '" + tmp + "\\DeniedMid\\Leaf'; "
            "Write-Host ('RETURNED=' + $r) } "
            "catch { Write-Host ('THREW=' + $_.Exception.GetType().Name) }"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("THREW=UnauthorizedAccessException", out)
        self.assertNotIn("RETURNED=", out)

    def test_seam_io_error_at_leaf_stops(self) -> None:
        """注入模拟意外 IO 错误（叶子）：同样必须停止。"""
        tmp = str(self.tmp)
        proc = _run_ps_lib(
            "$DaoShengPathExistsProbe = { param($p) "
            "if ($p -eq ('" + tmp + "\\Leaf')) { "
            "throw [System.IO.IOException]::new('simulated IO error') } "
            "return $false }; "
            "try { $r = Get-CanonicalPathForComparison '" + tmp + "\\Leaf'; "
            "Write-Host ('RETURNED=' + $r) } "
            "catch { Write-Host ('THREW=' + $_.Exception.GetType().Name) }"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("THREW=IOException", out)
        self.assertNotIn("RETURNED=", out)

    def test_seam_drive_root_error_stops(self) -> None:
        """注入模拟「驱动器根不可用」错误：walk-up 到达驱动器根时探针抛错
        → 停止；绝不得静默返回原样文本。"""
        proc = _run_ps_lib(
            "$DaoShengPathExistsProbe = { param($p) "
            "if ($p -eq 'Z:\\') { "
            "throw [System.IO.IOException]::new('simulated unavailable drive') } "
            "return $false }; "
            "try { $r = Get-CanonicalPathForComparison 'Z:\\MissingDrivePath'; "
            "Write-Host ('RETURNED=' + $r) } "
            "catch { Write-Host ('THREW=' + $_.Exception.GetType().Name) }"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("THREW=IOException", out)
        self.assertNotIn("RETURNED=", out)

    # ---- 无注入：生产探针对本机真实路径的分类 ----

    def test_real_probe_classifies_existing_and_definitively_missing(self) -> None:
        """生产 Test-PathExistsForComparison：已存在 → True；缺失叶子 /
        缺失中间组件 → False（FNFE/DNFE，确定不存在）。"""
        existing = self.tmp / "ExistingDir"
        existing.mkdir()
        proc = _run_ps_lib(
            "Write-Host ('existing=' + (Test-PathExistsForComparison '"
            + str(existing) + "')); "
            "Write-Host ('missingleaf=' + (Test-PathExistsForComparison '"
            + str(existing) + "\\MissingLeaf')); "
            "Write-Host ('missinginter=' + (Test-PathExistsForComparison '"
            + str(self.tmp) + "\\MissingInter\\Deeper'))"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("existing=True", out)
        self.assertIn("missingleaf=False", out)
        self.assertIn("missinginter=False", out)

    def test_real_probe_nonexistent_drive_fails_loud(self) -> None:
        """无注入：本机不存在的盘符由 OS 报告为 DNFE（确定不存在）→
        walk-up 到达盘符根而根仍报告缺失 → 不可用根 → 抛
        InvalidOperationException fail-loud，不再逐字保留原样文本（与
        Python LongPathNameErrorTest.test_nonexistent_drive_root_fails_loud
        同决策）。"""
        free = None
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            if not os.path.exists(letter + ":\\"):
                free = letter
                break
        if free is None:
            self.skipTest("no free drive letter on this machine")
        value = free + ":\\MissingDrivePath"
        proc = _run_ps_lib(
            "try { $r = Get-CanonicalPathForComparison '" + value + "'; "
            "Write-Host ('RETURNED=' + $r) } "
            "catch { Write-Host ('THREW=' + $_.Exception.GetType().Name); "
            "Write-Host ('MSG=' + $_.Exception.Message) }"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("THREW=InvalidOperationException", out)
        self.assertIn("could not be verified as existing", out)
        self.assertNotIn("RETURNED=", out)

    def test_seam_root_always_missing_fails_loud(self) -> None:
        """seam 注入（模拟错误注入，非真实网络集成测试）：探针对所有路径
        返回 $false（模拟整条路径含根都报告缺失，如不存在盘符或不可用
        UNC 共享根的形状）→ walk-up 到达根后必须抛
        InvalidOperationException，绝不返回原样文本。"""
        proc = _run_ps_lib(
            "$DaoShengPathExistsProbe = { param($p) return $false }; "
            "try { $r = Get-CanonicalPathForComparison 'Z:\\MissingDrivePath'; "
            "Write-Host ('RETURNED=' + $r) } "
            "catch { Write-Host ('THREW=' + $_.Exception.GetType().Name); "
            "Write-Host ('MSG=' + $_.Exception.Message) }"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("THREW=InvalidOperationException", out)
        self.assertIn("could not be verified as existing", out)
        self.assertNotIn("RETURNED=", out)

    def test_real_probe_unavailable_unc_share_fails_loud(self) -> None:
        """本机 OS 级真实分类（回环主机上必然不存在的共享名，非远程 UNC
        服务器集成测试；本机没有可用的真实不可达 UNC 服务器）：生产探针
        对 \\127.0.0.1\<缺失共享> 真实命中 IOException（不可用共享，不是
        DNFE）→ Get-CanonicalPathForComparison 抛
        InvalidOperationException，不得返回原样文本。"""
        value = '\\\\127.0.0.1\\dao-sheng-nonexistent-share-probe\\sub'
        proc = _run_ps_lib(
            "try { $r = Get-CanonicalPathForComparison '" + value + "'; "
            "Write-Host ('RETURNED=' + $r) } "
            "catch { Write-Host ('THREW=' + $_.Exception.GetType().Name); "
            "Write-Host ('MSG=' + $_.Exception.Message) }"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("THREW=InvalidOperationException", out)
        self.assertIn("existence probe failed", out)
        self.assertNotIn("RETURNED=", out)

    # ---- 真实 ACL 集成测试（无注入，Set-Acl Deny ACE）----

    def test_real_acl_denied_intermediate_fails_loud(self) -> None:
        """真实 ACL 集成测试（helper 级）：DeniedDir 上 Set-Acl Deny
        （ListDirectory/ReadAttributes，ContainerInherit）→ 生产探针对
        DeniedDir\\ChildDir\\Leaf 真实命中访问拒绝 → 抛
        InvalidOperationException（消息明确「未被当成不存在」），
        walk-up 不得越过被拒组件。

        前置自验证（见 _deny_effective_for_current_identity）：当前进程的
        实际探测未产生预期的访问拒绝时显式 skip——注入不可靠不等于探针
        契约失败（精确的 OS 原因尚未确定）；分类逻辑的 fail-loud 验证由
        seam 注入测试与真实 UNC 测试保留。"""
        denied = self.tmp / "DeniedDir"
        child = denied / "ChildDir"
        child.mkdir(parents=True)
        self._acl(denied, "deny")
        self.addCleanup(self._acl, denied, "remove")
        if not self._deny_effective_for_current_identity(child):
            self.skipTest(
                "Deny ACE applied but the current process's actual probe did "
                "not produce the expected access denial (GetAttributes "
                "succeeded); the OS-level reason is not established - real-ACL "
                "fault injection is identity-dependent; see "
                "_deny_effective_for_current_identity"
            )
        proc = _run_ps_lib(
            "try { $r = Get-CanonicalPathForComparison '" + str(child) + "\\Leaf'; "
            "Write-Host ('RETURNED=' + $r) } "
            "catch { Write-Host ('THREW=' + $_.Exception.GetType().Name); "
            "Write-Host ('MSG=' + $_.Exception.Message) }"
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("THREW=InvalidOperationException", out)
        self.assertIn("existence probe failed", out)
        self.assertIn("not 'missing' and was not treated as such", out)
        self.assertNotIn("RETURNED=", out)

    def test_real_acl_end_to_end_guard_fails_loud(self) -> None:
        """真实 ACL 集成测试（端到端）：数据根真实存在但位于被 Deny ACE
        拒绝读取的目录下 → 中央守卫分类探针真实命中访问拒绝 → exit 1 +
        [FAIL] data home + existence probe failed；既不被当成「缺失」也不
        被当成「仓库内 / 仓库外」判定成功，任何写入都未发生。

        前置自验证同 test_real_acl_denied_intermediate_fails_loud：当前
        进程的实际探测未产生预期的访问拒绝时显式 skip。"""
        denied = self.tmp / "DeniedHome"
        data_home = denied / "DataHome"
        data_home.mkdir(parents=True)
        self._acl(denied, "deny")
        self.addCleanup(self._acl, denied, "remove")
        if not self._deny_effective_for_current_identity(data_home):
            self.skipTest(
                "Deny ACE applied but the current process's actual probe did "
                "not produce the expected access denial (GetAttributes "
                "succeeded); the OS-level reason is not established - real-ACL "
                "fault injection is identity-dependent; see "
                "_deny_effective_for_current_identity"
            )
        proc = _run_ps(
            ["status"], env=_env(**{DATA_HOME_ENV: str(data_home)}),
        )
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 1, out)
        self.assertIn("[FAIL] data home", out)
        self.assertIn("existence probe failed", out)
        self.assertIn("nothing was written", out)
        # 被拒根目录仍在（其 stat 经未拒绝的父目录条目可查）。DataHome 本身
        # 的 stat 恰被 Deny ACE 阻断——那正是探针命中并 fail-loud 的形状，
        # 无法也不应在此读取验证；守卫在 dispatch 之前失败，未发生任何写入。
        self.assertTrue(denied.is_dir())


if __name__ == "__main__":
    unittest.main()
