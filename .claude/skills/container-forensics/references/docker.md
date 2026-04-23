# Docker Container Forensics

`container-forensics` の Phase 2 / Phase 3 から呼ばれる、Docker container の image / layer / volume / log / runtime 状態の解析。

## いつ切替えるか

- 侵害された Docker container の image / runtime artefact 解析
- container escape / image supply-chain 侵害の調査
- CTF DFIR で `tar.gz` 化した image / `docker save` 出力が evidence

## Phase 1 — image の取得

live host から:

```bash
docker save <image:tag> -o image.tar
docker inspect <image:tag> > inspect.json
docker history --no-trunc <image:tag> > history.txt
docker logs <container_id> > container.log
docker diff <container_id> > diff.txt
```

`docker save` 出力は OCI / Docker image format (tar)。中身:

```
manifest.json
<sha256>.json     (config)
<layer-sha256>/layer.tar
```

## Phase 2 — layer 解析

```bash
mkdir image && tar -xf image.tar -C image
ls image/
cat image/manifest.json
```

各 layer を展開して filesystem として走査:

```bash
mkdir layers
for d in image/*/layer.tar; do
  tag=$(dirname "$d" | xargs basename)
  mkdir layers/$tag
  tar -xf "$d" -C layers/$tag/
done
```

`overlay` の lowerdir / upperdir 対応で layer を順に重ねれば最終 fs。

## Phase 3 — image 内の重点項目

```
/etc/passwd / /etc/shadow            user 設定
/etc/cron* /etc/systemd/             永続化
/usr/local/bin /usr/bin /opt/         任意 binary 投入
/var/log/                              log
/root/.ssh/ /home/*/.ssh/              key
/tmp/ /dev/shm/                        一時 file (削除済 dropper)
~/.docker/config.json                  registry 認証
.dockerenv                             container 識別
```

各 layer の作成時刻 / cmd を `docker history` と相関し、不審 layer を特定:

```bash
docker history --no-trunc <image:tag> | grep -i 'curl\|wget\|chmod\|chown\|RUN'
```

## Phase 4 — runtime 状態 (container 動作中)

```bash
docker exec <id> ps -auxf
docker exec <id> ss -tnlp
docker exec <id> ls -la /proc/*/exe
docker exec <id> netstat -anp
docker exec <id> cat /etc/passwd

docker top <id>                # process tree
docker stats <id>              # resource usage
docker port <id>               # 公開 port

# escape hint
docker inspect <id> | jq '.[].HostConfig.{Privileged, CapAdd, SecurityOpt}'
docker inspect <id> | jq '.[].Mounts'    # bind mount で host 露出
```

## Phase 5 — log / event

```bash
docker logs <id>                              # stdout / stderr
journalctl -u docker.service                  # docker daemon log
cat /var/lib/docker/containers/<id>/<id>-json.log  # 全 stdout

# host audit
ausearch -k docker_socket
auditctl -l                                    # rule 確認
```

## Phase 6 — image vulnerability scan

```bash
trivy image <image:tag>
grype <image:tag>
syft <image:tag> -o cyclonedx-json > sbom.json
```

CVE や 古い base image の検出。base image が侵害されている supply chain ケースなら別 image 比較も必要。

## Phase 7 — escape 兆候

```
- privileged: true
- /var/run/docker.sock マウント (container 内で host docker daemon 操作可)
- CAP_SYS_ADMIN / CAP_SYS_PTRACE / CAP_SYS_MODULE
- host net / pid / ipc namespace 共有
- /proc / /sys host mount
- AppArmor / seccomp profile が unconfined
- dangerous mount (/, /etc, /var/lib/docker)
```

## Phase 8 — レポート

```
- image identity / version / digest
- 不審 layer / 不審 binary (path / hash)
- runtime config 異常 (privileged / cap / mount)
- log 抽出 (重要 event)
- IOC (内部接続 / process / file)
- 推奨対応 (image 再 build / runtime 強化)
```

## Tools

```
docker (CLI / inspect / history / save)
trivy / grype / syft (image scan + SBOM)
dive (interactive layer browse)
WebFetch
Bash (sandbox)
strings / xxd / yara
```
