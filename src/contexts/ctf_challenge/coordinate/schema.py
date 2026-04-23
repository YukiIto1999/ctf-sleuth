from __future__ import annotations

from dataclasses import dataclass

from shared.result import Flag

from ..domain import SolveAttempt


@dataclass(frozen=True, slots=True)
class ChallengeReport:
    """1 challenge の run 結果

    Attributes:
        challenge_name: 対象 challenge 名
        flag: 得られたフラグ
        confirmed: CORRECT 到達判定
        attempts: 提出試行のタプル
        step_count: 実行ステップ数
        reasoning: 推論ログ抜粋
    """

    challenge_name: str
    flag: Flag | None
    confirmed: bool
    attempts: tuple[SolveAttempt, ...]
    step_count: int
    reasoning: str = ""


@dataclass(frozen=True, slots=True)
class CoordinatorReport:
    """coordinator 全体の run 結果

    Attributes:
        reports: ChallengeReport のタプル
    """

    reports: tuple[ChallengeReport, ...]

    @property
    def solved_count(self) -> int:
        """confirmed な ChallengeReport の総数"""
        return sum(1 for r in self.reports if r.confirmed)

    @property
    def attempted_count(self) -> int:
        """試行した ChallengeReport の総数"""
        return len(self.reports)
