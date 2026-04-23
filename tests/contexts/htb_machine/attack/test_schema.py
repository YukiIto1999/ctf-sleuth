from __future__ import annotations

from contexts.htb_machine.attack import HTB_OUTPUT_SCHEMA


class TestHtbOutputSchema:
    """HTB_OUTPUT_SCHEMA の契約検証"""

    def test_required_fields(self) -> None:
        """必須フィールド"""
        assert set(HTB_OUTPUT_SCHEMA["required"]) == {"summary", "chain"}
