
# Memory Dump Analysis with Volatility

`memory-analysis` から呼ばれる variant 別 deep dive

## When to Use

- インシデント後ホストの RAM dump (`.raw`, `.lime`, `.vmem`, `.dmp`) を渡された
- volatility3 の plugin 出力を体系的に運用したい
- legacy 環境で volatility 2.x も併用が必要

**使わない場面**: dump 取得手順の議論（→ `memory-analysis`）、別 framework の比較（→ `memory-analysis`）。

## Approach / Workflow

### Phase 1 — 環境セットアップ

```bash
# Volatility 3 (modern, default)
pip install volatility3
vol3 -f mem.raw windows.info

# Volatility 2 (legacy, profile 必須)
pip install volatility
vol -f mem.raw imageinfo
```

Volatility 3 はプロファイル auto-detect (Windows / macOS は ISF 自動取得)。Linux は `dwarf2json` で kernel ISF を別途生成。

### Phase 2 — Triage チェックリスト

```bash
# Windows
vol3 -f mem.raw windows.info
vol3 -f mem.raw windows.pslist
vol3 -f mem.raw windows.pstree
vol3 -f mem.raw windows.cmdline
vol3 -f mem.raw windows.netstat
vol3 -f mem.raw windows.netscan
vol3 -f mem.raw windows.malfind
vol3 -f mem.raw windows.dlllist
vol3 -f mem.raw windows.modscan
vol3 -f mem.raw windows.svcscan
vol3 -f mem.raw windows.registry.hivelist
vol3 -f mem.raw windows.handles --pid <PID>

# Linux
vol3 -f mem.raw linux.info
vol3 -f mem.raw linux.pslist
vol3 -f mem.raw linux.pstree
vol3 -f mem.raw linux.bash       # bash history
vol3 -f mem.raw linux.psaux
vol3 -f mem.raw linux.lsmod
vol3 -f mem.raw linux.malfind
vol3 -f mem.raw linux.check_syscall
vol3 -f mem.raw linux.check_modules
vol3 -f mem.raw linux.envars
```

### Phase 3 — 不審 process の絞り込み

```
- 親 process の妥当性 (services.exe, explorer.exe, init/systemd)
- cmdline の有無 / 不審なフラグ (-NoP / -EncodedCommand / curl http://*)
- 起動時刻が異常 (boot 直後でない process)
- exe ファイルの存在 (psscan 出力に DKOM 隠蔽の徴候)
```

### Phase 4 — code injection の確認

```bash
vol3 -f mem.raw windows.malfind --pid <PID>
# → MZ header / RWX VAD region が出る
vol3 -f mem.raw windows.vadinfo --pid <PID>
vol3 -f mem.raw windows.vaddump --pid <PID> --vma <addr>
```

抽出した binary を yara / pe parsing にかけて family 同定:

```bash
yara -r rules/ extracted.bin
clamscan extracted.bin
```

### Phase 5 — file / network artefact

```bash
vol3 -f mem.raw windows.filescan | grep -iE 'temp|appdata|users'
vol3 -f mem.raw windows.dumpfiles --virtaddr <addr>
vol3 -f mem.raw windows.netscan
```

`netscan` 出力から外部 C2 候補・内部 lateral 候補。timestamp と process を紐付ける。

### Phase 6 — 認証情報

```bash
vol3 -f mem.raw windows.hashdump
vol3 -f mem.raw windows.cachedump
vol3 -f mem.raw windows.lsadump
```

詳細 / mimikatz tier は `memory-analysis`。

### Phase 7 — 永続化 / registry

```bash
vol3 -f mem.raw windows.registry.printkey --key 'Software\\Microsoft\\Windows\\CurrentVersion\\Run'
vol3 -f mem.raw windows.registry.printkey --key 'Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce'
vol3 -f mem.raw windows.registry.userassist
vol3 -f mem.raw windows.registry.shellbags
```

Linux では `/etc/cron*`、`/etc/systemd/system/*.service` を memory 内 strings から探すか、disk image と相関。

### Phase 8 — IOC まとめ

```
- IOC: ファイル名 / hash / IP / domain / mutex / registry key
- 推定 family (yara hit + behavior)
- timeline (process 起動 / network 発生 / registry 変更)
- 残存リスク (永続化メカニズムの除去状況)
```

### Phase 9 — レポート

```
- 環境 (OS / build / dump サイズ / 取得時刻)
- 不審 process リスト
- 注入 / hollowing 兆候
- network IOC
- 認証情報露出
- 永続化 IOC
- 推奨対応 (filename block / IP block / patch / reset)
```

## Tools

```
volatility3 / volatility2
yara
clamav
strings
WebFetch
Bash (sandbox)
```
