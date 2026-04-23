from __future__ import annotations

import re

_SLUG_REPLACE_WITH_DASH = re.compile(r"[\s_]+")
_SLUG_INVALID = re.compile(r"[^a-z0-9-]")
_SLUG_DASHES = re.compile(r"-+")


def slugify(name: str) -> str:
    """URL とファイルシステムに安全な slug 生成

    Args:
        name: 元となる名称文字列

    Returns:
        小文字化と記号除去を経た slug 文字列
    """
    lowered = name.lower().strip()
    hyphenated = _SLUG_REPLACE_WITH_DASH.sub("-", lowered)
    cleaned = _SLUG_INVALID.sub("", hyphenated)
    collapsed = _SLUG_DASHES.sub("-", cleaned)
    return collapsed.strip("-")
