# Kubernetes etcd Security Assessment

`kubernetes-security` から呼ばれる、Kubernetes etcd cluster の encryption at rest / TLS / access control / backup 暗号化 / network isolation の評価。

## いつ切替えるか

- self-managed K8s cluster で etcd 設定を audit
- 重要 cluster (production) の etcd backup / TLS / access を確認
- pentest 開始時に etcd 直接 access の可能性を見る

managed K8s (EKS / GKE / AKS) では etcd は cloud 管理のため直接評価不可。

## Phase 1 — etcd 構成把握

```bash
# control plane node で
ps aux | grep etcd
cat /etc/kubernetes/manifests/etcd.yaml
```

確認項目:

```
--listen-client-urls=https://...:2379       (TLS にて listen)
--listen-peer-urls=https://...:2380
--cert-file / --key-file
--client-cert-auth=true
--peer-client-cert-auth=true
--trusted-ca-file
--peer-trusted-ca-file
--data-dir=/var/lib/etcd
--auto-tls                                  ← false 推奨 (CA 管理 cert 使用)
```

## Phase 2 — encryption at rest

apiserver の `--encryption-provider-config` を確認:

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: [secrets, configmaps]
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64>
      - identity: {}
```

`identity` が一番上にあると暗号化されない。`aescbc` / `aesgcm` / `kms` (KMS provider) が一番上にあるべき。

## Phase 3 — TLS / 認証

```
- 全 client は cert auth で接続するか
- peer 通信が TLS か
- CA は cluster CA / 専用 CA / shared CA か
- expiration までの残期間
```

```bash
openssl x509 -in /etc/kubernetes/pki/etcd/server.crt -noout -dates
```

## Phase 4 — network isolation

```
- etcd port (2379 / 2380) が control plane node 同士のみ
- worker からアクセス不可
- 外部 (internet / VPC peer) からアクセス不可
- iptables / SecurityGroup / NetworkPolicy で確認
```

```bash
ss -tnlp | grep 2379
iptables -L -n | grep 2379
```

## Phase 5 — etcd 直接 dump 試験 (read-only)

cert を持っているなら:

```bash
ETCDCTL_API=3 etcdctl \
  --endpoints=https://etcd1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  get / --prefix --keys-only | head
```

cluster admin の場合のみ。攻撃 vector の確認用 (cert を盗まれた場合のリスク評価)。

## Phase 6 — backup

```
- etcdctl snapshot save backup.db で snapshot 取れるか
- backup の保存先 (S3 / local / GCS) と暗号化
- backup file の access policy
- 過去 snapshot の保持期間
```

snapshot は実質「全 cluster state」なので暗号化必須。

## Phase 7 — 是正

```
1. encryption at rest を aescbc / kms に
2. peer / client TLS + cert auth 必須
3. network isolation: etcd subnet を control plane 専用に
4. backup を KMS 暗号化 + access log 化
5. cert rotation 自動化
6. etcd version を最新 patch level に
7. 不要 grant (etcd の root user 等) を削除
```

## Phase 8 — レポート

```
- etcd version / member 数
- TLS / cert 状況
- encryption provider 設定
- backup 設定
- network isolation
- finding (severity 別)
- 推奨対応
```

## Tools

```
etcdctl
kube-bench (CIS section 2)
openssl
WebFetch
Bash (sandbox)
```
