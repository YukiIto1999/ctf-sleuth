from __future__ import annotations

import re

from shared.probe import InputShape

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?$")
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$", re.IGNORECASE)
_QUESTION_RE = re.compile(r"[?？]\s*$|^(what|how|why|when|who|explain|describe|tell me)\b", re.IGNORECASE)
_HTB_IP_PREFIXES = ("10.10.", "10.129.")


def analyze_shape(raw: str) -> InputShape:
    """入力文字列の純粋構造判定

    Args:
        raw: 入力文字列

    Returns:
        正規表現に基づく InputShape
    """
    s = raw.strip()
    is_ip = bool(_IP_RE.match(s))
    is_http = bool(_URL_RE.match(s))
    is_domain = bool(_DOMAIN_RE.match(s)) and not is_ip and not is_http
    looks_like_question = bool(_QUESTION_RE.search(s))
    htb_hint = is_ip and s.startswith(_HTB_IP_PREFIXES)
    return InputShape(
        raw=s,
        is_http_url=is_http,
        is_ip=is_ip,
        is_domain=is_domain,
        looks_like_question=looks_like_question,
        htb_hint=htb_hint,
    )
