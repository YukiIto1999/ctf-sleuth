from __future__ import annotations

import pytest

from shared.probe import FileKind, HttpProbe, InputProbe, InputShape
from shared.task import TaskType
from workflows.dispatch.policies import classify_heuristic


def _shape(raw: str, **overrides: bool) -> InputShape:
    """テスト用 InputShape の生成

    Args:
        raw: 入力文字列
        **overrides: 真偽フィールドの上書き

    Returns:
        デフォルト False の InputShape
    """
    defaults = {
        "raw": raw,
        "is_http_url": False,
        "is_ip": False,
        "is_domain": False,
        "looks_like_question": False,
        "htb_hint": False,
    }
    defaults.update(overrides)
    return InputShape(**defaults)  # type: ignore[arg-type]


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
        shape_kwargs: shape 部分の上書き
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


def test_existing_file_classified_as_artifact() -> None:
    """既存ファイルの artifact_analysis 分類"""
    p = _probe("/tmp/x.bin", is_existing_path=True, file_kind=FileKind.ELF)
    c = classify_heuristic(p)
    assert c.task_type is TaskType.ARTIFACT_ANALYSIS
    assert c.confidence >= 0.9


def test_htb_ip_classified_as_htb() -> None:
    """HTB IP レンジの htb_machine 分類"""
    p = _probe("10.10.10.5", shape_kwargs={"is_ip": True, "htb_hint": True})
    c = classify_heuristic(p)
    assert c.task_type is TaskType.HTB_MACHINE


def test_ctfd_api_hit_classified_as_ctf() -> None:
    """CTFd API 応答時の ctf_challenge 分類"""
    http = HttpProbe(status=200, server_header=None, ctfd_api_ok=True, final_url="https://ctf.x/")
    p = _probe("https://ctf.x", shape_kwargs={"is_http_url": True}, http=http)
    c = classify_heuristic(p)
    assert c.task_type is TaskType.CTF_CHALLENGE


def test_domain_without_ctfd_falls_to_osint() -> None:
    """CTFd 不一致 URL の osint_investigation fallback"""
    http = HttpProbe(status=200, server_header="nginx", ctfd_api_ok=False, final_url="https://x/")
    p = _probe("https://example.com", shape_kwargs={"is_http_url": True}, http=http)
    c = classify_heuristic(p)
    assert c.task_type is TaskType.OSINT_INVESTIGATION
    assert c.alternatives, "should surface CTF as alternative"


def test_question_text_is_osint_research() -> None:
    """疑問文の osint_investigation 分類"""
    p = _probe("What is JWT algorithm confusion?", shape_kwargs={"looks_like_question": True})
    c = classify_heuristic(p)
    assert c.task_type is TaskType.OSINT_INVESTIGATION


def test_low_signal_text_has_low_confidence() -> None:
    """シグナル乏しい入力の低信頼度"""
    p = _probe("xyz random")
    c = classify_heuristic(p)
    assert c.task_type is TaskType.OSINT_INVESTIGATION
    assert c.confidence < 0.5


@pytest.mark.asyncio
async def test_classify_async_wrapper_matches_heuristic() -> None:
    """async classify の heuristic 一致"""
    from workflows.dispatch.policies import HeuristicClassifier

    p = _probe("10.10.10.5", shape_kwargs={"is_ip": True, "htb_hint": True})
    assert (await HeuristicClassifier().classify(p)).task_type is TaskType.HTB_MACHINE
