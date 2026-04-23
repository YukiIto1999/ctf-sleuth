from __future__ import annotations

import pytest

from contexts.htb_machine.domain import Difficulty, Machine


class TestMachine:
    """Machine の不変性検証"""

    def test_is_frozen(self) -> None:
        """Machine が frozen であることの検証"""
        m = Machine(id=1, name="x", ip="10.10.10.5", os="linux")
        with pytest.raises((AttributeError, TypeError)):
            m.ip = "..."  # type: ignore[misc]


class TestDifficulty:
    """Difficulty 列挙の検証"""

    def test_unknown_default_value(self) -> None:
        """Difficulty.UNKNOWN 値"""
        assert Difficulty.UNKNOWN.value == "unknown"
