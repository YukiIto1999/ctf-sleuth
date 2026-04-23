
# Linux ELF Malware Analysis

`reverse-engineering` から呼ばれる variant 別 deep dive

## When to Use

- Linux server / container / IoT 由来の不審 ELF を分析
- botnet / mining / ransomware / rootkit の機能・IOC 抽出
- artifact_analysis BC の `FileKind.ELF`

**使わない場面**: kernel module ベースの rootkit (→ `rootkit-analysis`)、UEFI 系 (→ `rootkit-analysis`)。

## Approach / Workflow

### Phase 1 — triage

```bash
file binary
sha256sum binary
strings -n 8 binary | head -200
strings -e l binary | head -50           # wide
readelf -h binary                         # ELF header
readelf -d binary                         # dynamic section
readelf -l binary                         # program header
nm -D binary                              # dynamic symbol
ldd binary                                # 依存
checksec --file=binary
```

確認:

```
- arch (x86 / x64 / ARM / ARM64 / MIPS-R6 / MIPSEL / PowerPC) — IoT botnet は MIPS / ARM 多
- 静的 link (busybox 風 self-contained) ↔ dynamic
- 言語 (Go / Rust / C / C++)
- packer (UPX / 自作)
- stripped か (symbol 残あり / 全削除)
```

### Phase 2 — packer

```bash
upx -d binary -o unpacked
binwalk -e binary
```

UPX 改造 (magic 削除 / signature 加工) は手動 unpack: GDB で `OEP` (original entry point) に到達するまで step、memory dump。

### Phase 3 — string / IOC 抽出

```
- C2 (URL / domain / IP / port)
- mutex / lock file path
- /etc / cron / systemd 永続化先
- shell command (curl / wget / chmod / chmod / chown / iptables)
- mining pool (stratum+tcp:// / xmr.* / pool.*)
- IRC channel (旧 botnet)
- crypto wallet (BTC: 1.* / 3.* / bc1*, XMR: 4.*)
```

### Phase 4 — Ghidra / radare2 で decompile

`reverse-engineering` の手順を ELF に適用。Linux 特有:

```
- syscall 直接呼出し (libc 経由でない / sys_exit 0xa9 等)
- /proc/<pid>/exe を hide する処理
- LD_PRELOAD で既存 process に library 注入
- ptrace anti-debug
- prctl(PR_SET_NAME) で process 名偽装
```

### Phase 5 — 永続化機構

```
/etc/cron.d/<name>
/etc/cron.hourly/<name> /etc/cron.daily/<name>
/var/spool/cron/crontabs/<user>
/etc/systemd/system/<name>.service
/etc/init.d/<name>
/etc/rc.local
~/.bashrc / .profile
/etc/ld.so.preload  (LD_PRELOAD persistence)
~/.ssh/authorized_keys (key 追加)
/usr/local/bin/<random>
```

binary 内で文字列 / sprintf / system 呼出しから永続化先を特定。

### Phase 6 — network 行動

```
- DGA (Domain Generation Algorithm) by date
- C2 URL + endpoint pattern (/gate.php / /api/check 等)
- protocol 平文 / XOR / RC4
- bot 命令 (download / upload / ddos / scan)
```

### Phase 7 — 動的解析 (隔離 VM)

```bash
# 隔離 namespace で動かす
unshare -n ./binary &
strace -fe network ./binary
ltrace -e 'libc.*' ./binary
inotifywait -m / -r 2>/dev/null         # ファイル変更監視
tcpdump -i any -w out.pcap host <c2>
```

### Phase 8 — yara / family 同定

```
yara -r linux-botnet.yar binary
# 既知 family: Mirai / Gafgyt / Tsunami / XorDDoS / Mozi
# TLSH / ssdeep で 既知 sample との類似度
```

### Phase 9 — レポート / IOC

```
- ELF identity (hash / arch / strip / pack)
- 推定 family / 類似度
- C2 / mining pool / wallet
- 永続化機構
- 横展開挙動 (scan / brute / exploit)
- 推定影響 (DDoS / mining / data theft)
- yara rule / sigma rule の draft
```

## Tools

```
file / strings / readelf / nm / objdump / ldd
ghidra / radare2 / IDA / Cutter
upx / binwalk
strace / ltrace / gdb
yara / ssdeep / TLSH
WebFetch
Bash (sandbox)
```
