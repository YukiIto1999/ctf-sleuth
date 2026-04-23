from __future__ import annotations

import pytest

from shared.task import ExecutionRequest, TaskInput, TaskType


class TestExecutionRequest:
    """ExecutionRequest の不変性検証"""

    def test_params_are_readonly(self) -> None:
        """params の読取専用性の検証"""
        r = ExecutionRequest(
            task_type=TaskType.OSINT_INVESTIGATION,
            input=TaskInput(raw="example.com"),
            params={"target": "example.com"},
            model_spec="claude-opus-4-6",
        )
        with pytest.raises(TypeError):
            r.params["x"] = "y"  # type: ignore[index]
