from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from contexts.ctf_challenge.domain import (
    Challenge,
    ChallengeId,
    FlagVerdict,
    SolveAttempt,
)
from contexts.ctf_challenge.solve import (
    SOLVER_OUTPUT_SCHEMA,
    Solver,
    SolverOutput,
)
from layers.sandbox import StubSandbox


@dataclass
class _FakeTextBlock:
    """偽 TextBlock

    Attributes:
        text: テキスト内容
    """

    text: str


class _FakeAssistantMessage:
    """偽 AssistantMessage"""

    def __init__(self, content: list[Any]) -> None:
        """偽メッセージの初期化

        Args:
            content: 含めるブロック列
        """
        self.content = content


class _FakeResultMessage:
    """偽 ResultMessage"""

    def __init__(self, structured_output: dict[str, Any] | None = None) -> None:
        """偽 result の初期化

        Args:
            structured_output: 返却する構造化出力
        """
        self.structured_output = structured_output


class _FakeHookMatcher:
    """偽 HookMatcher"""

    def __init__(self, *, hooks: list[Any]) -> None:
        """偽 matcher の初期化

        Args:
            hooks: hook 関数のリスト
        """
        self.hooks = hooks


@pytest.fixture
def patch_sdk_types(monkeypatch: pytest.MonkeyPatch):
    """solver モジュール内の SDK 型差替フィクスチャ

    Args:
        monkeypatch: pytest fixture

    Returns:
        差替対象モジュール
    """
    import contexts.ctf_challenge.solve.handler as mod

    monkeypatch.setattr(mod, "AssistantMessage", _FakeAssistantMessage)
    monkeypatch.setattr(mod, "TextBlock", _FakeTextBlock)
    monkeypatch.setattr(mod, "ResultMessage", _FakeResultMessage)
    monkeypatch.setattr(mod, "HookMatcher", _FakeHookMatcher)
    return mod


class _FakeClient:
    """ClaudeSDKClient 互換の偽クライアント"""

    def __init__(self, messages: list[Any], *, collect_hook: list | None = None) -> None:
        """偽クライアントの初期化

        Args:
            messages: 返却するメッセージ列
            collect_hook: hook 関数回収用リスト
        """
        self._messages = messages
        self._hook_collector = collect_hook if collect_hook is not None else []
        self.query_calls: list[str] = []

    async def __aenter__(self) -> _FakeClient:
        """async context manager の入場

        Returns:
            自身
        """
        return self

    async def __aexit__(self, *exc: Any) -> None:
        """async context manager の退場"""
        return None

    async def query(self, prompt: str) -> None:
        """偽 query 記録

        Args:
            prompt: 受け付けた prompt
        """
        self.query_calls.append(prompt)

    async def receive_response(self) -> AsyncIterator[Any]:
        """事前設定メッセージの逐次 yield

        Yields:
            保持中のメッセージ
        """
        for m in self._messages:
            yield m


def _make_factory(messages: list[Any], hook_collector: list | None = None):
    """ClaudeSDKClient factory の生成

    Args:
        messages: 返却するメッセージ列
        hook_collector: PreToolUse hook 回収用リスト

    Returns:
        options を受けて _FakeClient を返す関数
    """

    def factory(*, options: Any) -> _FakeClient:
        """偽クライアントの生成と hook 回収

        Args:
            options: ClaudeAgentOptions 相当

        Returns:
            _FakeClient インスタンス
        """
        if hook_collector is not None:
            hooks = options.hooks or {}
            pre = hooks.get("PreToolUse") or []
            for matcher in pre:
                hook_collector.extend(matcher.hooks)
        return _FakeClient(messages, collect_hook=hook_collector)

    return factory


def _challenge() -> Challenge:
    """テスト用 Challenge の生成

    Returns:
        固定の Challenge
    """
    return Challenge(
        id=ChallengeId(1),
        name="pwn-easy",
        category_raw="Pwn",
        strategy=None,
        description="Exploit me",
        value=100,
    )


def _make_submitter(verdict_map: dict[str, FlagVerdict]):
    """verdict 写像に基づく偽 flag submitter の生成

    Args:
        verdict_map: flag 文字列から FlagVerdict への写像

    Returns:
        submit 関数と試行履歴リストの組
    """
    attempts: list[SolveAttempt] = []

    async def submit(challenge_name: str, flag: str) -> SolveAttempt:
        """事前写像に基づく擬似 submit

        Args:
            challenge_name: challenge 名
            flag: 提出 flag

        Returns:
            verdict 付き SolveAttempt
        """
        verdict = verdict_map.get(flag, FlagVerdict.INCORRECT)
        a = SolveAttempt(
            challenge_name=challenge_name,
            flag=flag,
            verdict=verdict,
            message=f"test verdict={verdict.value}",
            submitted_at=datetime.now(UTC),
        )
        attempts.append(a)
        return a

    return submit, attempts


@pytest.mark.asyncio
async def test_solver_returns_flag_from_structured_output(patch_sdk_types) -> None:
    """構造化出力からの flag 抽出"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, _ = _make_submitter({"FLAG{x}": FlagVerdict.CORRECT})
    messages = [
        _FakeResultMessage(
            structured_output={"type": "flag_found", "flag": "FLAG{x}", "method": "xor"}
        ),
    ]

    solver = Solver(
        challenge=_challenge(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_make_factory(messages),
    )
    out: SolverOutput = await solver.solve()

    assert out.flag is not None
    assert out.flag.value == "FLAG{x}"
    assert out.reasoning == "xor"


@pytest.mark.asyncio
async def test_solver_returns_none_when_no_structured_output(patch_sdk_types) -> None:
    """構造化出力不在時の flag=None"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, _ = _make_submitter({})
    messages = [_FakeResultMessage(structured_output=None)]

    solver = Solver(
        challenge=_challenge(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_make_factory(messages),
    )
    out = await solver.solve()
    assert out.flag is None
    assert not out.confirmed


@pytest.mark.asyncio
async def test_hook_rewrites_bash_to_docker_exec(patch_sdk_types) -> None:
    """Bash の docker exec 書換"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, _ = _make_submitter({})
    hooks: list = []
    messages = [_FakeResultMessage(structured_output=None)]

    solver = Solver(
        challenge=_challenge(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_make_factory(messages, hook_collector=hooks),
    )
    await solver.solve()
    assert hooks, "PreToolUse hook not registered"

    hook = hooks[0]
    result = await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la /tmp"},
        },
        "tid",
        None,
    )
    rewritten = result["hookSpecificOutput"]["updatedInput"]["command"]
    assert "docker exec -i stub-container bash -c" in rewritten
    assert "'ls -la /tmp'" in rewritten
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


@pytest.mark.asyncio
async def test_hook_denies_non_bash_non_web_tools(patch_sdk_types) -> None:
    """非 Bash 非 Web ツールの deny"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, _ = _make_submitter({})
    hooks: list = []
    messages = [_FakeResultMessage(structured_output=None)]

    Solver(
        challenge=_challenge(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_make_factory(messages, hook_collector=hooks),
    )
    solver = Solver(
        challenge=_challenge(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_make_factory(messages, hook_collector=hooks),
    )
    await solver.solve()
    hook = hooks[0]
    result = await hook(
        {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {}},
        "tid",
        None,
    )
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Read" in result["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.asyncio
async def test_hook_passes_through_webfetch(patch_sdk_types) -> None:
    """WebFetch の allow 素通し"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, _ = _make_submitter({})
    hooks: list = []
    messages = [_FakeResultMessage(structured_output=None)]

    solver = Solver(
        challenge=_challenge(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_make_factory(messages, hook_collector=hooks),
    )
    await solver.solve()
    hook = hooks[0]
    out = await hook(
        {"hook_event_name": "PreToolUse", "tool_name": "WebFetch", "tool_input": {}},
        "tid",
        None,
    )
    assert out == {}


@pytest.mark.asyncio
async def test_submit_flag_is_intercepted_and_recorded(patch_sdk_types) -> None:
    """submit_flag 傍受と記録"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, attempts = _make_submitter({"FLAG{ok}": FlagVerdict.CORRECT})
    hooks: list = []
    messages = [_FakeResultMessage(structured_output=None)]

    solver = Solver(
        challenge=_challenge(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_make_factory(messages, hook_collector=hooks),
    )
    await solver.solve()
    hook = hooks[0]

    out = await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "submit_flag FLAG{ok}"},
        },
        "tid",
        None,
    )

    assert len(attempts) == 1
    assert attempts[0].verdict is FlagVerdict.CORRECT
    rewritten = out["hookSpecificOutput"]["updatedInput"]["command"]
    assert rewritten.startswith("echo ")
    assert "CORRECT" in rewritten


@pytest.mark.asyncio
async def test_incorrect_flag_does_not_confirm(patch_sdk_types) -> None:
    """誤 flag 提出時の非 confirmed"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, _ = _make_submitter({"FLAG{wrong}": FlagVerdict.INCORRECT})
    hooks: list = []
    messages = [_FakeResultMessage(structured_output=None)]

    solver = Solver(
        challenge=_challenge(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_make_factory(messages, hook_collector=hooks),
    )
    await solver.solve()
    hook = hooks[0]
    await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "submit_flag FLAG{wrong}"},
        },
        "tid",
        None,
    )

    assert solver._confirmed is False


def test_solver_output_schema_has_flag_and_method() -> None:
    """SOLVER_OUTPUT_SCHEMA の必須フィールド検証"""
    assert SOLVER_OUTPUT_SCHEMA["required"] == ["type", "flag", "method"]
    assert "flag_found" in SOLVER_OUTPUT_SCHEMA["properties"]["type"]["enum"]
