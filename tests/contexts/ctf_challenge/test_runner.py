from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contexts.ctf_challenge.coordinate import ChallengeReport, CoordinatorReport
from contexts.ctf_challenge.domain import (
    FlagVerdict,
    SolveAttempt,
)
from contexts.ctf_challenge.runner import _extract_url_token, _to_analysis_report
from shared.errors import MissingRequiredParamError
from shared.result import Flag
from shared.task import ExecutionRequest, TaskInput, TaskType


def _request(params: dict[str, str]) -> ExecutionRequest:
    """テスト用 ExecutionRequest の生成

    Args:
        params: パラメータ dict

    Returns:
        CTF_CHALLENGE 固定の ExecutionRequest
    """
    return ExecutionRequest(
        task_type=TaskType.CTF_CHALLENGE,
        input=TaskInput(raw="x"),
        params=params,
        model_spec="claude-opus-4-6",
    )


class TestExtractUrlToken:
    """_extract_url_token の検証"""

    def test_missing_url_raises(self) -> None:
        """url 欠落時の MissingRequiredParamError"""
        with pytest.raises(MissingRequiredParamError) as exc:
            _extract_url_token(_request({"token": "t"}))
        assert "url" in exc.value.missing

    def test_missing_token_raises(self) -> None:
        """token 欠落時の MissingRequiredParamError"""
        with pytest.raises(MissingRequiredParamError) as exc:
            _extract_url_token(_request({"url": "https://x"}))
        assert "token" in exc.value.missing

    def test_both_present(self) -> None:
        """url と token 揃った場合の組"""
        url, token = _extract_url_token(_request({"url": "https://x", "token": "t"}))
        assert url == "https://x"
        assert token == "t"


class TestToAnalysisReport:
    """_to_analysis_report の検証"""

    def _report(self, *reports: ChallengeReport) -> CoordinatorReport:
        """テスト用 CoordinatorReport の生成

        Args:
            *reports: 含める ChallengeReport

        Returns:
            CoordinatorReport
        """
        return CoordinatorReport(reports=reports)

    def test_summary_counts_solved_over_attempted(self) -> None:
        """summary の solved 数と attempted 数"""
        r1 = ChallengeReport(
            challenge_name="a",
            flag=Flag("FLAG{1}"),
            confirmed=True,
            attempts=(),
            step_count=3,
        )
        r2 = ChallengeReport(
            challenge_name="b",
            flag=None,
            confirmed=False,
            attempts=(),
            step_count=10,
        )
        analysis = _to_analysis_report(self._report(r1, r2))
        assert analysis.summary == "Solved 1 of 2 challenges"

    def test_sections_render_flag_and_status(self) -> None:
        """sections の flag と status 描画"""
        r = ChallengeReport(
            challenge_name="pwn-baby",
            flag=Flag("FLAG{ok}"),
            confirmed=True,
            attempts=(),
            step_count=5,
            reasoning="buffer overflow",
        )
        analysis = _to_analysis_report(self._report(r))
        assert analysis.sections == (
            ("pwn-baby", "Flag: FLAG{ok} (confirmed)\n\nReasoning: buffer overflow"),
        )

    def test_sections_for_unsolved_say_not_found(self) -> None:
        """未解決時の not found 表示"""
        r = ChallengeReport(
            challenge_name="x",
            flag=None,
            confirmed=False,
            attempts=(),
            step_count=0,
        )
        analysis = _to_analysis_report(self._report(r))
        assert analysis.sections[0][1] == "Flag: not found (gave up)"

    def test_evidence_flattens_all_attempts(self) -> None:
        """evidence の全 attempts 平坦化"""
        a1 = SolveAttempt(
            challenge_name="a",
            flag="F1",
            verdict=FlagVerdict.INCORRECT,
            message="try again",
            submitted_at=datetime(2026, 4, 21, tzinfo=UTC),
        )
        a2 = SolveAttempt(
            challenge_name="a",
            flag="F2",
            verdict=FlagVerdict.CORRECT,
            message="nice",
            submitted_at=datetime(2026, 4, 21, 0, 1, tzinfo=UTC),
        )
        r = ChallengeReport(
            challenge_name="a",
            flag=Flag("F2"),
            confirmed=True,
            attempts=(a1, a2),
            step_count=2,
        )
        analysis = _to_analysis_report(self._report(r))
        assert len(analysis.evidence) == 2
        assert analysis.evidence[0].source == "ctfd:submit:a"
        assert "F1" in analysis.evidence[0].content
        assert "F2" in analysis.evidence[1].content
        assert analysis.evidence[1].note == "nice"
