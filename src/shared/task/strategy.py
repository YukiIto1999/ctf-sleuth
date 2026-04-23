from __future__ import annotations

from enum import StrEnum


class Strategy(StrEnum):
    """ctf_challenge 配下の下位戦略"""

    PWN = "pwn"
    REV = "rev"
    CRYPTO = "crypto"
    WEB = "web"
    FORENSICS = "forensics"
    OSINT = "osint"
