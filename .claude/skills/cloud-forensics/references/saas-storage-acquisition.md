# SaaS Cloud Storage Forensic Acquisition

`cloud-forensics` の Phase 6 から呼ばれる、Google Drive / OneDrive / Dropbox / Box 等の SaaS storage 内データの API + endpoint sync client artefact 経由 acquisition。

## いつ切替えるか

- 調査対象 user が SaaS storage を使っており、保存された file / version / 共有先を確認したい
- exfil 調査で SaaS storage に出されたデータの追跡
- endpoint 上の sync client artefact (DB / cache / log) で履歴を再構成
- CTF DFIR で OneDrive / Drive / Dropbox の log 解析問題

## Phase 1 — 取得経路の選択

| 経路 | 適用 |
|---|---|
| Provider API + admin token | tenant / org admin がある場合の最も網羅的取得 |
| Per-user OAuth + 個人 token | 単一 user の data だけ取りたい |
| Endpoint sync client artefact | live access が無い / API 制限 / 削除済 file の復元 |
| eDiscovery / Vault | M365 / Google Workspace の管理者向け hold + export |

## Phase 2 — provider 別 API 取得

### Google Drive (Workspace)

```
- Admin SDK Reports API: ログイン / drive アクセス / sharing 変更
- Drive API: file メタデータ + リビジョン + 共有 ACL
- Vault: legal hold + export (eDiscovery)
- gam7 (admin tool) や rclone で bulk download
```

```bash
gam user <user> show filelist > files.csv
gam report drive 2024-01-01 to 2024-01-15 > drive-audit.csv
```

### OneDrive / SharePoint (M365)

```
- Microsoft Graph API: drives / driveItems / activities
- Audit Log Search (Microsoft Purview): file アクセス / sharing
- SharePoint Audit Log
- M365 Compliance / eDiscovery
```

```bash
# Graph (要 Files.Read.All / AuditLog.Read.All)
GET /users/<id>/drive/root/children
GET /users/<id>/drive/items/<itemId>/versions
```

### Dropbox / Box

```
- Dropbox Business API: events / sharing
- Box: Events API / Reports API / Box Shield
- API token は admin (Dropbox: team_admin, Box: as-user)
```

## Phase 3 — endpoint sync client artefact

Windows / macOS の sync client は local DB / cache / log を残す:

```
Google Drive (Drive for Desktop):
  %LOCALAPPDATA%\Google\DriveFS\<user>\
    metadata_sqlite_db
    sync_log.* / experiments.db

OneDrive:
  %LOCALAPPDATA%\Microsoft\OneDrive\settings\
    *.dat / *.db
  %LOCALAPPDATA%\Microsoft\OneDrive\logs\

Dropbox:
  %APPDATA%\Dropbox\instance1\
    config.dbx (encrypted SQLite)
    filecache.db
    sync_history.db

Box Drive:
  %LOCALAPPDATA%\Box\Box\
    db (sqlite)
```

これらを SQLite 解析 (→ `disk-forensics`) すると同期 file 名 / hash / 操作 timestamp / shared_with が抽出できる。

## Phase 4 — sharing / link 履歴

```
- 公開リンクの作成 / 解除 (audit log の event_name)
- 外部 user への招待
- 権限変更 (viewer → editor → owner)
- domain 外への共有
```

exfil 経路として最重要。

## Phase 5 — version / revision

```
- 過去 version の存在
- 削除 file の trash retention
- 復元可能性
```

provider 別:

```
Drive:    最大 100 revision / 30 日 (デフォルト)
OneDrive: 最大 500 version
Dropbox:  Plus = 30 日 / Business = 180 日
Box:      管理者設定
```

## Phase 6 — 取得 file の解析

取得した file を:

- yara / clamav で malicious 確認
- exiftool で metadata 確認
- hash で IOC 化

## Phase 7 — レポート

```
- user / mailbox / drive
- 期間
- file 一覧 (path / hash / size / 作成 / 最終 access)
- sharing 履歴 (公開 / 外部 / domain 外)
- 異常 sync (短時間に大量 download / 削除)
- IOC
- 推奨対応 (sharing 取消 / token revoke / DLP rule)
```

## Tools

```
gam7 (Google Workspace admin)
Microsoft Graph PowerShell
rclone
sqlite3 (sync client DB)
yara / clamav
WebFetch
Bash (sandbox)
```
