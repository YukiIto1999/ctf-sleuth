from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HttpProbe:
    """HTTP HEAD/GET 観測の結果

    Attributes:
        status: HTTP ステータスコード
        server_header: Server ヘッダ値
        ctfd_api_ok: CTFd API エンドポイント応答の真偽
        final_url: リダイレクト後の最終 URL
    """

    status: int | None
    server_header: str | None
    ctfd_api_ok: bool
    final_url: str | None
