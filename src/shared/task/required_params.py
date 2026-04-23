from __future__ import annotations

from .param_spec import ParamSpec
from .task_type import TaskType

_CTFD_PARAMS = (
    ParamSpec("url", True, "CTFd base URL"),
    ParamSpec("token", True, "CTFd API token"),
)
_HTB_PARAMS = (
    ParamSpec("machine", True, "HTB machine id (integer)"),
    ParamSpec("ip", True, "machine IP (VPN connected)"),
    ParamSpec("token", True, "HTB API token"),
)
_ARTIFACT_PARAMS: tuple[ParamSpec, ...] = ()
_OSINT_PARAMS: tuple[ParamSpec, ...] = ()

REQUIRED_PARAMS_BY_TYPE: dict[TaskType, tuple[ParamSpec, ...]] = {
    TaskType.CTF_CHALLENGE: _CTFD_PARAMS,
    TaskType.HTB_MACHINE: _HTB_PARAMS,
    TaskType.ARTIFACT_ANALYSIS: _ARTIFACT_PARAMS,
    TaskType.OSINT_INVESTIGATION: _OSINT_PARAMS,
}
