from __future__ import annotations

import pytest

from layers.sandbox import DockerSandbox, SandboxConfig, SandboxNotStartedError


class TestDockerSandboxUnstarted:
    """未 start 状態での DockerSandbox 挙動検証"""

    def test_container_id_requires_start(self) -> None:
        """未 start container_id 参照の SandboxNotStartedError"""
        sb = DockerSandbox(SandboxConfig(image="x"))
        with pytest.raises(SandboxNotStartedError):
            _ = sb.container_id

    @pytest.mark.asyncio
    async def test_exec_before_start_raises(self) -> None:
        """未 start exec の SandboxNotStartedError"""
        sb = DockerSandbox(SandboxConfig(image="x"))
        with pytest.raises(SandboxNotStartedError):
            await sb.exec("ls")

    @pytest.mark.asyncio
    async def test_stop_without_start_is_noop(self) -> None:
        """未 start stop の no-op"""
        sb = DockerSandbox(SandboxConfig(image="x"))
        await sb.stop()

    def test_config_preserved(self) -> None:
        """受取 SandboxConfig の保持"""
        cfg = SandboxConfig(image="custom:latest")
        sb = DockerSandbox(cfg)
        assert sb.config is cfg
        assert sb.config.image == "custom:latest"
