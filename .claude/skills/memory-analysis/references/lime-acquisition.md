
# Linux Memory Forensics with LiME + Volatility 3

`memory-analysis` から呼ばれる variant 別 deep dive

## When to Use

- ライブ Linux ホストから memory を取得する必要がある (LSASS 相当の構造はないが、heap / kernel / process memory が必要)
- CTF / DFIR で Linux memory dump 取得手順を再現したい
- IR で侵害 Linux ホストの memory 取得 → 別ホストで vol3 解析を行う

**使わない場面**: dump 取得済みで解析のみ (→ `memory-analysis` / `memory-analysis`)、Windows host (→ `procdump` / `winpmem`)。

## Approach / Workflow

### Phase 1 — LiME 準備

LiME は kernel module として load されるので、対象 kernel に対応する build が必要。

```bash
# 取得 (受信側)
git clone https://github.com/504ensicsLabs/LiME

# 送信ホスト (調査対象) で build
cd LiME/src
make
# → lime-<KERNEL_VERSION>.ko が生成
```

kernel header / build-essential が無いホストでは事前 build した module を持ち込む。

### Phase 2 — dump 取得

ローカルに保存:

```bash
sudo insmod ./lime-$(uname -r).ko "path=/mnt/evidence/mem.lime format=lime"
```

ネット経由（forensics best practice — local 書込で fs を汚さない）:

```bash
# 受信側
nc -lvp 4444 > mem.lime
# 送信側
sudo insmod ./lime-$(uname -r).ko "path=tcp:<RECEIVER_IP>:4444 format=lime"
```

LiME format は header + segment 列。Volatility 3 が直接読める。

### Phase 3 — チェーン保全

```bash
sha256sum mem.lime > mem.lime.sha256
gpg --sign mem.lime.sha256
```

evidence chain として日時 / ホスト / 取得者 / 取得方法を別記。

### Phase 4 — Symbol 生成

LiME dump 解析には対応 kernel ISF が必要。

```bash
# 対象 kernel の vmlinux / dwarf を取得
# Ubuntu: dbgsym package (ddebs.ubuntu.com)
# Debian: linux-image-...-dbg
# CentOS/RHEL: kernel-debuginfo

git clone https://github.com/volatilityfoundation/dwarf2json
cd dwarf2json && go build
./dwarf2json linux \
  --elf /usr/lib/debug/boot/vmlinux-$(uname -r) \
  > kernel-$(uname -r).json
mv kernel-$(uname -r).json ~/.local/share/volatility3/symbols/linux/
```

clone 不能環境では `volatility3-symbols` distro パッケージ / GitHub release を使う。

### Phase 5 — Triage

```bash
vol3 -f mem.lime linux.info
vol3 -f mem.lime linux.pslist
vol3 -f mem.lime linux.pstree
vol3 -f mem.lime linux.psaux
vol3 -f mem.lime linux.bash
vol3 -f mem.lime linux.lsmod
vol3 -f mem.lime linux.sockstat
vol3 -f mem.lime linux.malfind
vol3 -f mem.lime linux.envars
```

優先抽出:

- `linux.bash` で historical コマンド
- `linux.psaux` で argv / 起動親子関係
- `linux.sockstat` で外部接続
- `linux.malfind` で injection / shellcode

### Phase 6 — kernel 系試験

```bash
vol3 -f mem.lime linux.check_modules         # /sys/module との不一致
vol3 -f mem.lime linux.hidden_modules        # struct module list traverse
vol3 -f mem.lime linux.check_syscall         # syscall table hook
vol3 -f mem.lime linux.check_idt             # IDT hook
vol3 -f mem.lime linux.check_creds           # creds 共有異常
vol3 -f mem.lime linux.elfs                  # process 上の ELF mapping
```

詳細は `rootkit-analysis` 参照。

### Phase 7 — file / mount

```bash
vol3 -f mem.lime linux.mountinfo
vol3 -f mem.lime linux.lsof
vol3 -f mem.lime linux.envars
```

mount table の異常 (`/proc` を覆う overlay 等) は LD_PRELOAD ベース userspace rootkit のサイン。

### Phase 8 — レポート

```
- 取得方法 (LiME version / kernel / 取得時刻)
- ISF 出所 (dbgsym / 自前 build)
- 不審 process / 親子関係 / cmdline / bash history
- 外部接続候補
- 注入 / hidden module 兆候
- 永続化候補 (cron / systemd / autostart)
- 推奨対応
```

## Tools

```
LiME (kernel module)
volatility3 (vol3)
dwarf2json
nc (netcat) for remote acquisition
sha256sum / gpg
WebFetch
Bash (sandbox)
```
