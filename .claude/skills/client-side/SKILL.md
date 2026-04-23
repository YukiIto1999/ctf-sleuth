---
name: client-side
description: XSS (reflected / stored / DOM)、CSRF、CORS 緩和、clickjacking、prototype pollution などブラウザ側で発火する脆弱性の体系的試験。CTF web の client-side 系問題、SPA 系 bug bounty で発火する。
category: web
tags:
  - web
  - client-side
  - xss
  - csrf
  - cors
  - clickjacking
  - prototype-pollution
---

# Client-Side Vulnerabilities

## When to Use

- DOM 内に user-controlled な文字列が入る経路がある（reflect / store / fragment / postMessage）
- クッキーベース認証で state 変更操作があり CSRF / SameSite を試す価値がある
- 別オリジンからの fetch が許される CORS 構成の妥当性を評価する
- iframe 経由の clickjacking 検証
- prototype pollution gadget でフロント挙動を歪められないか確認

**使わない場面**: 純粋なサーバ側注入 (→ `injection` / `server-side`)、ネイティブアプリの代替 client (→ `mobile` 系)。

各 variant の深掘りは references/ を参照: XSS 手動 / 汎用ツール = `references/xss-manual.md`、burp Pro 運用 = `references/xss-burp.md`、CSRF 単独深掘り = `references/csrf.md`、CORS 漏洩経路 = `references/cors.md`。

## Approach / Workflow

### Phase 1 — 入力源とシンクの map

入力源（source）:

```
- query / fragment / hash
- form input / textarea
- cookie 値
- localStorage / sessionStorage / IndexedDB
- postMessage data
- WebSocket onmessage
- import_map / 外部 script 読込
```

シンク（sink）:

```
- innerHTML / outerHTML / insertAdjacentHTML
- document.write / write Stream
- eval / Function / setTimeout('string')
- href = "javascript:..."
- React: dangerouslySetInnerHTML
- Vue: v-html
- Angular: bypassSecurityTrust*
```

source → sink のチェーンを 1 本ずつ trace する。frontend が SPA なら `webpack-source-map-explorer` でビルド前の構造を覗く。

### Phase 2 — 文脈別 XSS payload

| context | payload 例 |
|---|---|
| HTML body | `<script>alert(1)</script>` `<img src=x onerror=alert(1)>` |
| HTML attribute (双引用符内) | `" autofocus onfocus=alert(1) x="` |
| HTML attribute (引用符無) | `x onmouseover=alert(1)` |
| JS string (双引用符) | `";alert(1);"` |
| JS template literal | `${alert(1)}` |
| URL context (href / src) | `javascript:alert(1)` |
| CSS context | `expression(alert(1))` (旧 IE) / 一般 web では限定的 |

CSP がある場合は `script-src` の許可元・unsafe-inline / unsafe-eval / hash-nonce を確認し、bypass gadget（JSONP / 古いライブラリ / strict-dynamic with nonce reuse）を探す。Trusted Types が有効なら sink を policy 経由でしか書けない。

### Phase 3 — CSRF

- state 変更 endpoint を列挙（POST / PUT / DELETE）
- CSRF トークン: 形式（per-session / per-request）、検証の有無、Origin / Referer 検証の有無
- SameSite cookie 値: `Lax`/`Strict`/`None`、cross-site GET でも triggered か
- 現代では SameSite=Lax がデフォルトのため、`<form method=POST>` + auto submit はほぼ封じられる。`<a target=_blank>` 経由の top-level navigation で渡す方法、subdomain takeover 経由で同一サイト扱いに持ち込む方法を検討

### Phase 4 — CORS

- `Access-Control-Allow-Origin` が動的反射されているか
- `null` origin が許容されているか（`<iframe sandbox>` から発火）
- `Access-Control-Allow-Credentials: true` と `*` の組合せ可否
- preflight の `Access-Control-Allow-Headers` ワイルドカード

### Phase 5 — clickjacking

`X-Frame-Options` / `Content-Security-Policy: frame-ancestors` 不在で iframe 埋込み可能。被害者操作を仕込む UI overlay PoC を `<iframe sandbox="allow-forms allow-same-origin">` で組み立てる。

### Phase 6 — prototype pollution

- ブラウザ側 sink: `Object.assign({}, JSON.parse(input))`、`lodash.merge` / `lodash.set` パターン、jQuery の deep extend
- gadget: グローバルへの property 注入（`__proto__.<name>` → `Object.prototype.<name>`）から、後段 lib（template lookup、DOMPurify、sanitize-html）の挙動が歪まないか
- サーバ側 prototype pollution は `server-side` skill で扱う

### Phase 7 — PoC

| 種別 | PoC 形式 |
|---|---|
| reflected XSS | URL を貼る + 実行 GIF |
| stored XSS | 投稿 → 別ユーザが閲覧 → cookie / token 奪取 |
| CSRF | 受動 HTML を hosted page に貼る + state 変更を示す |
| CORS | attacker.com から fetch + credentials → response 取得 |
| clickjacking | overlay HTML + 標的の click が発火 |
| prototype pollution | gadget 起動 + 機能改変 |

## Tools

```
curl
ffuf
DOMPurify-bypass-cheatsheet (参照用)
xsser / xsstrike
Burp / mitmproxy (intercept)
Playwright (DOM 検証)
WebFetch
Bash (sandbox)
```

## Related Skills

- `web-pentester`, `web-app-logic`, `api-security`, `server-side`
- `injection` (server side reflection が source の場合)

## Rules

1. **PoC は被害最小** — alert(1) 程度の証明にとどめ、cookie 流出は test account のものに限定
2. **stored XSS は隔離** — 一般ユーザに見える領域には書かない。test profile / sandbox を使う
3. **CSRF 試験を本番で動かさない** — 実機の他ユーザに影響しないよう、test account 同士で示す
4. **トークン秘匿** — 取得した session / CSRF token を report に生で貼らない
