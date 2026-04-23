from __future__ import annotations

from contexts.htb_machine.domain import OwnType


class TestOwnType:
    """OwnType 列挙の検証"""

    def test_values(self) -> None:
        """OwnType 値集合"""
        assert {t.value for t in OwnType} == {"user", "root"}
