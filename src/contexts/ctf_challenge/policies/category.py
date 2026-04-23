from __future__ import annotations

from shared.task import Strategy

_CATEGORY_MAP: dict[str, Strategy] = {
    "pwn": Strategy.PWN,
    "pwnable": Strategy.PWN,
    "binary exploitation": Strategy.PWN,
    "binary": Strategy.PWN,
    "exploit": Strategy.PWN,
    "exploitation": Strategy.PWN,
    "rev": Strategy.REV,
    "reverse": Strategy.REV,
    "reversing": Strategy.REV,
    "reverse engineering": Strategy.REV,
    "re": Strategy.REV,
    "crypto": Strategy.CRYPTO,
    "cryptography": Strategy.CRYPTO,
    "web": Strategy.WEB,
    "web exploitation": Strategy.WEB,
    "web security": Strategy.WEB,
    "forensics": Strategy.FORENSICS,
    "forensic": Strategy.FORENSICS,
    "osint": Strategy.OSINT,
}


def normalize_category(raw: str) -> Strategy | None:
    """CTFd category の Strategy 正規化

    Args:
        raw: CTFd 由来の category 文字列

    Returns:
        対応する Strategy もしくは None
    """
    key = raw.strip().lower()
    if not key:
        return None
    return _CATEGORY_MAP.get(key)
