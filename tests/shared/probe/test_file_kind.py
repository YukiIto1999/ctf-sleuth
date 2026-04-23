from __future__ import annotations

from shared.probe import FileKind


class TestFileKind:
    """FileKind 列挙の値安定性検証"""

    def test_values(self) -> None:
        """代表値の検証"""
        assert FileKind.ELF.value == "elf"
        assert FileKind.UNKNOWN.value == "unknown"
