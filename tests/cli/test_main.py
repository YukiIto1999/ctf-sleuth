from __future__ import annotations

import pytest

from cli.main import main
from shared.errors import (
    AmbiguousClassificationError,
    ClassificationUnderconfidentError,
    MissingRequiredParamError,
    NonInteractiveShellError,
)


def test_dispatches_plan_subcommand(monkeypatch: pytest.MonkeyPatch) -> None:
    """plan サブコマンドの委譲

    Args:
        monkeypatch: pytest fixture
    """
    import cli.main as mod

    captured: list[tuple[str, bool]] = []

    async def fake_cmd_plan(task_input, *, non_interactive):
        """偽 cmd_plan

        Args:
            task_input: 入力
            non_interactive: 対話無効化フラグ

        Returns:
            0
        """
        captured.append(("plan", non_interactive))
        return 0

    async def fake_cmd_run(task_input, *, non_interactive):
        """偽 cmd_run (呼ばれないはず)

        Args:
            task_input: 無視
            non_interactive: 無視

        Returns:
            99
        """
        captured.append(("run", non_interactive))
        return 99

    monkeypatch.setattr(mod, "cmd_plan", fake_cmd_plan)
    monkeypatch.setattr(mod, "cmd_run", fake_cmd_run)

    rc = main(["plan", "example.com", "--non-interactive"])
    assert rc == 0
    assert captured == [("plan", True)]


def test_dispatches_run_subcommand(monkeypatch: pytest.MonkeyPatch) -> None:
    """run サブコマンドの委譲

    Args:
        monkeypatch: pytest fixture
    """
    import cli.main as mod

    captured: list[str] = []

    async def fake_cmd_run(task_input, *, non_interactive):
        """偽 cmd_run

        Args:
            task_input: 入力
            non_interactive: 無視

        Returns:
            0
        """
        captured.append("run")
        return 0

    async def fake_cmd_plan(task_input, *, non_interactive):
        """偽 cmd_plan (呼ばれないはず)

        Args:
            task_input: 無視
            non_interactive: 無視

        Returns:
            99
        """
        captured.append("plan")
        return 99

    monkeypatch.setattr(mod, "cmd_plan", fake_cmd_plan)
    monkeypatch.setattr(mod, "cmd_run", fake_cmd_run)

    rc = main(["run", "example.com"])
    assert rc == 0
    assert captured == ["run"]


@pytest.mark.parametrize(
    "exc",
    [
        ClassificationUnderconfidentError("x"),
        MissingRequiredParamError(("url",)),
        AmbiguousClassificationError("ambiguous"),
        NonInteractiveShellError("non-interactive"),
    ],
)
def test_classification_errors_return_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, exc: Exception
) -> None:
    """分類系例外時の終了コード 2

    Args:
        monkeypatch: pytest fixture
        capsys: 標準エラーキャプチャ
        exc: 送出対象の例外
    """
    import cli.main as mod

    async def fake_cmd_plan(task_input, *, non_interactive):
        """例外を送出する偽 cmd_plan

        Args:
            task_input: 無視
            non_interactive: 無視

        Raises:
            Exception: 例外
        """
        raise exc

    monkeypatch.setattr(mod, "cmd_plan", fake_cmd_plan)

    rc = main(["plan", "x"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "error" in err


def test_not_implemented_returns_3(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """NotImplementedError 時の終了コード 3

    Args:
        monkeypatch: pytest fixture
        capsys: 標準エラーキャプチャ
    """
    import cli.main as mod

    async def fake_cmd_plan(task_input, *, non_interactive):
        """NotImplementedError を送出する偽 cmd_plan

        Args:
            task_input: 無視
            non_interactive: 無視

        Raises:
            NotImplementedError: 常に送出
        """
        raise NotImplementedError("wip")

    monkeypatch.setattr(mod, "cmd_plan", fake_cmd_plan)
    rc = main(["plan", "x"])
    assert rc == 3
    assert "not yet implemented" in capsys.readouterr().err
