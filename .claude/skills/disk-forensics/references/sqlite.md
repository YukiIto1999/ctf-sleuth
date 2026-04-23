
# SQLite Database Forensics

`disk-forensics` から呼ばれる variant 別 deep dive

## When to Use

- browser / messaging / mobile (iOS / Android) アプリの SQLite DB が evidence
- 削除済 record の復元が必要
- WAL / journal / freelist 領域からの遺物抽出
- CTF DFIR で `.sqlite` / `.db` ファイルが flag 隠し場所

**使わない場面**: live DB に対する SQL インジェクション (→ `exploiting-sql-injection-*`)。

## Approach / Workflow

### Phase 1 — file 確認

```bash
file db.sqlite                       # SQLite format 3 を確認
sha256sum db.sqlite db.sqlite-wal db.sqlite-journal db.sqlite-shm 2>/dev/null
ls -la db.sqlite*                    # 関連 file の同梱確認
```

WAL モードの DB は `.db` と `.db-wal` / `.db-shm` がセット。`.db` 単独だけ取得すると最新 commit が抜ける。

### Phase 2 — schema と active record

```bash
sqlite3 db.sqlite '.schema'                              # 全 schema
sqlite3 db.sqlite '.tables'
sqlite3 db.sqlite 'SELECT name, type FROM sqlite_master'

sqlite3 db.sqlite 'SELECT * FROM <table>' > active.csv
```

WAL モードを統合した最新状態:

```bash
sqlite3 db.sqlite 'PRAGMA journal_mode'                  # 現状
sqlite3 db.sqlite 'PRAGMA wal_checkpoint(FULL)'          # checkpoint で WAL 統合 (書込発生)
                                                          # → forensic 用途では COPY を編集
```

evidence 保全のため、原本コピーに対して checkpoint。

### Phase 3 — 削除 record の復元

SQLite は record 削除時に物理消去せず freelist にマーク。

```bash
sqlite_undelete db.sqlite > undelete.txt
```

または `sqlite-deleted-records-parser` (github):

```bash
python sqlparse_CLI.py -f db.sqlite -o output/
```

freelist + 未使用 page / unused space に過去の record が残る。

### Phase 4 — WAL / journal の解析

```bash
# WAL は前 commit までの変更 frame
xxd db.sqlite-wal | head -50                  # header (`377f0682` magic)
```

`walitean` / `walitas` (オープンソースツール) で WAL を decode:

```
- 各 frame の page id / commit / 内容
- rollback された変更 (commit されなかった変更) の検出
- timeline (どの順で書込まれたか)
```

journal モード (旧式) の `*-journal` は rollback 用 backup。同じ手順で参照。

### Phase 5 — timestamp encoding

SQLite の timestamp は schema 依存:

```
ISO8601 string  : '2024-01-15T12:34:56'
Unix epoch sec  : 1705325696
Unix epoch ms   : 1705325696000
WebKit ms       : Chromium / Safari (1601-01-01 base, 100ns)
NSDate          : iOS (2001-01-01 base, sec)
Mac Absolute    : 2001-01-01 base, sec (NSDate と同じ)
Windows FILETIME: 1601-01-01 base, 100ns
```

特定アプリの典型:

```
Chrome history.urls.last_visit_time   : WebKit ms
Firefox places.moz_places.last_visit_date : Unix microsec
iOS Messages chat.message_date          : NSDate (offset by 978307200 from Unix epoch)
WhatsApp messages.timestamp            : ms (Android) / NSDate (iOS)
```

decode 関数:

```python
from datetime import datetime, timedelta, timezone
def webkit_ms(v): return datetime(1601,1,1,tzinfo=timezone.utc) + timedelta(microseconds=v)
def nsdate(v): return datetime(2001,1,1,tzinfo=timezone.utc) + timedelta(seconds=v)
```

### Phase 6 — 主要 app の DB

```
Chrome (Default プロファイル):
  History            urls / visits / downloads / segments
  Cookies            cookies / meta
  Login Data         logins
  Web Data           autofill / credit_cards

Firefox:
  places.sqlite      moz_places / moz_historyvisits / moz_bookmarks

WhatsApp Android:
  msgstore.db        messages / chat / call_log
  wa.db              wa_contacts

iOS Messages:
  ~/Library/SMS/sms.db  message / chat / handle / attachment

Telegram (Desktop):
  cache 系 (E2E のため平文は限定的)

Signal:
  signal.db (SQLCipher 暗号化、master key 別途)
```

### Phase 7 — レポート

```
- 対象 DB / WAL / journal の SHA-256
- table と record 件数 (active / 削除済)
- 復元 record (timestamp / 内容抜粋)
- timeline
- 推奨 IOC
```

## Tools

```
sqlite3 / sqliteviewer / DB Browser for SQLite
sqlite_undelete / sqlite-parser (forensic 用)
walitas / walitean (WAL parser)
plaso (ext_sqlite plugins)
python (timestamp decode)
WebFetch
Bash (sandbox)
```
