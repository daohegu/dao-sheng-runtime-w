"""Wire Client —— Model seam 之下的共享出站 wire implementation（ADR 0009）

Seam（ADR 0009 Decision 3；模块级函数、无状态、无 config ownership）：
- `validate_config(endpoint, model, timeout_seconds, retry_limit) -> None`
- `post_json(endpoint, timeout_seconds, retry_limit, path, payload, extract) -> str`

共享 transport / retry / backoff / JSON 边界 / extract 契约 enforcement 在
本文件只测试一次（Decision 8 / Q6）；两 Backend Adapter 的 wire 固有
endpoint path / payload shape / extract 留在各自 adapter 测试。

失败语义五类（Decision 5）：传输失败（URLError / OSError / HTTP 5xx）可
重试；HTTP 4xx 不可重试；JSON decode failure 不可重试；extract 失败
（KeyError / IndexError / TypeError）不可重试（集中捕获统一转
ModelUnavailable）；响应契约违规（extract result 非 str）不可重试。

有意的契约收紧（Decision 6 / Q3）：extract result 统一 enforce `str`。

`ModelUnavailable` 唯一定义位 = `dao_sheng.model`（ADR 0008 决定 1）——
本文件只引用，不重定义。

性质声明：mock 单元测试——进程内 mock HTTP 服务证明 wire 行为，不是
真实 server 验证（真实 wire 实测证据 = ADR 0008 裁定 3，Phase C）。
"""

import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dao_sheng.model import ModelUnavailable
from dao_sheng.model_wire import post_json, validate_config


class _WireHandler(BaseHTTPRequestHandler):
    """最小 wire 模拟：POST JSON → JSON（路径无关，wire 形态由测试侧
    配置控制）。

    server 属性（测试侧配置）：requests（每路径计数）、last_bodies、
    fail_first（每路径前 N 次返回 503 = 模拟重启窗口）、status（固定
    状态码覆盖）、sleep（响应前挂起 = 模拟慢服务）、bad_json（200 但
    响应不是 JSON）、bad_shape（200 但响应缺 extract 所需字段）、
    empty_choices（200 但 choices 为空列表）、list_body（200 但响应为
    列表）、bad_value（200 但取值为 null）、int_value（200 但取值为
    整数）。
    """

    def do_POST(self):
        srv = self.server
        count = srv.requests.get(self.path, 0) + 1
        srv.requests[self.path] = count
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        srv.last_bodies[self.path] = body
        status = srv.status
        if status is None and count <= srv.fail_first.get(self.path, 0):
            status = 503
        if status is not None:
            self.send_response(status)
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": {"code": status}}).encode("utf-8")
            )
            return
        if srv.sleep:
            time.sleep(srv.sleep)
        if srv.bad_json:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not json at all")
            return
        if srv.bad_shape:
            payload = {"unrelated": 1}
        elif srv.empty_choices:
            payload = {"choices": []}
        elif srv.list_body:
            payload = []
        elif srv.bad_value:
            payload = {"result": None}
        elif srv.int_value:
            payload = {"result": 42}
        else:
            payload = {"result": "ok:" + body["tag"]}
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class _WireServerTestBase(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _WireHandler)
        self.server.requests = {}
        self.server.last_bodies = {}
        self.server.fail_first = {}
        self.server.status = None
        self.server.sleep = 0.0
        self.server.bad_json = False
        self.server.bad_shape = False
        self.server.empty_choices = False
        self.server.list_body = False
        self.server.bad_value = False
        self.server.int_value = False
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


class ValidateConfigTest(unittest.TestCase):
    def test_validate_config_accepts_valid(self):
        """合法注入配置通过（返回 None，不抛）。"""
        self.assertIsNone(
            validate_config(
                endpoint="e",
                model="m",
                timeout_seconds=5.0,
                retry_limit=0,
            )
        )

    def test_validate_config_rejects_invalid(self):
        """四项校验语义逐字保留（ADR 0009 Decision 4 / Q4）：构造即
        fail-loud（ValueError），不携带坏配置运行。"""
        base = dict(endpoint="e", model="m", timeout_seconds=5.0, retry_limit=0)
        for overrides in (
            dict(endpoint=""),
            dict(endpoint="   "),
            dict(model=""),
            dict(model="   "),
            dict(timeout_seconds=None),
            dict(timeout_seconds=0),
            dict(timeout_seconds=-1),
            dict(retry_limit=None),
            dict(retry_limit=-1),
        ):
            with self.assertRaises(ValueError):
                validate_config(**{**base, **overrides})


class PostJsonTest(_WireServerTestBase):
    def test_success_returns_extracted_string(self):
        """一次 wire 调用：payload 以 JSON POST 发出，extract 取值返回。"""
        result = post_json(
            self.endpoint,
            5.0,
            0,
            "/test/echo",
            {"tag": "hello"},
            lambda data: data["result"],
        )
        self.assertEqual(result, "ok:hello")
        self.assertEqual(
            self.server.last_bodies["/test/echo"], {"tag": "hello"}
        )
        self.assertEqual(self.server.requests["/test/echo"], 1)

    # —— 传输失败 = 可重试（重启窗口语义，INV-1）——

    def test_reconnect_recovers_after_restart_window(self):
        """前 2 次 503（重启窗口），第 3 次成功——调用方只见一次成功。"""
        self.server.fail_first["/test/echo"] = 2
        result = post_json(
            self.endpoint,
            5.0,
            3,
            "/test/echo",
            {"tag": "hello"},
            lambda data: data["result"],
        )
        self.assertEqual(result, "ok:hello")
        self.assertEqual(self.server.requests["/test/echo"], 3)

    def test_retry_exhausted_raises(self):
        """永远不可用 → retry_limit 耗尽 → ModelUnavailable。"""
        self.server.fail_first["/test/echo"] = 999
        with self.assertRaises(ModelUnavailable):
            post_json(
                self.endpoint,
                5.0,
                1,
                "/test/echo",
                {"tag": "x"},
                lambda data: data["result"],
            )
        self.assertEqual(self.server.requests["/test/echo"], 2)  # 初次 + 1 次重试

    # —— HTTP 4xx = 不可重试（服务端拒绝）——

    def test_client_error_not_retried(self):
        """400 → ModelUnavailable，不重试（retry_limit 再大也只 1 次请求）。"""
        self.server.status = 400
        with self.assertRaises(ModelUnavailable):
            post_json(
                self.endpoint,
                5.0,
                3,
                "/test/echo",
                {"tag": "x"},
                lambda data: data["result"],
            )
        self.assertEqual(self.server.requests["/test/echo"], 1)

    def test_timeout_honored(self):
        """注入的 timeout_seconds 生效（慢服务 → 超时 = 可重试传输失败）。"""
        self.server.sleep = 1.0
        start = time.monotonic()
        with self.assertRaises(ModelUnavailable):
            post_json(
                self.endpoint,
                0.2,
                0,
                "/test/echo",
                {"tag": "x"},
                lambda data: data["result"],
            )
        self.assertLess(time.monotonic() - start, 0.9)

    # —— JSON decode failure = 不可重试 ——

    def test_malformed_json_raises_without_retry(self):
        """200 但响应不是 JSON → ModelUnavailable，不重试（1 次请求）。"""
        self.server.bad_json = True
        with self.assertRaises(ModelUnavailable):
            post_json(
                self.endpoint,
                5.0,
                3,
                "/test/echo",
                {"tag": "x"},
                lambda data: data["result"],
            )
        self.assertEqual(self.server.requests["/test/echo"], 1)

    # —— extract 失败（KeyError / IndexError / TypeError）= 不可重试 ——

    def test_extract_key_error_raises_without_retry(self):
        """响应缺 extract 所需字段 → KeyError 集中转 ModelUnavailable，不重试。"""
        self.server.bad_shape = True
        with self.assertRaises(ModelUnavailable):
            post_json(
                self.endpoint,
                5.0,
                3,
                "/test/echo",
                {"tag": "x"},
                lambda data: data["result"],
            )
        self.assertEqual(self.server.requests["/test/echo"], 1)

    def test_extract_index_error_raises_without_retry(self):
        """choices 为空列表 → IndexError 集中转 ModelUnavailable，不重试。"""
        self.server.empty_choices = True
        with self.assertRaises(ModelUnavailable):
            post_json(
                self.endpoint,
                5.0,
                3,
                "/test/echo",
                {"tag": "x"},
                lambda data: data["choices"][0]["text"],
            )
        self.assertEqual(self.server.requests["/test/echo"], 1)

    def test_extract_type_error_raises_without_retry(self):
        """响应为列表（非 dict）→ TypeError 集中转 ModelUnavailable，不重试。"""
        self.server.list_body = True
        with self.assertRaises(ModelUnavailable):
            post_json(
                self.endpoint,
                5.0,
                3,
                "/test/echo",
                {"tag": "x"},
                lambda data: data["result"],
            )
        self.assertEqual(self.server.requests["/test/echo"], 1)

    # —— 响应契约违规（extract result 非 str）= 不可重试（Decision 6 / Q3）——

    def test_non_string_none_raises_without_retry(self):
        """extract 取值为 null → ModelUnavailable（统一 enforce str），不重试。"""
        self.server.bad_value = True
        with self.assertRaises(ModelUnavailable):
            post_json(
                self.endpoint,
                5.0,
                3,
                "/test/echo",
                {"tag": "x"},
                lambda data: data["result"],
            )
        self.assertEqual(self.server.requests["/test/echo"], 1)

    def test_non_string_int_raises_without_retry(self):
        """extract 取值为整数 → ModelUnavailable，不重试。"""
        self.server.int_value = True
        with self.assertRaises(ModelUnavailable):
            post_json(
                self.endpoint,
                5.0,
                3,
                "/test/echo",
                {"tag": "x"},
                lambda data: data["result"],
            )
        self.assertEqual(self.server.requests["/test/echo"], 1)


if __name__ == "__main__":
    unittest.main()
