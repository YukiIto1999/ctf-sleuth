from __future__ import annotations

import re

from ..domain import Target, TargetKind

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?$")
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$",
    re.IGNORECASE,
)
_USERNAME_RE = re.compile(r"^[a-z0-9._-]{2,64}$", re.IGNORECASE)


def classify_target(raw: str) -> Target:
    """入力文字列からの TargetKind 推定

    Args:
        raw: 入力文字列

    Returns:
        kind 付き Target
    """
    s = raw.strip()
    if _EMAIL_RE.match(s):
        return Target(raw=s, kind=TargetKind.EMAIL)
    if _URL_RE.match(s):
        return Target(raw=s, kind=TargetKind.URL)
    if _IP_RE.match(s):
        return Target(raw=s, kind=TargetKind.IP)
    if _DOMAIN_RE.match(s):
        return Target(raw=s, kind=TargetKind.DOMAIN)
    if _USERNAME_RE.match(s) and "." not in s:
        return Target(raw=s, kind=TargetKind.USERNAME)
    return Target(raw=s, kind=TargetKind.TEXT)
