from __future__ import annotations

from pathlib import Path

from contexts.artifact_analysis.domain import Artifact
from shared.probe import FileKind


class TestArtifactFilename:
    """Artifact.filename の挙動検証"""

    def test_returns_path_name(self) -> None:
        """path.name の返却"""
        art = Artifact(
            path=Path("/tmp/dir/sample.bin"),
            kind=FileKind.ELF,
            size_bytes=0,
            sha256="x",
        )
        assert art.filename() == "sample.bin"
