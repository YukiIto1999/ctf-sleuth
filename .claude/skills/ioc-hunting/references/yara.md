
# YARA-based Threat Hunting

`ioc-hunting` から呼ばれる variant 別 deep dive

## When to Use

- file system / memory / packet 内の既知 / 推定 malware を pattern で hunt
- rule 開発 (新規 family / variant 用)
- 自社 / community ruleset の運用

**使わない場面**: IOC 単純 lookup (→ `ioc-hunting`)、binary 単発 rev (→ `reverse-engineering`)。

## Approach / Workflow

### Phase 1 — YARA rule 構造

```yara
rule MyMalware_v1
{
    meta:
        author = "myteam"
        date = "2024-01-15"
        family = "MyMalware"
        tlp = "GREEN"
        reference = "https://blog..."

    strings:
        $magic = { 4D 5A 90 00 ?? ?? ?? ?? FF FF }
        $s1    = "Mozilla/5.0 (Custom UA)" wide ascii
        $s2    = /\/api\/v[0-9]+\/log\?id=[a-z0-9]+/ ascii
        $crypt = { 60 FB 67 8C 30 [4-8] 1A 2C }

    condition:
        uint16(0) == 0x5A4D and
        filesize < 5MB and
        2 of ($s*) and
        $magic
}
```

### Phase 2 — rule 開発 workflow

```
1. sample 取得 + triage
2. unique strings / patterns を発見
3. 'goodware' (常用 binary) で false positive 確認
4. 別 sample でも matching するかで family 範囲 確認
5. メタ情報 (family / version / TLP / 参照)
6. condition tighten (filesize / type / multiple AND)
7. test — yara -r rules/ samples/
```

### Phase 3 — file system hunt

```bash
yara -r rules/ /var/data/                # 再帰
yara -p 8 rules/ files/                  # 並列 8 スレッド
yara -L rules/ samples/                  # match 出力
yara --print-strings rules/ samples/     # match string 出力
yara --print-meta rules/ samples/         # meta print
```

### Phase 4 — memory hunt (Volatility 連携)

```bash
vol3 -f mem.raw yarascan.yarascan --yara-rules rules/
```

memory 上の MZ / shellcode / suspicious string を識別。

### Phase 5 — packet hunt

```bash
suricata --runmode autofp -c suricata.yaml -r in.pcap
# yara plugin あり (suricata-update yara-rules)
zeek -r in.pcap (zeek script で yara を呼ぶ)
```

または `nDPI` / `tshark + yara` の組合せ。

### Phase 6 — 公開 ruleset

```
yara-forge:                 community 統合 ruleset
ditekshen/yara-rules:        高品質 family rule 集
elastic/protections-artifacts: Elastic 公開 yara
fireeye/yara-base:            (Mandiant 由来)
malwarebazaar:                family rule sharing
threatfox:                     C2 IOC -> yara 化
```

組合せて運用、ただし false positive は自社環境で test。

### Phase 7 — rule の品質 / 公開

```
- false positive rate を測定
- 'goodware' set (Microsoft binary / 一般 lib) で test
- 似 family の rule を inheritance / module で集約
- 公開時は TLP / license / disclaimer
```

### Phase 8 — automation / CI

```
- pre-commit hook で rule の syntax / format check
- CI で 標準 sample set (clean + malicious) に対して rule fire 確認
- production 前に 1 週間程度 audit mode で fire 観察
- alert 化基準 を threshold で
```

### Phase 9 — レポート / IOC 共有

```
- developed rule (count / family / TLP)
- false positive rate
- detected sample / cluster
- 推奨 (rule 投入 / sigma 連携 / FW signature)
```

## Tools

```
yara / yara-forge / yara-rules
yarGen (ベース rule 自動生成)
yarAnalyzer / Klara (rule scanning + retrohunt)
malwarebazaar / threatfox (sample / rule)
volatility3 (yarascan)
suricata + yara plugin
WebFetch / WebSearch
Bash (sandbox)
```
