
# Threat Intelligence Report Generation

`threat-intel` から呼ばれる variant 別 deep dive

## When to Use

- IR / investigation の結果を 内外 stakeholder に報告
- 月次 / 四半期の TI report
- alert に対する actor analysis を一発加える形
- TI feed の subscriber に向けたレポート

**使わない場面**: 単発 IOC sheet (→ `threat-intel`)、actor TTP 分析 (→ `threat-intel`)、attribution 研究 (→ `threat-intel`)。

## Approach / Workflow

### Phase 1 — audience / 目的の確定

```
strategic (executive / board)
   - "誰が我々を狙っているか" "影響" を short narrative
   - 数 page、技術詳細 抑える
operational (defense team)
   - 攻撃 chain / detection rule / mitigation の actionable な情報
   - MITRE ATT&CK 番号 / sigma / yara
tactical (SOC analyst / IR)
   - IOC / yara / sigma / pcap pattern
   - すぐ feed / SIEM に投入できる format
```

### Phase 2 — 構造 (推奨)

```
1. Executive Summary (3-5 文 / TLP / confidence)
2. Background (campaign / actor / 観測期間)
3. Attribution
   - actor / cluster
   - confidence (information / low / moderate / high)
   - 帰属根拠 (TTP / infra / code / lang)
4. TTPs (MITRE ATT&CK Matrix mapping)
5. Tooling / Infrastructure
6. Targeting (industry / geography / role)
7. Detection / Hunting Guidance
   - sigma / yara / suricata rule
   - SIEM query (KQL / SPL)
8. Mitigations
9. IOCs (Appendix)
10. References
```

### Phase 3 — confidence / 推定の表現 (ICD 203)

```
We assess with high confidence that  ≥ 80%
We assess with moderate confidence that  50-80%
We assess with low confidence that  20-50%
There is some indication that  < 20% (informational)
```

これらの語彙で各 claim の確度を明示。

### Phase 4 — Appendix の IOC sheet

```
| Type | Value | First Seen | Last Seen | Confidence | TLP | Notes |
|---|---|---|---|---|---|---|
| ipv4 | 1.2.3.4 | 2024-01-01 | 2024-01-15 | high | GREEN | C2 endpoint observed in campaign X |
| domain | evil.com | ... | ... | | | |
| sha256 | <hash> | ... | ... | | | |
```

STIX 2.1 / MISP event 形式で別途 export。

### Phase 5 — 言語 / トーン

```
- 客観的 / 推定 / 観察 を区別
- 受身よりも能動 (avoid 'was observed' 連発)
- 短い段落 / bullet で読みやすく
- 専門用語を audience に応じて解説
```

戦略向けは 'so what?' を最初に書き、技術 detail は付録に押し込む。

### Phase 6 — TLP / sharing

```
- 各 section の TLP color
- 共有 partner 名 (specific recipient list for TLP:AMBER+STRICT / RED)
- redaction (内部 host / 個人情報)
- watermark (organization / report id)
```

### Phase 7 — レビュー / quality gate

```
- claim ごとに citation あり?
- confidence 表記が claim 強度と一致?
- attribution の根拠が複数?
- IOC が SIEM に投入可能 format?
- detection rule が動作確認済?
- 受け取り先 stakeholder の audience に合った詳細度?
```

### Phase 8 — 自動化

```
- structured input (incident summary + IOC list + actor mapping) を template に流し込む
- jinja2 / handlebars で markdown 生成
- pdf / docx 化 (pandoc)
- MISP / OpenCTI に export (STIX)
```

## Tools

```
markdown / pandoc
MISP / OpenCTI (event 管理)
ATT&CK Navigator
sigma / yara / suricata (rule)
WebFetch / WebSearch
Bash (sandbox)
```
