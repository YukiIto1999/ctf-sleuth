
# Linux Log Forensics Investigation

`endpoint-forensics` から呼ばれる variant 別 deep dive

## When to Use

- Linux server / workstation の log に基づく侵害分析
- ssh / sudo / kernel / アプリ別 log の重点抽出
- timeline 構築用に log を統合したい
- CTF DFIR の Linux log 解析問題

**使わない場面**: filesystem 上の binary / config 解析（→ `disk-forensics`）、memory 主軸（→ `memory-analysis`）。

## Approach / Workflow

### Phase 1 — log inventory

```
/var/log/auth.log              # Debian/Ubuntu 認証
/var/log/secure                # RHEL/CentOS 認証
/var/log/syslog / messages     # 一般 system
/var/log/kern.log              # kernel
/var/log/audit/audit.log       # auditd (rule 設定済の場合)
/var/log/wtmp / btmp / lastlog # binary, last/lastb で表示
/var/log/cron                  # cron 実行
/var/log/mail.log
/var/log/dpkg.log              # apt / dpkg
/var/log/apt/history.log       # apt cmdline 履歴
/var/log/dnf.log / yum.log     # RHEL 系 package
/var/log/nginx/* /apache2/* /httpd/*
/var/log/<service>/*
~/.bash_history / .zsh_history
journalctl --directory=/mnt/evidence/var/log/journal/
```

evidence 取得時に `/var/log/` 全体 + `journal` ディレクトリを保全。rotate された圧縮 log (`*.gz`、`*.1`) も忘れず。

### Phase 2 — auth log 重点

```bash
# ssh login 成功 / 失敗
grep -E 'Accepted (password|publickey)' /var/log/auth.log
grep 'Failed password' /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn

# sudo 実行
grep 'sudo:' /var/log/auth.log | grep COMMAND

# user / group 変更
grep -E 'useradd|usermod|userdel|groupadd|groupmod' /var/log/auth.log

# session
grep 'session opened' /var/log/auth.log
```

`last`、`lastb` で wtmp / btmp を読む:

```bash
last -f /var/log/wtmp -F             # login 履歴 (full timestamp)
lastb -f /var/log/btmp -F            # 失敗 login
```

### Phase 3 — systemd journal

```bash
journalctl --directory=/mnt/evidence/var/log/journal/ --since '2024-01-01'
journalctl --directory=... -u sshd
journalctl --directory=... _PID=1234
journalctl --directory=... -p err           # error 以上
journalctl --directory=... --output=json | jq .
```

### Phase 4 — auditd

auditd が動いていれば `/var/log/audit/audit.log` に SYSCALL / EXECVE / PATH / NETFILTER record。

```bash
ausearch -k <key> -ts recent
ausearch -m EXECVE -ts today
ausearch -ua <uid> -ts today
ausearch -i -m USER_LOGIN
aureport -au                  # auth report
aureport -m                   # account modifications
aureport --executable
```

不審 EXECVE (`/usr/bin/curl`、`/bin/sh -i`、`nc -e`) を絞り込む。

### Phase 5 — application log

```bash
# nginx / apache の access.log で SQLi / XSS / SSRF 試行
grep -iE 'union.*select|select.*from|<script|/etc/passwd|169\.254\.169\.254' /var/log/nginx/access.log

# error.log で stack trace / fatal
grep -i 'fatal\|panic\|emergency' /var/log/<service>/*

# database (postgresql / mysql) の slow / error
grep -iE 'authentication failed|access denied' /var/log/postgresql/*
```

### Phase 6 — package install / patch 状況

```bash
zcat /var/log/dpkg.log* | grep ' install '
zcat /var/log/apt/history.log* | grep -E 'Install:|Remove:' | head
zcat /var/log/dnf.log* | grep -E 'Installed:|Removed:'
```

不審なタイミング (深夜 / 不在期間) の install を確認。

### Phase 7 — 整形 / 統合

```bash
# 全 log を時刻順に統合
multitail /var/log/syslog /var/log/auth.log /var/log/kern.log    # live
# あるいは plaso / log2timeline で super-timeline
log2timeline.py super.plaso /mnt/evidence/var/log/
psort.py super.plaso > super.csv
```

### Phase 8 — IOC / timeline

```
- ssh 成功 (timestamp / src IP / user / key fingerprint)
- sudo 実行 (timestamp / user / cmd)
- 不審 binary 実行 (auditd EXECVE)
- 外部 download (curl / wget)
- service 異常 (start / fail / crash)
- package install (時刻 / cmdline)
```

### Phase 9 — レポート

```
- 期間 / log source
- 重要 event (timeline)
- 認証 / 権限昇格の chain
- アプリ層の攻撃指標
- 推奨 (rule / patch / segmentation)
```

## Tools

```
journalctl
ausearch / aureport
last / lastb
grep / awk / sed / jq
plaso / log2timeline
WebFetch
Bash (sandbox)
```
