
# Azure Storage Account Misconfiguration Detection

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- Azure subscription / resource group の storage account を網羅的に audit
- public Blob exposure / ransomware リスクの事前評価
- bug bounty / pentest で Azure 関連 storage の問題を探す

**使わない場面**: 既に exfil が起きた後の log 解析（→ `detection-cloud-anomalies`）。

## Approach / Workflow

### Phase 1 — inventory

```bash
az login --identity 2>/dev/null || az login
az storage account list --query "[].{name:name, rg:resourceGroup, kind:kind, sku:sku.name, allowBlobPublicAccess:allowBlobPublicAccess, supportsHttpsTrafficOnly:supportsHttpsTrafficOnly, minimumTlsVersion:minimumTlsVersion}" -o table
```

または Microsoft Graph / azure-mgmt-storage SDK:

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.storage import StorageManagementClient
client = StorageManagementClient(DefaultAzureCredential(), subscription_id)
for acct in client.storage_accounts.list():
    ...
```

### Phase 2 — 主要チェック項目

| 観点 | desired | NG パターン |
|---|---|---|
| public access | `allowBlobPublicAccess = false` | `true` (legacy default) |
| HTTPS-only | `supportsHttpsTrafficOnly = true` | `false` |
| 最小 TLS | `minimumTlsVersion = TLS1_2` | TLS1_0 / TLS1_1 |
| network rule | default deny + allowed VNet/IP | default allow |
| infrastructure encryption | enabled | disabled |
| customer-managed key | 必要なら enabled | platform-managed のみ |
| soft delete (blob) | enabled, retention >= 7 日 | disabled |
| versioning | enabled | disabled |
| hierarchical namespace | ADLS Gen2 利用なら enabled | gen1 mix |
| firewall + private endpoint | private endpoint 化 | 公開 endpoint |
| anonymous container | none | `Public Access Level = Blob/Container` |

### Phase 3 — container 単位の確認

```bash
az storage container list --account-name <acct> --query "[].{name:name, public:properties.publicAccess}" -o table
```

```python
for container in blob_service.list_containers():
    print(container.name, container.public_access)
```

`Blob` / `Container` の public access はデータ漏洩経路。

### Phase 4 — SAS token 監査

```
- account-level SAS の発行履歴 (storage account log)
- 長期 (7 日超) の SAS
- Stored Access Policy が無く revoke 不能な ad-hoc SAS
- IP / Protocol / 期限 制限が緩い SAS
```

```kql
StorageBlobLogs
| where AuthenticationType == "SAS"
| summarize Count = count() by AccountName, ObjectKey, OperationName
```

### Phase 5 — encryption / key

```python
acct.encryption.services.blob.enabled
acct.encryption.services.file.enabled
acct.encryption.key_source       # Microsoft.Storage / Microsoft.Keyvault
acct.encryption.require_infrastructure_encryption
```

CMK (customer-managed key) を必要とする規制下では、`key_source` が `Microsoft.Keyvault` でないと NG。

### Phase 6 — network restriction

```bash
az storage account network-rule list --account-name <acct>
# default-action: Allow / Deny
# ipRules / virtualNetworkRules
# bypass: AzureServices / Logging / Metrics
```

`default-action = Allow` は実質公開。private endpoint + `Deny` が望ましい。

### Phase 7 — 修正提案 / playbook

```
1. allowBlobPublicAccess = false
2. supportsHttpsTrafficOnly = true
3. minimumTlsVersion = TLS1_2
4. network rule default-deny + private endpoint
5. SAS は Stored Access Policy 経由 + 短期 (1 時間以内)
6. soft delete + versioning 有効
7. CMK + Key Vault rotation
8. infrastructure encryption double-encrypt
9. Defender for Storage + alert
```

### Phase 8 — レポート

```
- subscription / resource group / account 数
- 検出 misconfiguration (severity 別)
- 公開済 container 一覧
- 期限の長い SAS (件数 / 最古)
- 推奨対応 (上記 Phase 7)
```

## Tools

```
azure cli
azure-mgmt-storage Python SDK
Microsoft Defender for Storage
Sentinel / Log Analytics (StorageBlobLogs)
WebFetch
Bash (sandbox)
```
