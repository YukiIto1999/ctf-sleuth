---
name: osint
description: 公開情報のみを使った調査。URL / domain / IP / email / username / 自由テキストを対象に、source の信頼度を評価しながら反復探索する。osint_investigation BC のメイン skill。
category: osint
tags:
  - osint
  - public-source
  - search
  - pivot
  - reconnaissance
---

# OSINT (Open-Source Intelligence)

## When to Use

- osint_investigation BC が target を分析する
- bug bounty / pentest / SE / DFIR の前段で公開情報だけで広げる
- CTF OSINT 系問題

**使わない場面**: 攻撃面の active scan (→ `reconnaissance`、`web-pentester`)、認証ありの非公開ソース (→ scope 違反)。

## Approach / Workflow

### Phase 1 — target 種別ごとの基本情報

| target | 入手先 |
|---|---|
| URL | HTTP header / TLS cert / robots / sitemap / Wayback |
| domain | WHOIS / DNS / crt.sh / DNSSEC / passive DNS |
| IP | rDNS / ASN / Shodan / Censys / FOFA / 地理 |
| email | header / haveibeenpwned / DMARC / DKIM / SPF / 漏洩 DB |
| username | Sherlock 風 cross-platform / コミット / 投稿 |
| 自由テキスト | 検索 (Google / 多言語) / 日付 / 専門用語 / 引用先 |
| 画像 | exif / TinEye / Yandex / Google Lens / 背景判定 |
| 動画 | フレーム抽出 → 画像 OSINT / 字幕 / 影 / 看板 |

### Phase 2 — passive (active 通信なし) を優先

```
WebFetch でアーカイブ / 公開 page 確認
WebSearch で公開情報を集める
crt.sh, archive.org, archive.today
Wayback CDX api で過去 snapshot を時系列に
```

直接 server に試験リクエストを投げない。

### Phase 3 — pivot 戦略

```
URL    → ホスト → ASN → 関連 host
domain → reg-info → registrant の他 domain
IP     → 同 ASN / 同 cert / 同 fingerprint の他 host
email  → 名 / 関連 SNS / 漏洩 DB
username → 別 platform の同 handle
text   → 引用元 / 関連 entity / 言語別 search
画像   → 場所 / 撮影機器 / 同 image の他出現
```

複数 source で cross-check。1 source 一致は推測、3 以上一致で「裏が取れた」感覚。

### Phase 4 — domain 系の重点

```bash
# DNS
dig target.com any
dig +short ns target.com / mx target.com / txt target.com / soa target.com
dig +short -x <ip>

# WHOIS / RDAP
whois target.com
rdap target.com

# Cert transparency
curl -s "https://crt.sh/?q=%25.target.com&output=json" | jq

# passive DNS / archive
- securitytrails / dnsdb / virustotal pdns (有料)
- archive.org / Wayback CDX
```

詳細は `phishing-investigation`。

### Phase 5 — email / phishing 起源

`phishing-investigation` の手順。Received chain で 真の送信元 IP を特定。

### Phase 6 — 認知 / 信頼度評価

source ごとに:

```
- primary (公的記録 / 一次情報 / 公式 announcement)
- secondary (報道 / 引用)
- tertiary (個人ブログ / SNS post)
- 矛盾 / 整合性
- 古い情報 (timestamp 確認、リンク切れ)
```

### Phase 7 — 倫理 / 法的境界

```
- 公開情報のみ
- 認証 bypass / 不正 API 利用は OSINT の範疇外
- 個人 (人物) の OSINT は慎重: 直接接触禁止 / 公開された情報のみ / privacy 配慮
- 商業 DB (LeakSearch / Dehashed 等) の利用は契約 / 国内法を確認
```

### Phase 8 — レポート

```
- target / kind
- 取得情報 (source 別)
- 整合性 / 矛盾点
- 推奨 next step
- 信頼度 (info / low / medium / high / critical)
```

## Tools

```
WebFetch / WebSearch
crt.sh / Wayback CDX / archive.today
Sherlock / Maigret / WhatsMyName (username)
holehe / haveibeenpwned (email)
Shodan / Censys / FOFA (IP / cert / banner)
exiftool / TinEye / Google Lens (image)
ROVer / SpiderFoot / theHarvester (集約)
Bash (sandbox)
```

## Related Skills

- `reconnaissance`, `techstack-identification`, `github-workflow`, `social-engineering`
- `threat-intel`, `phishing-investigation`, `threat-intel`
- `phishing-investigation`, `ioc-hunting`
- `bug-bounter`, `web-bounty`, `red-teamer`
- `essential-tools`

## Rules

1. **public source only**
2. **法令 / privacy** — 個人調査は必要最小限
3. **対人接触禁止** — target が人物のとき
4. **redaction** — 共有 report で個人情報を mask
