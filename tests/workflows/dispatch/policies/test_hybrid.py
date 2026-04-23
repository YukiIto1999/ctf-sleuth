from __future__ import annotations

import pytest

from shared.probe import FileKind, HttpProbe, InputProbe, InputShape
from shared.task import Classification, TaskType
from workflows.dispatch.policies import HybridClassifier, HybridConfig


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


class _StubLlm:
    """Classification を固定で返す LLM スタブ

    Attributes:
        result: 返却する Classification
        calls: 呼出回数
    """

    def __init__(self, result: Classification | None = None) -> None:
        """スタブの初期化

        Args:
            result: 返却する Classification
        """
        self.result = result
        self.calls = 0

    async def classify(self, probe: InputProbe) -> Classification:
        """classify の擬似実行

        Args:
            probe: 入力観測結果

        Returns:
            保持している Classification
        """
        self.calls += 1
        assert self.result is not None, "stub was not supposed to be called"
        return self.result


class _FailingLlm:
    """例外を送出する LLM スタブ

    Attributes:
        calls: 呼出回数
    """

    def __init__(self, exc: Exception | None = None) -> None:
        """失敗スタブの初期化

        Args:
            exc: 送出する例外
        """
        self._exc = exc or RuntimeError("llm unavailable")
        self.calls = 0

    async def classify(self, probe: InputProbe) -> Classification:
        """常に例外を送出する classify

        Args:
            probe: 入力観測結果

        Raises:
            Exception: 初期化時指定の例外
        """
        self.calls += 1
        raise self._exc


@pytest.mark.asyncio
async def test_skips_llm_when_confidence_high() -> None:
    """高信頼度時の LLM 省略"""
    stub = _StubLlm(result=None)
    clf = HybridClassifier(stub, config=HybridConfig(escalate_below=0.75))
    probe = _probe(
        "10.10.10.5",
        shape_kwargs={"is_ip": True, "htb_hint": True},
    )
    result = await clf.classify(probe)
    assert result.task_type is TaskType.HTB_MACHINE
    assert stub.calls == 0


@pytest.mark.asyncio
async def test_escalates_on_low_confidence() -> None:
    """低信頼度時の LLM 委譲"""
    llm_result = Classification(
        task_type=TaskType.CTF_CHALLENGE,
        confidence=0.88,
        required_params=(),
        reasoning="llm revised",
    )
    stub = _StubLlm(result=llm_result)
    clf = HybridClassifier(stub, config=HybridConfig(escalate_below=0.75))

    probe = _probe("ambiguous-text")
    result = await clf.classify(probe)
    assert stub.calls == 1
    assert result is llm_result


@pytest.mark.asyncio
async def test_escalates_when_ambiguous() -> None:
    """曖昧時の LLM 委譲"""
    llm_result = Classification(
        task_type=TaskType.OSINT_INVESTIGATION,
        confidence=0.9,
        required_params=(),
        reasoning="llm disambiguated",
    )
    stub = _StubLlm(result=llm_result)
    clf = HybridClassifier(
        stub, config=HybridConfig(escalate_below=0.0, escalate_if_ambiguous=True)
    )

    probe = _probe("example.com", shape_kwargs={"is_domain": True})
    result = await clf.classify(probe)
    assert stub.calls == 1
    assert result is llm_result


@pytest.mark.asyncio
async def test_passes_through_high_conf_non_ambiguous() -> None:
    """高信頼度かつ非曖昧時の素通し"""
    stub = _StubLlm(result=None)
    clf = HybridClassifier(
        stub,
        config=HybridConfig(escalate_below=0.7, escalate_if_ambiguous=True),
    )
    probe = _probe("/tmp/x", is_existing_path=True, file_kind=FileKind.ELF)
    result = await clf.classify(probe)
    assert result.task_type is TaskType.ARTIFACT_ANALYSIS
    assert result.confidence >= 0.9
    assert stub.calls == 0


@pytest.mark.asyncio
async def test_falls_back_to_heuristic_on_llm_failure() -> None:
    """LLM 失敗時の heuristic fallback"""
    failing = _FailingLlm(exc=RuntimeError("no auth"))
    clf = HybridClassifier(
        failing,
        config=HybridConfig(escalate_below=0.99, escalate_if_ambiguous=False),
    )
    probe = _probe("example.com", shape_kwargs={"is_domain": True})
    result = await clf.classify(probe)
    assert result.task_type is TaskType.OSINT_INVESTIGATION
    assert result.confidence == pytest.approx(0.65)
    assert failing.calls == 1
    assert "llm escalation failed" in result.reasoning
    assert "RuntimeError" in result.reasoning
