from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from shared.sandbox import MountSpec

CONTAINER_LABEL = "ctf-sleuth"

_DEFAULT_EXTRA_HOSTS: Mapping[str, str] = MappingProxyType(
    {"host.docker.internal": "host-gateway"}
)


@dataclass(frozen=True, slots=True)
class SandboxConfig:
    """sandbox container の起動設定

    Attributes:
        image: 使用 Docker image
        mounts: マウント仕様のタプル
        memory_limit_bytes: メモリ上限
        cpu_nanocpus: CPU 上限
        working_dir: container 内作業ディレクトリ
        extra_hosts: /etc/hosts 追加エントリ
        cap_add: 追加ケーパビリティ
        security_opt: security options
        label: 識別ラベル名
        command: 起動コマンド
    """

    image: str
    mounts: tuple[MountSpec, ...] = ()
    memory_limit_bytes: int = 16 * 1024**3
    cpu_nanocpus: int = 2_000_000_000
    working_dir: str = "/challenge"
    extra_hosts: Mapping[str, str] = field(default_factory=lambda: _DEFAULT_EXTRA_HOSTS)
    cap_add: tuple[str, ...] = ("SYS_ADMIN", "SYS_PTRACE")
    security_opt: tuple[str, ...] = ("seccomp=unconfined",)
    label: str = CONTAINER_LABEL
    command: tuple[str, ...] = ("sleep", "infinity")
