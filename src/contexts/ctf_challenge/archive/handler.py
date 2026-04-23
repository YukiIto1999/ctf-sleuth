from __future__ import annotations

import logging
from pathlib import Path

import yaml

from ..domain import Challenge, ChallengeSet
from ..policies import filename_from_url
from ..services import CtfdGateway

logger = logging.getLogger(__name__)


async def persist_challenges(
    ctfd: CtfdGateway,
    challenge_set: ChallengeSet,
    dest: Path,
) -> tuple[Path, ...]:
    """ChallengeSet の filesystem 永続化

    Args:
        ctfd: CTFd ゲートウェイ
        challenge_set: 書出対象の ChallengeSet
        dest: 書出先ルート

    Returns:
        作成もしくは更新された challenge ディレクトリのタプル
    """
    dest.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for ch in challenge_set.challenges:
        path = await persist_one(ctfd, ch, dest)
        out.append(path)
    return tuple(out)


async def persist_one(ctfd: CtfdGateway, challenge: Challenge, dest: Path) -> Path:
    """1 challenge の冪等な永続化

    Args:
        ctfd: CTFd ゲートウェイ
        challenge: 対象 Challenge
        dest: 書出先ルート

    Returns:
        challenge ディレクトリのパス
    """
    ch_dir = dest / challenge.slug()
    ch_dir.mkdir(parents=True, exist_ok=True)
    _write_metadata(challenge, ch_dir / "metadata.yml")
    await _download_distfiles(ctfd, challenge, ch_dir / "distfiles")
    return ch_dir


def _write_metadata(challenge: Challenge, path: Path) -> None:
    """metadata.yml の上書書出

    Args:
        challenge: 対象 Challenge
        path: 書出先ファイルパス
    """
    data = {
        "name": challenge.name,
        "id": challenge.id.value,
        "category": challenge.category_raw,
        "strategy": challenge.strategy.value if challenge.strategy else None,
        "value": challenge.value,
        "description": challenge.description,
        "connection_info": challenge.connection_info,
        "tags": list(challenge.tags),
        "hints": [
            {"content": h.content, "cost": h.cost}
            for h in challenge.hints
        ],
        "distfile_urls": list(challenge.distfile_urls),
    }
    path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    )


async def _download_distfiles(ctfd: CtfdGateway, challenge: Challenge, dest: Path) -> None:
    """distfile の差分ダウンロード

    Args:
        ctfd: CTFd ゲートウェイ
        challenge: 対象 Challenge
        dest: distfile 書出先ディレクトリ
    """
    if not challenge.distfile_urls:
        return
    dest.mkdir(exist_ok=True)
    for url in challenge.distfile_urls:
        fname = filename_from_url(url)
        target = dest / fname
        if target.exists():
            continue
        try:
            data = await ctfd.download_distfile(url)
        except Exception as e:  # noqa: BLE001
            logger.warning("distfile download failed %s: %s", url, e)
            continue
        target.write_bytes(data)
        logger.info("downloaded: %s (%d bytes)", fname, len(data))


def list_distfiles(ch_dir: Path) -> tuple[str, ...]:
    """challenge ディレクトリ直下 distfile 名の列挙

    Args:
        ch_dir: challenge ディレクトリ

    Returns:
        ソート済 distfile 名のタプル
    """
    distfiles = ch_dir / "distfiles"
    if not distfiles.exists():
        return ()
    return tuple(sorted(f.name for f in distfiles.iterdir() if f.is_file()))
