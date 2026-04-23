from __future__ import annotations

import pytest

from contexts.ctf_challenge.solve.strategies import (
    GENERIC_HINTS,
    StrategyHints,
    get_hints,
)
from shared.task import Strategy


class TestStrategyHintsValue:
    """StrategyHints 値オブジェクトの検証"""

    def test_is_frozen(self) -> None:
        """StrategyHints が frozen であることの検証"""
        h = StrategyHints(skill_names=("a",), tool_focus=("b",), prompt_section="c")
        with pytest.raises((AttributeError, TypeError)):
            h.prompt_section = "x"  # type: ignore[misc]

    def test_defaults_are_empty(self) -> None:
        """デフォルト空値の検証"""
        h = StrategyHints()
        assert h.skill_names == ()
        assert h.tool_focus == ()
        assert h.prompt_section == ""


class TestGetHints:
    """get_hints の戦略別解決検証"""

    @pytest.mark.parametrize(
        "strategy",
        list(Strategy),
    )
    def test_every_strategy_has_non_empty_hints(self, strategy: Strategy) -> None:
        """全 Strategy での prompt_section の非空性

        Args:
            strategy: 検査対象 Strategy
        """
        h = get_hints(strategy)
        assert h.prompt_section.strip(), f"{strategy} has no prompt_section"

    @pytest.mark.parametrize(
        "strategy",
        list(Strategy),
    )
    def test_every_strategy_suggests_at_least_one_skill(self, strategy: Strategy) -> None:
        """全 Strategy での skill_names の非空性

        Args:
            strategy: 検査対象 Strategy
        """
        h = get_hints(strategy)
        assert h.skill_names, f"{strategy} has no skill_names"

    def test_none_returns_generic(self) -> None:
        """None 指定時の GENERIC_HINTS 返却"""
        assert get_hints(None) is GENERIC_HINTS

    def test_generic_hints_are_non_empty(self) -> None:
        """GENERIC_HINTS の非空性"""
        assert GENERIC_HINTS.prompt_section.strip()
        assert GENERIC_HINTS.skill_names


class TestStrategyHintsPerCategory:
    """戦略別 hint 内容の検証"""

    def test_pwn_includes_exploit_expert(self) -> None:
        """pwn での exploit-expert と pwntools の含有"""
        h = get_hints(Strategy.PWN)
        assert "cve-exploitation" in h.skill_names
        assert "pwntools" in h.tool_focus

    def test_rev_includes_ghidra(self) -> None:
        """rev での reverse-engineering 含有 (ghidra は references/ghidra.md)"""
        h = get_hints(Strategy.REV)
        assert "reverse-engineering" in h.skill_names
        assert "ghidra" in h.tool_focus

    def test_crypto_includes_rsa_tool(self) -> None:
        """crypto での RsaCtfTool 含有"""
        h = get_hints(Strategy.CRYPTO)
        assert "RsaCtfTool" in h.tool_focus

    def test_web_includes_injection_skill(self) -> None:
        """web での injection と sqlmap 含有"""
        h = get_hints(Strategy.WEB)
        assert "injection" in h.skill_names
        assert "sqlmap" in h.tool_focus

    def test_forensics_includes_volatility(self) -> None:
        """forensics での volatility 含有"""
        h = get_hints(Strategy.FORENSICS)
        assert "memory-analysis" in h.skill_names
        assert "volatility3" in h.tool_focus

    def test_osint_includes_osint_skill(self) -> None:
        """osint での osint skill 含有"""
        h = get_hints(Strategy.OSINT)
        assert "osint" in h.skill_names
