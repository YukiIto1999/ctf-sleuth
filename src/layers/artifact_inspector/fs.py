from __future__ import annotations

import hashlib
from pathlib import Path

from contexts.artifact_analysis.domain import Artifact
from layers.probe import detect_file_kind


def inspect_artifact(path: Path) -> Artifact:
    """ファイル観測による Artifact の生成

    Args:
        path: 解析対象ファイルパス

    Returns:
        sha256 と FileKind を持つ Artifact
    """
    resolved = path.resolve()
    kind = detect_file_kind(resolved)
    stat = resolved.stat()
    digest = hashlib.sha256()
    with resolved.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return Artifact(
        path=resolved,
        kind=kind,
        size_bytes=stat.st_size,
        sha256=digest.hexdigest(),
    )
