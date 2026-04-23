from __future__ import annotations

from contexts.osint_investigation.investigate import INVESTIGATION_OUTPUT_SCHEMA
from shared.result import Severity


class TestInvestigationOutputSchema:
    """INVESTIGATION_OUTPUT_SCHEMA の契約検証"""

    def test_has_findings_array(self) -> None:
        """findings フィールドの必須性"""
        assert "findings" in INVESTIGATION_OUTPUT_SCHEMA["required"]

    def test_severity_enum_matches_domain(self) -> None:
        """severity enum と Severity の一致"""
        enum = INVESTIGATION_OUTPUT_SCHEMA["properties"]["findings"]["items"]["properties"]["severity"]["enum"]
        assert set(enum) == {s.value for s in Severity}
