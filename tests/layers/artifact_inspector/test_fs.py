from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from layers.artifact_inspector import inspect_artifact
from shared.probe import FileKind


class TestInspectArtifact:
    """inspect_artifact の検証"""

    def test_computes_size_and_hash(self, tmp_path: Path) -> None:
        """size と sha256 の計算

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "sample.bin"
        content = b"hello artifact"
        p.write_bytes(content)

        art = inspect_artifact(p)
        assert art.size_bytes == len(content)
        assert art.sha256 == hashlib.sha256(content).hexdigest()
        assert art.path == p.resolve()

    def test_detects_elf_magic(self, tmp_path: Path) -> None:
        """ELF マジックの検出

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "x"
        p.write_bytes(b"\x7fELF\x02\x01\x01")
        art = inspect_artifact(p)
        assert art.kind == FileKind.ELF

    def test_is_frozen(self, tmp_path: Path) -> None:
        """Artifact が frozen であることの検証

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "x"
        p.write_bytes(b"")
        art = inspect_artifact(p)
        with pytest.raises((AttributeError, TypeError)):
            art.size_bytes = 999  # type: ignore[misc]
