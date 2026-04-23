
# Firmware Extraction with binwalk

`firmware-iot-security` から呼ばれる variant 別 deep dive

## When to Use

- router / IoT / camera / printer の firmware image 解析
- artifact_analysis BC `FileKind.FIRMWARE`
- CTF hardware で firmware blob が flag 隠し場所

**使わない場面**: extracted file system 内 binary の解析 (→ `reverse-engineering` / `reverse-engineering`)、live device に対する hardware attack (→ `firmware-iot-security`)。

## Approach / Workflow

### Phase 1 — image triage

```bash
file fw.bin
sha256sum fw.bin
xxd fw.bin | head
ent fw.bin                          # entropy (圧縮 / 暗号化判定)
```

entropy ~ 8.0 → 圧縮 / 暗号化、構造特定が困難。

### Phase 2 — binwalk 実行

```bash
binwalk fw.bin                       # signature scan
binwalk -e fw.bin                     # extract embedded
binwalk -Me fw.bin                    # 再帰的 extract
binwalk --dd='*' fw.bin               # 全 signature を file 化
binwalk -A fw.bin                     # opcode 走査
binwalk -E fw.bin                     # entropy graph
```

検出される構造:

```
- bootloader (U-Boot)
- kernel image (uImage / vmlinux / zImage)
- root filesystem (squashfs / jffs2 / ubifs / yaffs / cramfs / ext2/3/4)
- device tree (DTB)
- compressed (gzip / lzma / xz / lz4 / lzo)
- encrypted (high entropy)
- 自前 packaging (vendor magic)
```

### Phase 3 — squashfs / jffs2 等の取扱

```bash
# squashfs
unsquashfs -d ./rootfs out.squashfs

# jffs2
mkdir -p mnt
mount -o loop -t jffs2 out.jffs2 mnt    # 古い、現代 kernel で要 module

# ubifs
ubidump -i out.ubi out_ubidump          # ubi_reader

# cramfs
mount -o loop -t cramfs out.cramfs mnt
```

mount できない場合は専用 tool:

```
ubi_reader / fwextractor / firmwalker
```

### Phase 4 — unblob (modern alternative)

```bash
pip install unblob
unblob fw.bin -o ./out
```

binwalk より新規 format への対応が広く、再帰展開も robust。

### Phase 5 — root filesystem 内 audit

extracted rootfs:

```
/etc/passwd / /etc/shadow            user / hash
/etc/init.d/ / /etc/rc.d/             起動 script
/etc/inittab
/etc/network/                         interface 設定
/etc/dropbear/                        SSH host key (default)
/etc/wpa_supplicant/                  WiFi 認証情報
/usr/bin /usr/sbin /sbin              custom binary
/usr/share/                           web UI / config / 暗号 key
/var/spool/cron/                      cron
SSH authorized_keys                   default key
TLS cert / key (HTTPS web UI)
firmware-default config / customer-overlay
```

### Phase 6 — binary 解析

抽出 binary を Ghidra / radare2 で解析:

```
- arch (MIPS-BE / MIPS-LE / ARM / x86 / ARM64 / PowerPC) 同定
- 言語 (uClibc / glibc 静的 link)
- vulnerable lib version (古い OpenSSL / dropbear / busybox)
- hardcoded credential / key
- network listening port
```

### Phase 7 — 暗号化 firmware

```
- 上 entropy 帯 → 暗号化 / 圧縮
- vendor 公開 update tool で 復号 logic を rev (RSA + AES 系が多い)
- 公開 firmware update binary に key が hardcoded されているケース
- secure boot を bypass しない限り部分のみ復号
```

### Phase 8 — レポート

```
- firmware identity (hash / vendor / version)
- 抽出 file system / 主要 path
- 検出 binary / library version
- 漏洩 default credential / key / cert
- network 公開 service
- 推定 OS / kernel
- 推奨修正 (vendor 通報 / 自社ならパッチ)
```

## Tools

```
binwalk / unblob / firmware-mod-kit
unsquashfs / ubidump / 7z
ent / xxd / strings
ghidra / radare2 / IDA
WebFetch
Bash (sandbox)
```
