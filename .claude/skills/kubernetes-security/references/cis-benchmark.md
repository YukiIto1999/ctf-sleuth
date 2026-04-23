# Kubernetes CIS Benchmark Audit (kube-bench)

`kubernetes-security` から呼ばれる、kube-bench で K8s cluster の CIS benchmark 準拠を control plane / worker / RBAC まで自動 audit。

## いつ切替えるか

- 既存 cluster の構成を CIS Kubernetes Benchmark で網羅評価
- pentest 開始時の low-hanging 抽出
- 自社 cluster の継続 audit baseline

## Phase 1 — 実行モード

### in-cluster (DaemonSet)

```bash
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml
kubectl logs -l app=kube-bench
```

### バイナリ直接 (control plane host で)

```bash
kube-bench run --targets master,node,controlplane,etcd,policies
```

### managed cluster

```
- EKS: kube-bench --targets node --version eks-1.5.0
- GKE: gke 用 profile
- AKS: aks 用 profile
```

managed では control plane が監査対象外 (Cloud provider 管理)。worker と RBAC を中心に。

## Phase 2 — 主要セクション

| セクション | 観点 |
|---|---|
| 1. Control Plane Components | apiserver / controller-manager / scheduler / etcd の起動オプション |
| 2. Etcd | etcd 認証 / 暗号化 |
| 3. Control Plane Configuration | TLS / audit / authorization mode |
| 4. Worker Nodes | kubelet 設定 (anonymous-auth / authorization-mode) |
| 5. Policies | RBAC / Pod Security / Network Policy / Secrets |

## Phase 3 — 高頻度 finding

```
- kubelet --anonymous-auth=true (anonymous request 許容)
- kubelet --authorization-mode=AlwaysAllow (どんな request も許可)
- apiserver --insecure-port が 0 でない
- apiserver --audit-log-path 未設定 (audit log 取得不能)
- apiserver --tls-cert-file 不在
- etcd 暗号化 (encryption at rest) 無効
- etcd peer / client TLS 無効
- ServiceAccount automountServiceAccountToken: 全 namespace で true
- default service account 過剰権限
- 古い K8s version (CVE 累積)
```

## Phase 4 — output 整形

`-o json` で出すと downstream に渡しやすい:

```bash
kube-bench run --json --output report.json
jq '.Controls[] | .tests[] | .results[] | select(.status=="FAIL")' report.json | less
```

## Phase 5 — 是正と検証

```
1. apiserver / kubelet flag を修正
2. cluster reroll (rolling restart)
3. kube-bench 再実行で finding が解消したか確認
4. 例外を `--config` で documented exemption に登録
```

## Phase 6 — 関連 deep-dive

```
etcd 詳細試験     → references/etcd.md
攻撃チェーン      → kubernetes-security の SKILL.md (本体)
manifest 静的監査 → references/manifest-scan.md
audit log 解析    → container-forensics
runtime 検出      → cloud-forensics の k8s-runtime-falco.md
```

## Phase 7 — レポート

```
- cluster version / provider (self-managed / EKS / GKE / AKS)
- finding 件数 (FAIL / WARN / PASS)
- 上位 critical 抜粋
- 推奨対応 (kubelet / apiserver flag / SA / RBAC)
- 修正後 baseline 計画
```

## Tools

```
kube-bench
kubectl
jq
WebFetch
Bash (sandbox)
```
