from __future__ import annotations

import pytest

from contexts.htb_machine.attack import AttackerOutput
from contexts.htb_machine.domain import Difficulty, Machine
from contexts.htb_machine.runner import _machine_from_request, _to_analysis_report
from shared.errors import MissingRequiredParamError
from shared.task import ExecutionRequest, TaskInput, TaskType


def _req(**params: str) -> ExecutionRequest:
    """テスト用 ExecutionRequest の生成

    Args:
        **params: パラメータ

    Returns:
        HTB_MACHINE 固定の ExecutionRequest
    """
    return ExecutionRequest(
        task_type=TaskType.HTB_MACHINE,
        input=TaskInput(raw=""),
        params=params,
        model_spec="claude-opus-4-6",
    )


def _machine() -> Machine:
    """テスト用 Machine の生成

    Returns:
        固定の Machine
    """
    return Machine(id=42, name="Sherlock", ip="10.10.10.5", os="linux", difficulty=Difficulty.EASY)


class TestMachineFromRequest:
    """_machine_from_request の検証"""

    def test_missing_machine_raises(self) -> None:
        """machine 欠落時の MissingRequiredParamError"""
        with pytest.raises(MissingRequiredParamError):
            _machine_from_request(_req(ip="10.10.10.5", token="t"))

    def test_missing_ip_and_token_raises(self) -> None:
        """ip と token 欠落の併記"""
        with pytest.raises(MissingRequiredParamError) as exc:
            _machine_from_request(_req(machine="1"))
        assert "ip" in exc.value.missing
        assert "token" in exc.value.missing

    def test_non_integer_machine_raises(self) -> None:
        """非整数 machine の MissingRequiredParamError"""
        with pytest.raises(MissingRequiredParamError):
            _machine_from_request(_req(machine="abc", ip="1.2.3.4", token="t"))

    def test_defaults_when_optional_missing(self) -> None:
        """任意パラメータ欠落時のデフォルト値"""
        m = _machine_from_request(_req(machine="42", ip="10.10.10.5", token="t"))
        assert m.id == 42
        assert m.ip == "10.10.10.5"
        assert m.name == "htb-42"
        assert m.os == "unknown"
        assert m.difficulty is Difficulty.UNKNOWN

    def test_difficulty_case_insensitive(self) -> None:
        """difficulty の大文字小文字無視"""
        m = _machine_from_request(
            _req(machine="1", ip="x", token="t", difficulty="EASY")
        )
        assert m.difficulty is Difficulty.EASY

    def test_unknown_difficulty_falls_back(self) -> None:
        """未知 difficulty の UNKNOWN fallback"""
        m = _machine_from_request(
            _req(machine="1", ip="x", token="t", difficulty="ultra")
        )
        assert m.difficulty is Difficulty.UNKNOWN


class TestToAnalysisReport:
    """_to_analysis_report の検証"""

    def test_renders_flags_in_summary(self) -> None:
        """summary への flag 反映"""
        machine = _machine()
        output = AttackerOutput(
            user_flag="u-123",
            root_flag=None,
            attempts=(),
            summary="stuck on privesc",
            chain=("step1", "step2"),
        )
        report = _to_analysis_report(machine, output)
        assert "user: u-123" in report.summary
        assert "root: not found" in report.summary
        titles = {title for title, _ in report.sections}
        assert "Attack chain" in titles
        assert "Summary" in titles
