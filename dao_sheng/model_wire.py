"""Wire Client —— Model seam 之下、Backend Adapter 共用的出站 wire
implementation / deep module（ADR 0009）。

职责（ADR 0009 Decision 2）：共享 transport / retry / backoff / JSON 边界
处理、共享 config validation、extract 结果统一 contract enforcement。
两 Backend Adapter 保留各自 endpoint path / payload shape / extract（协议
差异留在 adapter，不退化为纯 wire profile 数据壳）。

形态（Decision 3 / Q10）：模块级函数、无状态、无 config ownership——
config 仍属各 adapter（部署值由装配点注入，R-09 / U-5）。

失败语义五类（Decision 5）：
- 传输失败（URLError / OSError / HTTP 5xx）= 可重试（重启窗口语义，
  INV-1：手段故障不是个体故障）；
- HTTP 4xx = 不可重试（服务端拒绝）；
- JSON decode failure = 不可重试；
- extract 失败（KeyError / IndexError / TypeError）= 不可重试，集中捕获
  统一转 ModelUnavailable；
- 响应契约违规（extract result 非 str）= 不可重试，ModelUnavailable。

有意的契约收紧（Decision 6 / Q3）：extract result 统一 enforce `str`——
原先部分 adapter 可能返回 None 的行为被统一纠正为 ModelUnavailable。

`ModelUnavailable` 唯一定义位 = `dao_sheng.model`（ADR 0008 决定 1）——
本模块只抛出，不重定义。

出站通道（M09 棘轮显式调位，ADR 0009 Decision 7）：Model 出站
`urlopen` 仅限本模块（出站 allowlist = MODEL_WIRE_MODULES 刻意声明位）。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from dao_sheng.model import ModelUnavailable

#: 退避底数（秒）——Wire Client 内部算法参数（重连行为的一部分），
#: 不是部署值（部署值 = endpoint / model / timeout / retry 次数，
#: 由装配点注入各 adapter，R-09 / U-5）。
_RETRY_BASE_SECONDS = 0.1


def validate_config(
    endpoint: str,
    model: str,
    timeout_seconds: float,
    retry_limit: int,
) -> None:
    """共享 config validation（ADR 0009 Decision 4 / Q4）。

    两 Backend Adapter `__init__` 各自调用本函数，构造即 fail-loud
    （ValueError），不推迟到首次 request；四项校验语义逐字保留：
    endpoint / model 不得为空、timeout_seconds 必须为正数、retry_limit
    不得为负数。只校验注入值，不给任何默认值（R-09 / U-5）。
    """
    if not endpoint or not endpoint.strip():
        raise ValueError("endpoint 不得为空")
    if not model or not model.strip():
        raise ValueError("model 不得为空")
    if timeout_seconds is None or timeout_seconds <= 0:
        raise ValueError("timeout_seconds 必须为正数")
    if retry_limit is None or retry_limit < 0:
        raise ValueError("retry_limit 不得为负数")


def post_json(
    endpoint: str,
    timeout_seconds: float,
    retry_limit: int,
    path: str,
    payload: dict,
    extract: Callable,
) -> str:
    """一次 wire 调用（ADR 0009 Decision 3）。

    payload 以 JSON POST 发出，响应 JSON 交给 extract 取值返回。失败
    语义五类（Decision 5）：传输失败（URLError / OSError / HTTP 5xx）
    可重试（重启窗口语义，退避 `_RETRY_BASE_SECONDS * (2**attempt)`）；
    HTTP 4xx 不可重试（服务端拒绝）；JSON decode failure 不可重试；
    extract 失败（KeyError / IndexError / TypeError）不可重试（集中捕获
    统一转 ModelUnavailable）；响应契约违规（extract result 非 str）
    不可重试（统一 enforce，Decision 6 / Q3）。耗尽 → ModelUnavailable。
    """
    last_error: Exception | None = None
    for attempt in range(retry_limit + 1):
        try:
            request = urllib.request.Request(
                endpoint + path,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(
                request, timeout=timeout_seconds
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
            result = extract(data)
            if not isinstance(result, str):
                raise ModelUnavailable("Model 响应不合契约")
            return result
        except urllib.error.HTTPError as error:
            if error.code >= 500:
                last_error = error
            else:
                raise ModelUnavailable(
                    f"Model 调用被服务端拒绝（{error.code}），不重试"
                ) from error
        except (urllib.error.URLError, OSError) as error:
            last_error = error
        except json.JSONDecodeError as error:
            raise ModelUnavailable("Model 响应不合契约") from error
        except (KeyError, IndexError, TypeError) as error:
            raise ModelUnavailable("Model 响应不合契约") from error
        if attempt < retry_limit:
            time.sleep(_RETRY_BASE_SECONDS * (2**attempt))
    raise ModelUnavailable(
        f"Model 调用在 {retry_limit} 次重试后仍不可用"
    ) from last_error
