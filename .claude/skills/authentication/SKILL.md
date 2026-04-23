---
name: authentication
description: ログイン・トークン・MFA・CAPTCHA・bot 検出を含む認証機構の体系的試験。CTF web の auth bypass 問題、HTB の login portal、bug bounty の認証フローで発火する。
category: web
tags:
  - auth
  - login
  - mfa
  - captcha
  - jwt
  - oauth
  - saml
---

# Authentication

## When to Use

- web アプリの認証境界（login / signup / password reset / MFA / SSO）が攻撃面の中心になる
- 認証 bypass・MFA bypass・CAPTCHA bypass・SAML 詐称などの仮説を検証したい
- JWT / OAuth / OIDC のトークン処理に弱点がありそう
- credential stuffing / brute force の試験を準備する（許可済みスコープに限る）

**使わない場面**: 認証後の API 認可（→ `api-security`）、純粋な session storage XSS（→ `client-side`）、サーバ側 RCE 連鎖（→ `server-side`）。

## Approach / Workflow

### Phase 1 — 認証フロー観察

ログイン・登録・パスワードリセット・トークンリフレッシュ・ログアウトの各 endpoint を `curl -i` で叩いて以下を控える:

- 入力 / 出力フィールドの形
- session cookie / Bearer / refresh token の扱い
- ヘッダ (Set-Cookie の `HttpOnly` / `Secure` / `SameSite`、CSP、HSTS)
- レスポンスの差 (200 / 302 / 401 / 403、エラーメッセージの粒度)

### Phase 2 — bypass 仮説

| 種別 | 試す観点 |
|---|---|
| **デフォルト認証情報** | admin/admin、admin/<service-default> を試す。CVE 由来のデフォルトを確認 |
| **応答改竄** | 401 を 200 に書き換え、エラーフラグを `success: true` に変える proxy 介入 |
| **HTTP method 切替** | POST 限定の login を GET / OPTIONS / HEAD で叩いて挙動差を見る |
| **パラメータ重複 / type confusion** | `username[]=admin`、`password={"$ne":""}` (NoSQL) |
| **logic flaw** | password reset で他ユーザの ID を指定、registration で `role=admin` を渡す |

### Phase 3 — MFA / 2FA

```
1. MFA セットアップフローと検証フローを別個に観察。
2. setup endpoint が pre-auth でアクセス可能なら横取り可能。
3. verify endpoint が rate-limited か、推測ベースで突破可能か。
4. backup code 経路、recovery email 切替経路の取扱を確認。
5. JS 側で MFA が「フロント判定」になっていないか (response 改竄で skip)。
```

### Phase 4 — CAPTCHA / bot 検出

- サーバ側で response token を検証していなければクライアントだけで完結している
- `g-recaptcha-response` の再利用可否
- audio CAPTCHA の OCR / Whisper 経由 bypass
- behavioral 検出は Playwright で人間的タイミング (typing 80-200ms / random pause / mouse move) を再現する

### Phase 5 — JWT / OAuth / SAML

token 系は別 skill で深掘り（`testing-jwt-token-security`、`testing-oauth2-implementation-flaws`、`testing-jwt-token-security`、`testing-jwt-token-security`、`testing-oauth2-implementation-flaws`）。本 skill では:

- token の生成元 / 署名 / kid / nonce を確認
- redirect_uri の allowlist 緩和、`state` / `PKCE` 欠落
- SAML assertion 改竄（XML signature wrapping）が攻撃面に含まれるか調査

### Phase 6 — credential 系

```
hydra -L users.txt -P passwords.txt <target> http-post-form '/login:user=^USER^&pass=^PASS^:F=invalid'
```

許可スコープでのみ。一般的に CTF / bug bounty では low-volume でロジック検証中心、認可済 pentest で量を出す。

### Phase 7 — 確証と PoC

bypass の最小再現と影響（admin 権限、他ユーザアカウント乗っ取り）を 1 ステップで示す。

## Tools

```
curl
hydra / patator / medusa
ffuf
jwt_tool
saml-radar
Playwright (sandbox container 経由)
mitmproxy / burp
WebFetch
Bash (sandbox)
```

## Related Skills

- `web-pentester`, `api-security`, `client-side`, `server-side`, `web-app-logic`
- `testing-jwt-token-security`
- `testing-oauth2-implementation-flaws`, `detection-web`
- `injection`
- `social-engineering` (phishing 化された OAuth consent 系)

## Rules

1. **スコープ厳守** — credential 試験は明示許可されたアカウントのみで実行
2. **アカウントロック回避** — brute force は 1-5 回 / 時を上限とし、ロックポリシ確認後に動かす
3. **MFA bypass の最小実証** — 突破できた事実を示すだけで、それ以上の認可リソースに踏み込まない
4. **トークン取り扱い** — 取得 JWT / OAuth code / SAML assertion を report に生で貼らない
