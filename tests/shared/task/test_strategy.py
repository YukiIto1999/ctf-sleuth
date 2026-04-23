from __future__ import annotations

from shared.task import Strategy


class TestStrategy:
    """Strategy 列挙の値安定性検証"""

    def test_values(self) -> None:
        """Strategy の値集合の検証"""
        assert {s.value for s in Strategy} == {"pwn", "rev", "crypto", "web", "forensics", "osint"}
