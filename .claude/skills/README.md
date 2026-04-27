# .claude/skills — 統合 skill 集

CTF / OSINT CTF / セキュリティ演習で使う skill を統一フォーマットで集約したディレクトリ。
Claude Agent SDK (および Claude Code) が自動ロードする。

全 skill は MIT-original で書かれている。
許可 skill 名集合と src/ 側の参照整合は `src/foundation/skills/registry.py` + `tests/foundation/skills/test_registry.py` で機械検証する (`just archcheck` / `just test`)。

## 統一フォーマット

各 skill は `.claude/skills/<kebab-name>/SKILL.md` に配置する。
variant 別の deep-dive は `.claude/skills/<name>/references/<variant>.md`。

```yaml
---
name: <kebab-case>
description: <いつ発火すべきかを明示する 1-2 行>
category: <下記カテゴリ表から 1 つ>
tags: [<最大 8 個>]
---
# <タイトル>

## When to Use
<発火トリガ、および「使わない」条件>

## Approach / Workflow
<手順。phase 分けや番号付きステップが理想>

## Tools
<具体ツール名>

## Related Skills
<他 skill への kebab-name 参照>

## Rules
<遵守事項>
```

### フィールド仕様

- **name**: ディレクトリ名と完全一致させる。
  kebab-case
- **description**: Claude が skill 発火を判断する主材料。
  「いつ使うか」を明示する。
  曖昧語 ("helpful", "useful") は避け、具体トリガを書く
- **category**: 下表から **1 つ** だけ選ぶ (必須)

| category | 用途 |
| --- | --- |
| `ctf` | CTF 全般、一般手順 |
| `pentest` | ペネトレーションテスト方法論 |
| `osint` | OSINT 調査 |
| `dfir` | DFIR / incident response |
| `forensics` | フォレンジック (disk / memory / network / endpoint の個別手法) |
| `reverse` | リバースエンジニアリング / malware analysis |
| `crypto` | 暗号解析・実装検証 |
| `web` | Web アプリ攻撃・防御 |
| `mobile` | Android / iOS |
| `hardware` | 無線 / SDR / firmware / IoT |
| `bug-bounty` | バグバウンティ方法論 |
| `network` | ネットワーク解析全般 |
| `cloud` | クラウド (AWS / Azure / GCP / Kubernetes) |
| `intel` | threat intelligence / IOC / attribution |
| `defender` | blue team の検知 / hunting / detection rule |
| `general` | 横断的 / 分類困難 |

- **tags**: 任意。
  検索性向上用。
  最大 8 個、kebab-case

### 本文節

- `## When to Use` のみ必須
- `Approach / Workflow`, `Tools`, `Related Skills`, `Rules` は存在すれば書く
- 冗長な装飾 (ASCII art 大規模バナー等) は削る

### Domain organization

複数 variant を扱う skill は **parent SKILL.md (workflow + variant 選択 decision tree) + `references/<variant>.md` (variant 別 deep dive)** の構成を取る。
SKILL.md は概ね 500 行以下を目安、超えるなら variant を references に分離する。

## ディレクトリ構成の例

```
.claude/skills/
├── README.md                           # 本ファイル
├── injection/
│   ├── SKILL.md
│   └── references/
│       ├── sql-manual.md
│       ├── sql-sqlmap.md
│       ├── sql-second-order.md
│       └── nosql.md
├── memory-analysis/
│   ├── SKILL.md
│   └── references/
│       ├── volatility3.md
│       ├── volatility.md
│       ├── lime-acquisition.md
│       ├── rekall.md
│       ├── credentials.md
│       └── heap-spray.md
└── reverse-engineering/
    ├── SKILL.md
    └── references/
        └── ...
```

## 追加・削除のルール

- **追加**: 新 skill の `<name>/SKILL.md` を作成し、`src/foundation/skills/registry.py` の `_NAMES` に追記する。
  `tests/foundation/skills/test_registry.py` が disc と registry の一致を検証する
- **削除**: ディレクトリを `rm -rf` し、registry / src/contexts の参照を同時更新する。
  test_registry が乖離を検知する
- **改名 / 統合**: 同様に registry と src/contexts を同時更新

新 skill の作成は `skill-creator` (Anthropic 公式 plugin) に従う。
既存 skill の改善は `empirical-prompt-tuning` (mizchi/skills) で 2 面評価 + iterate する。
