
# Certificate Transparency for Phishing Detection

`phishing-investigation` から呼ばれる variant 別 deep dive

## When to Use

- 自社 brand を装う phishing domain の早期検出
- CT log 経由の subdomain enumeration
- attacker infrastructure の発見 (cert reuse / 同 issuer pattern)

**使わない場面**: 公式 cert の構成評価 (→ `performing-ssl-tls-security-assessment`)、attacker rev (→ `reverse-engineering`)。

## Approach / Workflow

### Phase 1 — CT log の概要

CT は cert を発行する CA が公開 log に append する仕組み。RFC 6962 / 9162。Google / Cloudflare / DigiCert などが log server を運営。

```
- 発行された全 cert の record (subject / issuer / SAN / not_before / not_after / log entry id)
- 数十億 entry の追記専用 log
- live tail (Certstream) と historical search (crt.sh) の双方が利用可
```

### Phase 2 — crt.sh で historical search

```bash
# brand を含む全 cert
curl -s "https://crt.sh/?q=%25mybrand%25&output=json" | jq -r '.[] | [.id, .name_value] | @tsv'

# 特定 domain の subdomain enumeration
curl -s "https://crt.sh/?q=%25.target.com&output=json" | jq -r '.[].name_value' | sort -u

# wildcard search
curl -s "https://crt.sh/?q=%25paypa%25&output=json" | jq -r '.[].name_value' | sort -u
```

### Phase 3 — Certstream で live monitor

```python
import certstream
def callback(message, context):
    if message['message_type'] == "certificate_update":
        for d in message['data']['leaf_cert']['all_domains']:
            if 'mybrand' in d.lower():
                print(d, message['data']['source']['url'])
certstream.listen_for_events(callback, url='wss://certstream.calidog.io/')
```

WebSocket 経由で realtime stream。typosquat alert system に組込み。

### Phase 4 — typosquat / homograph 検出

候補 domain を生成し CT log で 既発行 cert を確認:

```
dnstwist mybrand.com                # 多 variant 生成 (homograph / addition / removal / replacement)
URLcrazy / catphish 系
```

```python
import dnstwist
results = dnstwist.run(domain='mybrand.com', whois=False, format='csv')
# 各 variant について crt.sh query
```

### Phase 5 — pattern 検出

```
- 同一 cert (同 SAN list) で 複数 brand の組合せ → mass phishing kit
- short-lived cert (Let's Encrypt: 90 days) で頻繁 rotation → phishing
- subject CN が IP / 自己署名 → phishing よりは internal infra
- specific issuer (Sectigo / Let's Encrypt / ZeroSSL / Buypass) の偏り
```

### Phase 6 — 関連 indicator 抽出

検出 domain について:

```
- DNS resolve → IP / ASN
- Wayback で過去 page
- Shodan / Censys で同 fingerprint host
- VT / urlscan で過去観測
- Whois / RDAP で registrant
```

これら関連 indicator を IOC として TI feed に投入。

### Phase 7 — 自社 brand の防御

```
- cert issuer に CAA record で 限定
- 業者 brand monitoring service (GoDaddy / Group-IB Brand Protection / DigitalShadows)
- DMARC + DNS spoofing 監視
- typosquat domain の事前 register
- 検出時に takedown 申請 (registrar / hosting / CDN)
```

### Phase 8 — レポート / IOC

```
- 期間 / 監視 brand
- 検出 typosquat domain 数
- 関連 IP / ASN / cert issuer
- live phishing site の有無
- takedown 状況
- 推奨 (CAA / monitoring / awareness)
```

## Tools

```
crt.sh / curl / jq
certstream-python (calidog certstream)
dnstwist / urlcrazy / catphish
WebFetch / WebSearch
Bash (sandbox)
```
