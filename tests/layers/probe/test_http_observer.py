from __future__ import annotations

import httpx
import pytest

from layers.probe.http_observer import HttpxObserver


@pytest.mark.asyncio
async def test_returns_status_and_server_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """HEAD 応答の status と Server header と ctfd_api_ok の収集

    Args:
        monkeypatch: pytest fixture
    """

    def handler(request: httpx.Request) -> httpx.Response:
        """固定応答を返すハンドラ

        Args:
            request: httpx リクエスト

        Returns:
            経路別の固定応答
        """
        if request.url.path == "/api/v1/stats/users":
            return httpx.Response(401)
        return httpx.Response(200, headers={"server": "nginx/1.25"})

    import layers.probe.http_observer as mod

    real_client = httpx.AsyncClient

    def patched_client(*args, **kwargs) -> httpx.AsyncClient:
        """transport を差替えた AsyncClient factory

        Args:
            *args: 元 factory の位置引数
            **kwargs: 元 factory の名前引数

        Returns:
            MockTransport 注入済の AsyncClient
        """
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(mod.httpx, "AsyncClient", patched_client)

    probe = await HttpxObserver().observe("https://example.com")
    assert probe.status == 200
    assert probe.server_header == "nginx/1.25"
    assert probe.ctfd_api_ok is True


@pytest.mark.asyncio
async def test_http_error_returns_null_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP エラー時の null 値 probe

    Args:
        monkeypatch: pytest fixture
    """

    def handler(request: httpx.Request) -> httpx.Response:
        """例外を送出するハンドラ

        Args:
            request: 無視される

        Raises:
            httpx.ConnectError: 常に送出
        """
        raise httpx.ConnectError("refused")

    import layers.probe.http_observer as mod

    real_client = httpx.AsyncClient

    def patched_client(*args, **kwargs) -> httpx.AsyncClient:
        """transport を差替えた AsyncClient factory

        Args:
            *args: 元 factory の位置引数
            **kwargs: 元 factory の名前引数

        Returns:
            MockTransport 注入済の AsyncClient
        """
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(mod.httpx, "AsyncClient", patched_client)

    probe = await HttpxObserver().observe("https://unreachable")
    assert probe.status is None
    assert probe.server_header is None
    assert probe.ctfd_api_ok is False
    assert probe.final_url is None
