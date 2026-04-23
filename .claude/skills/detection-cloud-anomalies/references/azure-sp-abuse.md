
# Azure Service Principal Abuse Detection

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- service principal (app registration の identity) が compromise された / されかけた疑い
- 第三者 enterprise app が admin consent を取って敏感 scope を持っている
- non-interactive sign-in が高頻度になり baseline から外れる

**使わない場面**: user identity の sign-in 異常（→ `detection-cloud-anomalies`、`detection-web`）。

## Approach / Workflow

### Phase 1 — log source

```
ServicePrincipalSignInLogs       (interactive 不可 SP の sign-in)
NonInteractiveUserSignInLogs     (refresh token / device code 等)
AuditLogs                         (Add password to application 等)
MicrosoftGraphActivityLogs       (Graph 経由の API call)
RiskyServicePrincipals
```

### Phase 2 — シグナル

```
- service principal credential 追加 (Add password / certificate)
- application permission 追加 (.Read.All / .ReadWrite.All / Mail.Send)
- admin consent grant 大量
- 通常使わない resource (Mail / Files / People) への access
- 通常 region と異なる ASN / country からの sign-in
- ROPC (Resource Owner Password Credentials) flow の使用 (deprecated だが攻撃に使われる)
- Graph API 連発
- 同 SP が複数 tenant で活動
```

### Phase 3 — KQL hunting

#### credential 追加

```kql
AuditLogs
| where OperationName in ("Add service principal credentials","Update application – Certificates and secrets management")
| project TimeGenerated, InitiatedBy, TargetResources
```

#### admin consent

```kql
AuditLogs
| where OperationName == "Consent to application"
| extend AppId = tostring(parse_json(TargetResources)[0].id)
| extend Scope = tostring(parse_json(parse_json(TargetResources)[0].modifiedProperties)[0].newValue)
| where Scope has_any (".ReadWrite.All", ".Read.All", "Mail.Send", "offline_access", "Directory")
```

#### SP sign-in 異常

```kql
AADServicePrincipalSignInLogs
| where TimeGenerated > ago(1d)
| extend Country = tostring(LocationDetails.countryOrRegion)
| summarize Countries = make_set(Country), Count = count() by ServicePrincipalName
| where array_length(Countries) > 1 and Count > 100
```

#### Graph API 大量

```kql
MicrosoftGraphActivityLogs
| where AppId == "<sp-app-id>"
| summarize Count = count() by RequestUri, bin(TimeGenerated, 5min)
| where Count > 100
```

#### ROPC 使用

```kql
SigninLogs
| where AuthenticationProtocol == "ropc"
```

### Phase 4 — リスクスコアリング

```
publisher unverified                    +3
.ReadWrite.All / Mail.Send             +3
short-lived secret 直後の大量 API call +3
複数 tenant で同 app_id                +2
ROPC 使用                               +2
admin consent から 24h 以内に高頻度    +2
ASN 異常 (eg コンシューマ ISP)         +2
```

### Phase 5 — 応答

```
1. SP の sign-in 即時 disable (Microsoft Graph: PATCH /servicePrincipals/{id} { accountEnabled: false })
2. credential / secret 全削除
3. role assignment / app role 付与の rollback
4. 関連 token revoke
5. enterprise app 経由の consent 取消し (DELETE /oauth2PermissionGrants)
6. publisher policy 強化 (verified publisher 必須化)
```

### Phase 6 — 予防

```
- admin consent workflow (high-risk scope は管理者承認)
- "verified publisher" 必須化
- Conditional Access for Workload Identities
- secret rotation 自動化 / certificate-based 認証推奨
- managed identity の活用 (secret 不要)
```

### Phase 7 — レポート

```
- 該当 SP の app_id / display_name / publisher
- credential 追加履歴
- 取得 scope と発火した API
- 関与 IP / ASN / country
- 影響 (mailbox / file / role)
- 推奨対応 (上記 Phase 5 + 予防)
```

## Tools

```
Microsoft Graph PowerShell
Sentinel KQL
ROADtools / AzureHound (read-only audit)
WebFetch
Bash (sandbox)
```
