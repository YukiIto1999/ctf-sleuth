from __future__ import annotations

from contexts.ctf_challenge.domain import FlagVerdict


class TestFlagVerdict:
    """FlagVerdict 列挙値の検証"""

    def test_values(self) -> None:
        """FlagVerdict の値集合"""
        assert {v.value for v in FlagVerdict} == {
            "correct",
            "already_solved",
            "incorrect",
            "unknown",
        }
