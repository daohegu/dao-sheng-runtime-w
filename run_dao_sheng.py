"""DaoSheng 最小启动入口（部署层脚本；阶段 B，决定 D-053）。

定位：composition root 的最小调用方。USER_GUIDE §6.1 使用形态 = 以 Python
调用 compose()；本脚本把该形态落到一个最小交互式入口——不是 CLI 框架、
不是常驻服务、不是调度器 / Worker / 模型编排层（阶段 B 边界）。

流程（阶段 B 授权六项；数据根布局为 Git 升级安全修复后的外部数据根）：
1. 解析外部数据根（Git worktree 之外；DAO_SHENG_DATA_HOME 覆盖，默认
   %LOCALAPPDATA%\\DaoSheng；解析规则与 dao-sheng.ps1 完全一致；解析
   结果位于仓库内 → fail-loud 拒绝，绝不静默接受）；
2. 读取实例根：<数据根>/config/install-state.json（安装层元数据；
   INSTALLATION_CONTRACT：Core 不读取 config/，本脚本属部署层；记录的
   instance_root 位于仓库内 → fail-loud；数据根未安装且仓库内检测到
   遗留个人数据 → fail-loud 迁移提示，绝不静默启动空白实例）；
3. 读取模型部署配置：<数据根>/config/model-config.json（运行配置；
   缺失 = 未配置 → Model 两侧 None → 回合降级，U-5 不预设）；
4. 经现有 Composition Root（composition.compose，R-09 唯一构造位）完成
   真实装配——不新建装配路径；
5. 读取用户提交的一项任务（argv 或 stdin）；
6. Individual.act(Turn(content, MemoryOrigin.EXTERNAL)) → persist()
   （严格交替，决定 ⑬；经历经现有 persist 路径写入个体 Memory 载体）；
7. 显示结果；配置缺失 / 模型不可用 → 可诊断信息（降级回合 action=None，
   决定 ⑯；退出码非零）。

成长触发入口（阶段 C，决定 D-054）：`--grow <reference>` = 对一条既有
经历记录显式运行现有成长管线一次（digest → extract → reflect →
verify_insight(insight)，canonical 顺序同 STEP 15 真实验证先例）。不是
调度器、不是每回合自动调用、不是后台循环——每次运行由用户明确下达；
阶段降级 = None（决定 ㉕：不写、不追加、不抛异常）。

观察触发入口（阶段 D，决定 D-055）：`--observe <relative_path>` = 以
现有 FileWorld（world seam 唯一只读观察手段，M06；root = 部署层注入
REPO_ROOT，K-07 保留条件 1 / R-09）观察一个明确授权的相对路径——
观察 = 有来源的事实，不是判断（K-08），只取元数据（path/exists/
is_file/size），不读文件内容。观察结果进入个体经验流 = 现有 M04 回合
入口（world.py 文档：通道由 M04 决定；composition 无 world 装配位，
M06 决定 ⑫）：观察事实作为一项 EXTERNAL 回合内容 → act → persist。
不是新 World Engine、不是监控服务、不是后台调度器——每次观察由用户
明确下达。

Host 同步触发入口（阶段 D，决定 D-055）：`--sync-host` = 显式运行现有
host adapter 的 sync() 一次（重新解析状态位置 + 重导入新增内容，
M09 S4；宿主侧幂等 = 导入日志 append-only）。配置来源 =
<数据根>/config/host-config.json（HostConfig 槽位同名 JSON；缺失 =
未配置 → HostConfig() 全 None → compose 不装配 host，U-5 不预设）。
不是调度器、不是后台循环——每次同步由用户明确下达。

部署层纪律：本脚本 import dao_sheng，dao_sheng 不 import 本脚本；模型
配置不硬编码进 Identity / Core / Doctrine（阶段 B 二节约束）。
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
from collections.abc import Mapping
from ctypes import wintypes
from pathlib import Path

from dao_sheng.composition import (
    HostConfig,
    ModelConfig,
    OperationalDefaults,
    RuntimeAssembly,
    compose,
)
from dao_sheng.individual import Turn, TurnOutcome
from dao_sheng.memory import MemoryOrigin
from dao_sheng.world import FileObservation, FileWorld

REPO_ROOT = Path(__file__).resolve().parent

# 外部数据根（Git worktree 之外）：全部可变个人运行时数据——identity /
# faculties / continuity / memory（SQLite + WAL/SHM）/ capabilities 记录 /
# install-state / model-config / host-config / 日志——位于仓库之外。普通
# 源码升级（git pull）无论上游是否开始跟踪仓库内同名路径，都不可能触碰
# 它们（.gitignore 对已被上游跟踪的路径无保护作用）。解析规则与
# dao-sheng.ps1 的 Resolve-DataHome 完全一致：
# - DAO_SHENG_DATA_HOME 非空 → 覆盖（前导 ~ 展开；相对路径按当前工作
#   目录解析；规范化为绝对路径）；
# - 默认：Windows %LOCALAPPDATA%\DaoSheng（缺失回退
#   %USERPROFILE%\AppData\Local\DaoSheng）；POSIX $XDG_DATA_HOME/dao-sheng
#   （缺失回退 ~/.local/share/dao-sheng）；
# - 解析结果位于 Git worktree 内 → fail-loud 拒绝，绝不静默接受。
DATA_HOME_ENV = "DAO_SHENG_DATA_HOME"
LEGACY_DATA_DIRS = ("instances", "config", "log")

# 部署层显示约定：入口输出统一 UTF-8（Windows 控制台默认 locale 编码会
# 使中文结果不可读；"清晰显示结果"属阶段 B 入口职责）。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


_long_path_name_w = None  # 显式声明 argtypes / restype 后的 GetLongPathNameW 缓存

# 经本机实测（Windows 11 26100，2026-10-15）确认属于「路径组件不存在」、
# 允许调用方向上回退到最长存在前缀的错误码：
# 2 = ERROR_FILE_NOT_FOUND（缺失叶子组件；保留名 CON/NULL 亦返回 2）；
# 3 = ERROR_PATH_NOT_FOUND（缺失中间组件 / 不存在盘符的盘符根及其子路径）。
# 不可用 UNC 根实测不落在 2 / 3：不可达主机（\\nonexistent-host\share 及
# 其子路径）返回 53（ERROR_BAD_NETPATH）；可达主机上不存在的共享
# （\\127.0.0.1\share 及其子路径）返回 67（ERROR_BAD_NAME）；裸服务器名
# （\\server）返回 161（ERROR_BAD_PATH）——一律 fail-loud，绝不回退。
# 实测结论：普通不存在路径（缺失叶子或中间组件、不存在盘符）一律返回
# 2 或 3，绝不返回 123；123 = ERROR_INVALID_NAME 只出现在语法非法形状
# （非法字符 <>|*?、尾部点/空格、超长组件）。MSDN 另确认：GetLongPathNameW
# 需要对路径及其各父目录有 List Folder / Read Data / Read Attributes 权限，
# 无法查询时会返回 5（ERROR_ACCESS_DENIED）——这不是「组件不存在」的信号，
# 不得回退。注意：3 也出现在「根本身不可用」的形状（不存在盘符的盘符根
# 实测 3）——回退不得因此把根不可用当成正常缺失，见 _expand_short_names
# 的根终止判定。
_GLPN_NOT_FOUND_ERRORS = frozenset({2, 3})


def _get_long_path_name(path: str) -> str | None:
    """GetLongPathNameW 包装：把「已存在」路径中 8.3 短名组件展开为其
    磁盘长名。仅当 last error 经实测确认属于「路径组件不存在」
    （ERROR_FILE_NOT_FOUND / ERROR_PATH_NOT_FOUND，实测 2 / 3）时返回
    None——调用方 _expand_short_names 向上回退到最长存在前缀，不存在
    的组件逐字保留（不存在的组件不可能有短名，绝不凭空编造展开）。
    其余失败（ERROR_ACCESS_DENIED=5、ERROR_INVALID_NAME=123、意外码）
    一律抛出 OSError（winerror 携带错误码）——fail-loud，绝不静默吞掉。

    必须用 WinDLL("kernel32", use_last_error=True) 并在每次调用前
    set_last_error(0)：ctypes.windll 不能可靠捕获本次调用的 last error
    （其间其他 ctypes 调用可能覆盖它），返回 0 后必须立即
    get_last_error() 读取。

    ctypes argtypes / restype 显式声明（LPCWSTR / LPWSTR / DWORD）：
    ctypes 默认返回类型是 c_int，会把返回值（长度 / 所需缓冲区大小）
    误读为负数或截断，必须声明为 DWORD。MSDN 返回值语义：
    - 成功 → 长名长度（不含 NUL）→ 0 < written < size，取 buffer.value；
    - 缓冲区不足 → 所需缓冲区长度（含 NUL）→ 按该长度重试（必然终止：
      重试后 written = 所需长度 - 1 < size）；
    - 失败 → 0：立即读 GetLastError 分类。2 / 3 → 返回 None（普通不存在
      路径与待创建数据目录实测只会命中这两个码 → 待创建场景始终可正常
      规范化，不会被 fail-loud 阻断）；5 / 123 / 其他 → 抛 OSError。

    已实测评估（tests.test_data_home ShortPathParityTest）：不解析
    junction / 符号链接——返回链接条目自身的长名，保留「不解析符号
    链接」的既有设计语义。"""
    global _long_path_name_w
    if _long_path_name_w is None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetLongPathNameW.argtypes = [
            wintypes.LPCWSTR,  # lpszPath
            wintypes.LPWSTR,   # lpBuffer（create_unicode_buffer 实例）
            wintypes.DWORD,    # cchBuffer
        ]
        kernel32.GetLongPathNameW.restype = wintypes.DWORD
        _long_path_name_w = kernel32.GetLongPathNameW
    get_long_path_name = _long_path_name_w
    size = max(260, len(path) + 1)
    while True:
        buffer = ctypes.create_unicode_buffer(size)
        ctypes.set_last_error(0)
        written = get_long_path_name(path, buffer, size)
        if 0 < written < size:
            return buffer.value
        if written == 0:
            err = ctypes.get_last_error()
            if err in _GLPN_NOT_FOUND_ERRORS:
                return None  # 组件不存在（实测 2 / 3）：调用方向上回退
            # CPython OSError 构造为位置参数（errno, strerror, filename,
            # winerror）——keyword 形式会 TypeError。errno 传 None（未知
            # 语义 errno，刻意不伪装），winerror 保留原始 GetLastError。
            raise OSError(
                None,
                f"GetLongPathNameW failed on {path!r}: GetLastError={err} "
                "(only ERROR_FILE_NOT_FOUND/ERROR_PATH_NOT_FOUND are treated "
                "as missing components)",
                path,
                err,
            )
        size = written + 1  # 缓冲区不足：MSDN 返回所需长度（含 NUL），按它重试


def _expand_short_names(path: str) -> str:
    """把 Windows 8.3 短名表示规范化为长名（非 Windows 下为 no-op）。

    与 dao-sheng.ps1 中 [System.IO.Path]::GetFullPath 的既有行为对齐：
    已存在的组件一律经 GetLongPathNameW 展开为磁盘长名（向上回退到最
    长存在前缀，再把不存在的剩余组件逐字追加——不存在的组件不可能有
    短名）。GitHub Windows runner 的 TEMP 为 C:\\Users\\RUNNER~1\\...，
    PowerShell 报告 C:\\Users\\runneradmin\\...——对完全存在的路径两侧
    产出同一文本（已实测：ShortPathParityTest）。但对「已存在 8.3 短名
    组件 + 不存在叶子」形状，PS 5.1 GetFullPath 的输出受同进程内调用
    顺序影响（本机实测：先调用子路径 → 长形；先对父路径调用 GetFullPath
    再调用子路径 → 短形），该形状的文本 parity 不能无条件宣称；Python
    侧 walk-up 恒展开已存在组件，dao-sheng.ps1 的 Test-PathInsideRepo
    经 Get-CanonicalPathForComparison 采用同样的 walk-up 规范化，保证
    两侧「仓库内」判定对该形状安全一致（tests.test_data_home
    ShortPathDivergenceSafetyTest）。不解析 junction / 符号链接（见
    _get_long_path_name）。

    回退只对探针判定为「确定不存在」（实测错误码 2 / 3）的组件进行。若
    回退到达根（盘符根或 UNC 共享根）而根探针仍报告缺失，说明该根不可
    用——不存在的盘符根，或不可达 / 不存在的 UNC 共享根——这不是「正常
    缺失组件」，必须 fail-loud 抛出 OSError，绝不原样返回输入（与
    dao-sheng.ps1 Get-CanonicalPathForComparison 的根终止判定一致）。
    位于已存在盘符上的正常新建数据目录（缺失叶子 / 中间组件）回退必然
    终止于已验证存在的组件（至少是盘符根本身），不受该规则影响。

    不以「路径文本是否包含 ~」作为判断条件：Windows API 文档明确短文件
    名不一定包含 ~（8.3 合法的长名，其短名就是原名本身，大小写保留），
    因此对 nt 上的路径无条件调用 GetLongPathNameW，由 API 本身决定是否
    需要展开。文本无 ~ 的已存在路径 API 返回同一文本（已实测评估：
    tests.test_data_home ShortPathParityTest
    test_safe83_component_without_tilde），无正确性损失。"""
    if os.name != "nt":
        return path
    remainder: list[str] = []
    current = path
    while True:
        expanded = _get_long_path_name(current)
        if expanded is not None:
            break
        head, tail = os.path.split(current)
        if not tail or head == current:
            # 回退已到达根（盘符根 / UNC 共享根）且根探针报告缺失：不可用
            # 的盘符根或不可达 / 不存在的 UNC 共享根不是正常缺失组件，
            # fail-loud，绝不原样返回输入。
            raise OSError(
                None,
                f"root of {path!r} ({current!r}) could not be verified as "
                "existing: unavailable drive root or missing / unreachable "
                "UNC share root is not a normal missing component",
                path,
            )
        remainder.append(tail)
        current = head
    for tail in reversed(remainder):
        expanded = os.path.join(expanded, tail)
    return expanded


def _normalize_path(path: Path) -> Path:
    """前导 ~ 展开 + 相对路径按当前工作目录解析 + 规范化绝对路径
    （不解析符号链接，与 PowerShell GetFullPath 行为对齐；Windows 下
    已存在组件的 8.3 短名展开为长名，同样与 GetFullPath 的展开行为
    对齐——见 _expand_short_names）。"""
    return Path(_expand_short_names(os.path.abspath(os.path.expanduser(str(path)))))


def _is_inside_repo(path: Path, repo_root: Path) -> bool:
    """路径是否位于 Git worktree（仓库根）内：规范化后做分隔符边界
    比较（等于仓库根，或以「仓库根 + 分隔符」为前缀）；Windows 下
    大小写不敏感（normcase），POSIX 下大小写敏感。两侧均经
    _normalize_path——同一实际位置的短名 / 长名表示判定一致（短形仓库
    根同样能拒绝长形仓库内数据根，反之亦然）。

    边界构造为 root.rstrip(os.sep) + os.sep：仓库根为盘符根时
    （normcase 后为「盘符: + 单一尾分隔符」），直接 root + os.sep 产生
    「盘符: + 双分隔符」，盘符根的直接子路径不以其为前缀 → 盘符根
    仓库的仓库内判定漏判；rstrip 再补一个分隔符保证单一分隔符边界
    （POSIX 根 "/" 同理："/".rstrip("/") + "/" == "/"）。不同盘符的
    路径盘符字符不同，不可能互为前缀，不会误判。不解析符号链接 /
    junction（与 _normalize_path 语义一致，见 test_junction_not_resolved）。"""
    resolved = os.path.normcase(str(_normalize_path(path)))
    root = os.path.normcase(str(_normalize_path(repo_root)))
    if resolved == root:
        return True
    return resolved.startswith(root.rstrip(os.sep) + os.sep)


def resolve_data_home(
    env: Mapping[str, str] | None = None, repo_root: Path = REPO_ROOT
) -> Path:
    """解析外部数据根（与 dao-sheng.ps1 Resolve-DataHome 完全一致）。

    DAO_SHENG_DATA_HOME 非空 → 覆盖；否则默认 Windows
    %LOCALAPPDATA%\\DaoSheng（缺失回退 %USERPROFILE%\\AppData\\Local\\DaoSheng）、
    POSIX $XDG_DATA_HOME/dao-sheng（缺失回退 ~/.local/share/dao-sheng）。
    解析结果位于 Git worktree 内 → RuntimeError fail-loud。"""
    if env is None:
        env = os.environ
    raw = env.get(DATA_HOME_ENV, "")
    if raw and raw.strip():
        data_home = _normalize_path(Path(raw.strip()))
    elif os.name == "nt":
        base = env.get("LOCALAPPDATA", "").strip()
        if not base:
            base = str(_normalize_path(Path("~") / "AppData" / "Local"))
        data_home = _normalize_path(Path(base) / "DaoSheng")
    else:
        xdg = env.get("XDG_DATA_HOME", "").strip()
        base = Path(xdg) if xdg else Path("~/.local/share")
        data_home = _normalize_path(base / "dao-sheng")
    if _is_inside_repo(data_home, repo_root):
        raise RuntimeError(
            f"数据根位于 Git worktree 内（{data_home}）：个人运行时数据必须"
            "位于仓库之外，普通源码升级才会与个人数据隔离。将 "
            f"{DATA_HOME_ENV} 指向仓库外目录，或取消该变量以使用默认外部"
            "数据根（未写入任何数据）。"
        )
    return data_home


def find_legacy_repo_data(repo_root: Path) -> list[Path]:
    """检测旧版布局遗留在 Git worktree 内的个人运行时数据（instances/、
    config/、log/ 下任意文件）。只读检测：不覆盖、不删除、不自动重置。"""
    found: list[Path] = []
    for rel in LEGACY_DATA_DIRS:
        directory = repo_root / rel
        if not directory.is_dir():
            continue
        found.extend(path for path in sorted(directory.rglob("*")) if path.is_file())
    return found


def load_instance_root(data_home: Path, repo_root: Path = REPO_ROOT) -> Path:
    """读取安装层元数据中的实例根（<data_home>/config/install-state.json）。

    fail-loud 三态：
    - 数据根元数据缺失 + 仓库内检测到遗留个人数据 → 迁移提示（绝不静默
      在新数据根启动空白实例让用户以为数据还在）；
    - 数据根元数据缺失 + 无遗留数据 → 常规 install 提示；
    - 记录的 instance_root 位于仓库内 → 拒绝。
    """
    state_path = data_home / "config" / "install-state.json"
    if not state_path.is_file():
        legacy = find_legacy_repo_data(repo_root)
        if legacy:
            sample = "; ".join(str(path) for path in legacy[:5])
            raise RuntimeError(
                f"安装层元数据缺失（{state_path}），且检测到旧版布局遗留在 "
                f"Git worktree 内的个人运行时数据（{len(legacy)} 个文件，"
                f"例如：{sample}）。Runtime 不会在仓库内启动实例，也不会"
                "静默在新数据根创建空白实例——遗留数据不会被覆盖、删除或"
                "自动重置。先执行 .\\dao-sheng.ps1 migrate-data 将遗留数据"
                "迁移到外部数据根（不覆盖任何既有目标），再执行 "
                ".\\dao-sheng.ps1 install。"
            )
        raise RuntimeError(
            f"安装层元数据缺失（{state_path}）：先执行 .\\dao-sheng.ps1 install"
        )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    instance_root = Path(state["instance_root"])
    if _is_inside_repo(instance_root, repo_root):
        raise RuntimeError(
            f"install-state.json 记录的 instance_root 位于 Git worktree 内"
            f"（{instance_root}）：个人运行时数据必须位于仓库之外。执行 "
            ".\\dao-sheng.ps1 migrate-data 迁移遗留实例数据后重新 install。"
        )
    return instance_root


def load_model_config(data_home: Path) -> ModelConfig:
    """读取运行配置（<data_home>/config/model-config.json，ModelConfig
    槽位同名 JSON）。

    缺失 = 未配置：返回全 None ModelConfig（U-5——入口不预设任何模型 /
    endpoint；compose 两侧 None → 回合降级，可诊断）。
    """
    config_path = data_home / "config" / "model-config.json"
    if not config_path.is_file():
        return ModelConfig()
    doc = json.loads(config_path.read_text(encoding="utf-8"))
    return ModelConfig(**doc)


def load_host_config(data_home: Path) -> HostConfig:
    """读取 host 部署配置（<data_home>/config/host-config.json，HostConfig
    槽位同名 JSON；阶段 D，决定 D-055）。

    缺失 = 未配置：返回全 None HostConfig（U-5——入口不预设任何宿主
    位置；compose 校验不通过 → 不装配 host，assembly.host=None）。
    槽位值 = 路径字符串 → Path（JSON 无法表达 Path）。
    """
    config_path = data_home / "config" / "host-config.json"
    if not config_path.is_file():
        return HostConfig()
    doc = json.loads(config_path.read_text(encoding="utf-8"))
    slots = {
        key: (Path(value) if value is not None else None)
        for key, value in doc.items()
    }
    return HostConfig(**slots)


def run_turn(
    assembly: RuntimeAssembly, content: str
) -> tuple[TurnOutcome, str]:
    """一个完整回合：act → persist（严格交替，决定 ⑬）。返回 outcome + reference。"""
    outcome = assembly.individual.act(
        Turn(content=content, memory_origin=MemoryOrigin.EXTERNAL)
    )
    reference = assembly.individual.persist()
    return outcome, reference


def run_growth(assembly: RuntimeAssembly, reference: str) -> int:
    """成长触发入口（阶段 C，决定 D-054）：对一条既有经历记录显式运行
    现有成长管线一次（Growth 公共表面恰 5 方法，决定 ㉗；canonical 顺序
    同 STEP 15 真实验证先例：digest / extract / reflect 作用于经历
    reference，verify_insight 作用于 extract 的 insight reference）。

    不新建 Growth Engine / 调度器 / 后台循环——只调用既有公共表面。
    降级阶段 = None（决定 ㉕）。返回退出码：0 = 全部阶段产出；
    1 = 任一阶段降级；2 = reference 缺失（M05 get 契约 fail-loud）。
    """
    if assembly.reflection_model is None:
        print(
            "Reflection 模型未配置（数据根 config/model-config.json reflection 侧未设定）："
            "成长阶段将全部降级。"
        )
    print(f"成长触发：经历 reference = {reference}")
    try:
        digest_ref = assembly.growth.digest(reference)
        insight_ref = assembly.growth.extract(reference)
        reflect_ref = assembly.growth.reflect(reference)
        verify_ref = (
            assembly.growth.verify_insight(insight_ref)
            if insight_ref is not None
            else None
        )
    except ValueError as e:
        print(f"成长触发失败（reference 无效）：{e}", file=sys.stderr)
        return 2

    degraded = False
    for name, ref in (
        ("digest", digest_ref),
        ("extract", insight_ref),
        ("reflect", reflect_ref),
        ("verify_insight", verify_ref),
    ):
        if ref is None:
            degraded = True
            print(f"{name}：（降级——手段未装配 / 不可用 / 空输出；不写、不追加）")
        else:
            record = assembly.memory.get(ref)
            print(
                f"{name}：reference={ref}"
                f" origin={record.memory_origin.value}"
                f" status={record.memory_status.value}"
                f" confidence={record.memory_confidence.value}"
            )
    return 1 if degraded else 0


def run_observe(
    assembly: RuntimeAssembly, relative_path: str
) -> tuple[FileObservation, TurnOutcome, str]:
    """观察触发入口（阶段 D，决定 D-055）：FileWorld 只读观察一个明确
    授权的相对路径（root = 部署层注入 REPO_ROOT，K-07 保留条件 1 /
    R-09；逃逸 = ValueError fail-loud）→ 观察事实文本（仅元数据，
    K-08 观察 ≠ 判断，不读文件内容）→ 现有 M04 回合入口
    act(Turn(观察事实, MemoryOrigin.EXTERNAL)) → persist（严格交替，
    决定 ⑬；经现有 persist 路径写入个体 Memory 载体）。

    不新建 World Engine / 监控服务 / 后台调度器——只调用既有公共表面
    （FileWorld 表面恰 observe，M06 棘轮）。返回观察 + 回合结果 +
    经历记录 reference。
    """
    world = FileWorld(REPO_ROOT)
    observation = world.observe(relative_path)
    fact = (
        "世界观察（FileWorld 只读元数据）："
        f"path={observation.path}"
        f" exists={observation.exists}"
        f" is_file={observation.is_file}"
        f" size={observation.size}"
    )
    outcome = assembly.individual.act(
        Turn(content=fact, memory_origin=MemoryOrigin.EXTERNAL)
    )
    reference = assembly.individual.persist()
    return observation, outcome, reference


def run_host_sync(assembly: RuntimeAssembly) -> int:
    """Host 同步触发入口（阶段 D，决定 D-055）：显式运行现有 host
    adapter 的 sync() 一次（M09 S4：重新解析状态位置 + 重导入新增
    内容；宿主侧幂等 = 导入日志 append-only）。不是调度器、不是后台
    循环——每次同步由用户明确下达。

    host 未装配（数据根 config/host-config.json 缺失或未完整配置）→ 可诊断
    信息 + 退出码 2。同步完成 → 退出码 0（新增 = 0 也是正常结果：
    幂等复跑）。
    """
    if assembly.host is None:
        print(
            "Host 未配置（数据根 config/host-config.json 缺失或未完整配置）："
            "host adapter 未装配，不执行同步。",
            file=sys.stderr,
        )
        return 2
    report = assembly.host.sync()
    print(f"Host 同步：状态位置 {len(report.state_locations)} 个")
    for location in report.state_locations:
        print(f"  - {location}")
    print(f"新增经历记录引用：{len(report.new_references)} 条")
    for ref in report.new_references:
        print(f"  - reference={ref}")
    return 0


def main(argv: list[str]) -> int:
    try:
        data_home = resolve_data_home()
    except (OSError, RuntimeError) as e:
        # OSError：_get_long_path_name 对权限拒绝 / 意外错误码 fail-loud
        # （见其 docstring）——同样按配置非法诊断，绝不静默继续。
        print(f"数据根配置非法：{e}", file=sys.stderr)
        return 2
    try:
        instance_root = load_instance_root(data_home, REPO_ROOT)
    except (OSError, ValueError, KeyError, RuntimeError) as e:
        print(f"配置缺失：{e}", file=sys.stderr)
        return 2
    try:
        model_config = load_model_config(data_home)
    except (OSError, ValueError, TypeError) as e:
        print(f"运行配置非法（{data_home / 'config' / 'model-config.json'}）：{e}", file=sys.stderr)
        return 2
    try:
        host_config = load_host_config(data_home)
    except (OSError, ValueError, TypeError) as e:
        print(f"运行配置非法（{data_home / 'config' / 'host-config.json'}）：{e}", file=sys.stderr)
        return 2
    try:
        assembly = compose(
            principles_source_path=REPO_ROOT / "docs" / "constitution" / "principles.md",
            individual_root=instance_root,
            model_config=model_config,
            operational_defaults=OperationalDefaults(),
            host_config=host_config,
        )
    except (RuntimeError, ValueError) as e:
        print(f"装配失败：{e}", file=sys.stderr)
        return 2

    if assembly.model is None:
        print("模型未配置（数据根 config/model-config.json 缺失或全未设定）：本回合将为降级回合。")
    else:
        print(
            f"模型后端：{model_config.agent_backend} @ {model_config.agent_endpoint}"
            f"（model={model_config.agent_model}）"
        )

    if argv[1:2] == ["--observe"]:
        # 观察触发入口（决定 D-055）：FileWorld 只读观察一个明确授权的
        # 相对路径，观察事实经现有 M04 回合入口进入个体经验流。
        relative_path = argv[2].strip() if len(argv) > 2 else ""
        if not relative_path:
            print("--observe 需要观察的相对路径：不执行观察。", file=sys.stderr)
            exit_code = 2
        else:
            try:
                observation, outcome, reference = run_observe(assembly, relative_path)
            except ValueError as e:
                print(f"观察失败（路径越界或无效）：{e}", file=sys.stderr)
                exit_code = 2
            else:
                print(
                    f"观察：exists={observation.exists}"
                    f" is_file={observation.is_file} size={observation.size}"
                )
                print(f"  path={observation.path}")
                if outcome.action is None:
                    print(
                        "行动：（降级回合——模型未配置或不可用；"
                        "观察已经 persist 路径记录）"
                    )
                    exit_code = 1
                else:
                    print(f"行动：\n{outcome.action}")
                    exit_code = 0
                print(f"观察经历记录 reference：{reference}")
    elif argv[1:2] == ["--sync-host"]:
        # Host 同步触发入口（决定 D-055）：现有 host adapter sync() 一次。
        exit_code = run_host_sync(assembly)
    elif argv[1:2] == ["--grow"]:
        # 成长触发入口（决定 D-054）：不执行回合，只对既有经历记录运行
        # 成长管线一次。
        reference = argv[2].strip() if len(argv) > 2 else ""
        if not reference:
            print("--grow 需要经历记录 reference：不执行成长。", file=sys.stderr)
            exit_code = 2
        else:
            exit_code = run_growth(assembly, reference)
    else:
        task = " ".join(argv[1:]).strip()
        if not task:
            try:
                task = input("向道生提交一项任务：").strip()
            except EOFError:
                task = ""  # 非交互 stdin 且无 argv：走下方空任务诊断路径
        if not task:
            print("任务为空：不执行回合。", file=sys.stderr)
            close = getattr(assembly.memory, "close", None)
            if close is not None:
                close()
            return 2

        outcome, reference = run_turn(assembly, task)
        print(f"回合 {outcome.turn_number}")
        if outcome.action is None:
            print("行动：（降级回合——模型未配置或不可用；经历已经 persist 路径记录）")
            exit_code = 1
        else:
            print(f"行动：\n{outcome.action}")
            exit_code = 0
        print(f"经历记录 reference：{reference}")

    close = getattr(assembly.memory, "close", None)
    if close is not None:
        close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
