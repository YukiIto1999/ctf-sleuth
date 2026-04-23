
# Heap Spray Exploitation Analysis

`memory-analysis` から呼ばれる variant 別 deep dive

## When to Use

- browser / Office / Reader / Java client が exploit を踏んだ後の memory dump
- 大量同一 region 確保 (browser process の VAD が肥大化) を疑う
- shellcode / ROP gadget の landing zone を memory 上に探したい
- CTF DFIR の exploit 解析問題

**使わない場面**: kernel exploit (→ `rootkit-analysis`)、code injection 系（→ `memory-analysis` の malfind 主軸）。

## Approach / Workflow

### Phase 1 — 候補 process の絞り込み

```bash
vol3 -f mem.raw windows.pslist | grep -iE 'firefox|chrome|edge|iexplore|excel|winword|adobe|acrobat|java|flash'
vol3 -f mem.raw windows.cmdline --pid <PID>
```

異常に大きな working set / Pageファイル使用量を持つ process を探す。

### Phase 2 — VAD 分析

```bash
vol3 -f mem.raw windows.vadinfo --pid <PID>
vol3 -f mem.raw windows.vadwalk --pid <PID>
```

heap spray の特徴:

```
- 同一 protection (PAGE_EXECUTE_READWRITE = 0x40 or PAGE_READWRITE) の region が連続
- size がほぼ同一 (4MB / 16MB / 64MB が典型)
- ProtoPTE ない (private memory)
- file backing なし (anon memory)
- 数百〜数千 region 並ぶ
```

### Phase 3 — region dump と pattern 検査

```bash
vol3 -f mem.raw windows.vaddump --pid <PID> --vma <addr>
xxd dump.bin | head -100
```

heap spray の典型 pattern:

```
- NOP sled: 0x90 が連続 (x86) / 0x9090 / 0x9090909090909090
- equivalent NOP: \x40\x40 (inc eax), \x41 (inc ecx), 0x0c0c0c0c (or al,0x0c)
- ROP chain: stack pivot 後の gadget address sequence
- shellcode marker: 0xfc 0xe8 0x82 (egg hunter), 0x55 0x8b 0xec (function prologue)
- unicode shellcode: 0x90 0x00 0x90 0x00 (UCS-2 spray for Internet Explorer)
```

`malfind` plugin で RWX + MZ 検出と組合せる:

```bash
vol3 -f mem.raw windows.malfind --pid <PID>
```

### Phase 4 — yara で shellcode 識別

```bash
vol3 -f mem.raw yarascan.yarascan --yara-rules shellcode.yar --pid <PID>
```

`shellcode.yar` 例:

```
rule generic_shellcode {
  strings:
    $nop_sled = { 90 90 90 90 90 90 90 90 90 90 }
    $eggHunter = { fc e8 82 ?? ?? ?? ?? }
    $rop_pivot = { c3 // ret gadget }
  condition: any of them
}
```

### Phase 5 — 攻撃 vector の同定

```bash
# browser process の navigation history
vol3 -f mem.raw windows.handles --pid <PID> --object-types File
vol3 -f mem.raw windows.dumpfiles --pid <PID>
strings -e l mem.raw | grep -iE 'http://|https://' | sort -u | head -50
```

巨大な JavaScript / SWF / VB / OLE が memory に残っていれば exploit kit / malicious page の手がかり。

### Phase 6 — exploit 後の挙動

heap spray 成功 → shellcode 実行で何をしたかを memory から再構成:

```
- 子 process 起動 (cmd.exe / powershell / rundll32) → pstree で確認
- 別 process への inject (malfind で RWX MZ)
- 永続化 (registry / scheduled task)
- C2 接続 (netscan)
```

### Phase 7 — レポート

```
- 対象 process / version
- spray 痕跡 (region 数 / size / protection / pattern)
- shellcode 抽出 (length / disasm 抜粋 / hash)
- exploit 後の挙動 timeline
- 推定 CVE / exploit kit 名
- 修正 (patch / mitigations)
```

## Tools

```
volatility3 (vadinfo / vadwalk / vaddump / malfind / yarascan)
yara
strings
xxd / hexdump
ghidra / radare2 (shellcode disassemble)
WebFetch
Bash (sandbox)
```
