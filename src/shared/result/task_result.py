from __future__ import annotations

from .analysis_report import AnalysisReport
from .findings_collected import FindingsCollected
from .flag_submitted import FlagSubmitted

TaskResult = FlagSubmitted | FindingsCollected | AnalysisReport
