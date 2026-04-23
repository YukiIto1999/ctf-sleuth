
# Linux System Artifact Analysis

`disk-forensics` から呼ばれる variant 別 deep dive

## When to Use

- Linux disk image / mount された profile / live host を調査
- 侵害後の persistence / lateral movement の証跡確認
- CTF DFIR で「user X が何をしたか」型 / 「permanent foothold は何か」型問題

**使わない場面**: Windows host (→ `disk-forensics`、`disk-forensics` の Windows artefact 節)。kernel module level（→ `rootkit-analysis`）。

## Approach / Workflow

### Phase 1 — log 集約

```
/var/log/auth.log              # 認証 (sshd / sudo / login)
/var/log/secure                # RHEL/CentOS の auth.log 相当
/var/log/syslog / messages     # 一般 system event
/var/log/kern.log              # kernel
/var/log/audit/audit.log       # auditd
/var/log/wtmp / btmp           # login (last / lastb で表示)
/var/log/lastlog               # 各 user の最終 login
/var/log/dpkg.log              # apt / dpkg 履歴
/var/log/apt/history.log       # apt 履歴 (cmdline)
/var/log/dnf.log / yum.log     # dnf / yum 履歴
/var/log/cron                  # cron 実行
/var/log/mail.log
/var/log/nginx/* /var/log/apache2/* /var/log/httpd/*
/var/log/<service>/...         # service 別
journalctl 出力 (systemd-journald) — `/var/log/journal/<machine-id>/system.journal`
```

journal は binary なので live で `journalctl --since '2024-01-01'`、image なら `journalctl --directory=/mnt/evidence/var/log/journal/`。

### Phase 2 — auth log の重点項目

```bash
grep -E 'Failed password|Accepted (password|publickey)' /var/log/auth.log
grep 'sudo:' /var/log/auth.log | grep -v 'COMMAND=/usr/bin/'   # 不審 sudo
grep 'session opened' /var/log/auth.log
grep 'useradd\|usermod\|groupadd' /var/log/auth.log
last -f /var/log/wtmp                                          # login 履歴
lastb -f /var/log/btmp                                         # 失敗 login
```

### Phase 3 — shell history

```
/home/<user>/.bash_history
/home/<user>/.zsh_history       # zsh extended history は `: <ts>:0;<cmd>` 形式
/home/<user>/.python_history
/home/<user>/.viminfo           # 編集 file
/home/<user>/.lesshst
/home/<user>/.mysql_history
/home/<user>/.psql_history
/root/.bash_history             # root の作業
```

不審 user に ssh key 追加されていないか:

```bash
cat /home/*/.ssh/authorized_keys
cat /root/.ssh/authorized_keys
ls -la /etc/ssh/sshd_config.d/   # drop-in config
```

### Phase 4 — 永続化機構

```
/etc/crontab
/etc/cron.{hourly,daily,weekly,monthly}/
/etc/cron.d/
/var/spool/cron/* (per-user cron table)
/etc/anacrontab

/etc/systemd/system/*.service
/etc/systemd/system/*.timer
/usr/lib/systemd/system/*.service (default)
~/.config/systemd/user/*.service

/etc/init.d/*                   # SysV
/etc/rc.local                   # 廃れたが残っていることがある
/etc/profile.d/*.sh             # login 時実行
/etc/bash.bashrc / /etc/zshrc
~/.bashrc / .bash_profile / .profile / .zshrc

/etc/ld.so.preload              # LD_PRELOAD 永続化の典型
/etc/sudoers / /etc/sudoers.d/* # sudo 設定改竄
```

不審な systemd unit:

```bash
systemctl list-units --type=service --state=running
systemctl cat <unit>            # ExecStart の中身
journalctl -u <unit>             # 実行履歴
```

### Phase 5 — user / group 改竄

```bash
cat /etc/passwd | awk -F: '$3==0 {print}'      # uid=0 が root 以外にあれば異常
cat /etc/shadow                                # password hash の有無
cat /etc/group | grep -E 'wheel|sudo|admin'
diff /etc/passwd-  /etc/passwd                 # backup との差分
```

### Phase 6 — 不審 binary / 設定

```bash
find / -perm -4000 -type f 2>/dev/null         # SUID
find / -perm -2000 -type f 2>/dev/null         # SGID
find / -newer /etc/passwd -type f 2>/dev/null  # passwd より新しい
find / -size +100M -type f 2>/dev/null         # 大きいファイル
debsums -c | head                              # Debian: パッケージ整合性
rpm -Va | head                                 # RHEL: パッケージ整合性
```

### Phase 7 — network / firewall 設定

```
/etc/hosts                              # 不審な host alias
/etc/resolv.conf                        # 不審 DNS server
/etc/iptables/* /etc/nftables.conf      # firewall rule
ss -tnlp / netstat -tnlp                # listening port
iptables-save / nft list ruleset
```

### Phase 8 — timeline / IOC

artefact の mtime / atime を Plaso で super-timeline 化。重要 event を時系列で並べて report。

```
- ssh login 成功
- sudo / su 実行
- user 追加 / 権限変更
- crontab 変更
- 不審 file 設置
- network 接続
```

## Tools

```
journalctl
ausearch / ausyscall (auditd)
last / lastb / who / w
RegRipper-like Linux ツール群
plaso / log2timeline (super-timeline)
strings / xxd
debsums / rpm -Va
WebFetch
Bash (sandbox)
```
