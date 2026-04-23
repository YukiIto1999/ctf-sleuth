from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InputShape:
    """観測なしで入力文字列を分類した純粋な判定

    Attributes:
        raw: 入力文字列
        is_http_url: HTTP/HTTPS URL 判定フラグ
        is_ip: IP アドレス判定フラグ
        is_domain: ドメイン名判定フラグ
        looks_like_question: 自然文疑問形の判定フラグ
        htb_hint: HTB 関連語の含有フラグ
    """

    raw: str
    is_http_url: bool
    is_ip: bool
    is_domain: bool
    looks_like_question: bool
    htb_hint: bool
