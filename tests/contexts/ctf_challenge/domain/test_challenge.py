from __future__ import annotations

import pytest

from contexts.ctf_challenge.domain import Challenge, ChallengeId, Hint
from shared.task import Strategy


class TestChallenge:
    """Challenge の挙動検証"""

    def test_frozen(self) -> None:
        """Challenge が frozen であることの検証"""
        ch = Challenge(
            id=ChallengeId(1),
            name="x",
            category_raw="Pwn",
            strategy=Strategy.PWN,
        )
        with pytest.raises((AttributeError, TypeError)):
            ch.name = "y"  # type: ignore[misc]

    def test_slug_from_name(self) -> None:
        """name からの slug 生成"""
        ch = Challenge(id=ChallengeId(1), name="Hello World!", category_raw="", strategy=None)
        assert ch.slug() == "hello-world"

    def test_slug_fallback_when_name_is_empty_after_strip(self) -> None:
        """空 slug 時の challenge-<id> fallback"""
        ch = Challenge(id=ChallengeId(42), name="***", category_raw="", strategy=None)
        assert ch.slug() == "challenge-42"


class TestHint:
    """Hint の挙動検証"""

    def test_default_cost_zero(self) -> None:
        """Hint.cost デフォルト値"""
        assert Hint(content="tip").cost == 0
