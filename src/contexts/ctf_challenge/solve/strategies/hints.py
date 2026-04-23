from __future__ import annotations

from dataclasses import dataclass

from shared.task import Strategy


@dataclass(frozen=True, slots=True)
class StrategyHints:
    """戦略別ガイダンスの不変値

    Attributes:
        skill_names: 関連 skill ディレクトリ名のタプル
        tool_focus: 中心ツールの識別子タプル
        prompt_section: system prompt に埋め込む本文
    """

    skill_names: tuple[str, ...] = ()
    tool_focus: tuple[str, ...] = ()
    prompt_section: str = ""


GENERIC_HINTS = StrategyHints(
    skill_names=("hackthebox", "essential-tools"),
    tool_focus=("bash", "curl", "python3", "strings", "xxd", "file"),
    prompt_section=(
        "## General strategy\n\n"
        "- Inspect distfiles and service banners first.\n"
        "- `strings`, `file`, `xxd` are always cheap to run.\n"
        "- If category is unknown, try each family: web endpoints, binary "
        "analysis, crypto primitives, filesystem artifacts."
    ),
)


def get_hints(strategy: Strategy | None) -> StrategyHints:
    """Strategy 別 StrategyHints の解決

    Args:
        strategy: 対象 Strategy もしくは None

    Returns:
        strategy に対応する StrategyHints
    """
    if strategy is None:
        return GENERIC_HINTS
    from . import crypto, forensics, osint, pwn, rev, web

    match strategy:
        case Strategy.PWN:
            return pwn.HINTS
        case Strategy.REV:
            return rev.HINTS
        case Strategy.CRYPTO:
            return crypto.HINTS
        case Strategy.WEB:
            return web.HINTS
        case Strategy.FORENSICS:
            return forensics.HINTS
        case Strategy.OSINT:
            return osint.HINTS
