from __future__ import annotations

from ..domain import Target, TargetKind

_KIND_SKILLS: dict[TargetKind, tuple[str, ...]] = {
    TargetKind.URL: (
        "osint",
        "reconnaissance",
        "web-pentester",
        "techstack-identification",
        "phishing-investigation",
        "threat-intel",
        "ioc-hunting",
        "essential-tools",
    ),
    TargetKind.DOMAIN: (
        "osint",
        "reconnaissance",
        "techstack-identification",
        "phishing-investigation",
        "threat-intel",
        "ioc-hunting",
        "essential-tools",
    ),
    TargetKind.IP: (
        "osint",
        "reconnaissance",
        "threat-intel",
        "ioc-hunting",
        "essential-tools",
    ),
    TargetKind.EMAIL: (
        "osint",
        "phishing-investigation",
        "threat-intel",
        "ioc-hunting",
        "social-engineering",
    ),
    TargetKind.USERNAME: (
        "osint",
        "github-workflow",
        "social-engineering",
        "techstack-identification",
    ),
    TargetKind.TEXT: (
        "osint",
        "threat-intel",
    ),
}

_KIND_HINTS: dict[TargetKind, str] = {
    TargetKind.URL: (
        "Inspect the URL: HTTP headers, TLS cert, robots.txt, sitemap.xml, "
        "Wayback snapshots, 3rd-party references."
    ),
    TargetKind.DOMAIN: (
        "WHOIS + DNS (NS, MX, TXT, CAA), certificate transparency logs "
        "(crt.sh), subdomain enumeration via public sources, historical A "
        "records if available."
    ),
    TargetKind.IP: (
        "rDNS, ASN / BGP info, Shodan-style public data, Wayback, geolocation "
        "claims cross-checked."
    ),
    TargetKind.EMAIL: (
        "Domain side: MX / SPF / DMARC. Header analysis if a mail sample is "
        "available. Disclosure databases (check availability, not credentials)."
    ),
    TargetKind.USERNAME: (
        "Cross-reference across public platforms (profiles, commits, posts). "
        "Writing style / timezone / interests; pivot to email / real name only "
        "if clearly public."
    ),
    TargetKind.TEXT: (
        "Treat as an investigative question: identify entities / claims, locate "
        "primary sources, cross-check multiple independent references."
    ),
}


def build_system_prompt(target: Target) -> str:
    """Target に対する system prompt の決定的生成

    Args:
        target: 対象 Target

    Returns:
        組立済の system prompt 文字列
    """
    skills = _KIND_SKILLS.get(target.kind, ())
    kind_hint = _KIND_HINTS.get(target.kind, "Investigate using public sources.")

    lines: list[str] = [
        "# Role",
        "You are an OSINT analyst. Investigate the target using only public",
        "information. Do not attempt authentication bypass, scanning, or",
        "intrusive probing. Respect platform ToS.",
        "",
        "# Target",
        f"- **Kind** : {target.kind.value}",
        f"- **Raw**  : {target.raw!r}",
        "",
        "# Approach",
        kind_hint,
        "",
    ]

    if skills:
        lines += [
            "# Relevant skills",
            "Skill descriptions under `.claude/skills/` auto-surface by category match.",
            "Candidates for this target kind:",
            *[f"- `{s}`" for s in skills],
            "",
        ]

    lines += [
        "# Tooling (READ CAREFULLY)",
        "This session runs via Claude Agent SDK (NOT Claude Code). You have ",
        "EXACTLY TWO tools available, both with pre-loaded schemas:",
        "  - `WebFetch` — call directly with `url` and `prompt` parameters",
        "  - `WebSearch` — call directly with `query` parameter",
        "",
        "These tools are **NOT deferred**. Do NOT call `ToolSearch`, `Skill`, ",
        "`Agent`, `Bash`, or any other tool — they are all blocked and NONE ",
        "are required for this task. Begin the investigation immediately by ",
        "calling `WebSearch` or `WebFetch` with appropriate arguments; do not ",
        "state that tools are unavailable without first trying a direct call.",
        "",
        "# Output",
        "Return JSON matching the schema: `{findings: [{summary, severity, "
        "recommendation?, evidence?: [...]}]}`. ",
        "- `severity` must be one of: info, low, medium, high, critical.",
        "- `evidence` values are short source citations (URLs or excerpts).",
        "- 3-8 findings typical; each MUST cite at least one evidence source.",
        "",
        "# Rules",
        "- Public information only. No authenticated / private / unauthorized access.",
        "- Do not fabricate. If unverified, set severity `info` and note the uncertainty.",
        "- Respect privacy; omit personal data beyond what is necessary for scope.",
        "- If the target is a person, do not attempt direct contact.",
    ]

    return "\n".join(lines).rstrip() + "\n"
