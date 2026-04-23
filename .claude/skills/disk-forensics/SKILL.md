---
name: disk-forensics
description: ディスクイメージから filesystem 解析・artefact 復元・timeline 再構成・SQLite / PST / LNK / Linux artefact / Chromium browser までを統合する DFIR ワークフロー。CTF forensics の disk image 系問題、artifact_analysis BC の DISK_IMAGE で発火。artefact 種別の深掘りは references/ 参照
category: forensics
tags:
  - disk-forensics
  - imaging
  - timeline
  - sleuthkit
  - sqlite
  - pst
  - lnk
  - browser
---

# Disk Forensics

## When to Use

- ディスクイメージ (`.dd`, `.E01`, `.AFF`, `.001`, `.vmdk`) を渡された
- フルシステム侵害の調査で persistent storage を見る必要
- CTF forensics で disk image から flag / artefact を復元する問題
- 個別の artefact (SQLite / PST / LNK / Linux 設定 / browser) 解析

**使わない場面**: メモリのみ (→ `memory-analysis`)、log のみ (→ `endpoint-forensics`)。

artefact 種別別の深掘りは references/ を参照: SQLite DB の active record + freelist / WAL = `references/sqlite.md`、Outlook PST / OST = `references/outlook-pst.md`、Windows LNK / JumpList = `references/lnk-jumplist.md`、Linux auth log / cron / shell history / 永続化機構 = `references/linux-artifacts.md`、Chromium 系 browser (Chrome / Edge / Brave / Opera) profile = `references/browser-hindsight.md`。

## Approach / Workflow

### Phase 1 — image 取得確認

取得済みの image に対して:

```bash
sha256sum disk.dd
file disk.dd
mmls disk.dd                     # partition 情報 (sleuthkit)
fsstat -o <offset> disk.dd       # filesystem 情報
```

E01 → raw 変換が必要なら `ewfmount` か `xmount`。

### Phase 2 — read-only mount

evidence 保全のため必ず read-only:

```bash
sudo mount -o ro,loop,offset=$((512*<sector>)) disk.dd /mnt/evidence
```

または autopsy / sleuthkit / The Sleuth Kit (TSK) ツールで直接読む。

### Phase 3 — filesystem 列挙

```bash
fls -r -m / -o <offset> disk.dd > body.txt    # body file (timeline 用)
fls -d -o <offset> disk.dd                    # 削除 file
icat -o <offset> disk.dd <inode> > recovered.bin
```

### Phase 4 — timeline 構築

```bash
mactime -b body.txt -d > timeline.csv
# または log2timeline (Plaso) で super-timeline
log2timeline.py timeline.plaso disk.dd
psort.py -o l2tcsv timeline.plaso > super-timeline.csv
```

super-timeline は MFT / USN / event log / registry / browser を統合。

### Phase 5 — Windows 主要 artefact

```
- $MFT (NTFS)              全 file metadata
- $UsnJrnl                  最近の変更
- $LogFile                  recent operations
- ShellBags                 explorer 経由フォルダアクセス
- Prefetch (.pf)            実行された exe の証跡 (~128 entries)
- Amcache.hve               実行 binary の SHA-1 hash
- ShimCache (AppCompatCache) 同上、別 source
- SRUM                      アプリ別ネット使用 (Win10+)
- Recent (.lnk + JumpList)  最近開いた file (→ `disk-forensics`)
- WindowsTimeline (ActivitiesCache.db) Win10 1803+
- registry: NTUSER.DAT / SYSTEM / SECURITY / SAM / SOFTWARE / DEFAULT
```

抽出ツール:

```bash
analyzeMFT.py -f $MFT -o mft.csv
RegRipper / regripper.pl
PECmd (prefetch)
JLECmd (jumplist)
LECmd (.lnk)
SBECmd (shellbags)
AmcacheParser
```

### Phase 6 — Linux 主要 artefact

```
- /var/log/* (auth.log, syslog, audit.log)
- /etc/cron.d/* /etc/systemd/system/*.service
- /home/*/.bash_history / .zsh_history / .python_history
- /home/*/.ssh/authorized_keys / known_hosts
- /var/spool/cron/*
- /etc/passwd / /etc/shadow / /etc/sudoers / /etc/sudoers.d/*
- /var/lib/dpkg/status / /var/log/apt/history.log (Debian系)
- /var/log/dnf.log (RHEL系)
- ~/.viminfo / .lesshst (recent file access)
- inode timestamps (atime / mtime / ctime / btime)
```

詳細は `disk-forensics` / `endpoint-forensics`。

### Phase 7 — file carving (削除 file 復元)

```bash
foremost -i disk.dd -o carved/
photorec disk.dd
scalpel -c scalpel.conf disk.dd -o carved/
bulk_extractor disk.dd -o bulk-out/
```

`bulk_extractor` は string-based artefact (URL / email / credit card / GPS) を一気に抽出。

### Phase 8 — DB 系の解析

```
SQLite (browser / iMessage / chat / mobile sync) → disk-forensics
PST/OST (Outlook)                                  → disk-forensics
LNK / JumpList                                    → disk-forensics
```

### Phase 9 — レポート

```
- image hash / partition / filesystem
- 取得 timeline (重要 event のみ)
- 不審 file (path / hash / size / timestamp / 推定経路)
- 認証 / 永続化 artefact
- IOC まとめ
- 推奨対応
```

## Tools

```
sleuthkit (mmls / fsstat / fls / icat / blkcat / mactime)
plaso / log2timeline / psort
RegRipper
PECmd / JLECmd / LECmd / SBECmd / AmcacheParser
foremost / photorec / scalpel / bulk_extractor
autopsy (GUI)
ewfmount / xmount (E01 / AFF mount)
WebFetch
Bash (sandbox)
```

## Related Skills

- `endpoint-forensics`, `memory-analysis`, `network-analyzer`
- `container-forensics`
- `ioc-hunting`
- `dfir`, `blue-teamer`

## Rules

1. **read-only** — image を絶対に書込まない (mount 時 `ro` / write blocker)
2. **chain of custody** — image 取得時 / 解析時の SHA-256 を記録
3. **timezone** — UTC で揃える
4. **PII redaction** — レポート共有前に user data を sealed area へ
