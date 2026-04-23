---
name: social-engineering
description: phishing / pretext / vishing / 物理 SE を 認可された scope で計画・実行・評価する。red team / 演習 / awareness 評価で発火。
category: pentest
tags:
  - social-engineering
  - phishing
  - pretext
  - vishing
  - physical
---

# Social Engineering

## When to Use

- 認可済 phishing / pretext / vishing exercise
- 物理 access (USB drop / 入館) 試験
- 組織 awareness 評価
- HTB / red team chain の初期 access として SE が許可されている場合

**使わない場面**: scope 外の対人接触、無認可の私的調査、harm を伴う試験。

## Approach / Workflow

### Phase 1 — 認可と RoE 確認

```
- 文書化された RoE (Rules of Engagement)
- target 範囲 (どの employee に / どの level の試験まで)
- 機密情報の取扱 (取得した credential / 内部 doc)
- escalation 連絡先 (法務 / HR)
- 心理的負荷の minimization
```

### Phase 2 — OSINT で pretext 設計

```
- LinkedIn / GitHub / 会社 web から組織 / 役職 / 関係性
- 公開イベント / press release / job posting
- SNS で発言から興味 / 専門領域
- 似 domain 取得 (typosquat)
- 組織内 jargon / プロセス語彙
```

### Phase 3 — phishing (email)

```
- gophish / King Phisher / SET
- 送信 infrastructure: SPF / DKIM / DMARC を整える (clean reputation)
- pretext: "HR 通知" "給与" "セキュリティ警告" "請求書" "OAuth consent"
- 仕掛け:
    1. 添付 (xlsm / docm / PDF) で OAuth / OTP 入力誘導
    2. link 先で SSO 風 phishing site → credential / OTP 取得
    3. browser-in-the-browser (BITB) phishing
    4. OAuth consent 攻撃 (illicit consent grant)
    5. M365 device code phishing
- tracking: open / click / submit を gophish などで集計
```

### Phase 4 — vishing / smishing

```
vishing: 電話で IT support 装い credential / OTP を聞く
smishing: SMS で 短縮 URL / 偽装通知 → phishing site
深層には Caller ID spoofing (engagement で要承認)
```

### Phase 5 — 物理

```
- USB drop (parking / cafeteria)
- tailgating
- 制服 / clip board pretext
- 侵入時の写真撮影 / 文書回収
- visitor badge 模倣
- 物理 lock pick (engagement で明示認可)
```

### Phase 6 — 取得後の処理

```
- credential はすぐに 監視チームと sync
- 一般 employee の private info は触れない
- 再発防止 / awareness 訓練の素材として利用
- victim 個人の identification は report で redact
```

### Phase 7 — レポート / awareness

```
- 期間 / scope / 送信件数 / open / click / submit ratio
- 攻撃 chain (どこまで届いたか)
- 防御点 (filter caught / employee reported)
- awareness 改善提案 (training / report ボタン / process)
- 個人特定を避けた集計
```

## Tools

```
gophish / King Phisher / SET
evilginx2 / modlishka / Muraena (BITB / reverse proxy phishing)
profile builder / pretext template
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `red-teamer`, `reconnaissance`, `osint`, `techstack-identification`, `bug-bounter`
- `phishing-investigation`, `threat-intel`
- `detection-web`, `testing-oauth2-implementation-flaws`
- `essential-tools`

## Rules

1. **scope 明確化** — 文書化された RoE に厳密に従う
2. **harm 最小化** — 個人のプライバシー / 心理的負荷を最小に
3. **法令 / 倫理** — 録音 / 撮影 / 入館は法的に認可されているか確認
4. **取得情報** — sealed area + minimum exposure
5. **debrief / awareness 教育** — 演習後に被害ありなしを問わず教育
