from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from contexts.htb_machine.domain import HtbAttempt, OwnType

from .config import HtbConfig
from .errors import HtbError

logger = logging.getLogger(__name__)

_SUBMIT_PATH = "/api/v4/machine/own"
_DEFAULT_DIFFICULTY = 5


class HtbClient:
    """HTB API の薄いファサード"""

    def __init__(self, config: HtbConfig, *, http: httpx.AsyncClient | None = None) -> None:
        """HTB クライアントの初期化

        Args:
            config: HTB 接続設定
            http: 注入する httpx.AsyncClient
        """
        self._config = config
        self._http = http
        self._owns_http = http is None

    async def __aenter__(self) -> HtbClient:
        """async context manager の入場

        Returns:
            自身の HtbClient
        """
        await self._ensure_http()
        return self

    async def __aexit__(self, *exc: object) -> None:
        """async context manager の退場"""
        await self.close()

    async def close(self) -> None:
        """保有する httpx クライアントのクローズ"""
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    async def submit_flag(
        self,
        *,
        machine_id: int,
        machine_name: str,
        own_type: OwnType,
        flag: str,
        difficulty: int = _DEFAULT_DIFFICULTY,
    ) -> HtbAttempt:
        """flag 提出と HtbAttempt 生成

        Args:
            machine_id: HTB machine ID
            machine_name: machine 名
            own_type: own 種別
            flag: 提出フラグ文字列
            difficulty: 提出時の難易度値

        Returns:
            判定結果を含む HtbAttempt

        Raises:
            HtbError: HTTP 通信失敗
        """
        http = await self._ensure_http()
        body = {"flag": flag, "id": machine_id, "difficulty": difficulty}
        try:
            resp = await http.post(
                _SUBMIT_PATH,
                json=body,
                headers=self._auth_headers(),
                timeout=self._config.timeout_seconds,
            )
        except httpx.HTTPError as e:
            raise HtbError(f"HTB submit failed: {e}") from e

        accepted, message = _parse_response(resp)
        return HtbAttempt(
            machine_name=machine_name,
            own_type=own_type,
            flag=flag,
            accepted=accepted,
            message=message,
            submitted_at=datetime.now(UTC),
        )

    async def _ensure_http(self) -> httpx.AsyncClient:
        """httpx クライアントの遅延生成

        Returns:
            使用可能な httpx.AsyncClient
        """
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self._config.base_url.rstrip("/"),
                timeout=self._config.timeout_seconds,
            )
        return self._http

    def _auth_headers(self) -> dict[str, str]:
        """認証ヘッダの構築

        Returns:
            Bearer token と Accept を含む dict
        """
        return {
            "Authorization": f"Bearer {self._config.token}",
            "Accept": "application/json",
        }


def _parse_response(resp: httpx.Response) -> tuple[bool, str]:
    """HTB own エンドポイント応答の正規化

    Args:
        resp: httpx からの応答

    Returns:
        受理判定と整形済メッセージの組
    """
    if resp.status_code >= 400:
        return False, f"HTTP {resp.status_code}: {resp.text[:500]}"
    try:
        data: dict[str, Any] = resp.json()
    except ValueError:
        return False, f"non-json response: {resp.text[:500]}"
    message = str(data.get("message") or data.get("info") or "").strip()
    accepted = resp.status_code == 200 and "incorrect" not in message.lower()
    return accepted, message or "(no message)"
