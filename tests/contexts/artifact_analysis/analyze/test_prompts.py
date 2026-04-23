from __future__ import annotations

from pathlib import Path

from contexts.artifact_analysis.analyze.prompts import build_system_prompt
from contexts.artifact_analysis.domain import Artifact
from shared.probe import FileKind


def _art(kind: FileKind = FileKind.ELF) -> Artifact:
    """テスト用 Artifact の生成

    Args:
        kind: FileKind

    Returns:
        固定値の Artifact
    """
    return Artifact(
        path=Path("/tmp/x"),
        kind=kind,
        size_bytes=1234,
        sha256="abc",
    )


class TestBuildSystemPrompt:
    """build_system_prompt の検証"""

    def test_role_and_artifact_section_present(self) -> None:
        """Role と Artifact セクションの出現"""
        out = build_system_prompt(_art(), container_path="/artifact/x")
        assert "# Role" in out
        assert "`/artifact/x`" in out
        assert "SHA-256" in out
        assert "abc" in out

    def test_kind_specific_tools_rendered(self) -> None:
        """FileKind 別ツールの出現"""
        out = build_system_prompt(_art(FileKind.PCAP), container_path="/p")
        assert "tshark" in out
        assert "wireshark" in out

    def test_kind_specific_skills_rendered(self) -> None:
        """FileKind 別 skill の出現"""
        out = build_system_prompt(_art(FileKind.ELF), container_path="/p")
        assert "`reverse-engineering`" in out

    def test_deterministic(self) -> None:
        """同一入力での同一出力"""
        art = _art()
        a = build_system_prompt(art, container_path="/p", container_arch="x86_64")
        b = build_system_prompt(art, container_path="/p", container_arch="x86_64")
        assert a == b
