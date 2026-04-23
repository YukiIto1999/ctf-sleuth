from __future__ import annotations

from contexts.ctf_challenge.coordinate import ChallengeReport, CoordinatorReport


def _report(*, confirmed: bool) -> ChallengeReport:
    """テスト用 ChallengeReport の生成

    Args:
        confirmed: 判定フラグ

    Returns:
        最小 ChallengeReport
    """
    return ChallengeReport(
        challenge_name="x",
        flag=None,
        confirmed=confirmed,
        attempts=(),
        step_count=0,
    )


class TestCoordinatorReport:
    """CoordinatorReport の property 検証"""

    def test_empty_counts_are_zero(self) -> None:
        """空 reports の solved と attempted"""
        r = CoordinatorReport(reports=())
        assert r.solved_count == 0
        assert r.attempted_count == 0

    def test_solved_count_filters_confirmed(self) -> None:
        """confirmed な report のみ計上"""
        r = CoordinatorReport(
            reports=(
                _report(confirmed=True),
                _report(confirmed=False),
                _report(confirmed=True),
            )
        )
        assert r.solved_count == 2
        assert r.attempted_count == 3
