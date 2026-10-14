"""llama.cpp Backend Adapter — ADR 0008 决定 3（Phase C）+ ADR 0009 调位
（INV-1 / R-09 / U-5）。

Seam：`LlamaCppModel.complete(prompt) -> str` / `chat(messages) -> str`
（llama.cpp Backend Adapter，实现 `dao_sheng.model` 的 Model Interface；
与 Ollama adapter 同构，ADR 0008 决定 3/4）；endpoint / model / timeout /
retry 全部注入、无默认值（R-09：部署值 = composition root 声明位）。

测试收敛（ADR 0009 Decision 8 / Q6）：共享 transport / retry / 退避 /
JSON 边界 / 契约 enforcement 只在 `tests/test_model_wire.py` 测试一次；
本文件只测 wire 固有 = endpoint path / payload shape / extract（llama.cpp
OpenAI 兼容 /v1/* 形态）+ 公共 Model 表面（两级调用 / 无部署默认值）+
完整 mock 成功路径（穿过 Model interface 的 complete / chat）。删除的
重复共享测试 ↔ 存活 wire 测试的逐条等价映射见实施 handoff（测试强度未
下降的证据）。

依据：ADR 0008（决定 3/4，裁定 3）、ADR 0009（transport 调位至 Wire
Client，本 adapter 保留 wire 固有）、INV-1（Model 重启对个体无影响）、
R-09（构造注入、无默认值）、U-5（部署形态 UNKNOWN 不预设）。

性质声明：本文件为 mock 单元测试——进程内 mock HTTP 服务证明 adapter
行为（两级调用、契约校验、fail-loud 表面），**不是**真实 llama.cpp
验证（真实 wire 验证 = 真实 llama-server 实测，属 Implementation /
Reality Verification，ADR 0008 裁定 3，单独报告于 Phase C 交接文件）。
mock 服务的请求 / 响应形态按真实 llama-server 实测 wire 形态构造
（2026-09-24）：
- POST /v1/completions → `choices[0].text`（object = text_completion）
- POST /v1/chat/completions → `choices[0].message.content`
  （object = chat.completion）
"""

import inspect
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dao_sheng.model_llama_cpp import LlamaCppModel


class _LlamaModelHandler(BaseHTTPRequestHandler):
    """最小 llama.cpp server 模拟：/v1/completions / /v1/chat/completions
    （POST JSON，OpenAI 兼容形态）。

    server 属性（测试侧配置）：requests（每路径计数）、last_bodies
    （服务端实际收到的 payload = wire 形态验证位）。共享 transport 故障
    模拟（503 / 4xx / 慢服务 / 坏响应 / 非字符串取值 / 空 choices）已
    调位至 tests/test_model_wire.py（ADR 0009 Decision 8：只测一次）。
    """

    def do_POST(self):
        srv = self.server
        srv.requests[self.path] = srv.requests.get(self.path, 0) + 1
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        srv.last_bodies[self.path] = body
        if self.path == "/v1/completions":
            payload = {
                "object": "text_completion",
                "choices": [
                    {"index": 0, "text": "gen:" + body["prompt"],
                     "finish_reason": "stop"}
                ],
            }
        elif self.path == "/v1/chat/completions":
            payload = {
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "chat:" + str(len(body["messages"])),
                        },
                    }
                ],
            }
        else:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class LlamaCppModelTest(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _LlamaModelHandler)
        self.server.requests = {}
        self.server.last_bodies = {}
        self._thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self._thread.start()
        # addCleanup 是 LIFO：先加 server_close 后加 shutdown → shutdown
        # 先执行（serve_forever 退出后再关 socket，避免 Windows 竞态）。
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        _host, port = self.server.server_address[:2]
        self.endpoint = f"http://{_host}:{port}"

    def make_client(self, retry_limit=0, timeout_seconds=5.0, model="test-model"):
        return LlamaCppModel(
            self.endpoint, model, timeout_seconds=timeout_seconds, retry_limit=retry_limit
        )

    # —— 两级调用（depth：wire 形态由 adapter 内化，这里经服务端收到的 body 验证）——

    def test_complete_success(self):
        client = self.make_client()
        self.assertEqual(client.complete("hello"), "gen:hello")
        body = self.server.last_bodies["/v1/completions"]
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["prompt"], "hello")
        self.assertFalse(body["stream"])
        self.assertEqual(self.server.requests["/v1/completions"], 1)

    def test_chat_success(self):
        client = self.make_client()
        self.assertEqual(
            client.chat([("system", "ctx"), ("user", "hi")]), "chat:2"
        )
        body = self.server.last_bodies["/v1/chat/completions"]
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(
            body["messages"],
            [
                {"role": "system", "content": "ctx"},
                {"role": "user", "content": "hi"},
            ],
        )
        self.assertFalse(body["stream"])

    def test_empty_input_rejected(self):
        """空输入 fail-loud（输入校验 = adapter 边界行为，不进重试）。"""
        client = self.make_client()
        with self.assertRaises(ValueError):
            client.complete("")
        with self.assertRaises(ValueError):
            client.complete("   ")
        with self.assertRaises(ValueError):
            client.chat([])
        self.assertEqual(self.server.requests, {})

    # —— 结构面（depth / R-09）——

    def test_surface_only_two_calls(self):
        """depth：调用方公共表面恰为两级 chat / complete（+ 构造）。"""
        surface = {
            name
            for name, value in vars(LlamaCppModel).items()
            if callable(value) and not name.startswith("_")
        }
        self.assertEqual(surface, {"chat", "complete"})

    def test_no_deployment_defaults(self):
        """R-09：endpoint / model / timeout / retry 全为注入项，无参数默认值。"""
        sig = inspect.signature(LlamaCppModel.__init__)
        for param in sig.parameters.values():
            if param.name == "self":
                continue
            self.assertIs(param.default, inspect.Parameter.empty)

    def test_constructor_delegates_validation(self):
        """构造即 fail-loud 的校验语义调位至共享 `validate_config`
        （ADR 0009 Decision 4）——本测试只证明委托发生（adapter 不再自带
        校验）；四项校验语义全矩阵在 tests/test_model_wire.py 测试一次。"""
        with self.assertRaises(ValueError):
            LlamaCppModel("", "m", timeout_seconds=5.0, retry_limit=0)
        self.assertEqual(self.server.requests, {})


if __name__ == "__main__":
    unittest.main()
