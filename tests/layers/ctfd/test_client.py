from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from contexts.ctf_challenge.domain import FlagVerdict
from layers.ctfd import CtfdClient, CtfdConfig


def _mock_client(responses: dict[tuple[str, str], dict | str]) -> httpx.AsyncClient:
    """固定応答を持つ httpx.AsyncClient の生成

    Args:
        responses: (method, path) から応答 body への写像

    Returns:
        MockTransport を持つ httpx.AsyncClient
    """

    def handler(request: httpx.Request) -> httpx.Response:
        """固定写像に基づく応答生成

        Args:
            request: httpx リクエスト

        Returns:
            対応する httpx.Response

        Raises:
            AssertionError: 写像に未登録のリクエスト
        """
        key = (request.method, request.url.path)
        if key not in responses:
            raise AssertionError(f"unexpected request: {key}")
        body = responses[key]
        if isinstance(body, dict):
            return httpx.Response(200, json=body)
        return httpx.Response(200, text=body)

    return httpx.AsyncClient(
        base_url="https://ctf.example.com",
        transport=httpx.MockTransport(handler),
    )


class TestCtfdConfig:
    """CtfdConfig の検証"""

    def test_token_only_is_valid(self) -> None:
        """token のみでの有効性"""
        CtfdConfig(base_url="https://x", token="t")

    def test_user_and_password_is_valid(self) -> None:
        """username + password での有効性"""
        CtfdConfig(base_url="https://x", username="u", password="p")

    def test_neither_raises(self) -> None:
        """認証情報なしでの ValueError"""
        with pytest.raises(ValueError):
            CtfdConfig(base_url="https://x")

    def test_only_username_raises(self) -> None:
        """username のみでの ValueError"""
        with pytest.raises(ValueError):
            CtfdConfig(base_url="https://x", username="u")


def _challenge_stubs() -> dict[str, Any]:
    """challenges 一覧のスタブ応答

    Returns:
        3 件の challenge stub 含む dict
    """
    return {
        "data": [
            {"id": 1, "name": "pwn-baby", "type": "standard"},
            {"id": 2, "name": "rev-warmup", "type": "standard"},
            {"id": 3, "name": "hidden", "type": "hidden"},
        ]
    }


def _challenge_detail(id_: int, name: str, category: str) -> dict[str, Any]:
    """challenge 詳細のスタブ応答

    Args:
        id_: challenge ID
        name: challenge 名
        category: category 文字列

    Returns:
        詳細 payload 含む dict
    """
    return {
        "data": {
            "id": id_,
            "name": name,
            "category": category,
            "description": "<p>desc</p>",
            "value": 100,
            "connection_info": "nc host 1337",
            "tags": [{"value": "warmup"}],
            "hints": [{"content": "look inside", "cost": 0}],
            "files": ["/files/abc/binary"],
        }
    }


def _users_me(id_: int = 7, team_id: int | None = None) -> dict[str, Any]:
    """users/me のスタブ応答

    Args:
        id_: user ID
        team_id: team ID

    Returns:
        users/me の data 部相当 dict
    """
    return {"data": {"id": id_, "team_id": team_id}}


@pytest.mark.asyncio
async def test_fetch_all_returns_visible_challenges_with_normalized_strategy() -> None:
    """可視 challenge の Strategy 正規化付き取得"""
    responses: dict[tuple[str, str], dict | str] = {
        ("GET", "/api/v1/challenges"): _challenge_stubs(),
        ("GET", "/api/v1/challenges/1"): _challenge_detail(1, "pwn-baby", "Pwn"),
        ("GET", "/api/v1/challenges/2"): _challenge_detail(2, "rev-warmup", "Reverse Engineering"),
        ("GET", "/api/v1/users/me"): _users_me(id_=7),
        ("GET", "/api/v1/users/7/solves"): {"data": []},
    }
    async with _mock_client(responses) as http:
        client = CtfdClient(
            CtfdConfig(base_url="https://ctf.example.com", token="t"),
            http=http,
        )
        cs = await client.fetch_all()

    from shared.task import Strategy

    assert [c.name for c in cs.challenges] == ["pwn-baby", "rev-warmup"]
    assert cs.challenges[0].strategy is Strategy.PWN
    assert cs.challenges[1].strategy is Strategy.REV
    assert cs.challenges[0].description == "desc"
    assert cs.challenges[0].tags == ("warmup",)
    assert cs.solved_names == frozenset()


@pytest.mark.asyncio
async def test_fetch_all_respects_team_solves_when_team_id_set() -> None:
    """team_id 指定時の team solves 優先"""
    responses: dict[tuple[str, str], dict | str] = {
        ("GET", "/api/v1/challenges"): _challenge_stubs(),
        ("GET", "/api/v1/challenges/1"): _challenge_detail(1, "pwn-baby", "Pwn"),
        ("GET", "/api/v1/challenges/2"): _challenge_detail(2, "rev-warmup", "rev"),
        ("GET", "/api/v1/users/me"): _users_me(team_id=42),
        ("GET", "/api/v1/teams/42/solves"): {
            "data": [{"challenge": {"name": "pwn-baby"}}]
        },
    }
    async with _mock_client(responses) as http:
        client = CtfdClient(
            CtfdConfig(base_url="https://ctf.example.com", token="t"),
            http=http,
        )
        cs = await client.fetch_all()
    assert "pwn-baby" in cs.solved_names
    assert [c.name for c in cs.unsolved()] == ["rev-warmup"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status, expected",
    [
        ("correct", FlagVerdict.CORRECT),
        ("already_solved", FlagVerdict.ALREADY_SOLVED),
        ("incorrect", FlagVerdict.INCORRECT),
        ("weird_status", FlagVerdict.UNKNOWN),
    ],
)
async def test_submit_flag_maps_status_to_verdict(status: str, expected: FlagVerdict) -> None:
    """status 文字列から FlagVerdict への写像

    Args:
        status: CTFd 応答 status 文字列
        expected: 期待される FlagVerdict
    """
    submit_body = {"data": {"status": status, "message": "msg"}}
    responses: dict[tuple[str, str], dict | str] = {
        ("GET", "/api/v1/challenges"): _challenge_stubs(),
        ("POST", "/api/v1/challenges/attempt"): submit_body,
    }
    async with _mock_client(responses) as http:
        client = CtfdClient(
            CtfdConfig(base_url="https://ctf.example.com", token="t"),
            http=http,
        )
        attempt = await client.submit_flag("pwn-baby", "FLAG{x}")
    assert attempt.verdict is expected
    assert attempt.challenge_name == "pwn-baby"
    assert attempt.flag == "FLAG{x}"
    assert attempt.message == "msg"


@pytest.mark.asyncio
async def test_submit_flag_sets_auth_header_from_token() -> None:
    """token からの Authorization ヘッダ設定"""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """リクエスト収集ハンドラ

        Args:
            request: httpx リクエスト

        Returns:
            固定応答
        """
        captured.append(request)
        if request.url.path == "/api/v1/challenges":
            return httpx.Response(200, json=_challenge_stubs())
        return httpx.Response(200, json={"data": {"status": "correct", "message": ""}})

    async with httpx.AsyncClient(
        base_url="https://ctf.example.com",
        transport=httpx.MockTransport(handler),
    ) as http:
        client = CtfdClient(
            CtfdConfig(base_url="https://ctf.example.com", token="t_ABC"),
            http=http,
        )
        await client.submit_flag("pwn-baby", "FLAG{x}")

    submit = next(r for r in captured if r.method == "POST")
    assert submit.headers.get("Authorization") == "Token t_ABC"
    body = json.loads(submit.content)
    assert body == {"challenge_id": 1, "submission": "FLAG{x}"}


@pytest.mark.asyncio
async def test_submit_flag_raises_when_challenge_not_found() -> None:
    """未知 challenge 名に対する CtfdError"""
    responses: dict[tuple[str, str], dict | str] = {
        ("GET", "/api/v1/challenges"): _challenge_stubs(),
    }
    async with _mock_client(responses) as http:
        client = CtfdClient(
            CtfdConfig(base_url="https://ctf.example.com", token="t"),
            http=http,
        )
        from layers.ctfd import CtfdError

        with pytest.raises(CtfdError):
            await client.submit_flag("nonexistent", "FLAG{x}")
