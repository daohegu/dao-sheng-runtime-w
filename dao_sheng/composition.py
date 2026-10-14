"""Composition root —— V1 唯一装配点（无调用方）。

依据：spec-composition-root.md §1/§2/§3、component-model.md §1、
R-09（accept don't create）、ADR 0002 / 0004 / 0005。

- 装配：Individual（M04 已接入：决定 ⑬ 起）及其全部依赖在此构造并注入
  （其余依赖逐步接入）；
  任何组件不自建依赖（R-09）。
- 装配时只读加载："道"设计层成文来源（ADR 0005）+ Identity 载体
  （M02：读取 / 校验 / 投影为只读 Identity；缺失或非法 → fail-loud）
  + Faculties 载体（M03 决定 ④：读取 / 校验 / 投影；缺失或非法 →
  fail-loud 不代建）+ Continuity 载体（M03 决定 ③：装配时校验；
  缺失 = 空日志；损坏 → fail-loud；投影不随装配结果携带——装配时
  快照会陈旧，消费方按需 load_continuity 读取，M04 / M07 接线）+ Memory
  Provider（M05 决定 ⑥：embedded SQLite 构造；目录 / DB 缺失 = 初始态，
  Provider 自建，ADR 0007——与 identity / faculties 载体的 fail-loud
  语义不同；目录创建在 memory_sqlite 内，本模块无写 marker）+ Model
  调用 adapter（M06 + ADR 0008：agent / reflection 两侧独立构造，逐侧
  backend dispatch（进程内 registry `_MODEL_BACKENDS`）；backend /
  endpoint / model 全未设 → 两侧 None（U-5 不预设）；部分设定 / 未知
  backend → fail-loud；构造规则见 `_build_model_client`）+ host 集成 adapter（M09 S5：HermesHostAdapter，
  唯一知道宿主名的层，ADR 0002 决定 1；声明位 HostConfig 全部未设定 →
  None（U-5 不预设）；部分设定 / 互斥 → fail-loud，规则见
  `_validate_host_config`）。Research / world 观察不接装配（M06 决定 ⑫：
  Research 后端未定、world root 无声明位——M04 按需要时接入）。
- 不设独立 life 层（ADR 0004 决定 1）。
- 声明位：Model 配置（M-1…M-3 / M-6 审计项的归位，U-5 不预设）、
  host 集成配置（M09 S5：HostConfig 声明位，U-5 不预设）、
  L4 运营策略默认值（principles.md 四层模型 L4；当前无已定值）、
  "DaoSheng 与 host 的关系"表述（M-04 / ADR 0002 决定 4 / R-12）。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path

from dao_sheng.capability_lifecycle import CapabilityManager
from dao_sheng.capability_verifier import CapabilityVerifier
from dao_sheng.continuity import append_continuity, load_continuity
from dao_sheng.doctrine import Doctrine, parse_doctrine
from dao_sheng.faculties import Faculties, parse_faculties
from dao_sheng.growth import ExperienceCandidate, Growth
from dao_sheng.hermes_host import HermesHostAdapter
from dao_sheng.identity import Identity, parse_identity
from dao_sheng.individual import Individual
from dao_sheng.layout import IndividualFiles
from dao_sheng.memory import (
    Correction,
    MemoryConfidence,
    MemoryOrigin,
    MemoryStatus,
    MemoryStore,
)
from dao_sheng.memory_sqlite import SqliteMemoryProvider
from dao_sheng.model import Model, ModelUnavailable
from dao_sheng.model_ollama import OllamaModel
from dao_sheng.model_llama_cpp import LlamaCppModel

#: "DaoSheng 与 host 的关系"表述 —— 声明位（M-04 / ADR 0002 决定 4 / R-12）。
#: 本常量是 V1 代码中该表述的唯一出现位置（启动配置描述，非 prompt 内容）；
#: 不得进入 Core 生成的任何文本（spec-individual.md §5.1）。
HOST_RELATION_STATEMENT = (
    "DaoSheng 运行于独立的 DaoSheng Runtime 进程，拥有并管理个体持久文件；"
    "host 进程（Hermes Desktop）不直接触碰 DaoSheng 的个体持久文件，"
    "两进程之间的全部交互经由 DaoSheng Runtime 内的 host 集成层进行。"
)


@dataclass(frozen=True)
class ModelConfig:
    """Model 配置声明位（spec-composition-root.md §3；审计项 M-1…M-3 /
    M-6；ADR 0008：逐侧 backend 选择）。

    全部槽位 None = 未设定：Model 部署形态 = UNKNOWN（U-5），具体值
    （backend / 端点 / 超时 / 重试 / Research 后端选择）由部署层在实现
    阶段给出；adapter 不自带默认值，本声明位不预设任何值（规则 11；
    无默认 backend——backend 名 = 结构性 adapter 标识，由部署层显式
    选择）。
    """

    agent_endpoint: str | None = None
    agent_model: str | None = None
    agent_backend: str | None = None
    reflection_endpoint: str | None = None
    reflection_model: str | None = None
    reflection_backend: str | None = None
    timeout_seconds: float | None = None
    retry_limit: int | None = None
    research_backend: str | None = None


@dataclass(frozen=True)
class HostConfig:
    """host 集成配置声明位（spec-composition-root.md §3；M09 S5）。

    全部槽位 None = 未设定：宿主部署形态 = UNKNOWN（U-5），具体值
    （状态库位置 / 宿主根 / 导入日志位置 / 裁定日志位置）由部署层给出；
    声明位不预设任何值（规则 11）。状态位置两槽互斥（只可配置其一）；
    布局知识归宿主 adapter 层（ADR 0002 决定 1），本声明位只传位置。
    adjudication_log（D-058 / ADR 0010 修订 Decision 12）= 人工冲突裁
    定日志位置（`host/adjudications.jsonl` 形态，与导入日志同宿主目录、
    完全分离）；None = 未配置 → 冲突组永远 fail-loud（最严格缺省，无硬
    编码隐式默认——R-09）。
    """

    state_db: Path | None = None
    hermes_home: Path | None = None
    import_log: Path | None = None
    adjudication_log: Path | None = None


@dataclass(frozen=True)
class OperationalValue:
    """一条 L4 运营策略参数（名 + 值）。"""

    name: str
    value: object


@dataclass(frozen=True)
class OperationalDefaults:
    """L4 运营策略默认值声明位（spec-composition-root.md §1）。

    空 = 全部未设定：当前 V1 无已定参数值，均为部署层待设项，不预设
    （principles.md 各条 L4 层；U-5 / 规则 11）。属运营策略，不是 Domain
    决定。可调项清单见 principles.md 各条 L4 层（调度频率、上限值等）。
    """

    entries: tuple[OperationalValue, ...] = ()


@dataclass(frozen=True)
class RuntimeAssembly:
    """装配结果：DaoSheng Runtime 的当前组件集合（M01：骨架）。

    M04 已接入 Individual（individual：顶层聚合，act / persist 双入口，
    R-01；构造仅本装配点，R-09；决定 ⑬ 起）。
    M05 已接入 Memory Provider（memory，决定 ⑥；仅本模块构造，R-09）。
    M06 已接入 Model 调用 adapter（model / reflection_model：
    `Model | None`——Model Backend Adapter，逐侧 backend dispatch
    （ADR 0008 决定 1/2；进程内 registry `_MODEL_BACKENDS`），实现
    Model Interface（`dao_sheng.model`），构造规则见
    `_build_model_client`；Research / world 观察不随装配——后端未定 /
    无声明位，M04 按需要时接入，M06 决定 ⑫）。
    M07 已接入 Growth 成长管线（growth，决定 ⑳–㉗：8 项依赖全部由本
    装配点注入——append 通道 = M03 唯一写入口绑定 continuity 载体路径
    的函数值，M03 决定 ⑤ 唯一调用方）。
    M08 已接入 Capability Manager（capability_manager，决定 ㉘–㉚：生命周期
    唯一权威；载体 = 四目录 adapter 形态，个体持久文件清单项 4；闸门 =
    M11 唯一实现 CapabilityVerifier 由本装配点注入——advance working →
    active 与 execute 均经闸门（K-05 / INV-11），拒绝 → 不可达 active /
    执行被阻，M11 决定 ㊱–㊴）。
    M09 已接入 host 集成 adapter（host：`HermesHostAdapter | None`，S5；
    唯一知道宿主名的层，ADR 0002 决定 1；全部未设定 = None，U-5）。
    其余依赖（Research adapter）逐步接入。

    注意：不携带 Continuity 投影——装配时快照会在追加后陈旧；消费方
    （M04 / M07）按需 load_continuity 读取。
    """

    doctrine: Doctrine
    identity: Identity
    faculties: Faculties
    memory: MemoryStore
    individual: Individual
    growth: Growth
    capability_manager: CapabilityManager
    individual_files: IndividualFiles
    model: Model | None
    reflection_model: Model | None
    model_config: ModelConfig
    operational_defaults: OperationalDefaults
    host: HermesHostAdapter | None


#: Model Backend registry（ADR 0008 裁定 ①：进程内配置解析 / 装配层——
#: 无持久化注册文件、非 DaoSheng Core 组件）：backend 名 → adapter 类。
#: 当前仅允许两个 Backend 形态（ADR 0008 决定 2/3）；引入第三形态 →
#: ADR（规则 8）。
_MODEL_BACKENDS: dict[str, type[OllamaModel] | type[LlamaCppModel]] = {
    "ollama": OllamaModel,
    "llama_cpp": LlamaCppModel,
}


def _build_model_client(
    role: str,
    backend: str | None,
    endpoint: str | None,
    model: str | None,
    timeout_seconds: float | None,
    retry_limit: int | None,
) -> Model | None:
    """一侧 Model 调用 adapter 的构造规则（M06 决定 ⑪ + ADR 0008：
    逐侧 backend dispatch）。

    - backend / endpoint / model 全未设定 → 该侧 None（U-5：无默认
      backend，部署值由部署层给出，不预设、不代建）；
    - 未知 backend 名 → fail-loud（仅允许 registry 内形态）；
    - 部分设定（含共享的 timeout_seconds / retry_limit 缺失）→
      fail-loud（坏配置不得进装配结果）；
    - 两侧（agent / reflection）独立判定、允许异 backend（ADR 0008
      裁定 ②）；共享 timeout / retry 槽位。
    """
    if backend is None and endpoint is None and model is None:
        return None
    if backend is not None and backend not in _MODEL_BACKENDS:
        raise RuntimeError(
            f"未知 Model backend（{role}）：{backend}——"
            f"仅允许 {' / '.join(_MODEL_BACKENDS)}"
        )
    missing = [
        name
        for name, value in (
            ("backend", backend),
            ("endpoint", endpoint),
            ("model", model),
            ("timeout_seconds", timeout_seconds),
            ("retry_limit", retry_limit),
        )
        if value is None
    ]
    if missing:
        raise RuntimeError(
            f"Model 配置不完整（{role}）：缺少 {' / '.join(missing)}——"
            "全部设定或全部不设定（U-5：未设定 = 该侧 adapter 不装配）"
        )
    adapter_cls = _MODEL_BACKENDS[backend]
    return adapter_cls(
        endpoint=endpoint,
        model=model,
        timeout_seconds=timeout_seconds,
        retry_limit=retry_limit,
    )


def _validate_host_config(config: HostConfig) -> bool:
    """host 集成声明位校验规则（M09 S5；同 `_build_model_client` 精神：
    全部未设定，或完整设定）。

    - 三槽全部 None → 不装配（U-5：宿主部署形态 UNKNOWN，不预设）；
    - 状态库位置 / 宿主根互斥（只可配置其一）且须恰好配置其一；
    - import_log（宿主侧导入日志位置，宿主层幂等状态，spec-individual.md
      §2.3）必须设定；
    - adjudication_log（D-058 / ADR 0010 修订 Decision 12，人工冲突裁
      定日志）可选：None = 未配置 → 冲突组永远 fail-loud（无硬编码隐式
      默认，R-09）；设定则必须与 import_log 同宿主目录（该实例 host/
      目录，裁定日志与导入日志完全分离但同属一个实例宿主目录）。

    部分设定 / 互斥 = 坏配置 → fail-loud（坏配置不得进装配结果）。
    返回 True = 应装配 adapter。
    """
    if (
        config.state_db is None
        and config.hermes_home is None
        and config.import_log is None
    ):
        return False
    problems: list[str] = []
    if config.state_db is not None and config.hermes_home is not None:
        problems.append("状态库位置与宿主根互斥（只可配置其一）")
    if config.state_db is None and config.hermes_home is None:
        problems.append("状态库位置 / 宿主根（恰好其一）")
    if config.import_log is None:
        problems.append("import_log（宿主侧导入日志位置）")
    if (
        config.adjudication_log is not None
        and config.import_log is not None
        and config.adjudication_log.parent != config.import_log.parent
    ):
        problems.append(
            "adjudication_log 须与 import_log 同宿主目录（该实例 host/ "
            "目录；裁定日志与导入日志分离但同属实例宿主目录）"
        )
    if problems:
        raise RuntimeError(
            f"Host 配置不完整：{' / '.join(problems)}——"
            "全部未设定或完整设定（U-5：未设定 = host adapter 不装配）"
        )
    return True


def compose(
    *,
    principles_source_path: Path,
    individual_root: Path,
    model_config: ModelConfig,
    operational_defaults: OperationalDefaults,
    host_config: HostConfig,
) -> RuntimeAssembly:
    """装配函数：全部依赖注入（R-09：accept don't create）。

    - principles_source_path：设计层成文单一来源（只读；ADR 0005）。
    - individual_root：个体持久文件清单的 root（部署层值）；其下的
      identity 载体 root/"identity.json" 须先由设计层初始化（data-ownership：
      Identity 仅设计层可写），缺失或非法 → 装配显式失败。
    - model_config / host_config / operational_defaults：由部署层构造后
      注入（无默认值）。
    """
    doctrine = parse_doctrine(principles_source_path.read_text(encoding="utf-8"))
    individual_files = IndividualFiles.layout(individual_root)
    identity_path = individual_files.identity
    if not identity_path.is_file():
        # Identity 载体由设计层初始化（data-ownership：仅设计层可写）；
        # Runtime 不预设、不代建（规则 11）——缺失即显式失败。
        raise RuntimeError(
            f"Identity 载体缺失（{identity_path}）：须先由设计层初始化"
        )
    identity = parse_identity(identity_path.read_text(encoding="utf-8"))
    faculties_path = individual_files.faculties
    if not faculties_path.is_file():
        # Faculties 载体由设计层初始化（内容 = 域常量，USER_RATIFIED；
        # 同批 identity 载体）；Runtime 不预设、不代建（规则 11）
        # ——缺失即显式失败（M02 决定 ② 对齐）。
        raise RuntimeError(
            f"Faculties 载体缺失（{faculties_path}）：须先由设计层初始化"
        )
    faculties = parse_faculties(faculties_path.read_text(encoding="utf-8"))
    # Continuity 装配时只校验（决定 ⑤ 装配面）：缺失 = 空日志（初始状态），
    # 损坏 → fail-loud；投影不随装配结果携带（快照会陈旧——消费方按需
    # load_continuity 读取，M04 / M07 接线）。
    load_continuity(individual_files.continuity)
    # Model 调用 adapter（M06）：两侧独立构造，仅装配点（R-09）；
    # 全未设 → 两侧 None（U-5 不预设），部分设定 → fail-loud。
    # 置于 Memory Provider 构造之前：坏配置在分配任何资源前 fail-loud
    # （失败路径不得泄漏未关闭的 Provider）。
    model = _build_model_client(
        "agent",
        model_config.agent_backend,
        model_config.agent_endpoint,
        model_config.agent_model,
        model_config.timeout_seconds,
        model_config.retry_limit,
    )
    reflection_model = _build_model_client(
        "reflection",
        model_config.reflection_backend,
        model_config.reflection_endpoint,
        model_config.reflection_model,
        model_config.timeout_seconds,
        model_config.retry_limit,
    )
    # host 集成声明位校验（M09 S5）：置于 Memory Provider 构造之前——
    # 坏配置在分配任何资源前 fail-loud（同 Model 构造规则，失败路径
    # 不得泄漏未关闭的 Provider）。
    host_enabled = _validate_host_config(host_config)
    # Memory Provider（M05 决定 ⑥）：embedded SQLite 构造，仅装配点（R-09）。
    # 目录 / DB 缺失 = 初始态（新建个体，空记忆）——Provider 自建，不读
    # 任何外部存储（ADR 0007）；与 identity / faculties 载体的 fail-loud
    # 语义不同（设计层初始化 vs 初始态自建）。
    memory = SqliteMemoryProvider(individual_files.memory_dir)
    # Individual（M04 决定 ⑬ 起）：顶层聚合构造仅装配点（R-09）；依赖 =
    # 本装配已构造的全部组件 + continuity 载体路径（读通道，决定 ⑱）+
    # agent 侧 model（未装配 = None → 全部回合降级，决定 ⑯）。
    individual = Individual(
        doctrine=doctrine,
        identity=identity,
        faculties=faculties,
        continuity_file=individual_files.continuity,
        memory=memory,
        model=model,
    )
    # Growth（M07 决定 ⑳–㉗）：成长管线构造仅装配点（R-09）；8 项依赖
    # 全部注入（决定 ㉒）：memory（6 方法契约实例）+ append_continuity
    # （M03 唯一写入口经 partial 绑定 continuity 载体路径 = 注入通道，
    # 唯一调用方 = 管线，M03 决定 ⑤）+ reflection 侧 model（未装配 =
    # None → 全部阶段降级，决定 ㉕）+ 三维枚举 / 修正记录 / 异常类型
    # （类型注入，growth.py 零 dao_sheng import）。
    growth = Growth(
        memory=memory,
        append_continuity=partial(append_continuity, individual_files.continuity),
        reflection_model=reflection_model,
        origin=MemoryOrigin,
        status=MemoryStatus,
        confidence=MemoryConfidence,
        correction=Correction,
        unavailable=ModelUnavailable,
    )
    # Hermes 宿主 adapter（M09 S5 / ADR 0002 决定 1）：唯一知道宿主名的
    # 层，仅装配点构造（R-09）；导入通道 = growth.import_experience（绑
    # 定方法值注入，经验回流接成长管线，M07）；候选类型 / origin 枚举类
    # 型注入（同 Growth 类型注入面——hermes_host.py 不 import memory 类
    # 型）；声明位全部未设定（U-5）→ None。
    if host_enabled:
        host = HermesHostAdapter(
            state_db=host_config.state_db,
            hermes_home=host_config.hermes_home,
            import_log=host_config.import_log,
            adjudication_log=host_config.adjudication_log,
            import_channel=growth.import_experience,
            candidate=ExperienceCandidate,
            origin=MemoryOrigin,
        )
    else:
        host = None
    # Capability 闸门（M11 决定 ㊱–㊴）：执行前闸门唯一实现，仅装配点构造
    # （R-09）；memory 6 方法契约实例注入（判据 2/3 读通道）；规则式
    # model-free——默认配置（无 model，U-5）下可闭环（AC 6）。
    capability_verifier = CapabilityVerifier(memory=memory)
    # Capability Manager（M08 决定 ㉘–㉚）：生命周期唯一权威仅装配点构造
    # （R-09）；载体根 = 个体持久文件清单项 4（layout 已落地
    # capabilities_dir）；memory = 提案源记录读通道（6 方法契约）；
    # verifier = M11 闸门（K-05 / INV-11）：advance working → active 与
    # execute 均经闸门；拒绝 → 不可达 active / 执行被阻。
    capability_manager = CapabilityManager(
        capabilities_dir=individual_files.capabilities_dir,
        memory=memory,
        verifier=capability_verifier,
    )
    return RuntimeAssembly(
        doctrine=doctrine,
        identity=identity,
        faculties=faculties,
        memory=memory,
        individual=individual,
        growth=growth,
        capability_manager=capability_manager,
        individual_files=individual_files,
        model=model,
        reflection_model=reflection_model,
        model_config=model_config,
        operational_defaults=operational_defaults,
        host=host,
    )
