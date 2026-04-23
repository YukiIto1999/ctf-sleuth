from __future__ import annotations

from shared.task import AlternativeClass, Classification, ParamSpec, TaskType


class TestClassification:
    """Classification の挙動検証"""

    def test_missing_params_detects_absence(self) -> None:
        """欠落パラメータ検出"""
        cls = Classification(
            task_type=TaskType.CTF_CHALLENGE,
            confidence=0.9,
            required_params=(
                ParamSpec("url", True, "CTFd URL"),
                ParamSpec("token", True, "CTFd token"),
                ParamSpec("notes", False, "optional"),
            ),
        )
        missing = cls.missing_params({"url": "https://x"})
        assert [p.name for p in missing] == ["token"]

    def test_is_ambiguous_true_when_close_alternative(self) -> None:
        """次点信頼度が近い場合の ambiguous 判定"""
        cls = Classification(
            task_type=TaskType.CTF_CHALLENGE,
            confidence=0.7,
            required_params=(),
            alternatives=(AlternativeClass(TaskType.OSINT_INVESTIGATION, 0.6),),
        )
        assert cls.is_ambiguous(margin=0.3)

    def test_is_ambiguous_false_when_gap_large(self) -> None:
        """次点信頼度が離れた場合の非 ambiguous 判定"""
        cls = Classification(
            task_type=TaskType.CTF_CHALLENGE,
            confidence=0.9,
            required_params=(),
            alternatives=(AlternativeClass(TaskType.OSINT_INVESTIGATION, 0.4),),
        )
        assert not cls.is_ambiguous(margin=0.3)
