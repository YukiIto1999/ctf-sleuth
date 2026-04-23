from __future__ import annotations

import re
from collections.abc import Iterable

from ..domain import Challenge
from .strategies import get_hints

_LOCALHOST_RE = re.compile(r"\b(?:localhost|127\.0\.0\.1)\b")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_HOST_PORT_RE = re.compile(r"^\S+\s+\d+$")


def build_system_prompt(
    *,
    challenge: Challenge,
    distfile_names: Iterable[str] = (),
    container_arch: str = "unknown",
) -> str:
    """Challenge と文脈から system prompt の構築

    Args:
        challenge: 対象の Challenge
        distfile_names: 同梱 distfile 名の列挙
        container_arch: container の arch 文字列

    Returns:
        決定的に生成された system prompt 文字列
    """
    hints = get_hints(challenge.strategy)
    conn_info = _rewrite_localhost(challenge.connection_info.strip())
    distfiles = tuple(distfile_names)

    parts: list[str] = []
    parts += _role_section()
    parts += _challenge_header(challenge, container_arch)
    parts += _description_section(challenge)
    parts += _service_section(conn_info)
    parts += _distfiles_section(distfiles)
    parts += _hints_section(challenge)
    parts += _strategy_section(hints)
    parts += _skills_section(hints)
    parts += _rules_section()

    return "\n".join(parts).rstrip() + "\n"


def _role_section() -> list[str]:
    """役割セクションの生成

    Returns:
        Role セクションの行リスト
    """
    return [
        "# Role",
        "You are an expert CTF solver. Execute tools; do not narrate.",
        "Keep trying approaches until you submit a correct flag.",
        "",
    ]


def _challenge_header(challenge: Challenge, container_arch: str) -> list[str]:
    """challenge ヘッダセクションの生成

    Args:
        challenge: 対象 Challenge
        container_arch: container の arch 文字列

    Returns:
        Challenge ヘッダの行リスト
    """
    strategy_label = (
        f" (strategy: {challenge.strategy.value})" if challenge.strategy else ""
    )
    lines = [
        "# Challenge",
        f"- **Name**     : {challenge.name}",
        f"- **Category** : {challenge.category_raw or 'Unknown'}{strategy_label}",
        f"- **Points**   : {challenge.value or '?'}",
        f"- **Arch**     : {container_arch}",
    ]
    if challenge.tags:
        lines.append(f"- **Tags**     : {', '.join(challenge.tags)}")
    lines.append("")
    return lines


def _description_section(challenge: Challenge) -> list[str]:
    """説明文セクションの生成

    Args:
        challenge: 対象 Challenge

    Returns:
        Description セクションの行リスト
    """
    return [
        "## Description",
        challenge.description or "_No description provided._",
        "",
    ]


def _service_section(conn_info: str) -> list[str]:
    """サービス接続セクションの生成

    Args:
        conn_info: 置換後の接続情報文字列

    Returns:
        Service Connection セクションの行リスト
    """
    if not conn_info:
        return []
    hint = _service_hint(conn_info)
    return [
        "## Service Connection",
        "```",
        conn_info,
        "```",
        hint,
        "",
    ]


def _service_hint(conn: str) -> str:
    """接続情報への補助テキスト生成

    Args:
        conn: 接続情報文字列

    Returns:
        接続方式に応じた補助テキスト
    """
    if _URL_RE.match(conn):
        return "Web service. Use bash `curl`/`python3 requests`, or `WebFetch`."
    if conn.startswith("nc ") or _HOST_PORT_RE.match(conn):
        return (
            "TCP service. bash calls are stateless — use a heredoc to send multi-line:\n"
            "```\n"
            f"{conn} <<'EOF'\n"
            "command1\n"
            "command2\n"
            "EOF\n"
            "```\n"
            "Or write a pwntools `remote(host, port)` script for stateful interaction."
        )
    return "Connect using the details above."


def _distfiles_section(distfiles: tuple[str, ...]) -> list[str]:
    """distfile セクションの生成

    Args:
        distfiles: container 内パス列挙用の distfile 名

    Returns:
        Attached Files セクションの行リスト
    """
    if not distfiles:
        return []
    lines = ["## Attached Files"]
    for name in distfiles:
        lines.append(f"- `/challenge/distfiles/{name}`")
    lines.append("")
    return lines


def _hints_section(challenge: Challenge) -> list[str]:
    """ヒントセクションの生成

    Args:
        challenge: 対象 Challenge

    Returns:
        Hints セクションの行リスト
    """
    visible = [h for h in challenge.hints if h.content]
    if not visible:
        return []
    lines = ["## Hints"]
    for h in visible:
        lines.append(f"- {h.content}")
    lines.append("")
    return lines


def _strategy_section(hints) -> list[str]:
    """strategy prompt セクションの生成

    Args:
        hints: 戦略別 StrategyHints

    Returns:
        strategy 固有セクションの行リスト
    """
    if not hints.prompt_section.strip():
        return []
    return [hints.prompt_section.rstrip(), ""]


def _skills_section(hints) -> list[str]:
    """関連 skill セクションの生成

    Args:
        hints: 戦略別 StrategyHints

    Returns:
        Related Skills セクションの行リスト
    """
    if not hints.skill_names:
        return []
    lines = [
        "## Related Skills",
        "Skill descriptions (`.claude/skills/<name>/SKILL.md`) that match the task",
        "are auto-surfaced. Candidates for this category:",
    ]
    for s in hints.skill_names:
        lines.append(f"- `{s}`")
    lines.append("")
    return lines


def _rules_section() -> list[str]:
    """行動規則セクションの生成

    Returns:
        Rules セクションの行リスト
    """
    return [
        "# Rules",
        "- Submit real flags only. Ignore placeholder flags like `CTF{flag}`, `flag{placeholder}`.",
        "- Verify every candidate with `submit_flag <flag>` before reporting.",
        "- Once CORRECT: output `FLAG: <value>` on its own line.",
        "- Do not guess without evidence. Cover maximum surface area.",
    ]


def _rewrite_localhost(conn: str) -> str:
    """localhost の host.docker.internal への書換

    Args:
        conn: 元の接続情報文字列

    Returns:
        書換後の接続情報文字列
    """
    return _LOCALHOST_RE.sub("host.docker.internal", conn)
