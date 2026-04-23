from __future__ import annotations

from typing import Final

_NAMES: Final[frozenset[str]] = frozenset(
    {
        "ai-threat-testing",
        "android-security",
        "api-security",
        "authentication",
        "blockchain-security",
        "blue-teamer",
        "bug-bounter",
        "client-side",
        "cloud-forensics",
        "cloud-pentester",
        "container-forensics",
        "coordination",
        "cve-exploitation",
        "detecting-kerberoasting-attacks",
        "detection-cloud-anomalies",
        "detection-web",
        "dfir",
        "disk-forensics",
        "endpoint-forensics",
        "essential-tools",
        "firmware-iot-security",
        "github-workflow",
        "hackerone",
        "hackthebox",
        "infrastructure",
        "injection",
        "ioc-hunting",
        "ios-security",
        "kubernetes-security",
        "memory-analysis",
        "network-analyzer",
        "network-hunter",
        "osint",
        "patt-fetcher",
        "performing-cryptographic-audit-of-application",
        "performing-ssl-tls-security-assessment",
        "phishing-investigation",
        "reconnaissance",
        "red-teamer",
        "replay-attack",
        "reverse-engineering",
        "rootkit-analysis",
        "script-generator",
        "server-side",
        "social-engineering",
        "source-code-scanning",
        "subghz-sdr",
        "system",
        "techstack-identification",
        "testing-jwt-token-security",
        "testing-oauth2-implementation-flaws",
        "threat-intel",
        "web-app-logic",
        "web-bounty",
        "web-pentester",
        "wifi-security",
    }
)


class Skill(str):
    """registry 登録済み skill 名"""

    def __new__(cls, value: str) -> Skill:
        """skill 名の検証付き Skill 化

        Args:
            value: 検証対象の skill 名

        Returns:
            Skill 型に昇格した名前

        Raises:
            ValueError: registry 未登録時
        """
        if value not in _NAMES:
            raise ValueError(f"unknown skill: {value!r}")
        return super().__new__(cls, value)


SKILLS: Final[frozenset[Skill]] = frozenset(Skill(n) for n in _NAMES)


def is_skill(name: str) -> bool:
    """skill 名の registry 登録有無

    Args:
        name: 判定対象の skill 名

    Returns:
        登録済みかの真偽
    """
    return name in _NAMES
