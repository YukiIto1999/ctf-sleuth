---
name: threat-intel
description: 戦略 / 運用 / 戦術レベルの cyber threat intelligence を統合運用する。TI feed (MISP / OTX / abuse.ch / VT / Mandiant) の取得・正規化、APT actor TTP の MITRE ATT&CK Navigator 可視化、attribution evidence の系統評価、戦略 / 運用 / 戦術レポート生成までを扱う。CTF DFIR / TI 開発で発火。variant 別の深掘りは references/ 参照
category: intel
tags:
  - threat-intel
  - feed
  - mitre
  - attribution
  - reports
  - misp
  - otx
---

# Threat Intelligence

## When to Use

- 既存 TI feed を運用 / 評価
- 自社 SIEM / FW / EDR への投入
- attribution / hunting の補助
- TI feed の信頼度 / overlap / coverage の比較

**使わない場面**: 個別の IOC 抽出 / 自動 enrichment / yara hunting (→ `ioc-hunting`)、phishing 単独調査 (→ `phishing-investigation`)。

variant 別の深掘りは references/ を参照: 戦略 / 運用 / 戦術レベルの TI report 生成 = `references/reports.md`、APT actor TTP の MITRE ATT&CK Navigator 可視化 = `references/mitre-navigator.md`、攻撃 campaign の actor 帰属 evidence の多面評価 = `references/attribution.md`。

## Approach / Workflow

### Phase 1 — feed 種別

```
OSS / 公開:
  abuse.ch (URLhaus / SSLBL / ThreatFox / MalwareBazaar / Feodo Tracker)
  AlienVault OTX
  CISA Joint Advisories (AAs / Alert)
  US-CERT / JPCERT / 各国 CERT
  Microsoft / Google / Cisco Talos blog
  TLP:WHITE な MISP communities

商用:
  Mandiant / Crowdstrike / RecordedFuture / Anomali / Intel 471 / Group-IB / Kaspersky / Trend / Symantec

政府 / クラブ:
  ISAC (FS-ISAC / H-ISAC / Auto-ISAC)
  CTI sharing forum (TLP:RED / AMBER)
```

### Phase 2 — 取得 / format

```
JSON (REST API / TAXII)
STIX 2.x (TAXII server)
MISP event JSON
CSV / TSV
RSS / Atom (blog)
yaml (sigma / yara)
```

```bash
# MISP feed の例
curl -H 'Authorization: <key>' https://misp.example/feeds/getEvent/<event_id>

# OTX
curl 'https://otx.alienvault.com/api/v1/pulses/subscribed' -H 'X-OTX-API-KEY: <key>'

# abuse.ch URLhaus
curl 'https://urlhaus-api.abuse.ch/v1/urls/recent/'
```

### Phase 3 — 正規化 (STIX / common schema)

複数 feed の indicator を共通 schema に:

```
type:          ipv4-addr / domain-name / url / file:hashes.SHA256 / email-addr / etc
value:
first_seen / last_seen
labels (TLP / kill-chain phase / actor)
source / confidence
related (相互参照)
```

opencti / MISP は STIX 2.1 を中で扱う。自前なら ECS-like schema に変換。

### Phase 4 — TI feed 評価軸

```
- coverage: actor / family / region / industry の網羅
- timeliness: indicator 発生から feed 反映までの遅延
- accuracy: false positive 率
- enrichment: context (TTP / actor / kill-chain phase)
- overlap: 他 feed との重複 (高 overlap は redundant)
- format: 自社 SIEM に投入可能か
- license: 商用利用 / 共有制限
```

### Phase 5 — SIEM / FW 連携

```
- SIEM (Splunk / Elastic / Sentinel) に lookup table として投入
- FW (Cisco / Palo / Fortinet / pfSense) の dynamic blocklist
- DNS (RPZ / Pi-hole / response policy)
- email gateway の hash / sender block
- EDR の indicator import
```

```
EventStore = SIEM
Blocklist = FW / DNS / proxy
Honeypot tracker / TI consumer
```

### Phase 6 — sharing / TLP

```
TLP:CLEAR (WHITE)  公開可
TLP:GREEN          community / partner OK
TLP:AMBER          organization 内のみ + 限定的 partner
TLP:AMBER+STRICT   組織内のみ
TLP:RED            named recipient のみ
```

引用 / 再頒布時に TLP color を尊重。

### Phase 7 — overlap / dedup

```python
# 複数 feed の indicator を sha256 hash でグループ化し source カウント
df = pd.read_csv('all-feeds.csv')
df.groupby('indicator')['source'].nunique().sort_values(ascending=False).head()
# 多 source 一致 = 高 confidence
```

### Phase 8 — レポート / 運用

```
- 評価対象 feed と weight
- coverage / timeliness / accuracy 一覧
- 自社 SIEM への 投入経路
- 推奨 (feed 追加 / 削除 / 重み調整)
- 統合 indicator の dedup 結果
```

## Tools

```
MISP / OpenCTI / TheHive (TI platform)
TAXII client (cabby / taxii2-client)
abuse.ch / OTX / VT / IntelMQ
splunk / elastic / sentinel (consumer 側)
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `ioc-hunting` (IOC 抽出 / enrichment / yara)
- `phishing-investigation` (phishing email / CT log)
- `osint`, `dfir`, `blue-teamer`

## Rules

1. **TLP 尊重**
2. **license / 商用利用条件** — 商用 feed の再頒布禁止条項を確認
3. **誤検知耐性** — 1 source の indicator は信頼度低
4. **継続更新** — feed 内の old IOC は週単位で revalidate
