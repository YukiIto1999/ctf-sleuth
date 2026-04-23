
# LNK / Jump List Artifact Analysis

`disk-forensics` から呼ばれる variant 別 deep dive

## When to Use

- Windows disk image / live profile から user の操作履歴を再構成する
- LNK ファイル (.lnk) や AutomaticDestinations / CustomDestinations の解析が必要
- USB 接続履歴 / ネット share 利用 / リモートファイル参照の証跡を取りたい

**使わない場面**: Linux / macOS host (→ `disk-forensics`)、registry-only な解析（→ `disk-forensics` の Windows artefact 節）。

## Approach / Workflow

### Phase 1 — LNK ファイルの所在

```
%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Recent\         # 最近開いた file
%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Recent\AutomaticDestinations\   # JumpList
%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Recent\CustomDestinations\
%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Office\Recent\
%USERPROFILE%\Desktop\*.lnk
%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\
```

Recent は最大 ~150 entries が回転。古い証跡は overwrite で消えている可能性。

### Phase 2 — LECmd で LNK 解析

```bash
LECmd.exe -d C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Recent\ --csv .
```

抽出される情報:

```
- TargetPath          実 file path
- TargetCreatedTime   target の作成時刻
- TargetModifiedTime
- TargetAccessedTime
- TargetIDListSize
- WorkingDirectory
- Arguments           実行時引数
- IconLocation
- VolumeSerial
- VolumeLabel         (USB 等の volume 識別)
- DriveType           Fixed / Removable / Network
- MachineId           作成 machine
- MAC address         作成 PC の NIC
- ObjectID            UUID
- BirthObjectID
```

USB 接続の証跡は `DriveType=Removable` + `VolumeSerial` を SYSTEM hive `USBSTOR` と相関。

### Phase 3 — JumpList 解析

JumpList = アプリ別の最近使った file 一覧 (Win7+)。

```bash
JLECmd.exe -d C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Recent\AutomaticDestinations\ --csv .
```

ファイル名は `<AppId>.automaticDestinations-ms` で AppId が application を特定:

```
1b4dd67f29cb1962    Word
9b9cdc69c1c24e2b    Notepad++
918e0ecb43d17e23    Chrome
...
```

(完全リスト: github.com/EricZimmerman/JLECmd の参照表)

中身は OLE Compound File。各 stream に LNK 構造がそのまま入っている。

### Phase 4 — CustomDestinations

```bash
JLECmd.exe -d ...\CustomDestinations\ --csv .
```

App が独自に管理 (例: Outlook の "ピン留め" / Windows Explorer の "frequent folders")。LNK + Header + Footer の混合。

### Phase 5 — 重点解析項目

```
- 通常使わないアプリで file が開かれていないか (notepad で credential.txt 等)
- ネットドライブ / UNC path が target に出る → C2 / lateral movement
- USB volume serial → 物理デバイス出入り
- arguments に PowerShell -enc / cmd /c → 実行 obfusc
- TargetCreatedTime と LNK 自体の created 差 → 古い file を attacker が re-target
```

### Phase 6 — timeline 統合

LNK / JumpList は user activity の重要 source。Plaso で super-timeline に統合:

```bash
log2timeline.py timeline.plaso C:\Users\<user>\
psort.py -o l2tcsv timeline.plaso > super.csv
```

または `LECmd --csv` を別途取ってから手動マージ。

### Phase 7 — レポート

```
- 対象 user / プロファイルパス
- 期間内の file アクセス (path / count / first / last)
- USB device 列 (volume serial / first seen / last seen)
- ネット share アクセス
- 実行されたアプリ + 引数
- 不審点 (notepad で credential / PowerShell 経由実行 / 外部 UNC)
```

## Tools

```
LECmd / JLECmd (Eric Zimmerman tools)
plaso / log2timeline / psort
sleuthkit (file 取得用)
strings / xxd (manual parse)
WebFetch
Bash (sandbox)
```
