from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from contexts.osint_investigation.domain import Target, TargetKind
from contexts.osint_investigation.investigate import Investigator
from contexts.osint_investigation.investigate.handler import (
    _findings_from_payload,
    _severity_from_str,
)
from shared.result import Severity


class TestFindingsFromPayload:
    """_findings_from_payload の検証"""

    def test_parses_minimal_finding(self) -> None:
        """最小 finding の復元"""
        now = datetime.now(UTC)
        raw = [{"summary": "TLS weak", "severity": "medium"}]
        findings, evidence = _findings_from_payload(raw, now)
        assert len(findings) == 1
        assert findings[0].summary == "TLS weak"
        assert findings[0].severity is Severity.MEDIUM
        assert evidence == []

    def test_skips_entries_without_summary(self) -> None:
        """summary 欠落エントリの除外"""
        now = datetime.now(UTC)
        raw = [
            {"summary": "", "severity": "info"},
            {"severity": "info"},
            {"summary": "real", "severity": "info"},
        ]
        findings, _ = _findings_from_payload(raw, now)
        assert [f.summary for f in findings] == ["real"]

    def test_evidence_is_captured(self) -> None:
        """evidence リストの取込"""
        now = datetime.now(UTC)
        raw = [
            {
                "summary": "exposed key",
                "severity": "high",
                "evidence": ["github.com/u/r: key at L42", "hibp record"],
            }
        ]
        findings, evidence_pool = _findings_from_payload(raw, now)
        assert len(findings[0].evidence) == 2
        assert len(evidence_pool) == 2
        assert "github.com" in evidence_pool[0].content

    def test_unknown_severity_falls_back_to_info(self) -> None:
        """未知 severity の INFO fallback"""
        assert _severity_from_str("bogus") is Severity.INFO
        assert _severity_from_str("HIGH") is Severity.HIGH


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
    """investigator モジュール内の SDK 型差替

    Args:
        monkeypatch: pytest fixture

    Returns:
        差替対象モジュール
    """
    import contexts.osint_investigation.investigate.handler as mod

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
        self.query_calls: list[str] = []

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
        """query 呼出の記録

        Args:
            prompt: 受取 prompt
        """
        self.query_calls.append(prompt)

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

    def factory(*, options: Any) -> _FakeClient:
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

    return factory


@pytest.mark.asyncio
async def test_investigator_parses_structured_findings(patch_sdk) -> None:
    """構造化 findings の Finding 化"""
    messages = [
        _FakeResultMessage(
            structured_output={
                "findings": [
                    {
                        "summary": "outdated TLS",
                        "severity": "medium",
                        "recommendation": "upgrade",
                        "evidence": ["SSL Labs B"],
                    },
                    {
                        "summary": "open on port 22",
                        "severity": "info",
                        "evidence": [],
                    },
                ]
            }
        )
    ]
    inv = Investigator(
        target=Target(raw="example.com", kind=TargetKind.DOMAIN),
        client_factory=_factory(messages),
    )
    result = await inv.investigate()
    assert len(result.findings) == 2
    assert result.findings[0].summary == "outdated TLS"
    assert result.findings[0].severity is Severity.MEDIUM
    assert result.findings[0].recommendation == "upgrade"


@pytest.mark.asyncio
async def test_investigator_returns_empty_when_no_output(patch_sdk) -> None:
    """構造化不在時の空 findings"""
    messages = [_FakeResultMessage(structured_output=None)]
    inv = Investigator(
        target=Target(raw="x", kind=TargetKind.TEXT),
        client_factory=_factory(messages),
    )
    result = await inv.investigate()
    assert result.findings == ()


@pytest.mark.asyncio
async def test_investigator_hook_denies_bash(patch_sdk) -> None:
    """OSINT での Bash deny"""
    hooks: list = []
    inv = Investigator(
        target=Target(raw="x", kind=TargetKind.TEXT),
        client_factory=_factory([_FakeResultMessage(None)], hook_collector=hooks),
    )
    await inv.investigate()
    assert hooks, "PreToolUse hook not registered"
    result = await hooks[0](
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "whoami"},
        },
        "tid",
        None,
    )
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.asyncio
async def test_investigator_hook_passes_webfetch(patch_sdk) -> None:
    """OSINT での WebFetch 通過"""
    hooks: list = []
    inv = Investigator(
        target=Target(raw="x", kind=TargetKind.URL),
        client_factory=_factory([_FakeResultMessage(None)], hook_collector=hooks),
    )
    await inv.investigate()
    result = await hooks[0](
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://x"},
        },
        "tid",
        None,
    )
    assert result == {}
