from __future__ import annotations

from contexts.osint_investigation.domain import Target, TargetKind
from contexts.osint_investigation.investigate.prompts import build_system_prompt


class TestBuildSystemPrompt:
    """OSINT system prompt 生成の検証"""

    def test_target_rendered(self) -> None:
        """target 情報の出現"""
        out = build_system_prompt(Target(raw="example.com", kind=TargetKind.DOMAIN))
        assert "example.com" in out
        assert "domain" in out

    def test_kind_specific_skills(self) -> None:
        """kind 別 skill の出現"""
        out = build_system_prompt(Target(raw="u", kind=TargetKind.USERNAME))
        assert "`github-workflow`" in out

    def test_rules_section_forbids_intrusive(self) -> None:
        """Rules の公開情報限定規定"""
        out = build_system_prompt(Target(raw="x", kind=TargetKind.TEXT))
        assert "Public information only" in out
        assert "Do not fabricate" in out
