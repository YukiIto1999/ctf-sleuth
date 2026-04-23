from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BASE_URL = "https://labs.hackthebox.com"


@dataclass(frozen=True, slots=True)
class HtbConfig:
    """HTB API 接続設定

    Attributes:
        token: HTB API トークン
        base_url: HTB API のベース URL
        timeout_seconds: HTTP タイムアウト秒数
    """

    token: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        """token 必須性の検証

        Raises:
            ValueError: token が空の場合
        """
        if not self.token:
            raise ValueError("HtbConfig.token is required")
