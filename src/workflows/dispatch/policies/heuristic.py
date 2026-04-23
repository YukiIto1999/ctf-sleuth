from __future__ import annotations

from shared.probe import FileKind, InputProbe
from shared.task import (
    REQUIRED_PARAMS_BY_TYPE,
    AlternativeClass,
    Classification,
    TaskType,
)


def classify_heuristic(probe: InputProbe) -> Classification:
    """規則ベースの純粋分類

    Args:
        probe: 入力観測結果

    Returns:
        ヒューリスティックに基づく Classification
    """
    shape = probe.shape

    if probe.is_existing_path:
        kind = probe.file_kind or FileKind.UNKNOWN
        return Classification(
            task_type=TaskType.ARTIFACT_ANALYSIS,
            confidence=0.95,
            required_params=REQUIRED_PARAMS_BY_TYPE[TaskType.ARTIFACT_ANALYSIS],
            reasoning=f"existing local file of kind={kind.value}",
        )

    if shape.htb_hint:
        return Classification(
            task_type=TaskType.HTB_MACHINE,
            confidence=0.9,
            required_params=REQUIRED_PARAMS_BY_TYPE[TaskType.HTB_MACHINE],
            reasoning="IP in HTB range (10.10.x.x / 10.129.x.x)",
        )

    if probe.http and probe.http.ctfd_api_ok:
        return Classification(
            task_type=TaskType.CTF_CHALLENGE,
            confidence=0.9,
            required_params=REQUIRED_PARAMS_BY_TYPE[TaskType.CTF_CHALLENGE],
            reasoning="CTFd API endpoint responded at /api/v1/stats/users",
        )

    if shape.is_http_url or shape.is_domain:
        return Classification(
            task_type=TaskType.OSINT_INVESTIGATION,
            confidence=0.65,
            required_params=REQUIRED_PARAMS_BY_TYPE[TaskType.OSINT_INVESTIGATION],
            alternatives=(AlternativeClass(TaskType.CTF_CHALLENGE, 0.35),),
            reasoning="looks like URL/domain without CTFd signature; OSINT target as best guess",
        )

    if shape.looks_like_question:
        return Classification(
            task_type=TaskType.OSINT_INVESTIGATION,
            confidence=0.6,
            required_params=REQUIRED_PARAMS_BY_TYPE[TaskType.OSINT_INVESTIGATION],
            reasoning="free-form question; treating as OSINT/research task",
        )

    return Classification(
        task_type=TaskType.OSINT_INVESTIGATION,
        confidence=0.4,
        required_params=REQUIRED_PARAMS_BY_TYPE[TaskType.OSINT_INVESTIGATION],
        alternatives=(AlternativeClass(TaskType.ARTIFACT_ANALYSIS, 0.3),),
        reasoning="no strong signals; defaulting to OSINT with low confidence",
    )


class HeuristicClassifier:
    """規則ベース分類器の Classifier 実装"""

    async def classify(self, probe: InputProbe) -> Classification:
        """ヒューリスティック分類

        Args:
            probe: 入力観測結果

        Returns:
            分類結果の Classification
        """
        return classify_heuristic(probe)
