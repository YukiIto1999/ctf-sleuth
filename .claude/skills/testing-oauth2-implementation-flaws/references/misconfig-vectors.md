# OAuth Misconfiguration — 攻撃 Vectors

`testing-oauth2-implementation-flaws` のチェックリストで懸念が見つかった後の deep-dive 攻撃集。

## いつ切替えるか

- 対象が "Sign in with <provider>" 形式の social login / SSO を実装する
- OAuth 2.0 authorization code / implicit / device code / client credentials flow が登場する
- OAuth provider 側 (IdP) のスコープに含まれる、または consumer 側 (RP) の登録設定が攻撃面として与えられる

## Phase 1 — 観察

```
GET /.well-known/openid-configuration              # OIDC のメタ情報一覧
GET /.well-known/oauth-authorization-server        # OAuth 2.0 metadata
authorization endpoint, token endpoint, userinfo endpoint, jwks_uri
登録済 redirect_uri の確認 (UI / 設定画面 / API)
```

flow を見る:

```
authorization request → redirect with code → token exchange → userinfo call
```

各ステップで:

- `state` parameter の有無と検証
- `nonce` (OIDC) の有無と検証
- `code_challenge` / `code_verifier` (PKCE) の有無と検証
- `redirect_uri` の検証ロジック (完全一致 / 前方一致 / regex / open redirect)
- `scope` 要求の妥当性

## Phase 2 — redirect_uri 検証緩和

既知の bypass パターン:

```
登録: https://app.example.com/callback

攻撃 redirect_uri:
  https://app.example.com.attacker.com/callback             # subdomain trick
  https://app.example.com/callback@attacker.com             # userinfo URL
  https://app.example.com/callback?foo=https://attacker.com # query 追加
  https://app.example.com/callback/../../../attacker.com    # path traversal
  https://app.example.com/callback#@attacker.com            # fragment
  http://app.example.com/callback                           # scheme downgrade
  https://app.example.com:443@attacker.com/                 # port + userinfo
```

callback 側で `code` を attacker domain に流せれば、attacker が `token endpoint` で交換してアカウント乗取。

## Phase 3 — state / nonce 欠落 → CSRF

`state` / `nonce` が存在しないか検証されない場合:

```
1. 攻撃者が自分の OAuth flow を開始 (自分の code を取得)
2. その code を victim の browser に注入 (link / iframe / image redirect)
3. victim が clic / load → victim のアプリが attacker の code を交換
4. victim のアプリが「attacker のアカウント」でログイン状態に
   → victim が自分のものと思って機密データを入力
```

逆に provider 側で nonce が抜けていると ID token replay も成立。

## Phase 4 — PKCE 欠落 / 緩和

confidential client (server-side) でも PKCE は理想的に使うべき。public client (mobile / SPA) で PKCE が無いと:

```
1. attacker が同じ network 上で認可 code を盗聴 (proxy / OS バグ / inter-app)
2. token endpoint に交換 (client secret 不要なので攻撃者でも実行可)
3. アカウント乗取
```

`code_challenge_method=plain` を許容する provider は等価に脆弱。

## Phase 5 — scope 過剰 / privilege escalation

```
- 必要以上の scope を要求するアプリ (read だけで足りるのに admin)
- 同意画面で scope を読まずに許可される UX
- response_type=token で access token が URL fragment に出ると、proxy / referer / browser history に漏洩
- response_type=id_token token (hybrid) の組合せで意図しない token 渡し
```

## Phase 6 — token / refresh token 取扱

```
- access token が長期 (60 min 以上) かつ revocation 不可能
- refresh token が rotation しない (一度盗まれると永続)
- token を localStorage / URL に保存
- token replay protection 不在 (jti / dpop / mtls の欠落)
```

## Phase 7 — open redirect 連携

```
authorization endpoint が redirect_uri を緩く許容
+ アプリ自身に open redirect (`/redirect?url=`)
→ flow 内で attacker.com に code を流せる
```

## Phase 8 — provider 側 issue

provider が攻撃面の場合:

```
- token introspection endpoint が認証なしで露出
- discovery endpoint が改ざん可能 (CDN cache poisoning)
- jwks_uri に attacker URL を仕込めれば JWT 鍵置換と同じ
- device code flow の polling で user code を盗む
```

## Phase 9 — PoC

```
1. flow 図 (どの参加者の信頼境界が破られたか)
2. 攻撃 redirect_uri / state / scope の payload
3. アカウント乗取 / scope 過剰実証 (test account 同士)
4. 修正 (redirect_uri 完全一致 / state nonce PKCE 強制 / scope 最小)
```
