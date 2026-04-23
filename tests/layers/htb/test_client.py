from __future__ import annotations

import httpx
import pytest

from contexts.htb_machine.domain import OwnType
from layers.htb import HtbClient, HtbConfig, HtbError


def _mock_http(handler) -> httpx.AsyncClient:
    """MockTransport 付き httpx.AsyncClient の生成

    Args:
        handler: リクエスト処理関数

    Returns:
        httpx.AsyncClient
    """
    return httpx.AsyncClient(
        base_url="https://labs.hackthebox.com",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_submit_flag_accepted() -> None:
    """正解 flag の accepted 判定"""

    def handler(request: httpx.Request) -> httpx.Response:
        """正解応答ハンドラ

        Args:
            request: httpx リクエスト

        Returns:
            Congrats メッセージ
        """
        assert request.url.path == "/api/v4/machine/own"
        assert request.headers["Authorization"] == "Bearer t_abc"
        return httpx.Response(200, json={"message": "Congrats! Flag accepted."})

    async with _mock_http(handler) as http:
        client = HtbClient(HtbConfig(token="t_abc"), http=http)
        attempt = await client.submit_flag(
            machine_id=42,
            machine_name="Sherlock",
            own_type=OwnType.USER,
            flag="abcd1234",
        )
    assert attempt.accepted
    assert attempt.machine_name == "Sherlock"
    assert attempt.own_type is OwnType.USER


@pytest.mark.asyncio
async def test_submit_flag_rejected_via_message() -> None:
    """Incorrect メッセージ時の reject"""

    def handler(request: httpx.Request) -> httpx.Response:
        """Incorrect 応答ハンドラ

        Args:
            request: httpx リクエスト

        Returns:
            Incorrect flag 応答
        """
        return httpx.Response(200, json={"message": "Incorrect flag."})

    async with _mock_http(handler) as http:
        client = HtbClient(HtbConfig(token="t"), http=http)
        attempt = await client.submit_flag(
            machine_id=1,
            machine_name="x",
            own_type=OwnType.ROOT,
            flag="wrong",
        )
    assert not attempt.accepted
    assert "Incorrect" in attempt.message


@pytest.mark.asyncio
async def test_submit_flag_http_error_wraps() -> None:
    """HTTP 例外の HtbError ラップ"""

    def handler(request: httpx.Request) -> httpx.Response:
        """常に接続失敗を送出するハンドラ

        Args:
            request: httpx リクエスト

        Raises:
            httpx.ConnectError: 常に送出
        """
        raise httpx.ConnectError("refused")

    async with _mock_http(handler) as http:
        client = HtbClient(HtbConfig(token="t"), http=http)
        with pytest.raises(HtbError):
            await client.submit_flag(
                machine_id=1,
                machine_name="x",
                own_type=OwnType.USER,
                flag="x",
            )
