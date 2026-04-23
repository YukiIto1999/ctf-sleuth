
# Linux Kernel Rootkit Analysis

`rootkit-analysis` から呼ばれる variant 別 deep dive

## When to Use

- Linux memory dump / live host で kernel level の隠蔽が疑われる
- syscall hook / hidden module / DKOM / eBPF 由来 backdoor の調査
- artifact_analysis BC `FileKind.MEMORY_DUMP` で Linux

**使わない場面**: user-land rootkit (→ `rootkit-analysis`、`reverse-engineering`)、bootkit 系 (→ `rootkit-analysis`、`rootkit-analysis`)。

## Approach / Workflow

### Phase 1 — memory dump triage

```bash
vol3 -f mem.lime linux.info
vol3 -f mem.lime linux.lsmod
vol3 -f mem.lime linux.check_modules           # /sys/module との diff
vol3 -f mem.lime linux.hidden_modules          # struct module 連結 list traverse
vol3 -f mem.lime linux.check_syscall           # syscall table hook
vol3 -f mem.lime linux.check_idt               # IDT hook
vol3 -f mem.lime linux.check_creds             # creds 共有異常
vol3 -f mem.lime linux.malfind                 # 注入 region
```

### Phase 2 — 検出 pattern

```
syscall hook:    sys_call_table の特定 entry が module 範囲外を指す
LKM hide:        modules list (lsmod) と struct module の双方向 list で diff
DKOM:            task_struct の prev/next を編集して process を hide
file hide:       getdents / getdents64 系 hook で /proc/<pid> を 隠蔽
network hide:    tcp_seq_show / udp_seq_show を hook して socket を hide
log clean:       ftrace / printk hook
eBPF abuse:      kprobes 経由で kfunc を hook、TC hook / XDP hook で network 改竄
```

### Phase 3 — live host での検査 (live forensics)

```bash
rkhunter --check --skip-keypress
chkrootkit
tripwire --check                          # IDS が事前 baseline ある場合

# /proc vs /sys diff
diff <(ls /proc/ | grep '^[0-9]' | sort) <(ps -ef | awk '{print $2}' | sort -u)
diff <(cat /proc/modules | awk '{print $1}' | sort) <(ls /sys/module/ | sort)

# socket hide 検出
ss -tnpa
netstat -tnpa
# 出力差や lsof -i との不一致

# /etc/ld.so.preload (LD_PRELOAD persistence)
cat /etc/ld.so.preload

# eBPF program
bpftool prog list
bpftool map list
```

### Phase 4 — 既知 family

```
LKM rootkit:
  Reptile / Diamorphine / Suterusu / Adore-Ng / KoviD
eBPF rootkit:
  Boopkit / TripleCross / ebpfkit
DKOM only:
  custom kit (case-by-case)
runtime LKM injection (LKM 不要):
  zero-init kernel exploit + memory inject
```

### Phase 5 — extracted module の解析

memory から LKM を抽出:

```bash
vol3 -f mem.lime linux.lsmod --dump      # module を file に
file extracted.ko
```

抽出 .ko を Ghidra (Linux x86-64) で解析:

```
- module_init / module_exit
- syscall hook 関数
- 隠蔽 logic (process / file / module / port)
- 永続化 (modprobe.d / /etc/modules-load.d / cron)
- C2 / command 実行 (kthread_run + connect)
```

### Phase 6 — eBPF program 抽出

```bash
bpftool prog dump xlated id <id>          # eBPF bytecode
bpftool prog dump jited id <id>            # JIT 済 native
```

不審 program は load 元 (process) と attach 先 (kprobe / tracepoint / cgroup / xdp) を確認。

### Phase 7 — 修復

```
1. 隔離 (network 切断)
2. memory dump 取得 (LiME)
3. snapshot disk image
4. evidence 保全後、kernel 再 build / OS 再インストール
5. 再起動前に /etc/modules-load.d / autoload / dracut config を確認
6. baseline IDS / sysdig / falco を再導入
```

### Phase 8 — レポート / IOC

```
- 検出 method (vol3 plugin / rkhunter / diff)
- 推定 family / 類似度
- hook 一覧 (syscall / file / process / network)
- 抽出 .ko / eBPF prog の hash
- 永続化機構
- 推奨対応
```

## Tools

```
volatility3 (linux plugins)
rkhunter / chkrootkit / tripwire
ghidra
bpftool / bpftrace
strace / ltrace
WebFetch
Bash (sandbox)
```
