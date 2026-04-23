# Cloud-Native Runtime Forensics with Falco

`cloud-forensics` の Phase 4 から呼ばれる、Falco の YAML rule で container / Kubernetes ノードの syscall を監視し、shell spawn / file 改竄 / 不審ネット通信 / 権限昇格を検出する深掘り。

## いつ切替えるか

- container / Kubernetes ノード上で発生したシェル / file 操作 / ネットワーク異常を runtime レベルで観測する
- Kubernetes audit log (→ `container-forensics`) に出ない、container 内部の syscall を見たい
- CTF DFIR で Falco event log が evidence
- 既存 cluster の検出 rule を拡張する

## Phase 1 — Falco の役割

Falco は eBPF / kernel module でノード syscall を監視し、`falco-rules.yaml` の rule に一致する event を `priority` 付きで出力する。出力先は file / syslog / Webhook / gRPC / Kafka 等。

## Phase 2 — rule の主要カテゴリ

```
- terminal shell in container
- write below etc
- write below binary dir
- modify shell configuration file
- container drift (image にない binary 起動)
- unexpected outbound connection
- inbound from non-allowed source
- privileged container started
- mount sensitive path (/proc, /var/run/docker.sock)
- read sensitive file (/etc/shadow, /root/.ssh)
- attach to cluster admin role (k8s-audit)
- launch privileged pod
```

## Phase 3 — rule 例

```yaml
- rule: Terminal shell in container
  desc: A shell was spawned in a container
  condition: >
    spawned_process and container and shell_procs and proc.tty != 0
  output: >
    Shell in container (user=%user.name container=%container.id pid=%proc.pid name=%proc.name parent=%proc.pname cmd=%proc.cmdline)
  priority: NOTICE
  tags: [container, shell, mitre_execution]

- rule: Read sensitive file untrusted
  condition: >
    open_read and not user_known_read_sensitive_files_activities and sensitive_files
  output: >
    Sensitive file opened (user=%user.name file=%fd.name proc=%proc.cmdline container=%container.id)
  priority: WARNING
  tags: [filesystem, mitre_credential_access]
```

## Phase 4 — event の取り込み

```
- output channel = file → /var/log/falco.log を tail
- syslog → SIEM
- gRPC → falcosidekick / Webhook → Slack / OpenSearch / Kafka
```

```bash
tail -f /var/log/falco.log | jq .
falco --list                  # ロード済 rule 確認
falco --validate=falco_rules.yaml
```

## Phase 5 — incident triage

falco event の典型 timeline:

```
NOTICE  Terminal shell in container (pod=victim-...)
WARNING Sensitive file opened: /etc/shadow
WARNING Outbound connection to non-allowed CIDR (1.2.3.4)
ERROR   Container with privileged: true (pod=evil-...)
```

各 event を `audit.log` (Kubernetes API) と相関し、誰が pod を作成 / exec したかは `container-forensics` で追う。

## Phase 6 — 攻撃 chain 再構成

```
1. unauthorized exec into pod (k8s audit)
2. shell spawned (falco)
3. read /etc/shadow (falco)
4. install dropper /usr/local/bin/x (falco - write below binary dir)
5. outbound to C2 (falco)
6. container drift (falco - new binary not in image)
7. cluster-admin binding 追加 (k8s audit)
```

## Phase 7 — rule 改善

調査結果を新 rule に reflect:

```yaml
- rule: Outbound to known-bad CIDR
  condition: outbound and fd.sip in (suspicious_ips)
  output: ...
  priority: CRITICAL
```

`falco_rules.local.yaml` で site 特化拡張を持つ。

## Phase 8 — レポート

```
- 期間 / event 件数 / priority 別件数
- 検出 rule と event のサンプル
- 関連 pod / container / image / process
- IOC (file / IP / cmdline)
- 推奨 (rule 追加・PSP/PSA / network policy / image scan)
```

## Tools

```
falco
falcosidekick
falcoctl
kubectl (event 相関)
jq
WebFetch
Bash (sandbox)
```
