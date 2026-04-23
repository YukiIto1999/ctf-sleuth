from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest

from layers.llm_classifier.claude import LlmClassifier
from shared.probe import FileKind, HttpProbe, InputProbe, InputShape
from shared.task import AlternativeClass, TaskType


def _shape(raw: str, **overrides: bool) -> InputShape:
    """テスト用 InputShape の生成

    Args:
        raw: 入力文字列
        **overrides: 真偽フィールドの上書き

    Returns:
        デフォルト False の InputShape
    """
    base = {
        "raw": raw,
        "is_http_url": False,
        "is_ip": False,
        "is_domain": False,
        "looks_like_question": False,
        "htb_hint": False,
    }
    base.update(overrides)
    return InputShape(**base)  # type: ignore[arg-type]


def _probe(
    raw: str,
    *,
    shape_kwargs: dict | None = None,
    is_existing_path: bool = False,
    file_kind: FileKind | None = None,
    http: HttpProbe | None = None,
) -> InputProbe:
    """テスト用 InputProbe の生成

    Args:
        raw: 入力文字列
        shape_kwargs: shape の上書き
        is_existing_path: path 存在フラグ
        file_kind: FileKind
        http: HttpProbe

    Returns:
        組立済 InputProbe
    """
    return InputProbe(
        shape=_shape(raw, **(shape_kwargs or {})),
        is_existing_path=is_existing_path,
        file_kind=file_kind,
        http=http,
    )


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


@pytest.fixture
def patched_sdk_types(monkeypatch: pytest.MonkeyPatch):
    """LlmClassifier 内の SDK 型差替フィクスチャ

    Args:
        monkeypatch: pytest fixture

    Returns:
        差替対象のモジュール
    """
    import layers.llm_classifier.claude as mod

    monkeypatch.setattr(mod, "AssistantMessage", _FakeAssistantMessage)
    monkeypatch.setattr(mod, "TextBlock", _FakeTextBlock)
    monkeypatch.setattr(mod, "ResultMessage", _FakeResultMessage)
    return mod


class _FakeClient:
    """偽 ClaudeSDKClient"""

    def __init__(self, *, messages: list[Any]) -> None:
        """偽クライアントの初期化

        Args:
            messages: 返却するメッセージ列
        """
        self._messages = messages
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
        for msg in self._messages:
            yield msg


def _factory(messages: list[Any]):
    """ClaudeSDKClient factory の生成

    Args:
        messages: 返却するメッセージ列

    Returns:
        options を受けて _FakeClient を返す関数
    """

    def factory(*, options: Any) -> _FakeClient:
        """偽クライアントの生成

        Args:
            options: ClaudeAgentOptions 相当

        Returns:
            _FakeClient インスタンス
        """
        return _FakeClient(messages=messages)

    return factory


@pytest.mark.asyncio
async def test_parses_structured_output(patched_sdk_types) -> None:
    """構造化出力からの Classification 復元"""
    response = {
        "task_type": "ctf_challenge",
        "confidence": 0.92,
        "reasoning": "ctfd api responded",
        "alternatives": [{"task_type": "osint_investigation", "confidence": 0.1}],
    }
    messages = [_FakeResultMessage(structured_output=response)]
    clf = LlmClassifier(client_factory=_factory(messages))
    probe = _probe("https://ctf.example.com", shape_kwargs={"is_http_url": True})
    result = await clf.classify(probe)
    assert result.task_type is TaskType.CTF_CHALLENGE
    assert result.confidence == pytest.approx(0.92)
    assert result.alternatives == (
        AlternativeClass(TaskType.OSINT_INVESTIGATION, 0.1),
    )


@pytest.mark.asyncio
async def test_falls_back_to_text_if_no_structured(patched_sdk_types) -> None:
    """構造化不在時の素テキスト JSON fallback"""
    raw_text = json.dumps(
        {
            "task_type": "osint_investigation",
            "confidence": 0.7,
            "reasoning": "text fallback",
            "alternatives": [],
        }
    )
    messages = [
        _FakeAssistantMessage(content=[_FakeTextBlock(text=raw_text)]),
        _FakeResultMessage(structured_output=None),
    ]
    clf = LlmClassifier(client_factory=_factory(messages))
    probe = _probe("example.com", shape_kwargs={"is_domain": True})
    result = await clf.classify(probe)
    assert result.task_type is TaskType.OSINT_INVESTIGATION


@pytest.mark.asyncio
async def test_raises_when_no_output(patched_sdk_types) -> None:
    """出力皆無時の RuntimeError"""
    messages = [_FakeResultMessage(structured_output=None)]
    clf = LlmClassifier(client_factory=_factory(messages))
    probe = _probe("xyz")
    with pytest.raises(RuntimeError):
        await clf.classify(probe)
