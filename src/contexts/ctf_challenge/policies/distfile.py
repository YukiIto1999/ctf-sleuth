from __future__ import annotations

from urllib.parse import urlparse


def filename_from_url(url: str) -> str:
    """CTFd distfile URL 末尾からのファイル名抽出

    Args:
        url: distfile の URL

    Returns:
        ファイルシステム安全なファイル名
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    name = path.rsplit("/", 1)[-1] or "file"
    safe = "".join(c for c in name if c not in "\\/:*?\"<>|\x00")
    return safe or "file"
