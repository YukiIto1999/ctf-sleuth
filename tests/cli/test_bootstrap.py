from __future__ import annotations

from pathlib import Path

from cli.bootstrap import (
    _artifact_sandbox_factory,
    _ctf_sandbox_factory,
    _htb_sandbox_factory,
    make_config,
    make_runners,
)
from contexts.ctf_challenge.domain import Challenge, ChallengeId
from layers.artifact_inspector import inspect_artifact
from shared.task import Strategy, TaskType


def test_make_runners_returns_all_task_types() -> None:
    """make_runners の全 TaskType 網羅"""
    runners = make_runners()
    assert set(runners.keys()) == set(TaskType)


def test_make_config_inverts_non_interactive() -> None:
    """non_interactive フラグの反転"""
    assert make_config(non_interactive=True).interactive is False
    assert make_config(non_interactive=False).interactive is True


def test_artifact_sandbox_factory_mounts_read_only(tmp_path: Path) -> None:
    """artifact 用 sandbox での read-only mount"""
    p = tmp_path / "sample.bin"
    p.write_bytes(b"ELF")
    art = inspect_artifact(p)
    sandbox = _artifact_sandbox_factory(art, "/artifact/sample.bin", image="test-image")
    assert len(sandbox.config.mounts) == 1
    m = sandbox.config.mounts[0]
    assert m.source == art.path
    assert m.target == "/artifact/sample.bin"
    assert m.read_only is True


def test_htb_sandbox_factory_has_no_mounts() -> None:
    """HTB 用 sandbox の mount 空"""
    sandbox = _htb_sandbox_factory(image="test-image")
    assert sandbox.config.mounts == ()
    assert sandbox.config.image == "test-image"


def test_ctf_sandbox_factory_mounts_distfiles_and_metadata(tmp_path: Path) -> None:
    """ctf_challenge 用 sandbox での distfiles と metadata mount"""
    challenge = Challenge(
        id=ChallengeId(1),
        name="pwn-x",
        category_raw="Pwn",
        strategy=Strategy.PWN,
        description="",
        value=100,
        connection_info=None,
        tags=(),
        hints=(),
        distfile_urls=(),
    )
    ch_dir = tmp_path / challenge.slug()
    (ch_dir / "distfiles").mkdir(parents=True)
    (ch_dir / "distfiles" / "bin").write_bytes(b"\x7fELF")
    (ch_dir / "metadata.yml").write_text("name: pwn-x\n")

    sandbox = _ctf_sandbox_factory(challenge, tmp_path, image="test-image")
    targets = {m.target for m in sandbox.config.mounts}
    assert targets == {"/challenge/distfiles", "/challenge/metadata.yml"}
    assert all(m.read_only for m in sandbox.config.mounts)
