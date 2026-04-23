
# Memory Forensics with Volatility 3

`memory-analysis` から呼ばれる variant 別 deep dive

## When to Use

- 既に Volatility 3 環境が整っており、playbook 化された手順で再現性ある memory triage を回したい
- ISF symbol pack の調達 / Linux profile 生成も含めた end-to-end の手順が必要
- `memory-analysis` の概念解説でなく、実コマンドの順序とフラグを欲しい

**使わない場面**: Volatility 2 の legacy plugin が必須な対象（→ `memory-analysis` の v2 節）。

## Approach / Workflow

### Phase 0 — 受領と integrity

```bash
sha256sum mem.raw                      # チェーン保全
file mem.raw                           # フォーマット推定
```

ダンプは read-only マウント。analysis は別ディレクトリにコピーしたものに対して実施。

### Phase 1 — symbol / profile

Windows / macOS:

```bash
vol3 -f mem.raw windows.info
# auto fetch from https://github.com/JPCERTCC/MemoryForensic-Cheatsheets 系の ISF
```

Linux: kernel に対応する ISF を生成。

```bash
git clone https://github.com/volatilityfoundation/dwarf2json
cd dwarf2json && go build
./dwarf2json linux --elf /path/to/vmlinux > kernel.json
mv kernel.json ~/.local/share/volatility3/symbols/linux/
```

または既存 ISF 配布 (CVE 系の有名 dump は github に置かれている)。

### Phase 2 — Triage playbook

Windows:

```bash
vol3 -f mem.raw windows.info               > 00-info.txt
vol3 -f mem.raw windows.pslist             > 01-pslist.txt
vol3 -f mem.raw windows.pstree             > 02-pstree.txt
vol3 -f mem.raw windows.cmdline            > 03-cmdline.txt
vol3 -f mem.raw windows.psscan             > 04-psscan.txt
vol3 -f mem.raw windows.netscan            > 05-net.txt
vol3 -f mem.raw windows.malfind            > 06-malfind.txt
vol3 -f mem.raw windows.dlllist            > 07-dlllist.txt
vol3 -f mem.raw windows.modscan            > 08-modscan.txt
vol3 -f mem.raw windows.svcscan            > 09-svc.txt
vol3 -f mem.raw windows.registry.hivelist  > 10-hives.txt
vol3 -f mem.raw windows.handles            > 11-handles.txt
vol3 -f mem.raw windows.filescan           > 12-files.txt
vol3 -f mem.raw windows.driverscan         > 13-drivers.txt
vol3 -f mem.raw windows.callbacks          > 14-callbacks.txt
vol3 -f mem.raw windows.ssdt               > 15-ssdt.txt
```

Linux:

```bash
vol3 -f mem.raw linux.info                 > 00-info.txt
vol3 -f mem.raw linux.pslist               > 01-pslist.txt
vol3 -f mem.raw linux.pstree               > 02-pstree.txt
vol3 -f mem.raw linux.psaux                > 03-psaux.txt
vol3 -f mem.raw linux.bash                 > 04-bash.txt
vol3 -f mem.raw linux.lsmod                > 05-lsmod.txt
vol3 -f mem.raw linux.sockstat             > 06-sock.txt
vol3 -f mem.raw linux.malfind              > 07-malfind.txt
vol3 -f mem.raw linux.check_syscall        > 08-syscall.txt
vol3 -f mem.raw linux.check_modules        > 09-checkmod.txt
vol3 -f mem.raw linux.hidden_modules       > 10-hidmod.txt
vol3 -f mem.raw linux.envars               > 11-envars.txt
```

### Phase 3 — diff 系で隠蔽検出

```bash
diff <(awk '{print $2}' 01-pslist.txt) <(awk '{print $2}' 04-psscan.txt)
diff <(awk '{print $1}' 05-lsmod.txt) <(awk '{print $1}' 09-checkmod.txt)
```

差分があれば隠蔽の兆候。

### Phase 4 — focused dig

不審 PID / region を絞り込んだら詳細 plugin:

```bash
vol3 -f mem.raw windows.dumpfiles --pid <PID>
vol3 -f mem.raw windows.vadinfo --pid <PID>
vol3 -f mem.raw windows.vaddump --pid <PID> --vma <addr>
vol3 -f mem.raw windows.privileges --pid <PID>
vol3 -f mem.raw windows.envars --pid <PID>
vol3 -f mem.raw windows.handles --pid <PID> --object-types Mutant
```

### Phase 5 — 認証

```bash
vol3 -f mem.raw windows.hashdump
vol3 -f mem.raw windows.cachedump
vol3 -f mem.raw windows.lsadump
```

詳細 chain は `memory-analysis`。

### Phase 6 — yara overlay

```bash
vol3 -f mem.raw yarascan.yarascan --yara-rules rules/
```

`rules/` は社内 / threat intel feed。

### Phase 7 — レポート (timeline 主体)

```
時刻        イベント
HH:MM:SS  initial process X (PID 1234) cmd: ...
HH:MM:SS  inject into Y (PID 5678)
HH:MM:SS  network out to a.b.c.d:443
HH:MM:SS  registry add Run\\Foo
HH:MM:SS  credential dump
```

Phase 1-6 の出力を重ねて 1 本の timeline に。

## Tools

```
volatility3 (vol3)
dwarf2json
yara
strings
jq
WebFetch
Bash (sandbox)
```
