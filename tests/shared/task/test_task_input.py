from __future__ import annotations

import pytest

from shared.task import TaskInput, TaskType


class TestTaskInput:
    """TaskInput の不変性検証"""

    def test_is_frozen(self) -> None:
        """TaskInput が frozen であることの検証"""
        t = TaskInput(raw="hello", flags={"a": "b"})
        with pytest.raises((AttributeError, TypeError)):
            t.raw = "world"  # type: ignore[misc]

    def test_flags_is_readonly_mapping(self) -> None:
        """flags の読取専用性の検証"""
        t = TaskInput(raw="x", flags={"a": "b"})
        with pytest.raises(TypeError):
            t.flags["c"] = "d"  # type: ignore[index]

    def test_explicit_type_returns_none_if_missing(self) -> None:
        """type フラグ不在時の None 返却"""
        t = TaskInput(raw="x")
        assert t.explicit_type() is None

    def test_explicit_type_parses_flag(self) -> None:
        """type フラグからの TaskType 解決"""
        t = TaskInput(raw="x", flags={"type": "ctf_challenge"})
        assert t.explicit_type() is TaskType.CTF_CHALLENGE

    def test_explicit_type_rejects_invalid(self) -> None:
        """不正 type 値の拒否"""
        t = TaskInput(raw="x", flags={"type": "bogus"})
        with pytest.raises(ValueError):
            t.explicit_type()
