
# Memory Artifact Extraction with Rekall

`memory-analysis` から呼ばれる variant 別 deep dive

## When to Use

- Volatility 3 の plugin 出力に異常 (空 / 矛盾) があり、別 framework で cross-check したい
- Rekall 固有 plugin (apihooks 系 / VAD 系) の精度が必要
- legacy dump で Volatility profile が無く、Rekall の auto-detect で当たる場合

**使わない場面**: 標準 vol3 で十分な triage（→ `memory-analysis`）。Rekall は 2020 年以降 maintenance が薄いので primary には選ばない。

## Approach / Workflow

### Phase 1 — セットアップ

```bash
pip install rekall-agent rekall-core
rekall -f mem.raw imageinfo
```

Linux dump はプロファイル (kernel symbol pack) を必要とする (`rekall-profiles` repo)。

### Phase 2 — Triage

```bash
rekall -f mem.raw pslist
rekall -f mem.raw pstree
rekall -f mem.raw psscan       # DKOM-resistant
rekall -f mem.raw psxview      # multi-source 比較で隠蔽検出
rekall -f mem.raw cmdscan      # cmd.exe history
rekall -f mem.raw consoles     # console output
```

### Phase 3 — process injection / hollowing

```bash
rekall -f mem.raw malfind
rekall -f mem.raw vadinfo --pid <PID>
rekall -f mem.raw hollow_find        # process hollowing 専用
rekall -f mem.raw apihooks            # API hooking 検出
rekall -f mem.raw idt
rekall -f mem.raw ssdt
rekall -f mem.raw callbacks
```

`hollow_find` は image base address の inconsistency を見て hollowing を検出する。`apihooks` は IAT / EAT / inline hook を網羅。

### Phase 4 — rootkit 系

```bash
rekall -f mem.raw modscan
rekall -f mem.raw driverscan
rekall -f mem.raw kdbgscan         # KDBG validation
rekall -f mem.raw timers           # timer DPC hook
rekall -f mem.raw notifier_callbacks
```

Linux の場合:

```bash
rekall -f mem.raw linux_check_syscall
rekall -f mem.raw linux_check_modules
rekall -f mem.raw linux_check_idt
rekall -f mem.raw linux_check_creds
rekall -f mem.raw linux_lsmod
rekall -f mem.raw linux_hidden_modules
```

### Phase 5 — file / handle

```bash
rekall -f mem.raw filescan
rekall -f mem.raw dumpfiles --pid <PID>
rekall -f mem.raw handles --pid <PID>
```

### Phase 6 — Volatility 3 との diff

差分を取って結論する:

```bash
vol3 -f mem.raw windows.pslist | awk '{print $2,$3}' | sort > /tmp/vol-pslist
rekall -f mem.raw pslist | awk '{print $2,$3}' | sort > /tmp/rek-pslist
diff /tmp/vol-pslist /tmp/rek-pslist
```

差分が出る → 一方の framework の plugin が抜けている。3rd の framework (yarascan / direct strings) で確認。

### Phase 7 — レポート

```
- 取得 framework (Rekall version / plugin version)
- 既存 vol3 結果との一致 / 不一致
- 隠蔽 process / module の検出有無
- 抽出 binary の SHA-256 / yara 結果
- IOC 一覧
```

## Tools

```
rekall (rekall-core / rekall-agent)
volatility3 (cross-check)
yara
strings
WebFetch
Bash (sandbox)
```
