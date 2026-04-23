from __future__ import annotations

import zipfile
from pathlib import Path

from shared.probe import FileKind

_MAGIC_MAP: tuple[tuple[bytes, FileKind], ...] = (
    (b"\x7fELF", FileKind.ELF),
    (b"MZ", FileKind.PE),
    (b"\xcf\xfa\xed\xfe", FileKind.MACH_O),
    (b"\xfe\xed\xfa\xcf", FileKind.MACH_O),
    (b"\xce\xfa\xed\xfe", FileKind.MACH_O),
    (b"\xfe\xed\xfa\xce", FileKind.MACH_O),
    (b"\xd4\xc3\xb2\xa1", FileKind.PCAP),
    (b"\xa1\xb2\xc3\xd4", FileKind.PCAP),
    (b"\n\r\r\n", FileKind.PCAPNG),
    (b"%PDF-", FileKind.PDF),
    (b"\x89PNG", FileKind.IMAGE),
    (b"\xff\xd8\xff", FileKind.IMAGE),
    (b"GIF8", FileKind.IMAGE),
    (b"RIFF", FileKind.AUDIO),
    (b"ID3", FileKind.AUDIO),
)

_FIRMWARE_MAGIC: tuple[bytes, ...] = (
    b"\x27\x05\x19\x56",
    b"UBI#",
    b"hsqs",
    b"sqsh",
    b"\x1f\x8b\x08",
)


def _classify_zip(path: Path) -> FileKind:
    """ZIP コンテナの内訳から APK / IPA / 一般 ARCHIVE を判別。

    Args:
        path: ZIP コンテナとして開けるファイル。

    Returns:
        APK / IPA / ARCHIVE のいずれか。
    """
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return FileKind.ARCHIVE
    if any(n == "AndroidManifest.xml" or n.endswith("/AndroidManifest.xml") for n in names):
        return FileKind.APK
    if any(n.startswith("Payload/") and n.endswith(".app/Info.plist") for n in names):
        return FileKind.IPA
    return FileKind.ARCHIVE


def detect_file_kind(path: Path) -> FileKind:
    """ファイル先頭バイト列に基づく FileKind 推定

    Args:
        path: 検査対象のファイルパス

    Returns:
        マジックバイト一致時の FileKind もしくは UNKNOWN
    """
    try:
        with path.open("rb") as f:
            head = f.read(16)
    except OSError:
        return FileKind.UNKNOWN
    if head.startswith(b"PK\x03\x04"):
        return _classify_zip(path)
    for magic, kind in _MAGIC_MAP:
        if head.startswith(magic):
            return kind
    if any(head.startswith(m) for m in _FIRMWARE_MAGIC):
        return FileKind.FIRMWARE
    if head and all(32 <= b < 127 or b in (9, 10, 13) for b in head):
        return FileKind.TEXT
    return FileKind.UNKNOWN
