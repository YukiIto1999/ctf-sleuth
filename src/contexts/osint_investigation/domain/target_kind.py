from __future__ import annotations

from enum import StrEnum


class TargetKind(StrEnum):
    """OSINT 調査対象の種別"""

    URL = "url"
    DOMAIN = "domain"
    IP = "ip"
    EMAIL = "email"
    USERNAME = "username"
    TEXT = "text"
