from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from cli.command.run import cmd_run
from foundation.metrics import SessionMetrics
from shared.result import AnalysisReport
from shared.task import ExecutionRequest, TaskInput, TaskType


def _metrics() -> SessionMetrics:
    """テスト用 SessionMetrics の生成

    Returns:
        最小 SessionMetrics
    """
    now = datetime(2026, 4, 22, tzinfo=UTC)
    return SessionMetrics(
        cost_usd=0.0,
        turns=0,
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        started_at=now,
        completed_at=now,
    )


@pytest.mark.asyncio
async def test_cmd_run_orchestrates_plan_execute_persist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """plan と execute と persist の順序呼出

    Args:
        monkeypatch: pytest fixture
        tmp_path: pytest tmp_path fixture
        capsys: 標準出力キャプチャ
    """
    import cli.command.run as mod

    call_order: list[str] = []
    captured_request: list[ExecutionRequest] = []
    persist_called_with: list[tuple[ExecutionRequest, Any]] = []
    log_called_with: list[tuple[str, str, Path]] = []

    async def fake_plan(task_input, *, classifier, config):
        """偽 plan

        Args:
            task_input: 無視
            classifier: 無視
            config: 無視

        Returns:
            固定 ExecutionRequest
        """
        call_order.append("plan")
        return ExecutionRequest(
            task_type=TaskType.ARTIFACT_ANALYSIS,
            input=TaskInput(raw="x"),
            params={},
            model_spec="m",
        )

    async def fake_execute(request, *, runners):
        """偽 execute

        Args:
            request: 実行要求
            runners: 無視

        Returns:
            stub AnalysisReport
        """
        call_order.append("execute")
        captured_request.append(request)
        return AnalysisReport(summary="s", sections=(), evidence=())

    def fake_persist(request, result, *, writeups_dir, metrics):
        """偽 persist

        Args:
            request: 実行要求
            result: 実行結果
            writeups_dir: 書出先
            metrics: メトリクス

        Returns:
            tmp_path / "session-x"
        """
        call_order.append("persist")
        persist_called_with.append((request, result))
        dest = tmp_path / "session-x"
        dest.mkdir()
        return dest

    def fake_append(metrics, *, session_id, task_type, writeups_dir):
        """偽 append_to_project_log

        Args:
            metrics: 無視
            session_id: セッション ID
            task_type: タスク種別
            writeups_dir: 書出先
        """
        call_order.append("append_log")
        log_called_with.append((session_id, task_type, writeups_dir))

    monkeypatch.setattr(mod, "plan", fake_plan)
    monkeypatch.setattr(mod, "execute", fake_execute)
    monkeypatch.setattr(mod, "persist_task_result", fake_persist)
    monkeypatch.setattr(mod, "append_to_project_log", fake_append)
    monkeypatch.setattr(mod, "DEFAULT_WRITEUPS_DIR", tmp_path)
    monkeypatch.setattr(mod, "make_runners", lambda: {})
    monkeypatch.setattr(mod, "default_classifier", lambda: object())

    exit_code = await cmd_run(TaskInput(raw="x"), non_interactive=False)
    assert exit_code == 0
    assert call_order == ["plan", "execute", "persist", "append_log"]
    assert log_called_with[0][0] == "session-x"
    assert log_called_with[0][1] == "artifact_analysis"

    out = capsys.readouterr().out
    assert "result: AnalysisReport" in out
    assert "summary: s" in out
    assert "metrics:" in out
    assert "report saved:" in out
