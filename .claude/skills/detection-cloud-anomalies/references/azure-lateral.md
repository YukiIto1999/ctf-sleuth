
# Azure Lateral Movement Detection

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- Entra ID / Azure subscription 内で侵害が確認され、横展開の追跡が必要
- service principal abuse / golden SAML / cross-tenant guest pivot の調査
- Conditional Access bypass 後の動きを log で再構成

**使わない場面**: 単発 sign-in 異常のみ（→ `detection-cloud-anomalies`、`detection-web`）。

## Approach / Workflow

### Phase 1 — log source

```
SigninLogs, NonInteractiveUserSignInLogs, ServicePrincipalSignInLogs
AuditLogs (Entra)
AzureActivity (subscription level)
MicrosoftGraphActivityLogs (Graph 経由 API)
RiskDetections / RiskyUsers / RiskyServicePrincipals
```

### Phase 2 — 横展開 pattern

```
1. compromised user の token で Graph API を呼び他 user / app の情報取得
2. service principal credential / secret 追加 (Add password to application)
3. directory role 付与 (Privileged Role Administrator / Global Administrator)
4. cross-tenant access (B2B guest) を悪用した別 tenant への pivot
5. Conditional Access policy 改竄 (block を allow に)
6. Azure subscription role assignment 追加
7. Exchange / SharePoint admin role 取得 → mailbox 列挙
```

### Phase 3 — KQL hunting

#### service principal credential 追加

```kql
AuditLogs
| where OperationName has "Update application – Certificates and secrets management"
    or OperationName == "Add service principal credentials"
| project TimeGenerated, InitiatedBy, TargetResources
```

#### 高権限 role 付与

```kql
AuditLogs
| where OperationName == "Add member to role"
| extend RoleName = tostring(parse_json(TargetResources)[1].displayName)
| where RoleName in ("Global Administrator", "Privileged Role Administrator", "User Administrator", "Application Administrator", "Cloud Application Administrator")
```

#### token reuse / 異常 IP

```kql
SigninLogs
| where TimeGenerated > ago(1d)
| extend tokenIssuerType = tostring(TokenIssuerType)
| summarize Countries = make_set(tostring(LocationDetails.countryOrRegion)) by UserPrincipalName
| where array_length(Countries) > 2
```

#### B2B guest pivot

```kql
SigninLogs
| where ResourceTenantId != HomeTenantId
| project TimeGenerated, UserPrincipalName, ResourceDisplayName, ResourceTenantId, IPAddress
```

#### Graph API 大量呼出

```kql
MicrosoftGraphActivityLogs
| summarize Count = count() by SignInActivityId, UserId, AppId
| where Count > 500
```

### Phase 4 — Conditional Access 改竄

```kql
AuditLogs
| where OperationName has "Update conditional access policy"
| project TimeGenerated, InitiatedBy, TargetResources, Result
```

policy が disable / 範囲縮小されたら critical。

### Phase 5 — subscription level 操作

```kql
AzureActivity
| where OperationNameValue startswith "MICROSOFT.AUTHORIZATION"
| project TimeGenerated, OperationNameValue, Caller, ResourceGroup
```

`/ROLEASSIGNMENTS/WRITE` で Owner / Contributor 付与は要警戒。

### Phase 6 — 攻撃 chain 再構成

```
時刻       event                                     actor
HH:MM:SS   sign-in (impossible travel risk High)      compromised-user
HH:MM:SS   add service principal credential          → app-X
HH:MM:SS   sign-in as service principal app-X (ROPC) app-X
HH:MM:SS   add role assignment Global Admin          app-X
HH:MM:SS   read all mailboxes via Graph              app-X
HH:MM:SS   B2B guest accept on victim tenant         app-X
HH:MM:SS   sign-in to other tenant resources         guest user
```

### Phase 7 — 応答

```
1. compromised user / SP の session revoke
2. 追加された credential / secret の削除
3. 不審 role assignment 取消し
4. Conditional Access policy 巻き戻し
5. cross-tenant access settings 縮小
6. directory roles の audit
```

### Phase 8 — レポート

```
- 期間 / 関与 user / SP / app
- 攻撃 chain (MITRE ATT&CK Cloud)
- 影響範囲 (mailbox / file / 他 tenant resource)
- 残存リスク
- 推奨対応 (Conditional Access / risk policy / app consent)
```

## Tools

```
Microsoft Sentinel / Log Analytics (KQL)
Microsoft Graph (PowerShell)
ROADtools / AADInternals (read-only audit)
WebFetch
Bash (sandbox)
```
