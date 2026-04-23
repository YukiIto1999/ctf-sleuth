from __future__ import annotations

import pytest

from workflows.dispatch.policies.shape import analyze_shape


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://example.com", {"is_http_url": True, "is_domain": False, "is_ip": False}),
        ("http://example.com/path", {"is_http_url": True, "is_domain": False, "is_ip": False}),
        ("example.com", {"is_http_url": False, "is_domain": True, "is_ip": False}),
        ("sub.example.co.jp", {"is_http_url": False, "is_domain": True, "is_ip": False}),
        ("192.168.1.1", {"is_http_url": False, "is_domain": False, "is_ip": True}),
        ("10.10.10.5", {"is_http_url": False, "is_domain": False, "is_ip": True, "htb_hint": True}),
        ("10.129.50.100", {"is_http_url": False, "is_domain": False, "is_ip": True, "htb_hint": True}),
        ("10.0.0.1", {"is_http_url": False, "is_domain": False, "is_ip": True, "htb_hint": False}),
        ("What is JWT algorithm confusion?", {"looks_like_question": True}),
        ("how does ROP work", {"looks_like_question": True}),
        ("describe heap spray attack", {"looks_like_question": True}),
        ("random plain text", {"is_http_url": False, "is_domain": False, "is_ip": False, "looks_like_question": False}),
    ],
)
def test_analyze_shape_table(raw: str, expected: dict[str, bool]) -> None:
    """テーブル駆動での analyze_shape 検証

    Args:
        raw: 入力文字列
        expected: 期待属性辞書
    """
    shape = analyze_shape(raw)
    for attr, want in expected.items():
        assert getattr(shape, attr) == want, f"{attr} on {raw!r}: got {getattr(shape, attr)}"


def test_analyze_shape_strips_whitespace() -> None:
    """前後空白の除去"""
    assert analyze_shape("  example.com  ").raw == "example.com"


def test_analyze_shape_is_pure() -> None:
    """同一入力に対する同一出力"""
    a = analyze_shape("10.10.10.1")
    b = analyze_shape("10.10.10.1")
    assert a == b
