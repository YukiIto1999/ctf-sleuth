from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from shared.sandbox import Sandbox

from ..domain import Challenge, SolveAttempt
from ..services import CtfdGateway
from ..solve import Solver, SolverOutput
from .schema import ChallengeReport, CoordinatorReport

logger = logging.getLogger(__name__)


SandboxFactory = Callable[[Challenge], Awaitable[Sandbox]]

SolverFactory = Callable[[Challenge, Sandbox], Solver]


@dataclass
class Coordinator:
    """challenge を直列処理する Coordinator

    Attributes:
        ctfd: CTFd ゲートウェイ
        sandbox_factory: challenge 毎の sandbox 生成関数
        solver_factory: Solver 組立関数
    """

    ctfd: CtfdGateway
    sandbox_factory: SandboxFactory
    solver_factory: SolverFactory
    _reports: list[ChallengeReport] = field(default_factory=list, init=False)

    async def run(self, *, max_challenges: int | None = None) -> CoordinatorReport:
        """unsolved challenge の順次実行

        Args:
            max_challenges: 処理する challenge の上限

        Returns:
            全体結果の CoordinatorReport
        """
        challenge_set = await self.ctfd.fetch_all()
        pending = challenge_set.unsolved()
        if max_challenges is not None:
            pending = pending[:max_challenges]

        for ch in pending:
            report = await self._run_one(ch)
            self._reports.append(report)
            if report.confirmed:
                logger.info("solved: %s (flag=%s)", ch.name, report.flag.value if report.flag else "?")
            else:
                logger.info("gave up: %s", ch.name)

        return CoordinatorReport(reports=tuple(self._reports))

    async def _run_one(self, challenge: Challenge) -> ChallengeReport:
        """1 challenge 分の sandbox 起動と solve

        Args:
            challenge: 対象 Challenge

        Returns:
            ChallengeReport
        """
        sandbox = await self.sandbox_factory(challenge)
        try:
            await sandbox.start()
            solver = self.solver_factory(challenge, sandbox)
            output = await solver.solve()
            return _to_report(challenge, output)
        finally:
            try:
                await sandbox.stop()
            except Exception as e:  # noqa: BLE001
                logger.warning("sandbox.stop() failed: %s", e)


def _to_report(challenge: Challenge, output: SolverOutput) -> ChallengeReport:
    """Solver 出力の ChallengeReport 化

    Args:
        challenge: 対象 Challenge
        output: Solver 出力

    Returns:
        対応する ChallengeReport
    """
    return ChallengeReport(
        challenge_name=challenge.name,
        flag=output.flag,
        confirmed=output.confirmed,
        attempts=output.attempts,
        step_count=output.step_count,
        reasoning=output.reasoning,
    )


def make_flag_submitter(ctfd: CtfdGateway):
    """CtfdGateway 閉包の FlagSubmitter 生成

    Args:
        ctfd: CTFd ゲートウェイ

    Returns:
        Solver に渡す非同期 callback
    """

    async def submit(challenge_name: str, flag: str) -> SolveAttempt:
        """CtfdGateway 経由の flag 提出

        Args:
            challenge_name: challenge 名
            flag: フラグ文字列

        Returns:
            CTFd 応答の SolveAttempt
        """
        return await ctfd.submit_flag(challenge_name, flag)

    return submit
