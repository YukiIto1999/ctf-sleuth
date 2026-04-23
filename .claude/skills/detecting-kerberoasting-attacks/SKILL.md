---
name: detecting-kerberoasting-attacks
description: Kerberoasting (TGS-REP 大量要求 / RC4-HMAC 強制 / SPN 列挙) を Windows event log + Sysmon + EDR で検出する。`system` の defense 視点。
category: dfir
tags:
  - kerberoasting
  - detection
  - event-4769
  - rc4-hmac
  - sigma
  - blue-team
---

# Kerberoasting Detection

## When to Use

- 自社 AD 環境で Kerberoasting の可能性を継続監視
- compromise 疑い時の triage で TGS request の異常確認
- detection rule (Sigma / KQL / SPL) の改善

**使わない場面**: 攻撃側 (→ `system`)。

## Approach / Workflow

### Phase 1 — log source

```
Domain Controller の Security Event Log:
  4769  TGS Service Ticket Requested
        - Service Name: 対象 SPN
        - Account Name: 要求者
        - Ticket Encryption Type: 0x12 (AES-256) / 0x11 (AES-128) / 0x17 (RC4-HMAC) / 0x18 (RC4-HMAC-OLD)
        - Failure Code

  4768  TGT Requested (related)
  4624  Logon
  4625  Logon Failure
```

Sysmon EID 1 (process) / EID 11 (file) で Rubeus / GetUserSPNs / PowerView の起動 binary 監視も併用。

### Phase 2 — 検出 signature

```
1. 短時間に 多 SPN への TGS request (1 user → 5+ unique SPN / 5 min)
2. RC4-HMAC encryption type の TGS request (modern AD は AES default)
   - 攻撃者が opsec で specifying RC4 を要求するケースあり
3. service account の logon が 異常 host から発生
4. Targeted Kerberoasting:
   - 4738 (user account changed) で servicePrincipalName 設定
   - その後すぐ 4769 で対応 TGS 要求
   - 直後 servicePrincipalName 削除
5. PowerShell / cmd line に GetUserSPNs / Rubeus / kerberoast keyword
```

### Phase 3 — Sigma rule 例

```yaml
title: Kerberoasting via Multiple TGS-REP
description: User requesting multiple service tickets in a short window
status: experimental
logsource:
  product: windows
  service: security
detection:
  selection:
    EventID: 4769
    TicketEncryptionType:
      - '0x17'   # RC4-HMAC
      - '0x18'   # RC4-HMAC-OLD
    ServiceName|endswith: '$'
  filter:
    AccountName|endswith: '$'   # exclude machine accounts
  condition: selection and not filter
falsepositives:
  - legitimate Kerberos service usage in legacy environments
level: medium
```

### Phase 4 — KQL (Sentinel)

```kql
SecurityEvent
| where EventID == 4769
| where TicketEncryptionType in ("0x17", "0x18")
| extend Service = tostring(parse_json(EventData).ServiceName)
| extend Account = tostring(parse_json(EventData).TargetUserName)
| summarize UniqueServices = make_set(Service), Count = count() by Account, bin(TimeGenerated, 5m)
| where array_length(UniqueServices) > 5
```

### Phase 5 — Splunk (SPL)

```spl
index=wineventlog EventCode=4769
| eval ticket_etype=case(ticket_options="0x17", "RC4", ticket_options="0x18", "RC4_OLD", true(), "Other")
| where ticket_etype="RC4" OR ticket_etype="RC4_OLD"
| stats dc(Service_Name) as svc_count values(Service_Name) as svcs by Account_Name _time=bin(_time, 5m)
| where svc_count > 5
```

### Phase 6 — 補助検出

```
- Sysmon EID 1: cmd / pwsh で 'rubeus', 'kerberoast', 'GetUserSPNs', 'AddCmd' keyword
- EDR: Rubeus / Mimikatz binary signature
- AMSI hit (PowerShell でイミュータブルな obfuscation)
- LDAP query 4662: serviceprincipalname 属性参照 spike
```

### Phase 7 — false positive

```
- 古い software (legacy SQL / SCCM) の RC4 対応
- 大規模 deploy 直後の自動 service 再ログイン
- security scanner / inventory tool
- migration window
```

allowlist + 時間 window で抑制。

### Phase 8 — 応答

```
1. 該当 user の session revoke + password reset
2. 関連 service account の password rotation
3. RC4 encryption の disable (msDS-SupportedEncryptionTypes)
4. service account を gMSA に migrate
5. detection rule 強化 + alert tuning
```

### Phase 9 — レポート

```
- 期間 / 検出 event 数
- 関与 user / service / host
- crack 兆候 (offline / online)
- 影響評価
- 推奨 (gMSA / AES-only / detection rule / hardening)
```

## Tools

```
Sentinel / Splunk / OpenSearch (KQL/SPL)
Sysmon
WEC / WEF (Windows Event Collector)
sigma converter
WebFetch
Bash (sandbox)
```

## Related Skills

- `system`, `memory-analysis`
- `dfir`, `blue-teamer`
- `disk-forensics` (mixed env)

## Rules

1. **誤検知耐性** — 大規模 deploy / migration 期間は allowlist
2. **PII redaction**
3. **継続監視** — 1 回検出で終わらない
4. **integrity / timezone**
