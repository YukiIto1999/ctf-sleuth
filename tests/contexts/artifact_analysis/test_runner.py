from __future__ import annotations

from pathlib import Path

import pytest

from contexts.artifact_analysis.runner import _artifact_path_from_request
from shared.errors import MissingRequiredParamError
from shared.task import ExecutionRequest, TaskInput, TaskType


def _req(raw: str = "", params: dict[str, str] | None = None) -> ExecutionRequest:
    """テスト用 ExecutionRequest の生成

    Args:
        raw: input.raw 値
        params: パラメータ dict

    Returns:
        ARTIFACT_ANALYSIS 固定の ExecutionRequest
    """
    return ExecutionRequest(
        task_type=TaskType.ARTIFACT_ANALYSIS,
        input=TaskInput(raw=raw),
        params=params or {},
        model_spec="claude-opus-4-6",
    )


class TestArtifactPathFromRequest:
    """_artifact_path_from_request の検証"""

    def test_missing_path_raises(self) -> None:
        """path 欠落時の MissingRequiredParamError"""
        with pytest.raises(MissingRequiredParamError):
            _artifact_path_from_request(_req(raw=""))

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """不在ファイル時の FileNotFoundError

        Args:
            tmp_path: pytest tmp_path fixture
        """
        with pytest.raises(FileNotFoundError):
            _artifact_path_from_request(_req(raw=str(tmp_path / "nope")))

    def test_directory_rejected(self, tmp_path: Path) -> None:
        """ディレクトリ指定時の ValueError

        Args:
            tmp_path: pytest tmp_path fixture
        """
        with pytest.raises(ValueError):
            _artifact_path_from_request(_req(raw=str(tmp_path)))

    def test_uses_params_path_preferred_over_raw(self, tmp_path: Path) -> None:
        """params.path の raw 優先

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "x"
        p.write_bytes(b"x")
        q = tmp_path / "y"
        q.write_bytes(b"y")
        resolved = _artifact_path_from_request(
            _req(raw=str(p), params={"path": str(q)})
        )
        assert resolved == q

    def test_falls_back_to_raw_when_params_empty(self, tmp_path: Path) -> None:
        """params 空時の raw fallback

        Args:
            tmp_path: pytest tmp_path fixture
        """
        p = tmp_path / "x"
        p.write_bytes(b"x")
        resolved = _artifact_path_from_request(_req(raw=str(p)))
        assert resolved == p
