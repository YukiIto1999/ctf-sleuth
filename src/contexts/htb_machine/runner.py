from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from shared.errors import MissingRequiredParamError
from shared.result import AnalysisReport, Evidence
from shared.sandbox import Sandbox
from shared.task import ExecutionRequest

from .attack import Attacker, AttackerOutput
from .domain import Difficulty, HtbAttempt, Machine, OwnType
from .services import HtbGateway

logger = logging.getLogger(__name__)

HtbFactory = Callable[[str], AbstractAsyncContextManager[HtbGateway]]
MachineSandboxFactory = Callable[[], Sandbox]


async def run_htb_machine(
    request: ExecutionRequest,
    *,
    htb_factory: HtbFactory,
    sandbox_factory: MachineSandboxFactory,
) -> AnalysisReport:
    """htb_machine の実行エントリ

    Args:
        request: 実行要求
        htb_factory: token から HtbGateway を生成するファクトリ
        sandbox_factory: Sandbox を生成するファクトリ

    Returns:
        Attacker 結果を AnalysisReport 化した値
    """
    machine = _machine_from_request(request)
    token = str(request.params.get("token") or "").strip()

    sandbox = sandbox_factory()

    async with htb_factory(token) as htb:
        flag_submitter = _make_submitter(htb, machine)
        try:
            await sandbox.start()
            attacker = Attacker(
                machine=machine,
                sandbox=sandbox,
                flag_submitter=flag_submitter,
                model_spec=request.model_spec,
            )
            output = await attacker.attack()
        finally:
            try:
                await sandbox.stop()
            except Exception as e:  # noqa: BLE001
                logger.warning("sandbox.stop() failed: %s", e)

    return _to_analysis_report(machine, output)


def _machine_from_request(request: ExecutionRequest) -> Machine:
    """ExecutionRequest から Machine への復元

    Args:
        request: 実行要求

    Returns:
        復元された Machine

    Raises:
        MissingRequiredParamError: machine / ip / token のいずれか欠落
    """
    missing: list[str] = []
    machine_id_raw = request.params.get("machine")
    if not machine_id_raw:
        missing.append("machine")
    ip = str(request.params.get("ip") or request.input.raw).strip()
    if not ip:
        missing.append("ip")
    token = request.params.get("token")
    if not token:
        missing.append("token")
    if missing:
        raise MissingRequiredParamError(tuple(missing))

    try:
        machine_id = int(str(machine_id_raw))
    except ValueError as e:
        raise MissingRequiredParamError(("machine",)) from e

    name = str(request.params.get("machine_name") or f"htb-{machine_id}")
    os_name = str(request.params.get("os") or "unknown")
    try:
        difficulty = Difficulty(str(request.params.get("difficulty") or "unknown").lower())
    except ValueError:
        difficulty = Difficulty.UNKNOWN

    return Machine(id=machine_id, name=name, ip=ip, os=os_name, difficulty=difficulty)


def _make_submitter(htb: HtbGateway, machine: Machine):
    """HtbGateway と Machine を閉包した flag submitter の生成

    Args:
        htb: HTB ゲートウェイ
        machine: 対象 Machine

    Returns:
        Attacker に渡す非同期 callback
    """

    async def submit(own_type: OwnType, flag: str) -> HtbAttempt:
        """HtbGateway 経由の flag 提出

        Args:
            own_type: own 種別
            flag: 提出フラグ文字列

        Returns:
            HTB 応答の HtbAttempt
        """
        return await htb.submit_flag(
            machine_id=machine.id,
            machine_name=machine.name,
            own_type=own_type,
            flag=flag,
        )

    return submit


def _to_analysis_report(machine: Machine, output: AttackerOutput) -> AnalysisReport:
    """Attacker 出力の AnalysisReport 変換

    Args:
        machine: 対象 Machine
        output: Attacker 出力

    Returns:
        summary と sections と evidence を持つ AnalysisReport
    """
    status_user = "user: " + (output.user_flag or "not found")
    status_root = "root: " + (output.root_flag or "not found")
    summary = f"{machine.name} @ {machine.ip} ({machine.os}) — {status_user}, {status_root}"

    sections: list[tuple[str, str]] = [
        ("Summary", output.summary),
    ]
    if output.chain:
        chain_body = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(output.chain))
        sections.append(("Attack chain", chain_body))

    evidence = tuple(
        Evidence(
            source=f"htb:{machine.name}:{a.own_type.value}",
            captured_at=a.submitted_at,
            content=f"flag={a.flag} accepted={a.accepted}",
            note=a.message,
        )
        for a in output.attempts
    )

    return AnalysisReport(
        summary=summary,
        sections=tuple(sections),
        evidence=evidence,
    )
