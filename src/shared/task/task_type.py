from __future__ import annotations

from enum import StrEnum


class TaskType(StrEnum):
    """4 bounded context に対応する task 種別"""

    CTF_CHALLENGE = "ctf_challenge"
    HTB_MACHINE = "htb_machine"
    ARTIFACT_ANALYSIS = "artifact_analysis"
    OSINT_INVESTIGATION = "osint_investigation"
