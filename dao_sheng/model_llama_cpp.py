"""llama.cpp Backend Adapter —— 个体的认知手段（Model 调用；ADR 0008 决定
3 / INV-1 / R-09 / U-5）。

依据：ADR 0008（决定 3：本模块 = llama.cpp Backend Adapter，与 Ollama
adapter 同构——同一 Model Interface 两级调用面，wire 形态内化；构造注入
规则与 Ollama adapter 同构（R-09）；决定 4：seam 已 real，本模块是第二
具体实现；裁定 3：真实 wire 以真实 llama-server 实测验证，属
Implementation / Reality Verification）、ADR 0009（transport / 重试 /
退避 / JSON 边界 / 契约校验调位至共享 Wire Client
`dao_sheng/model_wire.py`；本 adapter 保留 wire 固有 = endpoint path /
payload shape / extract）、INV-1（Model 重启对个体无影响：重连 / 退避 =
手段内部行为，不暴露给 Core）、R-09（endpoint / model / timeout / retry
全部注入，无默认值）、U-5（部署形态 UNKNOWN——本模块不含任何具体模型 /
路径 / 部署值，全部由装配点注入）。

- wire 形态 = llama.cpp server HTTP API（OpenAI 兼容 /v1/*）：
  `complete` → POST `/v1/completions`（非流式 `stream: false`），取值
  `choices[0].text`；`chat` → POST `/v1/chat/completions`（非流式
  `stream: false`），取值 `choices[0].message.content`。请求 / 响应形态、
  错误响应形态（4xx / 5xx = `{"error": {"code", "message", "type"}}`
  envelope）均以真实 llama-server 实测为准（2026-09-24，ADR 0008 裁定
  3；实测证据路径见 Phase C 交接文件）。这是 adapter 内部细节（depth
  隐藏），不是部署决定。
- `model` 参数 = 不透明标识符：server 端语义（llama.cpp 以模型路径或
  别名标识已加载模型），adapter 原样透传，不对其做本地校验或回显核对
  ——与 Ollama adapter 不核对模型回显为同一纪律（手段不代 Core 判断）。
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


class LlamaCppModel:
    """llama.cpp Backend Adapter（实现 Model Interface——`dao_sheng.
    model.Model`，结构化符合，不要求继承；ADR 0008 决定 3）。

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
        """全部参数注入、无默认值（R-09；与 Ollama adapter 同构）。

        非法配置在装配点 fail-loud（ValueError）：不携带坏配置运行——
        校验语义调位至共享 `validate_config`（ADR 0009 Decision 4）。
        """
        validate_config(endpoint, model, timeout_seconds, retry_limit)
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retry_limit = retry_limit

    def complete(self, prompt: str) -> str:
        """补全调用：prompt → 模型续写（wire = /v1/completions，内化细节）。"""
        if not prompt or not prompt.strip():
            raise ValueError("prompt 不得为空")
        return post_json(
            self.endpoint,
            self.timeout_seconds,
            self.retry_limit,
            "/v1/completions",
            {"model": self.model, "prompt": prompt, "stream": False},
            lambda data: data["choices"][0]["text"],
        )

    def chat(self, messages: Sequence[tuple[str, str]]) -> str:
        """会话调用：(role, content) 序列 → 模型回复（wire =
        /v1/chat/completions，内化细节）。

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
            "/v1/chat/completions",
            {
                "model": self.model,
                "messages": [
                    {"role": role, "content": content}
                    for role, content in messages
                ],
                "stream": False,
            },
            lambda data: data["choices"][0]["message"]["content"],
        )
