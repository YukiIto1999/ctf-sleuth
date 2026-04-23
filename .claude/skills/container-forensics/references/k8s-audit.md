# Kubernetes Audit Log Analysis

`container-forensics` の Phase 4 から呼ばれる、Kubernetes API server の audit log (JSON lines) を解析し、exec-into-pod / secret 取得 / RBAC 変更 / privileged pod 作成 / anonymous API 利用などの不審活動を検出。

## いつ切替えるか

- Kubernetes cluster の侵害 / 不審 API 利用の調査
- RBAC 変更や privileged pod 起動の検出
- threat detection rule の構築 / 改善
- cluster compromise IR

## Phase 1 — audit log 取得

```
audit policy が `Metadata` / `Request` / `RequestResponse` で出力する設定が必要。
管理する場所:
  /var/log/kube-apiserver/audit.log         (kops / kubeadm 系)
  /var/log/kubernetes/audit/audit.log
  CloudWatch Logs (EKS)
  Stackdriver Logging (GKE)
  Azure Monitor (AKS)
```

audit log は JSONL:

```json
{"kind":"Event","apiVersion":"audit.k8s.io/v1","level":"RequestResponse","auditID":"...","stage":"ResponseComplete","requestURI":"/api/v1/namespaces/default/pods","verb":"create","user":{"username":"system:serviceaccount:default:default","groups":["system:serviceaccounts"]},"sourceIPs":["10.0.0.1"],"objectRef":{"resource":"pods","namespace":"default","name":"x"},"responseStatus":{"metadata":{},"code":201}}
```

## Phase 2 — 危険操作の抽出

| 操作 | フィルタ |
|---|---|
| exec into pod | `verb=create` + `requestURI=/api/v1/namespaces/.*/pods/.*/exec` |
| secret 取得 | `verb=get/list` + `objectRef.resource=secrets` |
| RBAC 変更 | `objectRef.resource in [roles, clusterroles, rolebindings, clusterrolebindings]` + `verb in [create, update, patch, delete]` |
| privileged pod 作成 | `verb=create` + `objectRef.resource=pods` + body に `securityContext.privileged=true` |
| anonymous access | `user.username=system:anonymous` |
| port-forward | `requestURI=/api/v1/namespaces/.*/pods/.*/portforward` |
| service account token mount | `verb=create` + `objectRef.resource=tokenrequests` |
| node API | `requestURI=/api/v1/nodes/.*/proxy/` (kubelet 直接アクセス) |

jq で抽出例:

```bash
jq -c 'select(
  (.requestURI // "") | test("/pods/[^/]+/exec")
)' audit.log
```

## Phase 3 — RBAC 改竄チェック

```bash
jq -c 'select(.objectRef.resource | IN("roles","clusterroles","rolebindings","clusterrolebindings"))
       | select(.verb | IN("create","update","patch","delete"))' audit.log
```

cluster-admin 相当 binding の追加:

```bash
jq -c 'select(.objectRef.resource=="clusterrolebindings")
       | select(.verb=="create")
       | .requestObject.roleRef.name' audit.log
# "cluster-admin" が出たら critical
```

## Phase 4 — service account 異常

```bash
# 通常使われない service account からの API call
jq -r '.user.username' audit.log | grep '^system:serviceaccount' | sort | uniq -c | sort -rn

# 短時間に大量 verb 実行する SA
jq -r '[.timestamp, .user.username, .verb] | @csv' audit.log
```

## Phase 5 — anonymous access

```bash
jq -c 'select(.user.username=="system:anonymous")' audit.log
```

`anonymous-auth=true` の cluster で anonymous が API 叩けるなら critical。

## Phase 6 — privileged pod / hostPath / hostNetwork

```bash
jq -c 'select(.verb=="create" and .objectRef.resource=="pods")
       | select(
           (.requestObject.spec.containers[]?.securityContext.privileged // false) == true
           or .requestObject.spec.hostNetwork == true
           or .requestObject.spec.hostPID == true
           or (.requestObject.spec.volumes[]?.hostPath != null)
         )' audit.log
```

## Phase 7 — IOC / actor 整理

```
- 関連 user / SA
- source IP / User-Agent (kubectl version 等)
- 操作した resource (pod / secret / role)
- timeline
```

## Phase 8 — alert 化

Falco / Sentinel / Splunk に投入する rule を策定:

```
- alert when role/rolebinding 作成 with cluster-admin
- alert when pod with privileged: true
- alert when exec/portforward into kube-system pod
- alert when 5+ secret get from same SA in 1 min
- alert when anonymous user makes API call
```

## Phase 9 — レポート

```
- 期間 / event 件数
- 検出した危険操作
- 関与した user / SA / IP
- 推定攻撃 chain
- 残存リスク (RBAC / SA / privileged 設定)
- 推奨対応 / 検出 rule 追加
```

## Tools

```
jq
splunk / OpenSearch / ELK
falco (rule 作成)
kubectl / kubectl-who-can / rakkess (RBAC 確認)
WebFetch
Bash (sandbox)
```
