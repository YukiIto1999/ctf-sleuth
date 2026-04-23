from __future__ import annotations

from enum import StrEnum


class OwnType(StrEnum):
    """HTB の flag 種別"""

    USER = "user"
    ROOT = "root"
