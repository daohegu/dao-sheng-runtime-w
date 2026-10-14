"""Ollama Backend Adapter —— 个体的认知手段（Model 调用；M06 / ADR 0008
决定 2；spec-adapters §2 / INV-1）。

依据：spec-adapters.md §2（chat / complete 两级调用；HTTP 细节、超时、
默认值 M-1…M-3 全部隐藏 = depth）、ADR 0008（决定 2：本模块 = Ollama
Backend Adapter；决定 4：Model 调用 seam hypothetical → real）、ADR 0009
（transport / 重试 / 退避 / JSON 边界 / 契约校验调位至共享 Wire Client
`dao_sheng/model_wire.py`；本 adapter 保留 wire 固有 = endpoint path /
payload shape / extract）、INV-1（Model 重启对个体无影响：重连 / 退避 =
手段内部行为，不暴露给 Core）、R-09（endpoint / model / timeout / retry
全部注入，无默认值——默认值声明位在 composition root，M-1…M-3 归位）、
U-5（部署形态 UNKNOWN，不预设任何具体值）。

- wire 形态（决定 ⑨）= Ollama native /api/*（V0 Model 调用部署面的
  全部执行证据形态：OllamaModel → /api/generate + OllamaReflection →
  /api/chat，完整证据路径见票 06 Comments / RECONSTRUCTION.md）；这是
  adapter 内部细节（depth 隐藏），不是部署决定；「若出现第二协议形态使
  seam 转 real → 按规则 8 立 ADR」触发条件已由 ADR 0008 履行（第二
  协议形态 llama.cpp 出现，seam 已 real）。
- 重试 / 退避（决定 ⑩ → ADR 0009 调位）：transport 语义（连接失败 /
  超时 / 5xx = 重启窗口指数退避重试至 retry_limit 耗尽 →
  ModelUnavailable；4xx = 服务端拒绝不重试；JSON decode / extract 失败 /
  契约违规不重试）调位至 Wire Client 单一实现位（ADR 0009 Decision 2 /
  5）；本 adapter 保留 wire 固有 = endpoint path / payload shape /
  extract（协议差异留在 adapter，Decision 2）。
- 本模块从 `dao_sheng.model_wire` 导入 `validate_config`（构造即
  fail-loud 的共享 config validation，Decision 4）与 `post_json`（一次
  wire 调用，Decision 3）；Model 出站通道（`urlopen`）调位至 Wire
  Client（M09 棘轮显式调位，ADR 0009 Decision 7；本 adapter 不再直接
  出站）。`ModelUnavailable` 由 Wire Client 抛出（唯一定义位 =
  `dao_sheng.model`，ADR 0008 决定 1），本模块不再引用。
"""

from __future__ import annotations

from collections.abc import Sequence

from dao_sheng.model_wire import post_json, validate_config


class OllamaModel:
    """Ollama Backend Adapter（实现 Model Interface——`dao_sheng.model.
    Model`，结构化符合，不要求继承；ADR 0008 决定 2）。

    公共表面恰为两级调用：`complete`（补全：prompt → 续写）与
    `chat`（会话：(role, content) 序列 → 回复）——interface = test
    surface（depth：wire 细节 / 重试 / 超时全部内化）。
    """

    def __init__(
        self,
        endpoint: str,
        model: str,
        timeout_seconds: float,
        retry_limit: int,
    ):
        """全部参数注入、无默认值（R-09；M-1…M-3：默认值不随 adapter）。

        非法配置在装配点 fail-loud（ValueError）：不携带坏配置运行——
        校验语义调位至共享 `validate_config`（ADR 0009 Decision 4）。
        """
        validate_config(endpoint, model, timeout_seconds, retry_limit)
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retry_limit = retry_limit

    def complete(self, prompt: str) -> str:
        """补全调用：prompt → 模型续写（wire = /api/generate，内化细节）。"""
        if not prompt or not prompt.strip():
            raise ValueError("prompt 不得为空")
        return post_json(
            self.endpoint,
            self.timeout_seconds,
            self.retry_limit,
            "/api/generate",
            {"model": self.model, "prompt": prompt, "stream": False},
            lambda data: data["response"],
        )

    def chat(self, messages: Sequence[tuple[str, str]]) -> str:
        """会话调用：(role, content) 序列 → 模型回复（wire = /api/chat）。

        调用方以 `(role, content)` 二元组给出完整消息序列（含最后一轮
        user 消息）；不预设任何 system 前缀——上下文组织是 Core 的事，
        adapter 不代 Core 做判断（手段不得定义个体，INV-1 同一纪律）。
        """
        if not messages:
            raise ValueError("messages 不得为空")
        return post_json(
            self.endpoint,
            self.timeout_seconds,
            self.retry_limit,
            "/api/chat",
            {
                "model": self.model,
                "messages": [
                    {"role": role, "content": content}
                    for role, content in messages
                ],
                "stream": False,
            },
            lambda data: data["message"]["content"],
        )
