
# APT Analysis with MITRE ATT&CK Navigator

`threat-intel` から呼ばれる variant 別 deep dive

## When to Use

- 既知 APT actor (APT29 / APT41 / Lazarus / Sandworm 等) の TTPs を整理
- 自社 detection / mitigation の coverage 評価
- IR 中の actor 推定 / 攻撃 chain との照合

**使わない場面**: actor 情報のない初動調査 (→ `osint`、`ioc-hunting`)、技術別 deep dive (→ 個別 skill)。

## Approach / Workflow

### Phase 1 — Navigator 起動

```
オンライン:    https://mitre-attack.github.io/attack-navigator/
ローカル:     git clone https://github.com/mitre-attack/attack-navigator
              docker compose up
```

ATT&CK Matrix を JSON layer として load。Enterprise / Mobile / ICS の Matrix を選択。

### Phase 2 — APT group の TTP 取得

ATT&CK にある:

```
- Group page (例: G0007 APT28) に associated technique 一覧
- subtechnique まで含む
- software / tool 一覧
```

```bash
# stix2 / TAXII 経由で取得
curl -s "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/intrusion-sets/intrusion-set--<id>.json"
```

### Phase 3 — Navigator layer JSON

```json
{
  "name": "APT29 coverage",
  "domain": "enterprise-attack",
  "techniques": [
    {"techniqueID": "T1566.001", "score": 1, "color": "#ff0000"},
    {"techniqueID": "T1059.001", "score": 1, "color": "#ff0000"},
    ...
  ]
}
```

```
score:    自社 coverage (0=未検知 / 1=部分検知 / 2=完全検知)
color:    視覚化色
comment:  detection rule reference
```

### Phase 4 — 自社 coverage 評価

```
- 各 technique について 検知 rule (Sigma / SIEM) があるか
- block 機能 (EDR / FW / WAF) があるか
- gap analysis: actor の TTP と自社 coverage の差
- patch / mitigation 適用済か
```

### Phase 5 — multi-actor 重ね合わせ

複数 layer を重ねると共通 TTP / 自社にとって最重要 technique が浮上:

```
APT29 layer + APT41 layer + Lazarus layer = 共通 TTP
共通部分は detection 優先度 critical
```

### Phase 6 — 自社 incident との照合

IR 中に観察された TTP を ATT&CK ID で記録 → Navigator layer で可視化:

```
Initial Access: T1566.001 phishing attachment
Execution:      T1059.003 cmd / T1059.001 powershell
Persistence:    T1547.001 registry run key
Privilege Esc:  T1055.012 process hollowing
Defense Evasion: T1027 obfuscated
Credential Acc: T1003.001 LSASS dump
Discovery:      T1083 file/dir discovery / T1057 process
Lateral:         T1021.002 SMB
Collection:      T1560.001 archive
Exfiltration:   T1041 C2 channel exfil
Impact:          T1486 encrypt
```

actor cluster mapping で 「APT-XX に類似」を出す。

### Phase 7 — TI feed との連動

```
- MISP cluster (APT cluster)
- ThreatConnect / Recorded Future / Mandiant
- CISA AAs (Joint Advisory)
- CERT 公開情報
```

actor profile の 確度 (high / moderate / low) を score に反映。

### Phase 8 — レポート

```
- 評価対象 actor / グループ
- 自社 coverage matrix
- gap (未検知 / 未防御 TTP)
- 優先度付き improvement plan
- 推奨 (rule 開発 / EDR 設定 / patch / training)
```

## Tools

```
MITRE ATT&CK Navigator
attack-website / attack-stix-data
sigma / atomic-red-team (テスト)
WebFetch / WebSearch
Bash (sandbox)
```
