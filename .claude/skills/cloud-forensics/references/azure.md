# Azure Cloud Forensics

`cloud-forensics` の Phase 2 / Phase 5 から呼ばれる、Azure subscription / tenant の侵害解析。Activity Log / Sign-In / Audit Log (Entra ID) / VM snapshot / NSG flow / Key Vault 監査の統合。

## いつ切替えるか

- Azure subscription / Entra ID tenant の侵害解析
- Reader / IR-only credential での post-incident 解析
- compromised user / SP / managed identity の行動再構成

## Phase 1 — IR 体制

```bash
# IR 用 read-only role
# Subscription: Reader + Log Analytics Reader
# Entra ID: Global Reader + Security Reader (audit log 閲覧用)
az login --tenant <TENANT>
az account show
```

evidence 隔離:

```bash
# Activity Log を export (要 Reader 以上)
az monitor activity-log list --start-time <ISO> --end-time <ISO> --output json > activity.json

# Audit log (Entra ID) - Microsoft Graph
az rest --method GET --url "https://graph.microsoft.com/v1.0/auditLogs/directoryAudits?\$filter=activityDateTime ge <ISO>"
az rest --method GET --url "https://graph.microsoft.com/v1.0/auditLogs/signIns?\$filter=createdDateTime ge <ISO>"
```

Sentinel / Log Analytics workspace に集約済なら KQL で取得:

```kusto
AuditLogs | where TimeGenerated between (datetime(...) .. datetime(...))
SigninLogs | where TimeGenerated between (...) | where ResultType != 0
AzureActivity | where TimeGenerated between (...)
```

## Phase 2 — control plane log の triage

| 観点 | KQL / az 例 |
|---|---|
| MFA 未使用 console login | `SigninLogs | where AuthenticationDetails contains "single factor"` |
| consent grant (illicit oauth) | `AuditLogs | where ActivityDisplayName == "Consent to application"` |
| user / role 改竄 | `ActivityDisplayName in ("Add member to role","Add app role assignment grant to user")` |
| service principal 作成 / credential 追加 | `ActivityDisplayName in ("Add service principal","Update application – Certificates and secrets management","Update service principal")` |
| MFA 無効化 / strong auth removal | `ActivityDisplayName == "Remove a strong authentication method"` |
| conditional access 変更 | `ActivityDisplayName contains "conditional access"` |
| 不審 IP からの sign-in | `SigninLogs | summarize count() by IPAddress, UserPrincipalName | order by count_ desc` |

## Phase 3 — VM / Disk snapshot 取得

```bash
# Managed Disk snapshot
az snapshot create --name ir-<host>-<date> --source <disk-id> --resource-group <rg>
az snapshot grant-access --name ir-<host>-<date> --duration-in-seconds 3600 --resource-group <rg>
# 取得した SAS URL から download → IR account にコピー → mount → disk-forensics
```

snapshot を IR vault に隔離後、`disk-forensics` skill (read-only mount + sleuthkit) に切替。

## Phase 4 — network log

```
NSG flow logs:        Network Watcher → Storage account JSON → Log Analytics
Azure Firewall:       AzureFirewallApplicationRule / NetworkRule
DNS Analytics:        DNS server logs → Log Analytics
```

KQL 例:

```kusto
AzureNetworkAnalytics_CL | where SubType_s == "FlowLog" 
  | where DestPublicIPs_s != "" and FlowDirection_s == "O"
```

## Phase 5 — IAM 改竄追跡

```bash
# Entra ID role assignment changes
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/roleManagement/directory/roleAssignments?\$filter=roleDefinitionId eq '<UAA/GA-id>'"

# Subscription-level RBAC change history (Activity Log 経由)
az monitor activity-log list \
  --resource-group <rg> \
  --query "[?contains(operationName.value,'roleAssignments')]"
```

## Phase 6 — secret / Key Vault 改竄

```bash
# Key Vault access (要 Diagnostic Setting で AuditEvent を取得済)
```

```kusto
AzureDiagnostics 
  | where ResourceType == "VAULTS"
  | where OperationName in ("VaultGet","SecretGet","KeyGet","CertificateGet")
  | summarize count() by CallerIPAddress, identity_claim_appid_g, OperationName
  | order by count_ desc
```

短時間の大量 GetSecret は exfil signal。

## Phase 7 — managed identity 行動の追跡

MI が Storage / Key Vault / Database から異常 access していないか:

```kusto
StorageBlobLogs 
  | where TimeGenerated > ago(7d)
  | where AuthenticationType == "ManagedIdentity"
  | summarize count() by ObjectKey, AccountName
  | order by count_ desc
```

## Phase 8 — timeline / 攻撃 chain

```
時刻       provider event              actor                影響
HH:MM:SS   SigninLogs (no MFA)        compromised-user     foothold
HH:MM:SS   Add member to GA role      compromised-user     privesc
HH:MM:SS   Add credential to SP       compromised-user     persistence
HH:MM:SS   GetSecret x100             compromised-SP       exfil
```

## Phase 9 — レポート

```
- 環境 (tenant / subscription)
- 期間
- 攻撃 chain (MITRE ATT&CK Cloud Matrix)
- 関与した user / SP / MI / role
- 影響範囲
- 残存リスク (key rotation / MFA reset / SP credential cleanup / conditional access 強化)
- 推奨 (PIM JIT / consent restriction / monitoring rule 強化)
```

## Tools

```
az cli / Microsoft Graph (az rest)
Log Analytics / Sentinel KQL
Defender for Cloud
PowerShell (Az / AzureAD modules)
WebFetch
Bash (sandbox)
```
