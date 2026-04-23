
# Rootkit Activity Detection

`rootkit-analysis` から呼ばれる variant 別 deep dive

## When to Use

- ホストが rootkit に侵されている疑い (top / ps / netstat に出ない process / port があるが負荷高い)
- antivirus / EDR が反応しないが behavior 異常
- CTF DFIR で 「process が hide されている」型問題

**使わない場面**: rootkit binary 自体の reverse (→ `rootkit-analysis`、`rootkit-analysis`)、user-land malware の rev (→ `reverse-engineering`)。

## Approach / Workflow

### Phase 1 — cross-view 比較

異なる方法で取得した listing を diff:

```bash
# Linux process
diff <(ls /proc/ | grep '^[0-9]' | sort) <(ps -ef | awk '{print $2}' | sort -u)
# /proc にあるが ps に無い → user-land hide
# /proc に無いが /proc/<pid>/exe を 直接見ると見える → kernel hide

# module
diff <(awk '{print $1}' /proc/modules | sort) <(ls /sys/module/ | sort)

# socket
ss -tnpa > /tmp/ss.out
netstat -tnpa > /tmp/netstat.out
# /proc/net/tcp(6) を直接読む
cat /proc/net/tcp /proc/net/tcp6 > /tmp/proctcp.txt

# files
ls -la / 2>/dev/null > /tmp/ls.out
strace -e trace=getdents64 ls / 2>/tmp/strace-ls.txt
```

cross-view で出る差分は rootkit が API 層で hide している兆候。

### Phase 2 — memory dump triage

memory acquisition後、`memory-analysis` の手順で:

```
- pslist vs psscan の差分 (DKOM)
- modules vs ModulesScan の差分 (LKM hide)
- check_syscall plugin の hooked entry
- malfind の RWX MZ region (user-land injection)
- driverscan / callbacks / ssdt (Windows) で kernel level hook
```

詳細: `rootkit-analysis`、`memory-analysis`。

### Phase 3 — integrity check

```
- AIDE / Tripwire の baseline と現状 diff
- rkhunter / chkrootkit
- debsums -c (Debian) / rpm -Va (RHEL)
- ssdeep / TLSH で 主要 binary の similarity 確認
- Microsoft sigcheck (Windows) / Sysinternals AutoRuns
```

baseline が無い環境では、distribution 公式 hash / pkg-debug-info と比較。

### Phase 4 — anomaly hunt

```
- /tmp /var/tmp /dev/shm に隠し binary
- /etc/ld.so.preload (LD_PRELOAD)
- cron / systemd timer / autoload に attacker entry
- ~/.bashrc / .profile / .bash_logout の追加行
- 隠しディレクトリ (`. ` / `..foo` / unicode 偽装)
```

```bash
find / -type f -newer /etc/passwd -not -path '/proc/*' -not -path '/sys/*' 2>/dev/null
find / -nouser -o -nogroup 2>/dev/null
find / -perm -4000 -type f 2>/dev/null              # SUID 不正
ls -la /etc/ld.so.preload 2>/dev/null
```

### Phase 5 — Windows 系の cross-view

```
- tasklist vs Process Explorer (psapi vs NT API)
- Get-NetTCPConnection vs netstat
- driverquery vs DeviceTree
- Sysmon Operational log vs Volatility windows.* output
- registry: HKLM\System\CurrentControlSet\Services\* の不審 service
- WMI persistence (root\subscription)
- WinDbg + LiveKd で kernel inspect
```

Sysmon + EDR 出力との突き合わせで隠蔽兆候を triage。

### Phase 6 — Anti-rootkit boot

```
- live USB / forensic boot で外側 OS から disk を read-only mount
- ESP / MBR / VBR の hash 検証
- /boot 配下の kernel image / initramfs を比較
- Linux: kexec で別 kernel boot して /proc を観察
```

### Phase 7 — 対応

```
1. network 切断 → memory dump
2. disk image
3. evidence 保全
4. OS 再インストール (kernel rootkit / bootkit の場合は確実)
5. baseline IDS (Falco / sysdig / Tripwire / AIDE) を再構築
6. 関連 IOC を組織 SIEM に投入
```

### Phase 8 — レポート / IOC

```
- 検出方法 (cross-view / memory forensics / integrity)
- 検出 indicator
- 推定 family
- 影響範囲 / 横展開
- 修復手順
- 検出 rule の draft
```

## Tools

```
rkhunter / chkrootkit / tripwire / aide
volatility3
sysmon / Sysinternals AutoRuns / Process Explorer
debsums / rpm -Va
strace / ltrace
WebFetch
Bash (sandbox)
```
