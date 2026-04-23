from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path

from shared.errors import MissingRequiredParamError
from shared.result import AnalysisReport, Evidence
from shared.sandbox import Sandbox
from shared.task import ExecutionRequest

from .archive import list_distfiles, persist_challenges
from .coordinate import Coordinator, CoordinatorReport, make_flag_submitter
from .domain import Challenge
from .services import CtfdGateway
from .solve import Solver

logger = logging.getLogger(__name__)

DEFAULT_CHALLENGES_DIR = Path("challenges")

CtfdFactory = Callable[[str, str], AbstractAsyncContextManager[CtfdGateway]]
ChallengeSandboxFactory = Callable[[Challenge, Path], Sandbox]


async def run_ctf_challenge(
    request: ExecutionRequest,
    *,
    ctfd_factory: CtfdFactory,
    sandbox_factory: ChallengeSandboxFactory,
    challenges_dir: Path = DEFAULT_CHALLENGES_DIR,
    max_challenges: int | None = None,
) -> AnalysisReport:
    """ctf_challenge の実行エントリ

    Args:
        request: 実行要求
        ctfd_factory: url と token から CtfdGateway を生成するファクトリ
        sandbox_factory: Challenge と challenges_dir から Sandbox を生成するファクトリ
        challenges_dir: challenge 永続化先ディレクトリ
        max_challenges: 処理 challenge の上限

    Returns:
        Coordinator 結果を AnalysisReport 化した値

    Raises:
        MissingRequiredParamError: url または token が未指定
    """
    url, token = _extract_url_token(request)

    async with ctfd_factory(url, token) as ctfd:
        challenge_set = await ctfd.fetch_all()
        logger.info("fetched %d challenges", len(challenge_set.challenges))

        await persist_challenges(ctfd, challenge_set, challenges_dir)

        flag_submitter = make_flag_submitter(ctfd)

        async def per_challenge_sandbox(challenge: Challenge) -> Sandbox:
            """challenge 毎の Sandbox 生成

            Args:
                challenge: 対象 Challenge

            Returns:
                ファクトリが返す Sandbox
            """
            return sandbox_factory(challenge, challenges_dir)

        def solver_factory(challenge: Challenge, sandbox: Sandbox) -> Solver:
            """challenge と sandbox からの Solver 組立

            Args:
                challenge: 対象 Challenge
                sandbox: 起動済 Sandbox

            Returns:
                初期化済 Solver
            """
            return Solver(
                challenge=challenge,
                sandbox=sandbox,
                flag_submitter=flag_submitter,
                model_spec=request.model_spec,
                distfile_names=list_distfiles(challenges_dir / challenge.slug()),
            )

        coordinator = Coordinator(
            ctfd=ctfd,
            sandbox_factory=per_challenge_sandbox,
            solver_factory=solver_factory,
        )
        report = await coordinator.run(max_challenges=max_challenges)

    return _to_analysis_report(report)


def _extract_url_token(request: ExecutionRequest) -> tuple[str, str]:
    """ExecutionRequest からの url と token の抽出

    Args:
        request: 実行要求

    Returns:
        url と token の組

    Raises:
        MissingRequiredParamError: url または token が未指定
    """
    url = request.params.get("url")
    token = request.params.get("token")
    missing = tuple(
        name for name, value in (("url", url), ("token", token)) if not value
    )
    if missing:
        raise MissingRequiredParamError(missing)
    return str(url), str(token)


def _to_analysis_report(report: CoordinatorReport) -> AnalysisReport:
    """CoordinatorReport の AnalysisReport 変換

    Args:
        report: Coordinator の全体結果

    Returns:
        summary と sections と evidence を持つ AnalysisReport
    """
    summary = f"Solved {report.solved_count} of {report.attempted_count} challenges"
    sections = tuple(
        (
            r.challenge_name,
            _section_body(r),
        )
        for r in report.reports
    )
    evidence = tuple(
        Evidence(
            source=f"ctfd:submit:{a.challenge_name}",
            captured_at=a.submitted_at,
            content=f"flag={a.flag} verdict={a.verdict.value}",
            note=a.message,
        )
        for r in report.reports
        for a in r.attempts
    )
    return AnalysisReport(summary=summary, sections=sections, evidence=evidence)


def _section_body(report) -> str:
    """ChallengeReport から section 本文への整形

    Args:
        report: ChallengeReport

    Returns:
        flag と reasoning を含む本文文字列
    """
    status = "confirmed" if report.confirmed else "gave up"
    flag = report.flag.value if report.flag else "not found"
    body = f"Flag: {flag} ({status})"
    if report.reasoning:
        body += f"\n\nReasoning: {report.reasoning}"
    return body
