from __future__ import annotations

from ..domain import Difficulty, Machine

_SKILLS = (
    # methodology
    "red-teamer",
    "hackthebox",
    "reconnaissance",
    "techstack-identification",
    "infrastructure",
    "system",
    "essential-tools",
    "script-generator",
    # web (HTB boxes very often expose a web entry)
    "web-pentester",
    "api-security",
    "authentication",
    "client-side",
    "server-side",
    "web-app-logic",
    "injection",
    "testing-jwt-token-security",
    "testing-oauth2-implementation-flaws",
    # binary / exploit / source
    "cve-exploitation",
    "reverse-engineering",
    "cve-exploitation",
    "source-code-scanning",
    # AD / Windows lateral
    "detecting-kerberoasting-attacks",
    # privesc / forensics-on-target
    "disk-forensics",
    "memory-analysis",
    "endpoint-forensics",
    # cloud / k8s (cloud-flavored HTB boxes / Pro Labs)
    "cloud-pentester",
    "kubernetes-security",
    "detection-cloud-anomalies",
    # cloud detection / lateral (informs both attacker and defender perspective)
    "detection-cloud-anomalies",
    # wireless / IoT / RF (rare but appears in some boxes / labs)
    "wifi-security",
    "subghz-sdr",
    "firmware-iot-security",
    "social-engineering",
    # orchestration / bug-bounty cross-pollination
    "coordination",
    "bug-bounter",
    "web-bounty",
    "hackerone",
)


_OS_HINTS: dict[str, str] = {
    "linux": (
        "Linux privesc: sudo -l, SUID bins (`find / -perm -u=s 2>/dev/null`), "
        "cron jobs, kernel exploits, capabilities, misconfigured PATH."
    ),
    "windows": (
        "Windows privesc: AV status, stored creds (cmdkey, runas), service "
        "misconfigs (`accesschk` / `sc qc`), SeImpersonate (Juicy/RoguePotato), "
        "unquoted service paths, AlwaysInstallElevated."
    ),
}


_DIFFICULTY_HINTS: dict[Difficulty, str] = {
    Difficulty.VERY_EASY: "Expect a single clear path; check default creds and obvious CVEs.",
    Difficulty.EASY: "Single chain (1-2 steps). CVE public PoC often applies.",
    Difficulty.MEDIUM: "2-3 step chain; may require tweaking public PoCs or light source review.",
    Difficulty.HARD: "Multi-step chain with custom exploitation. Expect bespoke services.",
    Difficulty.INSANE: "Deep chain with custom crypto/niche protocols. Prepare to read source.",
    Difficulty.UNKNOWN: "Difficulty unknown — treat as medium and adapt.",
}


def build_system_prompt(machine: Machine) -> str:
    """Machine に対する system prompt の決定的生成

    Args:
        machine: 対象 Machine

    Returns:
        組立済の system prompt 文字列
    """
    os_hint = _OS_HINTS.get(machine.os.lower(), "Generic target — identify OS early, then adapt.")
    diff_hint = _DIFFICULTY_HINTS.get(machine.difficulty, _DIFFICULTY_HINTS[Difficulty.UNKNOWN])

    lines: list[str] = [
        "# Role",
        "You are a penetration tester attacking an authorized HackTheBox machine.",
        "Proceed through the standard chain: recon → enumeration → initial access → ",
        "privilege escalation → capture user and root flags.",
        "",
        "# Target",
        f"- **Name**       : {machine.name}",
        f"- **IP**         : {machine.ip}",
        f"- **OS**         : {machine.os}",
        f"- **Difficulty** : {machine.difficulty.value}",
        "",
        "# OS-specific guidance",
        os_hint,
        "",
        "# Difficulty guidance",
        diff_hint,
        "",
        "# Skills",
        "Skill descriptions in `.claude/skills/` auto-surface. Likely useful here:",
        *[f"- `{s}`" for s in _SKILLS],
        "",
        "# Workflow",
        "1. Recon: `nmap -sV -sC -p-` via bash in sandbox.",
        "2. Enumerate exposed services; gather versions and default paths.",
        "3. Find initial access (web exploit / service CVE / default creds).",
        "4. Read `user.txt` under the unprivileged user's home.",
        "5. Privilege escalate to root / SYSTEM.",
        "6. Read `root.txt` under the administrator's home.",
        "",
        "# Flag submission",
        "- Call `submit_flag user <FLAG>` once you have `user.txt` contents.",
        "- Call `submit_flag root <FLAG>` once you have `root.txt` contents.",
        "- The framework verifies each via the HTB API and returns the result.",
        "",
        "# Output",
        "When both flags are obtained (or you're stuck), return JSON:",
        "`{user_flag, root_flag, summary, chain: [...]}` where `chain` is the",
        "list of discrete steps executed, in order.",
        "",
        "# Rules",
        "- Stay inside the sandbox; all commands run via Bash.",
        "- Never submit placeholder flags — verify via the framework.",
        "- If network is unreachable, confirm VPN is up before assuming the target is down.",
    ]

    return "\n".join(lines).rstrip() + "\n"
