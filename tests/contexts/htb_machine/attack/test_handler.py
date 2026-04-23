from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from contexts.htb_machine.attack import Attacker
from contexts.htb_machine.domain import Difficulty, HtbAttempt, Machine, OwnType
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
            structured_output: 構造化出力
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
def patch_sdk(monkeypatch: pytest.MonkeyPatch):
    """attacker モジュール内の SDK 型差替

    Args:
        monkeypatch: pytest fixture

    Returns:
        差替対象モジュール
    """
    import contexts.htb_machine.attack.handler as mod

    monkeypatch.setattr(mod, "AssistantMessage", _FakeAssistantMessage)
    monkeypatch.setattr(mod, "TextBlock", _FakeTextBlock)
    monkeypatch.setattr(mod, "ResultMessage", _FakeResultMessage)
    monkeypatch.setattr(mod, "HookMatcher", _FakeHookMatcher)
    return mod


class _FakeClient:
    """ClaudeSDKClient 互換の偽クライアント"""

    def __init__(self, messages: list[Any], *, hook_collector: list | None = None) -> None:
        """偽クライアントの初期化

        Args:
            messages: 返却メッセージ列
            hook_collector: hook 回収用リスト
        """
        self._messages = messages
        self._hook_collector = hook_collector if hook_collector is not None else []

    async def __aenter__(self) -> _FakeClient:
        """async context manager 入場

        Returns:
            自身
        """
        return self

    async def __aexit__(self, *exc: Any) -> None:
        """async context manager 退場"""
        return None

    async def query(self, prompt: str) -> None:
        """no-op query

        Args:
            prompt: 受取 prompt
        """
        pass

    async def receive_response(self) -> AsyncIterator[Any]:
        """事前設定メッセージの逐次 yield

        Yields:
            保持中メッセージ
        """
        for m in self._messages:
            yield m


def _factory(messages: list[Any], hook_collector: list | None = None):
    """偽 SDK client factory の生成

    Args:
        messages: 返却メッセージ列
        hook_collector: hook 回収用リスト

    Returns:
        options を受けて _FakeClient を返す関数
    """

    def make(*, options: Any) -> _FakeClient:
        """偽クライアントの生成と hook 回収

        Args:
            options: ClaudeAgentOptions 相当

        Returns:
            _FakeClient
        """
        if hook_collector is not None:
            hooks = options.hooks or {}
            pre = hooks.get("PreToolUse") or []
            for matcher in pre:
                hook_collector.extend(matcher.hooks)
        return _FakeClient(messages, hook_collector=hook_collector)

    return make


def _machine() -> Machine:
    """テスト用 Machine の生成

    Returns:
        固定の Machine
    """
    return Machine(id=42, name="Sherlock", ip="10.10.10.5", os="linux", difficulty=Difficulty.EASY)


def _make_submitter(verdicts: dict[tuple[OwnType, str], bool]):
    """verdict 写像に基づく HTB submitter の生成

    Args:
        verdicts: (own_type, flag) から accepted への写像

    Returns:
        submit 関数と attempts リストの組
    """
    attempts: list[HtbAttempt] = []

    async def submit(own_type: OwnType, flag: str) -> HtbAttempt:
        """固定判定の偽 submit

        Args:
            own_type: own 種別
            flag: 提出 flag

        Returns:
            HtbAttempt
        """
        accepted = verdicts.get((own_type, flag), False)
        a = HtbAttempt(
            machine_name="Sherlock",
            own_type=own_type,
            flag=flag,
            accepted=accepted,
            message="accepted" if accepted else "incorrect",
            submitted_at=datetime.now(UTC),
        )
        attempts.append(a)
        return a

    return submit, attempts


@pytest.mark.asyncio
async def test_attacker_parses_structured_output(patch_sdk) -> None:
    """構造化出力からの summary と chain 抽出"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, _ = _make_submitter({})
    messages = [
        _FakeResultMessage(
            structured_output={
                "summary": "owned via kernel exploit",
                "chain": ["nmap recon", "CVE-2024-XXXX", "SUID binary for root"],
                "user_flag": None,
                "root_flag": None,
            }
        )
    ]
    out = await Attacker(
        machine=_machine(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_factory(messages),
    ).attack()
    assert out.summary == "owned via kernel exploit"
    assert out.chain == ("nmap recon", "CVE-2024-XXXX", "SUID binary for root")


@pytest.mark.asyncio
async def test_hook_intercepts_submit_flag_user_and_accepts(patch_sdk) -> None:
    """user 提出の accept 経路"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, attempts = _make_submitter({(OwnType.USER, "abc"): True})
    hooks: list = []
    att = Attacker(
        machine=_machine(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_factory([_FakeResultMessage(None)], hook_collector=hooks),
    )
    await att.attack()
    assert hooks, "hook not registered"

    result = await hooks[0](
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "submit_flag user abc"},
        },
        "tid",
        None,
    )
    assert len(attempts) == 1
    assert attempts[0].own_type is OwnType.USER
    assert attempts[0].accepted
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "echo" in result["hookSpecificOutput"]["updatedInput"]["command"]


@pytest.mark.asyncio
async def test_hook_rejects_root_flag_when_incorrect(patch_sdk) -> None:
    """root 提出の reject 経路"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, attempts = _make_submitter({})
    hooks: list = []
    att = Attacker(
        machine=_machine(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_factory([_FakeResultMessage(None)], hook_collector=hooks),
    )
    await att.attack()
    result = await hooks[0](
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "submit_flag root wrong"},
        },
        "tid",
        None,
    )
    assert len(attempts) == 1
    assert not attempts[0].accepted
    assert "REJECTED" in result["hookSpecificOutput"]["updatedInput"]["command"]


@pytest.mark.asyncio
async def test_hook_bash_without_submit_rewrites_to_docker(patch_sdk) -> None:
    """submit_flag 以外 Bash の docker exec 書換"""
    sandbox = StubSandbox()
    await sandbox.start()
    submit, _ = _make_submitter({})
    hooks: list = []
    await Attacker(
        machine=_machine(),
        sandbox=sandbox,
        flag_submitter=submit,
        client_factory=_factory([_FakeResultMessage(None)], hook_collector=hooks),
    ).attack()
    result = await hooks[0](
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "nmap -sV 10.10.10.5"},
        },
        "tid",
        None,
    )
    cmd = result["hookSpecificOutput"]["updatedInput"]["command"]
    assert cmd.startswith("docker exec -i stub-container bash -c")
