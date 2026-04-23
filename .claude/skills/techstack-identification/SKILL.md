---
name: techstack-identification
description: OSINT で対象組織 / 対象 host の technology stack (web framework / language / cloud provider / lib version / SaaS) を identify する。pentest / bug bounty / OSINT で発火。
category: pentest
tags:
  - techstack
  - fingerprint
  - whatweb
  - wappalyzer
  - osint
  - reconnaissance
---

# Tech Stack Identification

## When to Use

- 対象 organization / host の使用技術を網羅的に把握
- pentest 開始時の inventory
- bug bounty で affected stack 全体を調査

**使わない場面**: 既に source code が手に入っている場合 (→ `source-code-scanning`)、内部 system のみ (→ `infrastructure`)。

## Approach / Workflow

### Phase 1 — passive (active 通信なし)

```
- BuiltWith / Wappalyzer (browser plugin) で web stack
- Wayback で過去 stack 変化
- LinkedIn / Glassdoor で job posting (使用技術の hint)
- GitHub org の repo / topic (Python / Go / Rust / Kotlin etc)
- conference talk / 公開資料
```

### Phase 2 — HTTP fingerprint

```bash
curl -sI https://target.com/                # Server / X-Powered-By header
whatweb -a 4 https://target.com
wappalyzer-cli https://target.com
nuclei -u https://target.com -t technologies/
httpx -title -status-code -tech-detect -u target.com
```

主要 fingerprint:

```
Server: nginx / Apache / IIS / Caddy / cloudflare
X-Powered-By: PHP/X.Y / Express / ASP.NET
Set-Cookie 名: laravel_session / JSESSIONID / PHPSESSID / connect.sid / __RequestVerificationToken / sails.sid
favicon hash (favicon.ico の MMH3 hash) → Shodan / fofa で同 stack 検索
HTTP error page の固有文字列
robots.txt / sitemap.xml の path 構成
HTML meta generator
JS bundle 名 / chunk hash (webpack / vite)
```

### Phase 3 — JS / SPA framework

```
- React / Vue / Angular / Svelte / Next.js / Nuxt / SvelteKit
- TypeScript / Babel transpile
- mjs / esm module
- service worker (PWA)
- SDK script (Stripe / Sentry / GA / hotjar / Datadog / OneSignal / FullStory)
```

JS source map (`.map`) が公開されていれば 元 source / file 構造が暴露される。

### Phase 4 — cloud provider / SaaS

```
- DNS CNAME に *.cloudfront.net / *.azureedge.net / *.akamaiedge.net / *.fastly.net
- CDN cookies / header (CF-RAY / X-Amz-Cf-Id / X-Azure-Ref)
- mail (MX) → Google / Office 365 / Mimecast / Sendgrid / Mailgun
- SSO (login URL) → Auth0 / Okta / OneLogin / Microsoft Entra
- payment → Stripe / Braintree / Square
- chat → Intercom / Drift / Zendesk
- CMS → WordPress (`/wp-admin`) / Drupal / Contentful / Sanity
- CRM → HubSpot / Salesforce / Pardot script
```

### Phase 5 — version fingerprint

```
- specific JS lib version (jquery-3.5.1.min.js)
- CSS framework (bootstrap, tailwind)
- WordPress plugin / theme version
- Drupal core version
- Apache / Nginx version (Server header)
- TLS extension fingerprint (JA3 / JA3S)
- Shodan / Censys 横断検索で 同 stack の他 host を発見
```

### Phase 6 — vulnerable version の絞り込み

stack identification → `cve-exploitation` で affected CVE を確認:

```
- jquery-1.x → XSS sink 多数
- WordPress < N → file disclosure / RCE
- Drupal < 7.X → CVE-2018-7600 (Drupalgeddon2)
- Apache 2.4.x → CVE-2021-41773 / 42013
- Nginx 1.x.x → CVE 系
```

### Phase 7 — レポート

```
- 対象 / 取得方法
- web stack inventory (server / framework / lib / cloud / SaaS)
- version 一覧
- 既知 CVE 候補 (cve-exploitation 連携)
- 推奨 (version upgrade / config 縮小)
```

## Tools

```
whatweb / wappalyzer-cli / nuclei / httpx
favicon hash tool (favicon.py / fofa）
shodan / censys / fofa / quake
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `reconnaissance`, `osint`, `github-workflow`
- `web-pentester`, `api-security`, `bug-bounter`, `web-bounty`, `hackerone`
- `cve-exploitation`
- `red-teamer`, `system`, `infrastructure`, `hackthebox`
- `essential-tools`

## Rules

1. **passive 優先 → active 確認** — scope ない host への scan を避ける
2. **rate / 帯域**
3. **取得情報** — sealed area
4. **誤検知耐性** — header spoofing による偽情報を疑う
