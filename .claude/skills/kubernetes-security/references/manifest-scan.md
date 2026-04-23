# Kubernetes Manifest Scanning (Kubesec)

`kubernetes-security` から呼ばれる、Kubesec で K8s manifest (Deployment / DaemonSet / Pod / StatefulSet) を静的 scan し、privesc リスク / best practice 逸脱を検出。

## いつ切替えるか

- IaC / Helm chart / kustomize の K8s manifest を deploy 前に検査
- CI pipeline で security gate
- 自社 Helm chart の継続評価
- pentest 開始時の static review

## Phase 1 — 実行

```bash
# 単一 manifest
kubesec scan deployment.yaml

# directory 配下を再帰
find ./manifests -name '*.yaml' -exec kubesec scan {} \;

# Helm chart を render してから
helm template ./chart | kubesec scan -
```

または HTTP API:

```bash
curl -X POST -F file=@deployment.yaml https://v2.kubesec.io/scan
```

## Phase 2 — 評価項目

```
Critical (-30):
  privileged: true
  capabilities.add: SYS_ADMIN
  hostPID: true
  hostNetwork: true
  hostIPC: true
  hostPath volume to / or /etc

Negative (-3 ~ -10):
  runAsUser: 0
  allowPrivilegeEscalation: true
  capabilities.add: 一般
  imagePullPolicy: Always 不在
  resources.limits 無し
  livenessProbe / readinessProbe 無し

Positive (+1 ~ +5):
  readOnlyRootFilesystem: true
  capabilities.drop: ["all"]
  runAsNonRoot: true
  seccompProfile: RuntimeDefault
  serviceAccountName 明示 + 非 default
  network policy 存在
  resources.limits 設定済
```

## Phase 3 — 出力解釈

```json
{
  "object": "Pod/example",
  "score": -27,
  "scoring": {
    "critical": [
      {"selector": "containers[].securityContext.privileged == true", "reason": "..."}
    ],
    "advise": [...]
  }
}
```

CI 化:

```yaml
- name: kubesec
  run: |
    score=$(kubesec scan deploy.yaml | jq '.[0].score')
    if [ "$score" -lt 0 ]; then
      echo "score=$score, failing" && exit 1
    fi
```

## Phase 4 — 補完ツール

```
- kubeaudit (詳細 audit)
- conftest + OPA rego (policy as code)
- kyverno CLI
- checkov (Terraform / K8s 統合)
- kics / KubeLinter
```

複数 tool 出力を merge して true positive を抽出。

## Phase 5 — 修正パターン

```yaml
spec:
  serviceAccountName: my-app
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: my-app:1.2.3@sha256:...
      imagePullPolicy: Always
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
      resources:
        limits:
          cpu: "500m"
          memory: "256Mi"
        requests:
          cpu: "100m"
          memory: "128Mi"
      livenessProbe: {...}
      readinessProbe: {...}
```

## Phase 6 — レポート

```
- repo / chart / manifest 数
- finding 件数 (severity 別)
- 上位 critical 抜粋
- 推奨修正 (テンプレ snippet 提示)
- CI gate の閾値設定
```

## Tools

```
kubesec
kubeaudit
checkov / kics / KubeLinter
conftest / kyverno
WebFetch
Bash (sandbox)
```
