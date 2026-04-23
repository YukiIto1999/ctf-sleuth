---
name: reverse-engineering
description: 任意の binary (ELF / PE / Mach-O / .dex / .class) を disassembly + decompilation + behavior 分析で読み解く一般 skill。CTF rev、artifact_analysis BC の binary 系、HTB の入手 binary 解析で発火。
category: reverse
tags:
  - reverse
  - ghidra
  - radare2
  - ida
  - decompilation
  - binary
---

# Binary Reverse Engineering

## When to Use

- CTF rev / pwn 問題で binary を渡された
- artifact_analysis BC が ELF / PE / MACH_O kind を検出
- bug bounty / pentest で取得した binary の logic / secret 抽出
- 不審 binary の triage 入口

**使わない場面**: source code review (→ `source-code-scanning`)、rootkit 専用解析 (→ `rootkit-analysis`)、Android/iOS バイナリ (→ `android-security` / `ios-security`)。

format / language / family 別の深掘りは references/ を参照:

- 一般 RE — Ghidra で disassemble + decompile + script: `references/ghidra.md`
- Linux ELF malware: `references/linux-elf.md`
- packed (UPX 等) の unpack: `references/packed-upx.md`
- PDF malware (PDFiD / pdf-parser / peepdf): `references/pdf.md`
- Go コンパイル binary: `references/golang.md`
- Rust コンパイル binary: `references/rust.md`
- .NET (C# / VB.NET) malware: `references/dotnet.md`
- Ransomware の暗号 routine: `references/ransomware.md`
- Cobalt Strike beacon config: `references/cobaltstrike-beacon.md`
- Cobalt Strike Malleable C2 profile: `references/cobaltstrike-malleable.md`
- C2 protocol を binary から再構成: `references/c2-protocol.md`
- malware の生成 traffic を sandbox で解析: `references/malware-traffic.md`

## Approach / Workflow

### Phase 1 — triage

```bash
file binary
sha256sum binary
strings -n 8 binary | head -100
strings -e l binary | head -50         # UTF-16 / wide string
xxd binary | head
size binary
readelf -h binary                       # ELF header
objdump -p binary | head                # PE / ELF section
otool -hL binary                        # macOS Mach-O
nm binary                               # symbol
```

確認項目:

```
- 種別 (ELF / PE / Mach-O / dex / class)
- arch (x86 / x64 / ARM / ARM64 / MIPS)
- bit (32 / 64)
- 静的 link / dynamic link
- 保護機構 (NX / PIE / Canary / RELRO / CFG / ASLR)
- 言語 / コンパイラ (Go / Rust / C / C++ / .NET)
- packed (UPX / themida / vmprotect 等)
```

`checksec` で保護機構を一括確認。`die` (Detect It Easy) で packer / 言語推定。

### Phase 2 — packer / 暗号化

```bash
upx -d binary                           # UPX なら直接 unpack
binwalk -e binary                        # 内部 archive / firmware
```

VMProtect / Themida 等は手動 dump 必要 (memory dump → 再構成)。詳細: `reverse-engineering`。

### Phase 3 — 静的解析 (Ghidra / radare2 / IDA)

```bash
# Ghidra (headless)
$GHIDRA_HOME/support/analyzeHeadless ./project rev_proj -import binary -postScript decompile.py
# 出力: decompiled C-like

# radare2
r2 -A binary
> aaaa                  # 全解析
> afl                    # function 一覧
> pdf @ main             # main 関数 disasm
> agf                    # call graph
> /a mov eax,1           # opcode 検索
> /R                     # ROP gadget
```

IDA Pro / Binary Ninja がある場合は GUI で type recovery を進める。

### Phase 4 — 主要観点

```
- main の論理 (CTF: flag check 関数)
- crypto routine (AES sbox, SHA constants 等)
- network (socket / connect / send / recv)
- file IO (open / read / write)
- 文字列 (URL / domain / file path / API key の hard-code)
- import 関数 (Windows API / libc 関数)
- anti-debug / anti-VM (ptrace / IsDebuggerPresent / cpuid)
- obfuscation (control-flow flattening / 文字列暗号化)
```

### Phase 5 — 動的解析 (補助)

```bash
# Linux
ltrace ./binary
strace -f ./binary
gdb ./binary
  (gdb) starti
  (gdb) info functions
  (gdb) break main
  (gdb) run
  (gdb) layout asm

# Windows (sandbox)
x64dbg / x32dbg / WinDbg
Process Monitor / API Monitor
```

危険 binary は安全な sandbox で。Cuckoo / any.run 系のオンライン sandbox は CTF / 個人検証で活用。

### Phase 6 — 言語別の特徴

```
Go:    関数名 (`main.main`, `runtime.*`)、文字列 table が大きい、stack 切替で trace 困難
       → reverse-engineering
Rust:  panic! の文字列で機能推定可、generics 展開で関数増殖
       → reverse-engineering
.NET:  IL → C# decompile (dnSpy / ILSpy)
       → reverse-engineering
Java/Android: dex → smali / Java
       → android-security, android-security
iOS:   ARM64, Mach-O fat binary, Objective-C runtime
       → ios-security, ios-security
```

### Phase 7 — symbolic execution

```bash
# angr (Python)
import angr
proj = angr.Project('binary', auto_load_libs=False)
state = proj.factory.entry_state()
simgr = proj.factory.simulation_manager(state)
simgr.explore(find=lambda s: b'flag' in s.posix.dumps(1))
```

CTF rev で license check / hash check の入力解の探索に有効。Z3 直接 / KLEE / Manticore も近接。

### Phase 8 — 結果まとめ

```
- binary identity (hash / format / arch)
- 言語 / コンパイラ / 主な library
- 保護機構
- main の論理 / 主要 function
- 抽出した secret / IOC
- 推定 family / behavior
- 推奨修正 (vulnerability ある場合)
```

## Tools

```
file / strings / xxd / nm
readelf / objdump / otool / dumpbin
ghidra / radare2 / IDA / Binary Ninja / Cutter
checksec / die
upx / binwalk
gdb / pwndbg / gef / pwntools
ltrace / strace / x64dbg / WinDbg
angr / Z3 / KLEE
WebFetch
Bash (sandbox)
```

## Related Skills

- `android-security`, `ios-security` (mobile)
- `rootkit-analysis` (kernel-level)
- `cve-exploitation`, `memory-analysis` (heap spray など memory artefact 解析)
- `ioc-hunting`
- `source-code-scanning`

## Rules

1. **隔離環境** — 不審 binary は VM / container 内で動的解析
2. **integrity** — binary の SHA-256 を保持
3. **共有** — 抽出した secret / API key を sealed area へ
4. **公開禁止** — 取得 binary を unauthorized 共有しない（マルウェア配布規制）
