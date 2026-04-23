from __future__ import annotations

from contexts.htb_machine.attack.prompts import build_system_prompt
from contexts.htb_machine.domain import Difficulty, Machine


class TestBuildSystemPrompt:
    """htb_machine prompt 生成の検証"""

    def test_target_details_rendered(self) -> None:
        """target 情報の出現"""
        m = Machine(id=1, name="Sherlock", ip="10.10.10.5", os="linux", difficulty=Difficulty.EASY)
        out = build_system_prompt(m)
        assert "Sherlock" in out
        assert "10.10.10.5" in out
        assert "easy" in out
        assert "Linux privesc" in out

    def test_windows_hint_for_windows_os(self) -> None:
        """Windows OS 時の hint"""
        m = Machine(id=1, name="m", ip="10.10.10.5", os="Windows", difficulty=Difficulty.MEDIUM)
        out = build_system_prompt(m)
        assert "Windows privesc" in out
