from __future__ import annotations

from contexts.ctf_challenge.domain import Challenge, ChallengeId, ChallengeSet


def _mk(names: list[str], solved: list[str] | None = None) -> ChallengeSet:
    """テスト用 ChallengeSet の生成

    Args:
        names: Challenge 名のリスト
        solved: solved 名のリスト

    Returns:
        組立済 ChallengeSet
    """
    challenges = tuple(
        Challenge(id=ChallengeId(i + 1), name=n, category_raw="", strategy=None)
        for i, n in enumerate(names)
    )
    return ChallengeSet(
        challenges=challenges,
        solved_names=frozenset(solved or []),
    )


class TestChallengeSet:
    """ChallengeSet の挙動検証"""

    def test_unsolved_filters_solved_names(self) -> None:
        """solved_names 除外での unsolved 抽出"""
        cs = _mk(["a", "b", "c"], solved=["b"])
        assert [c.name for c in cs.unsolved()] == ["a", "c"]

    def test_by_name_returns_matching_challenge(self) -> None:
        """名前一致 Challenge の取得"""
        cs = _mk(["a", "b"])
        assert cs.by_name("a") is not None
        assert cs.by_name("missing") is None
