
# Detecting OAuth Token Theft

`detection-web` から呼ばれる variant 別 deep dive

## When to Use

- 「impossible travel」「異常な国からのサインイン」アラートが出た
- pass-the-cookie / pass-the-token / device code phishing の疑い
- token sweep type incident（同一 token を複数 IP / UA から使用）の調査
- OAuth token 盗用が前提の defense-in-depth 評価
- CTF blue team / DFIR 系演習

**使わない場面**: token を**取得する**側の攻撃（→ `testing-oauth2-implementation-flaws`、`detection-web`）。

## Approach / Workflow

### Phase 1 — log source の整理

| プロバイダ | 主要 log |
|---|---|
| Entra ID | SignInLogs, AuditLogs, RiskyUsers, RiskyServicePrincipals (Microsoft Graph / Sentinel) |
| Okta | System Log API (`/api/v1/logs`), Workflows, Risk-based authentication events |
| Auth0 | Tenant Logs (`/api/v2/logs`), Anomaly Detection events |
| Google Workspace | Admin Audit, Login audit (Reports API) |
| GitHub | OAuth App audit log, security log |
| Generic OAuth provider | token issuance + refresh + revocation log |

### Phase 2 — 異常 sign-in シグナル

```
- 同 sub / userPrincipalName から短時間に異なる地域 (impossible travel)
- 同 token / sessionId が複数 source IP / device から発火
- 通常使わない user-agent (curl / scripts / outdated browser)
- 通常使わない grant type (device_code, refresh_token from new client)
- 通常使わない scope (offline_access が普段付かない user)
- Conditional Access policy bypass や failure → success の遷移
- MFA "satisfied by sign-in" or "not required by policy" が突然出現
```

### Phase 3 — Entra ID 固有

- **TokenIssuerType: AzureAD vs ADFS** の混在
- **AuthenticationProtocol: deviceCode** が突然出る
- **ConditionalAccessStatus: notApplied** で MFA が当たらない pattern
- **Risk Detection**: anonymizedIPAddress / atypicalTravel / unfamiliarFeatures
- **Sign-in Token Lifetime** が unusually long（既定 1h と異なる）
- **Continuous Access Evaluation (CAE)** が無効化されていないか

KQL クエリ例:

```
SigninLogs
| where TimeGenerated > ago(7d)
| extend Country = tostring(LocationDetails.countryOrRegion)
| summarize Countries = make_set(Country), Count = count() by UserPrincipalName, bin(TimeGenerated, 1h)
| where array_length(Countries) > 2
```

### Phase 4 — token replay の検出

```
1. access token の jti / sid を log に紐付ける
2. 同一 jti が複数 IP / ASN / user-agent で使用されていないか
3. refresh token rotation が想定通り起きているか (rotate せず再使用 = 窃取兆候)
4. token introspection が短期間に多数 (列挙の兆候)
```

### Phase 5 — device code phishing

```
- /devicecode endpoint への大量 polling 後に成功サインイン
- 不審な OAuth app への consent 直後の token 発行
- enterprise app に新規 service principal が permission grant を受けた直後
- redirect_uri に異常な値 (社外 / プライベート IP)
```

### Phase 6 — Conditional Access / risk-based policy

```
- 「sign-in risk」「user risk」が High / Medium のときに自動 block / MFA 要求
- 不明なデバイスからの token 発行を block
- token-bound (DPoP / mTLS / continuous access evaluation) の強制
- session lifetime を SaaS ごとに短縮 (financial = 1h, internal = 8h)
```

### Phase 7 — 対応 playbook

```
1. 該当 user の active session を全 revoke
   Microsoft Graph: revokeSignInSessions
   Okta: clear all sessions
2. refresh token 失効 (token revocation endpoint)
3. password / MFA factor 再登録
4. Conditional Access: location restriction 追加
5. application 側 risk policy 見直し
6. 関連 user / app への横展開 audit
```

### Phase 8 — レポート / IOC

```
- 異常 sign-in タイムライン (UTC 揃え)
- 関連 IP / ASN / user-agent / device-id
- 影響 scope (token から触れたリソース)
- 残存リスク (revoke できなかった token / app)
- 再発防止 (Conditional Access / token binding / risk policy)
```

## Tools

```
Microsoft Sentinel / Defender XDR (KQL)
Splunk / Elastic SIEM
jq (log JSON 整形)
WebFetch (provider API 経由 log 取得)
Bash (sandbox)
```
