from __future__ import annotations

import pytest

from contexts.osint_investigation.domain import TargetKind
from contexts.osint_investigation.policies import classify_target


class TestClassifyTarget:
    """classify_target の検証"""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("https://example.com/", TargetKind.URL),
            ("http://a.b/path", TargetKind.URL),
            ("example.com", TargetKind.DOMAIN),
            ("sub.example.co.jp", TargetKind.DOMAIN),
            ("192.168.1.1", TargetKind.IP),
            ("10.10.10.5", TargetKind.IP),
            ("someone@example.com", TargetKind.EMAIL),
            ("john_doe", TargetKind.USERNAME),
            ("user.name-123", TargetKind.TEXT),
            ("What did they do last summer?", TargetKind.TEXT),
            ("アクターX の活動記録", TargetKind.TEXT),
        ],
    )
    def test_classification(self, raw: str, expected: TargetKind) -> None:
        """テーブル駆動での TargetKind 判定

        Args:
            raw: 入力文字列
            expected: 期待 TargetKind
        """
        assert classify_target(raw).kind is expected

    def test_whitespace_stripped(self) -> None:
        """前後空白の除去"""
        assert classify_target("  example.com  ").raw == "example.com"
