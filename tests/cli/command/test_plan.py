from __future__ import annotations

import pytest

from cli.command.plan import cmd_plan
from shared.task import ExecutionRequest, TaskInput, TaskType


@pytest.mark.asyncio
async def test_cmd_plan_prints_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """plan 結果の標準出力表示

    Args:
        monkeypatch: pytest fixture
        capsys: 標準出力キャプチャ
    """
    import cli.command.plan as mod

    async def fake_plan(task_input, *, classifier, config):
        """偽 plan

        Args:
            task_input: 無視
            classifier: 無視
            config: 無視

        Returns:
            固定 ExecutionRequest
        """
        return ExecutionRequest(
            task_type=TaskType.OSINT_INVESTIGATION,
            input=TaskInput(raw="example.com"),
            params={"target": "example.com"},
            model_spec="claude-opus-4-6",
            reasoning="domain hit",
        )

    monkeypatch.setattr(mod, "plan", fake_plan)
    monkeypatch.setattr(mod, "default_classifier", lambda: object())

    exit_code = await cmd_plan(TaskInput(raw="example.com"), non_interactive=True)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "task_type: osint_investigation" in out
    assert "model: claude-opus-4-6" in out
    assert "reasoning: domain hit" in out
    assert "target: example.com" in out
