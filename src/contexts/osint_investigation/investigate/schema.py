from __future__ import annotations

INVESTIGATION_OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["info", "low", "medium", "high", "critical"],
                    },
                    "recommendation": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["summary", "severity"],
                "additionalProperties": False,
            },
        },
        "overall_confidence": {"type": "string"},
    },
    "required": ["findings"],
    "additionalProperties": False,
}
