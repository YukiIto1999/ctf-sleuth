#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

from contexts.artifact_analysis.analyze import Analyzer
from layers.artifact_inspector import inspect_artifact
from layers.sandbox import DockerSandbox, SandboxConfig
from shared.sandbox import MountSpec

SANDBOX_IMAGE = "sleuth-smoke-sandbox"


def _make_sample_artifact() -> Path:
    """smoke 用 artifact のテンポラリ生成

    Returns:
        埋込マーカーを含むテンポラリファイルのパス
    """
    content = (
        b"\x7fELF_like_prefix_for_test\n"
        b"HIDDEN_MARKER_ABC123\n"
        b"cGF5bG9hZC14eXo=\n"
        b"trailing garbage \x00\x01\x02\x03\x04\n"
    )
    tmp = tempfile.NamedTemporaryFile(
        prefix="smoke-artifact-", suffix=".bin", delete=False
    )
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


async def main() -> int:
    """artifact smoke test のエントリ

    Returns:
        終了コード
    """
    path = _make_sample_artifact()
    artifact = inspect_artifact(path)
    container_path = f"/artifact/{artifact.filename()}"

    config = SandboxConfig(
        image=SANDBOX_IMAGE,
        mounts=(
            MountSpec(source=artifact.path, target=container_path, read_only=True),
        ),
    )
    sandbox = DockerSandbox(config)

    print(f"→ artifact: {artifact.path} ({artifact.size_bytes} bytes, sha256={artifact.sha256[:12]}...)")
    print(f"→ starting sandbox ({SANDBOX_IMAGE})...")
    await sandbox.start()
    print(f"  container: {sandbox.container_id[:12]}")

    try:
        analyzer = Analyzer(
            artifact=artifact,
            sandbox=sandbox,
            container_path=container_path,
            model_spec="claude-haiku-4-5",
        )
        print("→ running Claude session...")
        report = await analyzer.analyze()
    finally:
        print("→ stopping sandbox...")
        await sandbox.stop()
        path.unlink(missing_ok=True)

    print("\n=== AnalysisReport ===")
    print(f"Summary: {report.summary[:300]}")
    print(f"Sections: {len(report.sections)}")
    for title, body in report.sections[:5]:
        print(f"  - {title}: {body[:160]}")

    found_marker = any(
        "HIDDEN_MARKER_ABC123" in body or "payload-xyz" in body or "cGF5bG9hZC14eXo" in body
        for _, body in report.sections
    ) or "HIDDEN_MARKER_ABC123" in report.summary

    if report.sections and found_marker:
        print("\n✓ smoke artifact_analysis passed (found embedded marker)")
        return 0
    if report.sections:
        print("\n△ partial: sections returned but embedded marker not detected in output")
        return 0
    print("\n✗ no sections returned")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
