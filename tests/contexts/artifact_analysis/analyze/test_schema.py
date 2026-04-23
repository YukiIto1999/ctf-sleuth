from __future__ import annotations

from contexts.artifact_analysis.analyze import ANALYSIS_OUTPUT_SCHEMA


class TestAnalysisOutputSchema:
    """ANALYSIS_OUTPUT_SCHEMA の契約検証"""

    def test_required_fields(self) -> None:
        """必須フィールド"""
        assert ANALYSIS_OUTPUT_SCHEMA["required"] == ["summary", "sections"]
