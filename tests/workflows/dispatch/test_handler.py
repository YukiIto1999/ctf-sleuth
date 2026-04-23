from __future__ import annotations

import pytest

from shared.errors import (
    AppError,
    ClassificationUnderconfidentError,
    MissingRequiredParamError,
    NonInteractiveShellError,
)
from shared.probe import HttpProbe
from shared.result import AnalysisReport, FindingsCollected
from shared.task import ExecutionRequest, TaskInput, TaskType
from workflows.dispatch import DispatchConfig, execute, plan


class _StubHttp:
    """テスト用の HTTP 観測スタブ"""

    def __init__(self, ctfd_ok: bool = True) -> None:
        """スタブの初期化

        Args:
            ctfd_ok: CTFd API 応答の有無
        """
        self._ctfd_ok = ctfd_ok

    async def observe(self, url: str) -> HttpProbe:
        """URL 観測の擬似実行

        Args:
            url: 観測対象 URL

        Returns:
            固定値の HttpProbe
        """
        return HttpProbe(
            status=200,
            server_header="nginx",
            ctfd_api_ok=self._ctfd_ok,
            final_url=url,
        )


def _req(task_type: TaskType, params: dict[str, str] | None = None) -> ExecutionRequest:
    """テスト用 ExecutionRequest の生成

    Args:
        task_type: タスク種別
        params: パラメータ dict

    Returns:
        固定 input を持つ ExecutionRequest
    """
    return ExecutionRequest(
        task_type=task_type,
        input=TaskInput(raw="x"),
        params=params or {},
        model_spec="claude-opus-4-6",
        reasoning="test",
    )


class TestPlan:
    """plan の検証"""

    @pytest.mark.asyncio
    async def test_explicit_type_short_circuits(self) -> None:
        """明示 type 指定による probe スキップ"""
        t = TaskInput(raw="whatever", flags={"type": "osint_investigation"})
        req = await plan(t)
        assert req.task_type is TaskType.OSINT_INVESTIGATION
        assert req.reasoning == "explicit --type"

    @pytest.mark.asyncio
    async def test_ctfd_url_with_token_succeeds(self) -> None:
        """CTFd URL と token 指定での ctf_challenge 成立"""
        t = TaskInput(
            raw="https://ctf.example.com",
            flags={"url": "https://ctf.example.com", "token": "t_abc"},
        )
        req = await plan(t, http_observer=_StubHttp(ctfd_ok=True))
        assert req.task_type is TaskType.CTF_CHALLENGE
        assert req.params["url"] == "https://ctf.example.com"
        assert req.params["token"] == "t_abc"

    @pytest.mark.asyncio
    async def test_ctfd_without_token_raises_missing(self) -> None:
        """token 欠落時の MissingRequiredParamError"""
        t = TaskInput(raw="https://ctf.example.com", flags={"url": "https://ctf.example.com"})
        with pytest.raises(MissingRequiredParamError) as exc:
            await plan(t, http_observer=_StubHttp(ctfd_ok=True))
        assert "token" in exc.value.missing

    @pytest.mark.asyncio
    async def test_low_confidence_input_raises(self) -> None:
        """低信頼度入力での ClassificationUnderconfidentError"""
        t = TaskInput(raw="xyzzy")
        with pytest.raises(ClassificationUnderconfidentError):
            await plan(t, config=DispatchConfig(min_confidence=0.5, interactive=False))

    @pytest.mark.asyncio
    async def test_ambiguous_non_interactive_raises(self) -> None:
        """非対話下での曖昧分類例外"""
        t = TaskInput(raw="https://example.com")
        with pytest.raises(NonInteractiveShellError):
            await plan(
                t,
                http_observer=_StubHttp(ctfd_ok=False),
                config=DispatchConfig(interactive=False),
            )


class TestExecute:
    """execute の検証"""

    @pytest.mark.asyncio
    async def test_ctf_challenge_routes_to_runner(self) -> None:
        """ctf_challenge の runner 委譲"""
        captured: list[ExecutionRequest] = []

        async def fake_runner(request: ExecutionRequest) -> AnalysisReport:
            """呼出を記録する偽 runner

            Args:
                request: 実行要求

            Returns:
                stub AnalysisReport
            """
            captured.append(request)
            return AnalysisReport(summary="stub", sections=(), evidence=())

        runners = {TaskType.CTF_CHALLENGE: fake_runner}
        request = _req(TaskType.CTF_CHALLENGE, {"url": "https://x", "token": "t"})
        result = await execute(request, runners=runners)

        assert captured == [request]
        assert isinstance(result, AnalysisReport)
        assert result.summary == "stub"

    @pytest.mark.asyncio
    async def test_htb_machine_routes_to_runner(self) -> None:
        """htb_machine の runner 委譲"""
        captured: list[ExecutionRequest] = []

        async def fake_runner(request: ExecutionRequest) -> AnalysisReport:
            """呼出を記録する偽 runner

            Args:
                request: 実行要求

            Returns:
                stub AnalysisReport
            """
            captured.append(request)
            return AnalysisReport(summary="stub-htb", sections=(), evidence=())

        runners = {TaskType.HTB_MACHINE: fake_runner}
        request = _req(
            TaskType.HTB_MACHINE,
            {"machine": "42", "ip": "10.10.10.5", "token": "t"},
        )
        result = await execute(request, runners=runners)
        assert captured == [request]
        assert isinstance(result, AnalysisReport)
        assert result.summary == "stub-htb"

    @pytest.mark.asyncio
    async def test_artifact_analysis_routes_to_runner(self, tmp_path) -> None:
        """artifact_analysis の runner 委譲

        Args:
            tmp_path: pytest tmp_path fixture
        """
        captured: list[ExecutionRequest] = []

        async def fake_runner(request: ExecutionRequest) -> AnalysisReport:
            """呼出を記録する偽 runner

            Args:
                request: 実行要求

            Returns:
                stub AnalysisReport
            """
            captured.append(request)
            return AnalysisReport(summary="stub", sections=(), evidence=())

        runners = {TaskType.ARTIFACT_ANALYSIS: fake_runner}
        request = _req(TaskType.ARTIFACT_ANALYSIS, {"path": str(tmp_path / "x")})
        result = await execute(request, runners=runners)
        assert captured == [request]
        assert isinstance(result, AnalysisReport)

    @pytest.mark.asyncio
    async def test_osint_investigation_routes_to_runner(self) -> None:
        """osint_investigation の runner 委譲"""
        captured: list[ExecutionRequest] = []

        async def fake_runner(request: ExecutionRequest) -> FindingsCollected:
            """呼出を記録する偽 runner

            Args:
                request: 実行要求

            Returns:
                空の FindingsCollected
            """
            captured.append(request)
            return FindingsCollected(findings=(), evidence=())

        runners = {TaskType.OSINT_INVESTIGATION: fake_runner}
        request = _req(TaskType.OSINT_INVESTIGATION)
        result = await execute(request, runners=runners)
        assert captured == [request]
        assert isinstance(result, FindingsCollected)

    @pytest.mark.asyncio
    async def test_unknown_task_type_raises(self) -> None:
        """runners に無い task_type での AppError"""
        request = _req(TaskType.CTF_CHALLENGE, {"url": "x", "token": "t"})
        with pytest.raises(AppError):
            await execute(request, runners={})
