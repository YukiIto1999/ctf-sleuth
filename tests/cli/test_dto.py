from __future__ import annotations

import argparse

from cli.dto import collect_flags, to_task_input


def _ns(**kwargs) -> argparse.Namespace:
    """テスト用 argparse Namespace の生成

    Args:
        **kwargs: 設定する属性

    Returns:
        argparse.Namespace
    """
    return argparse.Namespace(**kwargs)


class TestCollectFlags:
    """collect_flags の検証"""

    def test_returns_empty_when_no_fields(self) -> None:
        """属性未設定時の空 dict"""
        assert collect_flags(_ns(input="x")) == {}

    def test_extracts_task_type_as_type(self) -> None:
        """task_type の type キー化"""
        assert collect_flags(_ns(input="x", task_type="ctf_challenge")) == {
            "type": "ctf_challenge",
        }

    def test_extracts_known_keys(self) -> None:
        """url / token / machine / ip / model の抽出"""
        result = collect_flags(
            _ns(
                input="x",
                url="https://x",
                token="t",
                machine="42",
                ip="10.10.10.5",
                model="claude-opus-4-6",
            )
        )
        assert result == {
            "url": "https://x",
            "token": "t",
            "machine": "42",
            "ip": "10.10.10.5",
            "model": "claude-opus-4-6",
        }

    def test_skips_empty_values(self) -> None:
        """空値キーの除外"""
        assert collect_flags(_ns(input="x", url="", token="t")) == {"token": "t"}


class TestToTaskInput:
    """to_task_input の検証"""

    def test_produces_readonly_flags(self) -> None:
        """flags 読取専用性"""
        t = to_task_input(_ns(input="x", url="https://x"))
        assert t.raw == "x"
        assert t.flags["url"] == "https://x"
        import pytest

        with pytest.raises(TypeError):
            t.flags["new"] = "v"  # type: ignore[index]
