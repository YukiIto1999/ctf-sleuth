---
name: api-security
description: REST / GraphQL / WebSocket / LLM 統合 API に対する認可破り・スキーマ濫用・トークン漏洩等の評価。CTF web の API 系問題、HTB box の API 端点、bug bounty スコープに含まれる API 資産で発火する。
category: web
tags:
  - api
  - rest
  - graphql
  - websocket
  - web-llm
  - authorization
  - methodology
---

# API Security

## When to Use

- REST / GraphQL / WebSocket / LLM 統合 API のいずれかを攻撃面として持つ対象
- CTF web 問題で `/api/` や `/graphql` が露出している
- HTB の machine が API バックエンドを公開している
- bug bounty で in-scope に API 資産が含まれる

**使わない場面**: フロント HTML のみで完結し API 端点が無い対象、データベース直接攻撃が目的の場面（→ `injection` 系を使う）。

## Approach / Workflow

### Phase 1 — 端点の発見と仕様化

```
curl -sI https://target/api/                       # サーバ・バージョン
curl -s  https://target/api/openapi.json          # OpenAPI 露出
curl -s  https://target/swagger/                  # Swagger UI
curl -s  https://target/.well-known/security.txt
curl -s  https://target/graphql -H 'Content-Type: application/json' \
     -d '{"query":"{__schema{types{name}}}"}'      # GraphQL introspection
```

`ffuf -u https://target/FUZZ -w api-paths.txt` で path 列挙。フロント JS を `WebFetch` で取り、エンドポイント文字列を抽出する。

### Phase 2 — 認可モデルのマッピング

- 匿名 / API key / Bearer / セッション cookie / mTLS のいずれを使うか観察
- ロール / テナント / リソース ID の構成を把握
- レート制限・キャッシュ・retry-after ヘッダの有無

### Phase 3 — API 種別ごとの試験

| 種別 | 主要観点 |
|---|---|
| **REST** | BOLA / IDOR、mass assignment、HTTP method 切替（PUT/PATCH/DELETE 開放）、versioning bypass、API key の URL 漏洩、Host ヘッダ詐称 |
| **GraphQL** | introspection 経由のスキーマ抽出、深いネスト DoS、field suggestion 経由の権限漏洩、batching 攻撃、alias 重複、operation name 制限の欠落 |
| **WebSocket** | Cross-Site WebSocket Hijacking (Origin 検証欠落)、メッセージ署名なし改竄、認証情報の subprotocol 漏洩 |
| **Web-LLM 統合** | prompt injection、indirect injection、tool 過信任の権限境界破り、応答からの内部 system prompt 漏洩 |

### Phase 4 — 認可破り（最重要）

object-level authorization (BOLA / IDOR) は API の脆弱性 #1。観点:

1. 自分が作成したリソース ID を、別ユーザのトークンで GET できるか
2. ID が UUID v4 でなく逐次採番なら隣接 ID を試す
3. `X-User-Id` / `X-Tenant-Id` 系のヘッダ自由化を試す
4. nested URL (`/users/123/orders/456`) で外側の所属チェックが抜けていないか

### Phase 5 — マスアサインメント

`PUT /users/me` `{"name":"...", "is_admin": true}` などの上書き試験。schema が露出していれば、隠し field (admin / role / verified) を直接指定する。

### Phase 6 — レート制限とビジネスロジック

- 同一 endpoint の per-user / per-IP 制限を計測
- 並列で同 idempotency key を投げるレース
- 在庫・通知・送金など状態を進める endpoint で 2 重実行
- promo code・優待コード再使用

### Phase 7 — 確証と PoC

最小再現を作り、被害を 1 ステップで示す（他ユーザリソースの取得 / 権限昇格 / DoS）。本番影響を避け、可能なら test account 上で示す。

## Tools

```
curl
ffuf
graphql-cop / clairvoyance (GraphQL 専用)
wsrepl / websocat (WebSocket)
postman / bruno
mitmproxy / burp
nuclei (api-template)
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `web-pentester`, `web-app-logic`, `client-side`, `server-side`
- `injection`
- `authentication`, `testing-jwt-token-security`, `testing-oauth2-implementation-flaws`
- `detection-web` (防御視点で攻撃ログのパターンを学ぶ)
- `bug-bounter`, `web-bounty`

## Rules

1. **スコープ厳守** — 認可済みの API のみ。documented endpoint は攻撃対象として明示されていることを確認する
2. **本番試験を最小化** — 認可破り・mass assignment はテストアカウント間で示す。一般ユーザのデータには触れない
3. **DoS 回避** — GraphQL nested query / WebSocket flood は短時間・低帯域で確認し、その後やめる
4. **トークン取り扱い** — 取得した token / API key を report に貼らない（hash 化または最初/最後 4 文字のみ）
