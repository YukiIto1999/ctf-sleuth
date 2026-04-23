from __future__ import annotations

import httpx

from shared.probe import HttpProbe


class HttpxObserver:
    """httpx を用いた HttpObserver 標準実装"""

    def __init__(self, *, timeout: float = 3.0) -> None:
        """観測器の初期化

        Args:
            timeout: HTTP 要求タイムアウト秒数
        """
        self._timeout = timeout

    async def observe(self, url: str) -> HttpProbe:
        """指定 URL への HEAD + CTFd API 観測

        Args:
            url: 観測対象の URL

        Returns:
            観測結果の HttpProbe
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                head = await client.head(url)
                base = str(head.url).rstrip("/")
                ctfd_ok = False
                try:
                    api = await client.get(f"{base}/api/v1/stats/users")
                    ctfd_ok = api.status_code in (200, 401, 403)
                except httpx.HTTPError:
                    ctfd_ok = False
                return HttpProbe(
                    status=head.status_code,
                    server_header=head.headers.get("server"),
                    ctfd_api_ok=ctfd_ok,
                    final_url=str(head.url),
                )
        except httpx.HTTPError:
            return HttpProbe(status=None, server_header=None, ctfd_api_ok=False, final_url=None)
