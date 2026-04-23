from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from contexts.artifact_analysis.analyze import Analyzer
from contexts.artifact_analysis.domain import Artifact
from layers.sandbox import StubSandbox
from shared.probe import FileKind


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
    """Analyzer モジュール内の SDK 型差替

    Args:
        monkeypatch: pytest fixture

    Returns:
        差替対象モジュール
    """
    import contexts.artifact_analysis.analyze.handler as mod

    monkeypatch.setattr(mod, "AssistantMessage", _FakeAssistantMessage)
    monkeypatch.setattr(mod, "TextBlock", _FakeTextBlock)
    monkeypatch.setattr(mod, "ResultMessage", _FakeResultMessage)
    monkeypatch.setattr(mod, "HookMatcher", _FakeHookMatcher)
    return mod


class _FakeClient:
    """ClaudeSDKClient 互換の偽クライアント"""

    def __init__(self, messages: list[Any]) -> None:
        """偽クライアントの初期化

        Args:
            messages: 返却メッセージ列
        """
        self._messages = messages

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


def _factory(messages: list[Any]):
    """偽 SDK client factory の生成

    Args:
        messages: 返却メッセージ列

    Returns:
        options を受けて _FakeClient を返す関数
    """

    def make(*, options: Any) -> _FakeClient:
        """偽クライアント生成

        Args:
            options: 無視

        Returns:
            _FakeClient
        """
        return _FakeClient(messages)

    return make


def _artifact() -> Artifact:
    """テスト用 Artifact の生成

    Returns:
        固定値 Artifact
    """
    return Artifact(
        path=Path("/tmp/sample.bin"),
        kind=FileKind.ELF,
        size_bytes=1234,
        sha256="abcdef",
    )


@pytest.mark.asyncio
async def test_parses_structured_output(patch_sdk) -> None:
    """構造化出力からの summary と sections 抽出"""
    sandbox = StubSandbox()
    await sandbox.start()
    messages = [
        _FakeResultMessage(
            structured_output={
                "summary": "ELF x86_64 stripped",
                "sections": [
                    {"title": "Overview", "body": "PIE enabled"},
                    {"title": "Strings", "body": "no obvious flag"},
                ],
            }
        )
    ]
    report = await Analyzer(
        artifact=_artifact(),
        sandbox=sandbox,
        container_path="/artifact/sample.bin",
        client_factory=_factory(messages),
    ).analyze()
    assert report.summary == "ELF x86_64 stripped"
    assert report.sections == (
        ("Overview", "PIE enabled"),
        ("Strings", "no obvious flag"),
    )


@pytest.mark.asyncio
async def test_falls_back_when_no_structured_output(patch_sdk) -> None:
    """構造化不在時の default summary"""
    sandbox = StubSandbox()
    await sandbox.start()
    messages = [_FakeResultMessage(structured_output=None)]
    report = await Analyzer(
        artifact=_artifact(),
        sandbox=sandbox,
        container_path="/artifact/sample.bin",
        client_factory=_factory(messages),
    ).analyze()
    assert "no analysis produced" in report.summary
    assert report.sections == ()


@pytest.mark.asyncio
async def test_evidence_contains_artifact_metadata(patch_sdk) -> None:
    """evidence への sha256 と size 反映"""
    sandbox = StubSandbox()
    await sandbox.start()
    messages = [_FakeResultMessage(structured_output=None)]
    report = await Analyzer(
        artifact=_artifact(),
        sandbox=sandbox,
        container_path="/artifact/sample.bin",
        client_factory=_factory(messages),
    ).analyze()
    assert len(report.evidence) == 1
    assert "abcdef" in report.evidence[0].content
    assert "1234" in report.evidence[0].content
    assert "elf" in report.evidence[0].content
