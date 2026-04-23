---
name: memory-analysis
description: メモリダンプ (.raw / .mem / .vmem / .lime) を Volatility3 / Rekall で解析し、process / command line / network / loaded modules / credentials / rootkit 痕跡を抽出する。CTF forensics の memory 系問題、artifact_analysis BC の MEMORY_DUMP で発火。
category: forensics
tags:
  - memory
  - volatility
  - rekall
  - forensics
  - rootkit
  - credentials
---

# Memory Analysis

## When to Use

- 物理メモリのダンプファイル (`.raw`, `.mem`, `.vmem`, `.lime`, `.dmp`) が供給されている
- in-memory malware / process injection / credential theft の調査
- CTF forensics で RAM capture が出題
- artifact_analysis BC で `FileKind.MEMORY_DUMP` として認識された対象

**使わない場面**: ディスクイメージのみ (→ `disk-forensics`)、ログだけ (→ `endpoint-forensics`)。

variant 別の深掘りは references/ を参照: Volatility 3 の operational 運用 = `references/volatility3.md`、Volatility 2 系の plugin = `references/volatility.md`、Linux ホストでの LiME 取得 = `references/lime-acquisition.md`、Rekall framework = `references/rekall.md`、NTLM hash / cached credentials / LSA secret / Kerberos ticket / clear-text password の抽出 = `references/credentials.md`、heap spray 攻撃の memory 痕跡解析 = `references/heap-spray.md`。

## Approach / Workflow

### Phase 1 — プロファイル特定

```bash
vol3 -f mem.raw windows.info        # Windows
vol3 -f mem.raw linux.info          # Linux (要 ISF symbol pack)
vol3 -f mem.raw mac.info            # macOS
strings -a mem.raw | head -200      # OS hint
```

Windows なら build / version / 64bit を控える。Linux はカーネルバージョンに対応する ISF が必要なので、必要なら `dwarf2json` で生成する。

### Phase 2 — process と起動時情報

```bash
vol3 -f mem.raw windows.pslist
vol3 -f mem.raw windows.pstree
vol3 -f mem.raw windows.cmdline
vol3 -f mem.raw windows.psscan       # unlinked / hidden process
vol3 -f mem.raw linux.pslist
vol3 -f mem.raw linux.pstree
vol3 -f mem.raw linux.psaux
```

異常 process の指標: 親が `services.exe` でない `cmd.exe`、署名されていない `svchost.exe`、CommandLine が無い process、PID 0 / 4 以外で `System` 名乗り。

### Phase 3 — ネットワーク

```bash
vol3 -f mem.raw windows.netstat       # endpoint / process 紐付け
vol3 -f mem.raw windows.netscan       # closed connection 含む
vol3 -f mem.raw linux.sockstat
```

外部 C2 候補 IP / 内部 lateral 候補を抽出。

### Phase 4 — ロードされたモジュール / DLL

```bash
vol3 -f mem.raw windows.dlllist
vol3 -f mem.raw windows.modules
vol3 -f mem.raw windows.modscan
vol3 -f mem.raw windows.driverirp
vol3 -f mem.raw linux.lsmod
```

非署名 DLL の存在、`Modules` と `ModulesScan` の差分 (差分は隠蔽 module) を確認。

### Phase 5 — code injection / hollowing

```bash
vol3 -f mem.raw windows.malfind        # injected RWX region
vol3 -f mem.raw windows.hollowprocesses
vol3 -f mem.raw windows.svcscan
vol3 -f mem.raw linux.malfind
```

`malfind` 出力の MZ header 検出と RWX 属性は process injection の典型。`vadinfo` で region 詳細を見る。

### Phase 6 — 認証情報

```bash
vol3 -f mem.raw windows.hashdump
vol3 -f mem.raw windows.cachedump
vol3 -f mem.raw windows.lsadump
vol3 -f mem.raw windows.mimikatz       # plugin 化済 (要追加)
strings -e l mem.raw | grep -iE 'password|kerberos|krb5|TGT'
```

詳細手順は `memory-analysis` 参照。

### Phase 7 — file / handle / registry

```bash
vol3 -f mem.raw windows.filescan
vol3 -f mem.raw windows.dumpfiles --pid <PID>
vol3 -f mem.raw windows.handles --pid <PID>
vol3 -f mem.raw windows.registry.hivelist
vol3 -f mem.raw windows.registry.printkey --key 'Software\\Microsoft\\Windows\\CurrentVersion\\Run'
```

### Phase 8 — rootkit / kernel

```bash
vol3 -f mem.raw windows.driverscan
vol3 -f mem.raw windows.callbacks
vol3 -f mem.raw windows.ssdt
vol3 -f mem.raw linux.check_modules
vol3 -f mem.raw linux.check_syscall
vol3 -f mem.raw linux.hidden_modules
```

詳細は `rootkit-analysis`、`rootkit-analysis` 参照。

### Phase 9 — Rekall を補助に

ある version の plugin / 出力差で Rekall が便利な場面:

```bash
rekall -f mem.raw imageinfo
rekall -f mem.raw netstat
rekall -f mem.raw apihooks
```

詳細は `memory-analysis`。

### Phase 10 — レポート

```
- 取得情報 (OS / kernel / build)
- 不審 process / 親子関係 / cmdline
- 外部接続候補 IP
- 注入候補 region
- 認証情報露出 (hash / clear text)
- 取得 IOC (ファイル / ネット / 永続化キー)
- 推奨対応
```

## Tools

```
volatility3 (vol3)
rekall
strings -e l/b
yara (memory scan)
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `rootkit-analysis` (kernel-level memory artefact)
- `dfir`, `blue-teamer`
- `disk-forensics`, `network-analyzer`

## Rules

1. **dump の整合性** — SHA-256 を取って evidence chain を維持
2. **plugin 信頼性** — 出力に異常があれば別 plugin / 別 version で cross-check
3. **PII / credentials** — report への記載は redact、原データは sealed evidence 領域へ
4. **profile 不一致** — Linux で symbol pack が無いと出力が偏る → 必ず profile を整えてから推論
