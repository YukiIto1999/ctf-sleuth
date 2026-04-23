
# UEFI Bootkit Persistence Analysis

`rootkit-analysis` から呼ばれる variant 別 deep dive

## When to Use

- UEFI レイヤ persistence (BlackLotus / LoJax / CosmicStrand 等) の専門解析
- SPI flash dump / firmware capsule の精査
- Secure Boot bypass の検証
- ESP 内 EFI binary の改竄調査

**使わない場面**: Legacy MBR/VBR bootkit のみ (→ `rootkit-analysis`)、kernel rootkit (→ `rootkit-analysis`)。

## Approach / Workflow

### Phase 1 — dump 取得

```bash
# Linux ホストで SPI flash dump (要 root)
chipsec_util spi dump spi_dump.bin

# UEFI shell から
fpt -r -bios bios_dump.bin

# capsule (vendor 配布) も同様に解析
```

dump サイズは 8 / 16 / 32 MB が一般。

### Phase 2 — UEFITool で構造解析

```
UEFITool spi_dump.bin
# 階層:
# - SPI flash regions (Descriptor / GbE / ME / BIOS)
# - BIOS region 内 Firmware Volume
# - Firmware File: PEI / DXE / SMM / EFI driver / app
```

不審 module を特定:

```
- 標準 vendor (AMI / Phoenix / Insyde / Lenovo / HP) に無い GUID
- 不釣り合いに大きい module
- 圧縮済 (LZMA / TIANO) でない裸の PE module
- 過去 dump と diff で増減
```

### Phase 3 — module 抽出 + 解析

UEFITool で `.efi` を export → Ghidra で解析:

```
Language: x86-64 / x86 (CPU mode に応じて)
```

```
EFI_STATUS EfiMain(EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *SystemTable) {
    // BootService (BS) / RuntimeService (RT) hook
    SystemTable->BootServices->LocateProtocol(...);
    SystemTable->BootServices->OpenProtocol(...);
    SystemTable->RuntimeServices->GetVariable(...);
}
```

bootkit の典型コード:

- `EFI_LOAD_FILE_PROTOCOL` の hook
- `EFI_BOOT_SERVICES->LoadImage` / `StartImage` の override
- Windows boot manager (`bootmgfw.efi`) を memory 上で patch
- secure boot db / dbx (signature db) の改竄
- NVRAM Variable に payload を保存し再起動越しに復元

### Phase 4 — Secure Boot 状態

```bash
mokutil --sb-state          # SecureBoot enabled/disabled
efivar -l                   # NVRAM 一覧
efivar -p -n <GUID>-<Name>  # 中身表示
```

確認:

```
- SecureBoot = 1 (enabled)
- SetupMode = 0 (production)
- PK / KEK / db / dbx の content
- 攻撃で PK が削除 / 改竄されると custom mode に転落
- BlackLotus は dbx (revocation list) 改竄を使う
```

### Phase 5 — ESP (EFI System Partition) 検査

```bash
mount -o ro /dev/sda1 /mnt/esp
ls /mnt/esp/EFI/<vendor>/
file /mnt/esp/EFI/Microsoft/Boot/bootmgfw.efi
sha256sum /mnt/esp/EFI/Microsoft/Boot/*.efi
```

vendor 標準 .efi の hash と比較し改竄を確認。攻撃者が ESP に独自 .efi を置き、BCD で起動順序を変えるパターンも。

### Phase 6 — chipsec での追加検査

```bash
chipsec_main.py -m common.bios_wp           # BIOS write protect
chipsec_main.py -m common.spi_lock           # SPI lock
chipsec_main.py -m common.secureboot.variables
chipsec_main.py -m tools.uefi.scan_image -a uefi.cfg
chipsec_main.py -m tools.secureboot.te
```

不審 module / signature 不整合を検出。

### Phase 7 — 修復

```
1. SPI flash の正規 firmware を vendor から取得
2. dump 取得して compare → 改竄部位確認
3. 修復可能なら fpt / Programmer で reflash
4. 不能なら mainboard 交換が安全
5. ESP 上の .efi を vendor 正規版に置換
6. NVRAM 変数を default に
7. Secure Boot 再設定 (PK / KEK / db / dbx)
```

### Phase 8 — レポート / IOC

```
- 検出した implant の所在 (region / module GUID / hash)
- module の機能解析 summary
- Secure Boot bypass の手法
- NVRAM 変数の改竄状況
- 推奨修復手順
- yara / fwhunt rule の draft
```

## Tools

```
chipsec / chipsec_util
UEFITool
ghidra (UEFI module)
binwalk
fwhunt-scan / fwts
mokutil / efivar
WebFetch
Bash (sandbox)
```
