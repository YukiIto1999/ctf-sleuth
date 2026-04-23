from __future__ import annotations

import pytest

from contexts.ctf_challenge.policies import slugify


class TestSlugify:
    """slugify の挙動検証"""

    @pytest.mark.parametrize(
        "name, expected",
        [
            ("Hello World", "hello-world"),
            ("a/b\\c?d*e", "abcde"),
            ("multi   spaces", "multi-spaces"),
            ("with_underscores_here", "with-underscores-here"),
            ("...dots...", "dots"),
            ("CTF{flag}", "ctfflag"),
            ("日本語 mixed ascii", "mixed-ascii"),
        ],
    )
    def test_slugify_cases(self, name: str, expected: str) -> None:
        """slugify のテーブル駆動検証

        Args:
            name: 入力名称
            expected: 期待 slug
        """
        assert slugify(name) == expected

    def test_slugify_empty_is_empty(self) -> None:
        """空白のみ入力の空文字化"""
        assert slugify("   ") == ""
