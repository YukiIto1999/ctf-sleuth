
# IOC Enrichment Automation

`ioc-hunting` から呼ばれる variant 別 deep dive

## When to Use

- 抽出 IOC list を 一括で context 付け (reputation / first seen / family / actor)
- alert triage の補助情報として
- TI feed から IOC を取り込んで自社 environment 適合性確認

**使わない場面**: IOC 自体の抽出 (→ `ioc-hunting`)、TI feed の評価 (→ `threat-intel`)。

## Approach / Workflow

### Phase 1 — input format

```
CSV / TSV:    type,value
JSON / STIX:  structured
TI report (PDF / md):    parse necessary
text dump:    regex で IOC 抽出
```

### Phase 2 — IOC type 別 source

```
IPv4 / IPv6:
  - VirusTotal (vt-cli / vt-py)
  - AbuseIPDB
  - GreyNoise (scanner / benign / malicious)
  - Shodan / Censys (port / banner)
  - AlienVault OTX
  - MISP
  - SpamHaus / SORBS

domain:
  - VT / OTX / urlscan
  - abuse.ch URLhaus / Feodo Tracker / SSLBL
  - threatfox
  - WHOIS (registrant)
  - DNS history (passive DNS: SecurityTrails / DNSDB / VT pdns)
  - certificate transparency (crt.sh)
  - URLhaus host / WHOIS

URL:
  - VT / urlscan / hybridanalysis
  - PhishTank / OpenPhish

file hash:
  - VT (主要)
  - MalwareBazaar (abuse.ch)
  - Hybrid Analysis
  - JoeSandbox / ANY.RUN / 公開 sandbox
  - Mandiant Threat Intelligence
  - SHA-1 / SHA-256 / MD5 / TLSH / ssdeep

email:
  - haveibeenpwned (leak)
  - DKIM history
```

### Phase 3 — 並列 query (Python)

```python
import asyncio, httpx
async def query_vt(client, val):
    r = await client.get(f"https://www.virustotal.com/api/v3/.../{val}",
                          headers={"x-apikey": "..."})
    return r.json()
async def main(iocs):
    async with httpx.AsyncClient() as c:
        tasks = [query_vt(c, ioc) for ioc in iocs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return list(zip(iocs, results))
asyncio.run(main(iocs))
```

rate limit (VT free 4 req/min) を遵守。

### Phase 4 — 集約 schema

```
indicator
  type
  value
  first_seen / last_seen
  reputation (0-100)
  source_count
  related_actors
  related_families
  related_campaigns
  details_per_source: [{source, score, observation, url}]
  context: industry / geography / kill-chain phase
  tlp / confidence
```

### Phase 5 — 自動化 platform

```
MISP / OpenCTI / TheHive
SOAR (XSOAR / Tines / Splunk Phantom / Swimlane)
n8n / Zapier (簡易)
自前 Python script (cron / Lambda)
```

### Phase 6 — false positive / 信頼度評価

```
- 1 source の reputation だけでは判断しない
- 大規模 CDN / cloud IP の hash hit は noise
- TLP / age / source 信頼度を組合せた weighted score
- baseline (自社の正常 traffic) との照合
```

### Phase 7 — SIEM / FW へ feed

```
- threshold で自動 block (high confidence のみ)
- watchlist / rule lookup
- alert 化 (medium confidence)
- review queue (low confidence)
```

### Phase 8 — レポート

```
- 期間 / IOC 件数
- 各 type の enrichment 結果集計
- high-confidence / actor 同定済 IOC リスト
- 推奨対応 (block / monitor / further hunt)
```

## Tools

```
vt-cli / vt-py (VirusTotal)
otx-python (AlienVault)
abuse.ch APIs
shodan-python / censys-python
PassiveTotal / SecurityTrails / DNSDB
WHOIS / RDAP
MISP / OpenCTI / TheHive
WebFetch / WebSearch
Bash (sandbox)
```
