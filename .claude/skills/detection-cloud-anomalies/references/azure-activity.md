
# Azure Activity Log Threat Analysis

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- Azure subscription / tenant の侵害が疑われ、control plane 操作を log で再構成
- Entra ID sign-in 異常（impossible travel / risk-based）の調査
- 権限昇格 (role assignment / OAuth consent) 追跡
- 既存の Sentinel / Log Analytics 環境で hunting query 作成

**使わない場面**: Azure resource 自体の侵害 (VM / Storage data plane → `detection-cloud-anomalies` / VM forensics)。

## Approach / Workflow

### Phase 1 — log source の整備

```
Activity Log              control-plane (subscription level)
Microsoft.Resources       resource 操作
Microsoft.Authorization   role assignment / RBAC
Microsoft.Management      management groups
Sign-In Logs              Entra ID 認証イベント
Audit Logs                Entra ID 設定変更
RiskyUsers / RiskyServicePrincipals    Risk Detection
NSG Flow Logs             network
Azure Firewall Logs
```

Diagnostic Settings → Log Analytics workspace に集約し、Sentinel / Microsoft Graph で query。

### Phase 2 — KQL 重点 query

#### impossible travel / sign-in 異常

```kql
SigninLogs
| where TimeGenerated > ago(7d)
| extend Country = tostring(LocationDetails.countryOrRegion)
| summarize Countries = make_set(Country) by UserPrincipalName, bin(TimeGenerated, 1h)
| where array_length(Countries) > 2
```

#### role assignment 改竄

```kql
AzureActivity
| where OperationNameValue == "MICROSOFT.AUTHORIZATION/ROLEASSIGNMENTS/WRITE"
| extend Caller = tostring(parse_json(Authorization).evidence.role)
| where ActivityStatusValue == "Success"
```

#### OAuth consent (Entra)

```kql
AuditLogs
| where OperationName in ("Consent to application", "Add app role assignment grant to user")
| extend AppId = tostring(parse_json(TargetResources)[0].id)
```

#### risky service principal

```kql
AADServicePrincipalSignInLogs
| where ResultType != 0
| summarize FailCount = count() by ServicePrincipalName, IPAddress
| where FailCount > 50
```

### Phase 3 — 攻撃 pattern

```
- Add member to role (Global Administrator / Privileged Role Administrator)
- 同一 user の sign-in が短時間に多 country
- 「sign-in risk」「user risk」が High に上がった後の sensitive 操作
- Conditional Access policy が「Disabled」「Modified」される
- secret rotation / key vault access policy 変更
- diagnostic / lock 削除 (隠蔽兆候)
```

### Phase 4 — actor 追跡

```kql
AzureActivity
| where OperationNameValue startswith "MICROSOFT."
| where Caller == "<suspect_upn>"
| project TimeGenerated, OperationNameValue, ResourceProviderValue, ResourceGroup, ActivityStatusValue
| order by TimeGenerated asc
```

actor の操作 timeline を出し、attacker chain を組み立てる。

### Phase 5 — 関連 sign-in と alert 相関

```
- Risk Detection (atypicalTravel / unfamiliarFeatures / ipAddress)
- Conditional Access が apply / not apply
- MFA satisfied by sign-in
- token issuance type (AzureAD vs ADFS, deviceCode 等)
```

```kql
SigninLogs
| where UserPrincipalName == "<suspect>"
| extend ConditionalAccess = tostring(ConditionalAccessStatus)
| extend Risk = tostring(RiskLevelDuringSignIn)
| project TimeGenerated, IPAddress, AppDisplayName, ResultType, ConditionalAccess, Risk
```

### Phase 6 — 応答

```
1. compromised user の session revoke (Microsoft Graph: revokeSignInSessions)
2. password / MFA 再登録
3. 不審 OAuth app の disable / consent 取消し
4. role assignment 巻き戻し
5. Conditional Access policy 再有効化 / 強化
6. KeyVault secret rotation
```

### Phase 7 — レポート

```
- 期間 / event 件数
- 関与 user / app / IP / country
- 攻撃 chain
- 残存リスク
- 推奨 (Conditional Access / risk policy / app consent policy)
```

## Tools

```
Microsoft Sentinel / Log Analytics (KQL)
Microsoft Graph (PowerShell / curl)
Azure CLI
ROADtools / AADInternals (read-only audit)
WebFetch
Bash (sandbox)
```
