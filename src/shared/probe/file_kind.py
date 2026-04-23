from __future__ import annotations

from enum import StrEnum


class FileKind(StrEnum):
    """ファイルマジックから推定される種別"""

    ELF = "elf"
    PE = "pe"
    MACH_O = "mach_o"
    PCAP = "pcap"
    PCAPNG = "pcapng"
    DISK_IMAGE = "disk_image"
    MEMORY_DUMP = "memory_dump"
    PDF = "pdf"
    OFFICE = "office"
    APK = "apk"
    IPA = "ipa"
    FIRMWARE = "firmware"
    ARCHIVE = "archive"
    IMAGE = "image"
    AUDIO = "audio"
    TEXT = "text"
    UNKNOWN = "unknown"
