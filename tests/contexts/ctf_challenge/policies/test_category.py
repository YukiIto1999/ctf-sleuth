from __future__ import annotations

import pytest

from contexts.ctf_challenge.policies import normalize_category
from shared.task import Strategy


class TestNormalizeCategory:
    """normalize_category の挙動検証"""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Pwn", Strategy.PWN),
            ("pwnable", Strategy.PWN),
            ("Binary Exploitation", Strategy.PWN),
            ("Reverse Engineering", Strategy.REV),
            ("rev", Strategy.REV),
            ("RE", Strategy.REV),
            ("Crypto", Strategy.CRYPTO),
            ("Cryptography", Strategy.CRYPTO),
            ("Web", Strategy.WEB),
            ("Web Exploitation", Strategy.WEB),
            ("Forensics", Strategy.FORENSICS),
            ("OSINT", Strategy.OSINT),
            ("osint", Strategy.OSINT),
            ("  Pwn  ", Strategy.PWN),
        ],
    )
    def test_known_categories_map(self, raw: str, expected: Strategy) -> None:
        """既知カテゴリの Strategy 正規化

        Args:
            raw: 入力 category 文字列
            expected: 期待される Strategy
        """
        assert normalize_category(raw) is expected

    @pytest.mark.parametrize("raw", ["", "unknown", "Quiz", "misc"])
    def test_unknown_categories_return_none(self, raw: str) -> None:
        """未知カテゴリの None 返却

        Args:
            raw: 入力 category 文字列
        """
        assert normalize_category(raw) is None
