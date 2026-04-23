from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from contexts.ctf_challenge.coordinate import Coordinator, make_flag_submitter
from contexts.ctf_challenge.domain import (
    Challenge,
    ChallengeId,
    ChallengeSet,
    FlagVerdict,
    SolveAttempt,
)
from contexts.ctf_challenge.solve import SolverOutput
from layers.sandbox import StubSandbox
from shared.result import Flag


def _ch(id_: int, name: str) -> Challenge:
    """テスト用 Challenge の生成

    Args:
        id_: challenge ID
        name: challenge 名

    Returns:
        固定値の Challenge
    """
    return Challenge(
        id=ChallengeId(id_),
        name=name,
        category_raw="Pwn",
        strategy=None,
        description="",
        value=100,
    )


@dataclass
class _FakeCtfd:
    """CtfdClient 互換の偽クライアント

    Attributes:
        challenges: 保持 Challenge 群
        solved: solved 名集合
        submissions: 提出履歴
        submit_verdict: 固定判定値
    """

    challenges: tuple[Challenge, ...] = ()
    solved: frozenset[str] = frozenset()
    submissions: list[tuple[str, str]] = field(default_factory=list)
    submit_verdict: FlagVerdict = FlagVerdict.CORRECT

    async def fetch_all(self) -> ChallengeSet:
        """擬似 fetch_all

        Returns:
            保持中の ChallengeSet
        """
        return ChallengeSet(challenges=self.challenges, solved_names=self.solved)

    async def submit_flag(self, challenge_name: str, flag: str) -> SolveAttempt:
        """擬似 submit_flag

        Args:
            challenge_name: challenge 名
            flag: 提出 flag

        Returns:
            固定判定の SolveAttempt
        """
        self.submissions.append((challenge_name, flag))
        return SolveAttempt(
            challenge_name=challenge_name,
            flag=flag,
            verdict=self.submit_verdict,
            message="stub",
            submitted_at=datetime.now(UTC),
        )


class _FakeSolver:
    """固定 SolverOutput を返す偽 Solver"""

    def __init__(self, output: SolverOutput) -> None:
        """偽 Solver の初期化

        Args:
            output: 返却する SolverOutput
        """
        self._output = output

    async def solve(self) -> SolverOutput:
        """固定値を返す擬似 solve

        Returns:
            保持中の SolverOutput
        """
        return self._output


def _sandbox_factory():
    """sandbox 生成とリスト回収の factory 組立

    Returns:
        factory 関数と生成 sandbox リストの組
    """
    made: list[StubSandbox] = []

    async def factory(challenge: Challenge) -> StubSandbox:
        """StubSandbox 生成と回収

        Args:
            challenge: 対象 Challenge

        Returns:
            新規 StubSandbox
        """
        sb = StubSandbox()
        made.append(sb)
        return sb

    return factory, made


@pytest.mark.asyncio
async def test_coordinator_processes_unsolved_challenges() -> None:
    """solved 除外と unsolved 順次処理"""
    ctfd = _FakeCtfd(
        challenges=(_ch(1, "a"), _ch(2, "b"), _ch(3, "c")),
        solved=frozenset({"b"}),
    )

    def solver_factory(challenge, sandbox):
        """CORRECT 固定を返す偽 Solver factory

        Args:
            challenge: 対象 Challenge
            sandbox: Sandbox

        Returns:
            _FakeSolver
        """
        attempt = SolveAttempt(
            challenge_name=challenge.name,
            flag="FLAG{x}",
            verdict=FlagVerdict.CORRECT,
            message="",
            submitted_at=datetime.now(UTC),
        )
        return _FakeSolver(
            SolverOutput(
                flag=Flag("FLAG{x}"),
                attempts=(attempt,),
                confirmed=True,
                reasoning="stubbed",
                step_count=1,
            )
        )

    factory, made = _sandbox_factory()
    coord = Coordinator(ctfd=ctfd, sandbox_factory=factory, solver_factory=solver_factory)

    report = await coord.run()
    assert report.attempted_count == 2
    assert report.solved_count == 2
    names = {r.challenge_name for r in report.reports}
    assert names == {"a", "c"}
    assert len(made) == 2


@pytest.mark.asyncio
async def test_max_challenges_limits_processing() -> None:
    """max_challenges の上限反映"""
    ctfd = _FakeCtfd(
        challenges=tuple(_ch(i, f"ch{i}") for i in range(1, 6)),
    )

    def solver_factory(challenge, sandbox):
        """未解決固定の偽 Solver factory

        Args:
            challenge: 対象 Challenge
            sandbox: Sandbox

        Returns:
            _FakeSolver
        """
        return _FakeSolver(SolverOutput(flag=None, confirmed=False))

    factory, made = _sandbox_factory()
    coord = Coordinator(ctfd=ctfd, sandbox_factory=factory, solver_factory=solver_factory)

    report = await coord.run(max_challenges=2)
    assert report.attempted_count == 2
    assert len(made) == 2


@pytest.mark.asyncio
async def test_report_records_unsolved_when_flag_missing() -> None:
    """flag 取得失敗時の未解決記録"""
    ctfd = _FakeCtfd(challenges=(_ch(1, "a"),))

    def solver_factory(challenge, sandbox):
        """未解決固定の偽 Solver factory

        Args:
            challenge: 対象 Challenge
            sandbox: Sandbox

        Returns:
            _FakeSolver
        """
        return _FakeSolver(SolverOutput(flag=None, confirmed=False, reasoning="stuck"))

    factory, _ = _sandbox_factory()
    coord = Coordinator(ctfd=ctfd, sandbox_factory=factory, solver_factory=solver_factory)
    report = await coord.run()
    assert report.attempted_count == 1
    assert report.solved_count == 0
    r = report.reports[0]
    assert r.flag is None
    assert r.reasoning == "stuck"


@pytest.mark.asyncio
async def test_sandbox_is_stopped_even_when_solver_raises() -> None:
    """Solver 例外下での sandbox 停止保証"""
    ctfd = _FakeCtfd(challenges=(_ch(1, "a"),))
    stopped: list[str] = []

    class _TrackedSandbox(StubSandbox):
        """stop 呼出を記録する StubSandbox"""

        async def stop(self) -> None:
            """stop 呼出の記録"""
            stopped.append("stop")
            await super().stop()

    async def factory(challenge: Challenge) -> Any:
        """Tracked sandbox factory

        Args:
            challenge: 対象 Challenge

        Returns:
            _TrackedSandbox
        """
        return _TrackedSandbox()

    class _FailingSolver:
        """solve で例外を送出する Solver"""

        async def solve(self):
            """常に RuntimeError を送出

            Raises:
                RuntimeError: 常に送出
            """
            raise RuntimeError("boom")

    def solver_factory(challenge, sandbox):
        """失敗 Solver factory

        Args:
            challenge: 対象 Challenge
            sandbox: Sandbox

        Returns:
            _FailingSolver
        """
        return _FailingSolver()

    coord = Coordinator(ctfd=ctfd, sandbox_factory=factory, solver_factory=solver_factory)
    with pytest.raises(RuntimeError):
        await coord.run()
    assert stopped == ["stop"]


@pytest.mark.asyncio
async def test_make_flag_submitter_delegates_to_ctfd() -> None:
    """make_flag_submitter の CtfdClient 委譲"""
    ctfd = _FakeCtfd(submit_verdict=FlagVerdict.INCORRECT)
    submit = make_flag_submitter(ctfd)
    attempt = await submit("ch1", "FLAG{x}")
    assert attempt.verdict is FlagVerdict.INCORRECT
    assert ctfd.submissions == [("ch1", "FLAG{x}")]
