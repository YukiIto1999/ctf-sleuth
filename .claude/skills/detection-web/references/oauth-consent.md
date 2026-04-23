
# Detecting Suspicious OAuth Application Consent

`detection-web` から呼ばれる variant 別 deep dive

## When to Use

- 「ユーザの同意で attacker app が social login → Mail.Read / Files.Read.All を取得」型の illicit consent grant を疑う
- 急に新しい enterprise app / service principal が tenant 内に出現した
- consent granted のあとに不審な OAuth API call が発生
- phishing campaign の追跡で "Sign in with Microsoft" の誘導 URL が出てきた

**使わない場面**: token 盗用 / replay の検出（→ `detection-web`）、攻撃者視点で consent を取りに行く（→ `testing-oauth2-implementation-flaws`、`social-engineering`）。

## Approach / Workflow

### Phase 1 — log source

| プロバイダ | source |
|---|---|
| Entra ID | AuditLogs (`Add app role assignment grant to user`, `Consent to application`), ServicePrincipal events |
| Microsoft Graph | `oauth2PermissionGrants`, `appRoleAssignments`, `servicePrincipals` |
| Okta | System Log: `application.user_membership.add`, `application.policy.sign_on.update` |
| Google Workspace | Admin Audit: `oauth_access_grant` |
| Auth0 | Tenant Logs: `Successful Application Created` |

### Phase 2 — シグナル一覧

```
- 新規 service principal 作成 + 即座 admin consent
- consent された scope が広範囲 (.Read.All / .ReadWrite.All / Mail.Send / offline_access)
- publisher が unverified、または publisher 名が legit ベンダ騙り (例: "Microsoft Office 365 Login")
- redirect_uri が ngrok / cloudflare workers / その他 ephemeral host
- 同一 application_id が複数 tenant に展開 (供給ベンダ事案でなければ怪しい)
- consent 直後に大量 Graph API 呼出 (mailbox 列挙 / file 列挙 / contact 列挙)
- consent operator が user (= self consent), self-service consent 制限が緩い tenant
```

### Phase 3 — Microsoft Graph 列挙

```
GET https://graph.microsoft.com/v1.0/servicePrincipals?$filter=...
GET https://graph.microsoft.com/v1.0/oauth2PermissionGrants
GET https://graph.microsoft.com/beta/identityGovernance/.../assignments
```

KQL (Sentinel) 例:

```
AuditLogs
| where OperationName in ("Consent to application", "Add app role assignment grant to user")
| extend AppId = tostring(parse_json(TargetResources)[0].id)
| extend ConsentScope = tostring(parse_json(parse_json(TargetResources)[0].modifiedProperties)[0].newValue)
| where ConsentScope has_any (".Read.All", ".ReadWrite.All", "Mail.Send", "offline_access")
| order by TimeGenerated desc
```

### Phase 4 — リスクスコアリング

| 観点 | 点数 |
|---|---|
| publisher unverified | +3 |
| `.ReadWrite.All` / `Mail.Send` 含む | +3 |
| 複数 high-privilege scope | +2 |
| user consent (admin consent ではない) | +2 |
| redirect_uri に ephemeral host | +2 |
| consent 後 24h 以内に大量 Graph call | +2 |
| 公的 brand name の squatting | +2 |
| 平日深夜 / 休日の consent | +1 |

合計 5 点以上で要対応。

### Phase 5 — 対応 playbook

```
1. 該当 service principal の disable
   PATCH /servicePrincipals/{id}  { "accountEnabled": false }
2. consent 取消し
   DELETE /oauth2PermissionGrants/{id}
3. 関連 token revoke (該当 user 全 session 失効)
4. consent を許諾した user の audit (other apps への同意確認)
5. enterprise application policy: 「user consent for apps」を高 risk から admin approval flow に
6. 横展開: 同 app_id が他 user / tenant にも consent 受けていないか
```

### Phase 6 — 予防

```
- admin consent workflow 有効化 (.Read.All 等 high-risk scope は管理者承認必要)
- "verified publisher" 必須化
- Conditional Access for Workload Identities (Microsoft) で risky service principals を block
- redirect_uri allowlist
- consent log の SOC ingestion + alert
```

### Phase 7 — レポート / IOC

```
- application_id / display_name / publisher
- granted scope と user
- redirect_uri / homepage URL / publisher domain
- consent timestamp / IP / user-agent
- post-consent activity (Graph API 統計)
- 影響範囲 (取得可能だったメール / file 件数)
```

## Tools

```
Microsoft Graph (PowerShell / curl)
Sentinel KQL
jq
ROADtools / AzureHound (read-only audit)
WebFetch / WebSearch
Bash (sandbox)
```
