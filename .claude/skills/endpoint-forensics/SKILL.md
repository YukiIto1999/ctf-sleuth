---
name: endpoint-forensics
description: 侵害された endpoint (Windows / Linux / macOS) の memory + disk + log の triage と timeline 構築を一気通貫で進める。Linux 系 log や複数 source 相関 log analysis を内包する横断 skill。CTF DFIR で発火。log 種別の深掘りは references/ 参照
category: forensics
tags:
  - endpoint
  - dfir
  - timeline
  - log
  - linux
  - playbook
---

# Endpoint Forensics

## When to Use

- 侵害された endpoint (1 台) を完全 triage する標準 playbook が必要
- memory / disk / log を統合して 1 つの timeline / レポートを作る
- 複数 endpoint を並走させる場合の 1 台分の手順テンプレート
- 複数 log source の相関 timeline 化

**使わない場面**: cloud-only / serverless / SaaS endpoint (→ `cloud-forensics`)、memory dump 単独 (→ `memory-analysis`)、disk image 単独 (→ `disk-forensics`)。

log 系の深掘りは references/ を参照: Linux 系 log (syslog / auth.log / systemd journal / kern.log / アプリ log) の網羅的解析 = `references/linux-log.md`、複数 log source (system / application / network / security) の収集・正規化・相関による event timeline 化 = `references/log-analysis.md`。

## Approach / Workflow

### Phase 0 — 範囲定義

```
- endpoint 種別 (workstation / server / DC / DMZ web)
- OS / build / 役割
- 検出経緯 (alert / 異常通信 / user 報告)
- 隔離状況 (network 切離し済 / online のまま)
- 取得可能性 (live / image のみ / remote)
```

### Phase 1 — 初動: 揮発性高い順で取得

priority of acquisition:

```
1. RAM dump            (最揮発)
2. running process / network state スナップショット
3. shell history / log の現状
4. disk image          (静的)
5. external storage / log shipping (cloud / SIEM)
```

#### memory

```
Windows: winpmem / DumpIt / FTK Imager (CLI) / procdump (LSASS 等部分)
Linux:   LiME (→ memory-analysis)
macOS:   osxpmem / mac_apt
```

#### live system snapshot (必要なら)

```bash
# Linux
ps -auxf > ps.txt
ss -tnp > sockets.txt
last > last.txt
who > who.txt
sudo dmesg > dmesg.txt
journalctl --since "1 hour ago" > journal.txt
ls -la /proc/*/exe 2>/dev/null
```

```cmd
:: Windows (live, admin)
tasklist /v > tasklist.txt
netstat -anob > netstat.txt
schtasks /query /fo csv /v > tasks.csv
wmic startup list full > startup.txt
wmic service list config > services.txt
reg export HKLM\Software\Microsoft\Windows\CurrentVersion\Run run.reg
```

#### disk

write blocker 経由で `dd` / `dc3dd` / `ewfacquire`:

```bash
dc3dd if=/dev/sda hash=sha256 of=disk.dd hofs=disk.dd.hash
ewfacquire /dev/sda
```

### Phase 2 — Triage 並走

memory / disk / log を**並列**に triage:

```
memory:  → memory-analysis / memory-analysis
disk:    → disk-forensics
log:     → endpoint-forensics
windows: → disk-forensics
linux:   → disk-forensics
browser: → disk-forensics
sqlite:  → disk-forensics
email:   → disk-forensics
```

各 skill の triage 出力を 1 つの作業ディレクトリに集約:

```
case-001/
├── memory/         (vol3 出力)
├── disk/           (artefact / timeline / carved)
├── log/            (auth / app / sec)
├── browser/        (hindsight 出力)
├── timeline/       (super-timeline)
└── report/         (final markdown)
```

### Phase 3 — IOC 同定と相関

memory / disk / log それぞれから抽出した:

```
file artefact:    path / sha256 / 最初の出現時刻
process:          name / parent / cmdline / 親子関係
network:          IP / domain / port / 方向
auth:             user / source / time
persistence:      service / cron / autoload / registry
```

を 1 表に統合し、相関 (memory 上の process が disk 上の file に対応するか / log 上の auth event と一致するか) を確認。

### Phase 4 — Plaso super-timeline

```bash
log2timeline.py super.plaso disk.dd
log2timeline.py --append super.plaso /mnt/evidence/var/log/
psort.py -o l2tcsv super.plaso > super.csv
```

memory artefact 由来 event は plaso が直接扱えないので手動で merge。

### Phase 5 — 攻撃 chain の再構成

```
1. 初動 vector (phishing / RDP brute / SQLi 等)
2. 初期 foothold (実行された binary / shell)
3. 探索 (ローカル列挙 / 横展開準備)
4. 認証強奪 (mimikatz / DPAPI / cred theft)
5. 横展開 (lateral)
6. 永続化 (autorun / scheduled task / cron)
7. 目的達成 (data exfil / encrypt / sabotage)
```

### Phase 6 — 残存リスク評価

```
- 永続化機構の除去状況
- 流出 credentials の reset 状況
- 横展開先 endpoint の suspect 一覧
- C2 接続の遮断
- patch 状況
```

### Phase 7 — レポート

```
- 環境 (host / OS / 役割)
- timeline (UTC で event 列)
- 攻撃 chain
- IOC まとめ (file / network / persistence)
- 推奨対応 (短期 + 中期)
- 参考 evidence (chain of custody / hash)
```

## Tools

```
winpmem / DumpIt / LiME / osxpmem
dc3dd / ewfacquire
volatility3
sleuthkit / plaso / log2timeline
RegRipper / PECmd / JLECmd / LECmd
hindsight (browser)
WebFetch
Bash (sandbox)
```

## Related Skills

- `memory-analysis`, `disk-forensics`, `network-analyzer`
- `ioc-hunting`
- `system` (AD / privesc 痕跡), `rootkit-analysis` (kernel-level 検出)
- `dfir`, `blue-teamer`

## Rules

1. **整合性最優先** — 取得時 / 解析時の SHA-256 を必ず記録
2. **揮発性順** — RAM 取得を先に、disk image を後に
3. **隔離前の網状状記録** — network 切離す前に live 接続を先取得
4. **report は決め打ちしない** — 仮説と evidence を分けて記述
