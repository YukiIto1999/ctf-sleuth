---
name: web-bounty
description: web 中心の bug bounty 戦術。低 severity finding の chain / business logic 濫用 / 認可境界破り等で 高 impact bug を狙う。`bug-bounter` の web 特化版。
category: bug-bounty
tags:
  - web-bounty
  - chaining
  - business-logic
  - authorization
  - methodology
---

# Web-focused Bug Bounty

## When to Use

- bug bounty で 高額帯 web bug (P0/P1) を狙う
- 単独では low / medium の finding を chain して critical impact 化
- business-logic / authorization 系の深掘り

**使わない場面**: 単純 OWASP Top 10 hunt (→ `web-pentester` の各 specific skill)、infrastructure / mobile (→ 該当 skill)。

## Approach / Workflow

### Phase 1 — high-value 機能の identification

```
- 認証 / 認可 / 多テナント境界
- 金銭 / 残高 / クーポン / 招待
- file upload / download
- admin / privileged feature
- API の internal endpoint
- 状態を進める endpoint (transfer / approve / publish)
- 第三者連携 (OAuth / SAML / webhook)
- 検索 / report (SQLi / second-order)
```

これらの周辺で chain を作りやすい。

### Phase 2 — chain pattern

```
1. open redirect + 緩い OAuth redirect_uri = code 横取り → アカウント乗取
2. self-XSS + CSRF = stored XSS にする
3. IDOR + privileged feature = 他テナント資源破壊
4. SSRF + cloud metadata = role 取得 → IAM 調査 → 全 bucket 取得
5. cache poisoning + 1st-party domain 信頼 = mass session 取得
6. logout CSRF + login CSRF = victim を attacker のアカウントに login させる → input 盗取
7. format string in error log + log4shell-like = RCE
8. SQL injection + outbound DNS = blind data exfil + AS 同定
9. file upload + path traversal = web shell
10. JSON deserialization + custom format = gadget chain
11. race condition で coupon 多重消費
12. multi-step flow の 1 step skip で free upgrade
```

### Phase 3 — フロー観察 (workflow 異常)

`web-app-logic` の手順:

```
- ユーザフローを 1-2 本辿る
- 観察した object / endpoint で濫用バックログを作る (10-15 件)
- 不変条件を破る試験を順に実行
```

### Phase 4 — 認可境界の精密試験

```
- horizontal IDOR: 別 user の resource ID
- vertical privilege: admin endpoint への試験
- multi-tenant: 別 tenant の リソース ID
- pre-auth / post-auth の差分: 認証無しで叩ける endpoint があれば
- B2B / partner 経路: API key で別 customer 領域参照
```

### Phase 5 — 暗号化 / token chain

```
- JWT alg confusion → admin claim
- OAuth state / nonce 不在 → CSRF + 認証 hijack
- 緩い HMAC signature → 偽造 → 任意 user として API 叩ける
- SAML signature wrapping
- session id 推測可能 → 任意 user impersonate
```

### Phase 6 — race / TOCTOU

```
- 並列 redeem で coupon 多重消費
- transfer の余裕残高 race
- approve の時刻に注意 (single-packet attack)
- 並列 password change で session window 維持
```

### Phase 7 — 公開 secret + active 確認

```
- GitHub leak credential + 該当 service login
- log / debug endpoint 経由 internal IP / config
- old asset の subdomain takeover (CNAME 不在 + cloud reclaim)
```

### Phase 8 — 報告書 (重要)

bug bounty で報酬を最大化するコツ:

```
- impact を生々しく書く (CVSS だけでなく business 影響語る)
- 最小再現手順 (clean account → 5 step 内)
- 1 動画 / GIF (ASCIInema / asciicast)
- root cause を 開発者目線で
- 修正提案を 1 つ書く (時間節約 + report quality)
- 関連 chain を 同 report 内で示す (chained issues は別 report 化しない)
```

## Tools

```
burp + intruder + Param Miner + Backslash Powered Scanner + Hackvertor + Active Scan++
ffuf / nuclei / dalfox / xsstrike / sqlmap / interactsh
mitmproxy
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `bug-bounter`, `hackerone`, `osint`, `reconnaissance`, `techstack-identification`, `github-workflow`
- `web-pentester`, `api-security`, `injection`, `client-side`, `server-side`, `web-app-logic`, `authentication`
- `injection`, `server-side`, `testing-jwt-token-security`, `testing-oauth2-implementation-flaws`, `client-side`
- `cve-exploitation`, `source-code-scanning`
- `essential-tools`, `coordination`, `script-generator`, `patt-fetcher`

## Rules

1. **scope 厳守**
2. **chain は 1 report に**
3. **PII 取扱**
4. **責任ある開示**
5. **rate / 帯域** — production への高頻度 scan 禁止
