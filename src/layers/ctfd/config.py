from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CtfdConfig:
    """CTFd 接続設定

    Attributes:
        base_url: CTFd のベース URL
        token: API トークン
        username: ログインユーザ名
        password: ログインパスワード
        timeout_seconds: HTTP タイムアウト秒数
        verify_tls: TLS 検証フラグ
    """

    base_url: str
    token: str = ""
    username: str = ""
    password: str = ""
    timeout_seconds: float = 30.0
    verify_tls: bool = False

    def __post_init__(self) -> None:
        """認証情報の妥当性検証

        Raises:
            ValueError: token も (username, password) も与えられていない場合
        """
        if not self.token and not (self.username and self.password):
            raise ValueError("CtfdConfig requires token or (username, password)")
