from __future__ import annotations

from shared.probe import FileKind

from ..domain import Artifact

_KIND_SKILLS: dict[FileKind, tuple[str, ...]] = {
    FileKind.ELF: (
        "reverse-engineering",
        "rootkit-analysis",
        "ioc-hunting",
    ),
    FileKind.PE: (
        "reverse-engineering",
        "rootkit-analysis",
        "ioc-hunting",
    ),
    FileKind.MACH_O: (
        "reverse-engineering",
        "ioc-hunting",
    ),
    FileKind.PCAP: (
        "network-analyzer",
        "network-hunter",
        "performing-ssl-tls-security-assessment",
        "replay-attack",
        "reverse-engineering",
    ),
    FileKind.PCAPNG: (
        "network-analyzer",
        "reverse-engineering",
    ),
    FileKind.MEMORY_DUMP: (
        "memory-analysis",
        "rootkit-analysis",
        "ioc-hunting",
    ),
    FileKind.DISK_IMAGE: (
        "disk-forensics",
        "endpoint-forensics",
        "container-forensics",
        "rootkit-analysis",
    ),
    FileKind.PDF: (
        "reverse-engineering",
        "ioc-hunting",
    ),
    FileKind.OFFICE: (
        "ioc-hunting",
        "reverse-engineering",
    ),
    FileKind.APK: (
        "android-security",
        "ioc-hunting",
    ),
    FileKind.IPA: (
        "ios-security",
        "ioc-hunting",
    ),
    FileKind.FIRMWARE: (
        "firmware-iot-security",
        "rootkit-analysis",
        "reverse-engineering",
    ),
    FileKind.ARCHIVE: (
        "disk-forensics",
        "firmware-iot-security",
        "container-forensics",
        "ioc-hunting",
    ),
    FileKind.IMAGE: (),
    FileKind.AUDIO: (),
    FileKind.TEXT: (),
    FileKind.UNKNOWN: (
        "reverse-engineering",
        "ioc-hunting",
    ),
}

_KIND_TOOLS: dict[FileKind, tuple[str, ...]] = {
    FileKind.ELF: ("file", "strings", "readelf", "objdump", "ghidra", "radare2", "gdb", "yara"),
    FileKind.PE: ("file", "strings", "pefile", "ghidra", "dnspy", "yara"),
    FileKind.MACH_O: ("file", "otool", "strings", "ghidra"),
    FileKind.PCAP: ("tshark", "wireshark", "tcpdump", "zeek", "suricata"),
    FileKind.PCAPNG: ("tshark", "wireshark", "zeek"),
    FileKind.MEMORY_DUMP: ("volatility3", "rekall", "strings", "yara"),
    FileKind.DISK_IMAGE: ("fls", "icat", "mmls", "fsstat", "foremost", "autopsy", "sleuthkit"),
    FileKind.PDF: ("pdfid", "pdf-parser", "peepdf", "yara"),
    FileKind.OFFICE: ("oletools", "olevba", "oleid", "yara"),
    FileKind.APK: ("apktool", "jadx", "aapt", "dex2jar", "mobsf", "frida"),
    FileKind.IPA: ("class-dump", "otool", "frida", "objection", "ipsw"),
    FileKind.FIRMWARE: ("binwalk", "unblob", "fwanalyzer", "strings", "ghidra"),
    FileKind.ARCHIVE: ("unzip", "7z", "binwalk", "tar"),
    FileKind.IMAGE: ("exiftool", "steghide", "zsteg", "pngcheck", "binwalk"),
    FileKind.AUDIO: ("sox", "ffmpeg", "audacity"),
    FileKind.TEXT: ("cat", "strings", "grep"),
    FileKind.UNKNOWN: ("file", "strings", "xxd", "binwalk"),
}


def build_system_prompt(artifact: Artifact, *, container_path: str, container_arch: str = "unknown") -> str:
    """Artifact と sandbox 情報からの system prompt 生成

    Args:
        artifact: 解析対象の Artifact
        container_path: sandbox 内 artifact 絶対パス
        container_arch: sandbox の arch 文字列

    Returns:
        組立済の system prompt 文字列
    """
    skills = _KIND_SKILLS.get(artifact.kind, ())
    tools = _KIND_TOOLS.get(artifact.kind, ())

    lines: list[str] = [
        "# Role",
        "You are an expert forensic / reverse-engineering analyst.",
        "Examine the artifact below and produce a structured analysis report.",
        "",
        "# Artifact",
        f"- **File**    : `{container_path}` (read-only)",
        f"- **Name**    : {artifact.filename()}",
        f"- **Kind**    : {artifact.kind.value}",
        f"- **Size**    : {artifact.size_bytes} bytes",
        f"- **SHA-256** : `{artifact.sha256}`",
        f"- **Arch**    : {container_arch}",
        "",
        "# Workspace",
        "- `/challenge/workspace/` (writable) — store intermediate files here.",
        "- Original artifact is mounted read-only; do not modify it.",
        "",
    ]

    if tools:
        lines += [
            "# Relevant tools (pre-installed in sandbox)",
            ", ".join(f"`{t}`" for t in tools),
            "",
        ]

    if skills:
        lines += [
            "# Relevant skills",
            "Skill descriptions under `.claude/skills/` auto-surface by category match. ",
            "Candidates for this artifact kind:",
            *[f"- `{s}`" for s in skills],
            "",
        ]

    lines += [
        "# Task",
        "1. Inspect structure, metadata, and content using tools via Bash.",
        "2. Extract objective findings (file properties, embedded data, indicators).",
        "3. Build a structured report with numbered sections covering each finding.",
        "",
        "# Output",
        "Return JSON matching the schema: `{summary, sections: [{title, body}]}`.",
        "- `summary`: one-paragraph bottom line.",
        "- `sections`: 3-8 entries, each is a concrete finding with supporting evidence.",
        "",
        "# Rules",
        "- Do not modify the original artifact.",
        "- Cite commands and outputs in section body (markdown fenced blocks).",
        "- Stop when findings are exhausted; prefer depth over breadth.",
    ]

    return "\n".join(lines).rstrip() + "\n"
