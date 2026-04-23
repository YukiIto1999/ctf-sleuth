
# Kubernetes Pod Privilege Escalation Detection

`detection-cloud-anomalies` から呼ばれる variant 別 deep dive

## When to Use

- cluster で privileged pod / hostPath / docker.sock マウントが疑われる
- service account token の濫用 / cluster-admin 取得経路の追跡
- detection rule (Falco / OPA) を継続改善したい

**使わない場面**: cluster 全体の compliance audit (→ `kubernetes-security`)、pentest 視点の積極的攻撃 (→ `kubernetes-security`)。

## Approach / Workflow

### Phase 1 — 危険 PodSpec パターン

```
spec.containers[].securityContext.privileged: true
spec.containers[].securityContext.capabilities.add: [SYS_ADMIN, SYS_PTRACE, NET_ADMIN, ...]
spec.containers[].securityContext.allowPrivilegeEscalation: true
spec.containers[].securityContext.runAsUser: 0
spec.hostNetwork: true
spec.hostPID: true
spec.hostIPC: true
spec.volumes[]:
  hostPath: /                     # node root マウント
  hostPath: /var/run/docker.sock  # docker daemon control
  hostPath: /etc / /proc / /sys
  hostPath: /var/lib/kubelet
spec.serviceAccountName + token automountServiceAccountToken: true
```

### Phase 2 — 静的検出 (admission control)

OPA / Gatekeeper policy 例:

```rego
violation[{"msg": msg}] {
  input.review.object.spec.containers[_].securityContext.privileged == true
  msg := "privileged container is not allowed"
}
```

PodSecurityAdmission (PSA) profile:

```yaml
labels:
  pod-security.kubernetes.io/enforce: restricted
  pod-security.kubernetes.io/enforce-version: latest
```

### Phase 3 — 動的検出 (Falco)

代表 rule:

```
- Privileged container started
- Mount sensitive path (/proc, /var/run/docker.sock)
- Add capability SYS_ADMIN / NET_ADMIN
- Container drift: 新 binary が走った
- Shell spawned in container
- Read of service account token from non-allowed proc
```

詳細は `cloud-forensics`。

### Phase 4 — Kubernetes audit log 相関

audit log で:

```
verb=create resource=pods + body に privileged: true
verb=create resource=pods + hostPath
verb=create resource=clusterrolebindings (cluster-admin)
verb=update resource=daemonsets (横展開用 daemon set)
```

詳細は `container-forensics`。

### Phase 5 — Service Account token abuse

```
- token が自動 mount → /var/run/secrets/kubernetes.io/serviceaccount/token
- 過大 scope の SA (cluster-admin / get secrets across ns)
- token を pod 外に exfil → `oauth2PermissionGrants` 系で外部から API 叩く
```

検出:

```kql
// Falco: read of service account token from process not "kubelet"
// kubectl can-i は SA 権限調査
kubectl auth can-i --list --as=system:serviceaccount:default:default
```

### Phase 6 — escape 兆候

```
- container 内から /host (hostPath /) 操作
- nsenter -t 1 -a sh (host pid namespace 共有時)
- /proc/1/root 越しの host 操作
- kernel exploit (DirtyPipe / CoW 系)
- 共有 socket 経由 (/var/run/docker.sock で host docker daemon 叩く)
```

### Phase 7 — 応答

```
1. 不審 pod の delete
2. node の cordon + 必要なら drain & rebuild
3. SA token rotation / SA 縮小
4. cluster-admin binding 巻き戻し
5. PSA enforce 化 / OPA policy 強化
6. node OS の patch / runtime upgrade
```

### Phase 8 — レポート

```
- 期間 / 検出 pod 数
- privesc メカニズム別件数
- 関与 SA / namespace
- 残存リスク
- 推奨 (PSA / OPA / Falco rule / SA scope 縮小)
```

## Tools

```
falco
gatekeeper / opa
kube-bench / kubesec
kubectl auth can-i
kubectl-who-can / rakkess
WebFetch
Bash (sandbox)
```
