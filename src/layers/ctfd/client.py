from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from markdownify import markdownify as html2md

from contexts.ctf_challenge.domain import (
    Challenge,
    ChallengeId,
    ChallengeSet,
    FlagVerdict,
    Hint,
    SolveAttempt,
)
from contexts.ctf_challenge.policies import normalize_category

from .config import CtfdConfig
from .errors import CtfdError

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36"
_CSRF_RE = re.compile(r"csrfNonce':\s*\"([A-Fa-f0-9]+)\"")
_NONCE_RE = re.compile(r'(?:id|name)="nonce"[^>]*value="([^"]+)"')
_VERDICT_MAP: dict[str, FlagVerdict] = {
    "correct": FlagVerdict.CORRECT,
    "already_solved": FlagVerdict.ALREADY_SOLVED,
    "incorrect": FlagVerdict.INCORRECT,
}


class CtfdClient:
    """CTFd REST API のファサード"""

    def __init__(
        self,
        config: CtfdConfig,
        *,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        """CTFd クライアントの初期化

        Args:
            config: CTFd 接続設定
            http: 注入する httpx.AsyncClient
        """
        self._config = config
        self._http = http
        self._owns_http = http is None
        self._csrf_token = ""
        self._logged_in = bool(config.token)
        self._challenge_id_by_name: dict[str, int] = {}

    async def __aenter__(self) -> CtfdClient:
        """async context manager の入場

        Returns:
            自身の CtfdClient
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

    async def fetch_all(self) -> ChallengeSet:
        """全 challenge と solved 名集合の取得

        Returns:
            Challenge と solved_names を含む ChallengeSet
        """
        stubs = await self._get_json("/challenges?per_page=500")
        visible = [s for s in stubs.get("data", []) if s.get("type") != "hidden"]

        challenges: list[Challenge] = []
        for stub in visible:
            detail = await self._get_json(f"/challenges/{stub['id']}")
            payload = detail.get("data") or {}
            challenges.append(_challenge_from_payload(payload))
            self._challenge_id_by_name[payload.get("name", "")] = payload.get("id", 0)

        solved = await self._fetch_solved_names()
        return ChallengeSet(
            challenges=tuple(challenges),
            solved_names=frozenset(solved),
        )

    async def submit_flag(self, challenge_name: str, flag: str) -> SolveAttempt:
        """flag 提出と SolveAttempt 生成

        Args:
            challenge_name: 対象 challenge 名
            flag: 提出するフラグ文字列

        Returns:
            判定結果を含む SolveAttempt
        """
        challenge_id = await self._resolve_challenge_id(challenge_name)
        body = {"challenge_id": challenge_id, "submission": flag}
        response = await self._post_json("/challenges/attempt", body)
        data = response.get("data") or {}
        status = str(data.get("status", "unknown"))
        message = str(data.get("message", ""))
        verdict = _VERDICT_MAP.get(status, FlagVerdict.UNKNOWN)
        return SolveAttempt(
            challenge_name=challenge_name,
            flag=flag,
            verdict=verdict,
            message=message,
            submitted_at=datetime.now(UTC),
        )

    async def download_distfile(self, url: str) -> bytes:
        """配布ファイルの取得

        Args:
            url: 相対もしくは絶対の URL

        Returns:
            取得した生バイト列
        """
        http = await self._ensure_http()
        absolute = _absolutize(self._config.base_url, url)
        headers = self._auth_headers() if _same_host(self._config.base_url, absolute) else {}
        resp = await http.get(absolute, headers=headers, follow_redirects=True, timeout=60.0)
        resp.raise_for_status()
        return resp.content

    async def _ensure_http(self) -> httpx.AsyncClient:
        """httpx クライアントの遅延生成

        Returns:
            使用可能な httpx.AsyncClient
        """
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self._config.base_url.rstrip("/"),
                follow_redirects=False,
                verify=self._config.verify_tls,
                timeout=self._config.timeout_seconds,
                headers={"User-Agent": _USER_AGENT},
            )
        return self._http

    async def _ensure_logged_in(self) -> None:
        """未ログイン時の session ログイン

        Raises:
            CtfdError: nonce 抽出失敗もしくは認証失敗
        """
        if self._logged_in:
            return
        http = await self._ensure_http()
        resp = await http.get("/login")
        nonce_match = _NONCE_RE.search(resp.text)
        if not nonce_match:
            raise CtfdError("CTFd /login did not contain nonce field")
        login = await http.post(
            "/login",
            data={
                "name": self._config.username,
                "password": self._config.password,
                "_submit": "Submit",
                "nonce": nonce_match.group(1),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if login.status_code == 200:
            raise CtfdError("CTFd login failed (bad credentials)")
        self._logged_in = True

    async def _ensure_csrf(self) -> str:
        """CSRF トークンの取得とキャッシュ

        Returns:
            /challenges から取得した csrfNonce

        Raises:
            CtfdError: csrfNonce の抽出失敗
        """
        if self._csrf_token:
            return self._csrf_token
        http = await self._ensure_http()
        resp = await http.get("/challenges")
        match = _CSRF_RE.search(resp.text)
        if not match:
            raise CtfdError("Could not find csrfNonce on /challenges page")
        self._csrf_token = match.group(1)
        return self._csrf_token

    def _auth_headers(self) -> dict[str, str]:
        """認証ヘッダの構築

        Returns:
            Content-Type と Authorization を含む dict
        """
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._config.token:
            headers["Authorization"] = f"Token {self._config.token}"
        return headers

    async def _get_json(self, path: str) -> dict[str, Any]:
        """認証付き GET リクエスト

        Args:
            path: /api/v1 以下のパス

        Returns:
            JSON 応答辞書
        """
        await self._ensure_logged_in()
        http = await self._ensure_http()
        resp = await http.get(f"/api/v1{path}", headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()

    async def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """認証付き POST リクエスト

        Args:
            path: /api/v1 以下のパス
            body: 送信 JSON body

        Returns:
            JSON 応答辞書
        """
        await self._ensure_logged_in()
        http = await self._ensure_http()
        headers = self._auth_headers()
        if not self._config.token:
            headers["CSRF-Token"] = await self._ensure_csrf()
        resp = await http.post(f"/api/v1{path}", json=body, headers=headers)
        if resp.status_code == 403 and not self._config.token:
            self._csrf_token = ""
            headers["CSRF-Token"] = await self._ensure_csrf()
            resp = await http.post(f"/api/v1{path}", json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _resolve_challenge_id(self, name: str) -> int:
        """名前から challenge ID への解決

        Args:
            name: Challenge 名

        Returns:
            対応する CTFd 整数 ID

        Raises:
            CtfdError: 対応 challenge の不在
        """
        if name in self._challenge_id_by_name:
            return self._challenge_id_by_name[name]
        data = await self._get_json("/challenges?per_page=500")
        for stub in data.get("data", []):
            if "name" in stub and "id" in stub:
                self._challenge_id_by_name[stub["name"]] = stub["id"]
        if name not in self._challenge_id_by_name:
            raise CtfdError(f"challenge not found in CTFd: {name!r}")
        return self._challenge_id_by_name[name]

    async def _fetch_solved_names(self) -> frozenset[str]:
        """solved challenge 名集合の取得

        Returns:
            観測時点の solved 名集合
        """
        try:
            me = await self._get_json("/users/me")
            user = me.get("data") or {}
            team_id = user.get("team_id")
            if team_id:
                solves = await self._get_json(f"/teams/{team_id}/solves")
            else:
                user_id = user.get("id")
                if not user_id:
                    return frozenset()
                solves = await self._get_json(f"/users/{user_id}/solves")
            names = {
                s["challenge"]["name"]
                for s in solves.get("data", [])
                if isinstance(s.get("challenge"), dict) and s["challenge"].get("name")
            }
            return frozenset(names)
        except httpx.HTTPError as e:
            logger.warning("could not fetch solved challenges: %s", e)
            return frozenset()


def _challenge_from_payload(payload: dict[str, Any]) -> Challenge:
    """CTFd JSON payload から Challenge への変換

    Args:
        payload: /api/v1/challenges/<id> の data 部

    Returns:
        正規化された Challenge
    """
    raw_category = str(payload.get("category") or "")
    raw_desc = str(payload.get("description") or "")
    try:
        description = html2md(raw_desc, heading_style="atx", escape_asterisks=False).strip()
    except Exception:
        description = raw_desc
    tags = tuple(
        t["value"] if isinstance(t, dict) else str(t)
        for t in (payload.get("tags") or [])
    )
    hints = tuple(
        Hint(content=str(h.get("content") or ""), cost=int(h.get("cost") or 0))
        for h in (payload.get("hints") or [])
        if isinstance(h, dict)
    )
    distfile_urls = tuple(str(u) for u in (payload.get("files") or []))
    return Challenge(
        id=ChallengeId(value=int(payload.get("id") or 0)),
        name=str(payload.get("name") or f"challenge-{payload.get('id')}"),
        category_raw=raw_category,
        strategy=normalize_category(raw_category),
        description=description,
        value=int(payload.get("value") or 0),
        connection_info=str(payload.get("connection_info") or ""),
        tags=tags,
        hints=hints,
        distfile_urls=distfile_urls,
    )


def _same_host(a: str, b: str) -> bool:
    """URL の host 一致判定

    Args:
        a: 比較元 URL
        b: 比較先 URL

    Returns:
        hostname の一致判定
    """
    from urllib.parse import urlparse

    return urlparse(a).hostname == urlparse(b).hostname


def _absolutize(base: str, url: str) -> str:
    """相対 URL の絶対化

    Args:
        base: ベース URL
        url: 相対もしくは絶対 URL

    Returns:
        絶対 URL 文字列
    """
    if url.startswith(("http://", "https://")):
        return url
    return f"{base.rstrip('/')}/{url.lstrip('/')}"
