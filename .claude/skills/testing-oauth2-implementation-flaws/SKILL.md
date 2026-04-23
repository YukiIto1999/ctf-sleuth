---
name: testing-oauth2-implementation-flaws
description: OAuth 2.0 / OIDC 実装を flow 種別 (auth code / implicit / device / client credentials / refresh) ごとにチェックリスト評価する。CTF auth 系・bug bounty SSO 案件で発火。
category: web
tags:
  - oauth2
  - oidc
  - flow
  - chaining
  - methodology
---

# OAuth 2.0 / OIDC Implementation Flaw Testing

## When to Use

- 実装が複数の OAuth flow（authorization code / implicit / device / client credentials）を扱う
- discovery / metadata から flow 一覧を抽出して網羅的に検査したい
- 横断したチェックリスト的試験

**使わない場面**: JWT 部の試験 (→ `testing-jwt-token-security`)。
チェックリストで懸念が見つかった redirect_uri 緩和 / state 欠落 / PKCE 抜け / scope 過剰 / refresh token 取扱不備 等の深掘り攻撃は `references/misconfig-vectors.md` を参照。

## Approach / Workflow

### Phase 1 — 実装の flow 把握

```
GET /.well-known/openid-configuration         # OIDC
GET /.well-known/oauth-authorization-server   # OAuth 2.0
```

response から:

```
authorization_endpoint
token_endpoint
userinfo_endpoint
introspection_endpoint
revocation_endpoint
device_authorization_endpoint  (Device Flow があるか)
jwks_uri
response_types_supported       (code / token / id_token / hybrid)
grant_types_supported           (authorization_code / refresh / device_code / client_credentials)
code_challenge_methods_supported (S256 / plain)
scopes_supported
```

### Phase 2 — Authorization Code Flow チェックリスト

| 観点 | 試験 |
|---|---|
| redirect_uri 検証 | 完全一致か / 前方一致 / regex / open redirect 混在 |
| state | 必須か / 検証されるか / 推測困難か |
| nonce (OIDC) | id_token に含まれ replay 防止に使われるか |
| PKCE | S256 強制か、plain も許すか |
| code 単一使用 | 同 code 二度交換できるか |
| code 失効 | 数秒〜数分の TTL か |
| client_secret | confidential client で必須化されているか |
| code_verifier | server 側で 1 回限り検証か |
| iss / aud (id_token) | 検証されるか |
| token endpoint auth | basic / post / mtls / private_key_jwt のどれか |

### Phase 3 — Implicit Flow

modern では deprecated。出てきたら指摘:

- `response_type=token` / `id_token token` で fragment 漏洩
- referer / browser history / proxy log に access token 残る
- `nonce` が無いと replay 容易

### Phase 4 — Device Authorization Flow

```
1. user_code が短すぎる (< 8 chars) と brute force 可能
2. polling 期間に他者が authorize すると user code が漏れる
3. device_code が長期 (30 分以上) で再利用可能 → poisoning 余地
```

### Phase 5 — Client Credentials

```
- client_secret の長さと entropy
- secret rotation 仕組み
- IP 制限 / mtls の有無
- 過剰 scope (admin / read+write 全付与)
```

### Phase 6 — Refresh Token

```
- rotation 有 / 無
- absolute lifetime (例: 30 日上限)
- detect reuse → revoke chain
- bind to client / device (DPoP / mTLS) されているか
- localStorage / sessionStorage / cookie のどこに保存
```

### Phase 7 — Scope / consent

```
- consent screen が scope を曖昧表記していないか
- silent consent (prompt=none) で過剰 scope が付与されないか
- incremental authorization のサポート
- offline_access / openid / profile / email の最小範囲
```

### Phase 8 — Token introspection / revocation

```
- introspection endpoint の認証 (Bearer / Basic / mtls)
- revocation endpoint の認証
- revoke 後の token が他リソースで失効するか (即時 vs cache)
```

### Phase 9 — Cross-flow 連鎖

| chain | 結果 |
|---|---|
| open redirect + 緩い redirect_uri | code を attacker に流せる |
| CSRF (state 無) + cookie 認証維持 | victim のアプリが attacker の code を消費 |
| weak nonce + id_token replay | 古い id_token を再利用 |
| PKCE 無 + public client + 同一 device 上の悪意 app | code を傍受して交換 |

### Phase 10 — レポート

| 観点 | 評価 (Pass/Fail/Concern) |
|---|---|
| redirect_uri 完全一致 | |
| state 必須・検証 | |
| nonce 必須・検証 | |
| PKCE S256 強制 | |
| code 単一使用 | |
| token endpoint 認証 | |
| refresh rotation | |
| consent UX | |
| introspection / revocation 認証 | |

## Tools

```
burp + OAuth/OIDC extension
oauthtester
mitmproxy
authlib (検証実装の比較用)
WebFetch
Bash (sandbox)
```

## Related Skills

- `detection-web`
- `testing-jwt-token-security`
- `web-pentester`, `api-security`, `authentication`
- `client-side` (CSRF flow), `server-side` (open redirect)

## Rules

1. **スコープ厳守** — third-party IdP は別 scope。internal SSO のみ試験
2. **PoC 最小** — 1 chain での乗取確認で停止
3. **token 取扱** — log / report に access / refresh token を生で出さない
4. **修正提案を含めて報告** — どの設定をどう変えれば止まるかを spec 引用付で書く
