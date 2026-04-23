from __future__ import annotations

from shared.task import TaskType


class TestTaskType:
    """TaskType 列挙の値安定性検証"""

    def test_values(self) -> None:
        """TaskType の値集合の検証"""
        assert {t.value for t in TaskType} == {
            "ctf_challenge",
            "htb_machine",
            "artifact_analysis",
            "osint_investigation",
        }
