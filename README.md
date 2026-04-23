# ctf-sleuth

> Claude Agent SDK を用いた CTF / OSINT / ファイル解析 / HackTheBox machine の個人演習用セキュリティフレームワーク

## 概要

入力文字列 (URL / ファイルパス / IP / ドメイン / 自由テキスト) を自動分類し、4 種類の task runner のいずれかを起動する。各 runner は sandbox の要否や必須パラメータが異なる。LLM は Claude Max サブスクのみを利用し、API 課金は発生しない。

## 対応タスク

| task_type | 用途 | sandbox |
| --- | --- | --- |
| `ctf_challenge` | CTFd Jeopardy を pull して逐次 solve し flag を submit | 必要 |
| `htb_machine` | HackTheBox machine の user / root flag を取得 | 必要 |
| `artifact_analysis` | 単一ファイル (binary / pcap / memory dump 等) を解析 | 必要 |
| `osint_investigation` | 公開情報のみで対象を調査 | 不要 |

## 前提

- NixOS + WSL2 相当 (他 Linux でも devenv 対応環境であれば可)
- Claude Max サブスクで `claude login` 済
- Docker Engine 稼働 (sandbox を使う task で必要)

## インストールと実行

```bash
devenv shell                   # 開発シェル
uv sync                        # Python 依存取得 (初回のみ)
just sleuth run "<入力>"       # タスク実行
```

## アーキテクチャ

VSlice 骨格で BC (Bounded Context) 単位に凝集する構造を採用。

```
src/
├── contexts/<bc>/     # 4 BC (ctf_challenge / htb_machine / artifact_analysis / osint_investigation)
├── workflows/         # BC 横断ユースケース (dispatch)
├── foundation/        # 技術基盤 (metrics 等)
├── layers/            # adapter 実装 (claude_sdk / sandbox / ctfd / htb / ...)
├── shared/            # BC 横断純粋値 + 横断 port
└── cli/               # Composition Root + エントリ
```

依存方向は `import-linter` で CI 強制。詳細は [CLAUDE.md](CLAUDE.md) 参照。

## 成果物

実行結果は `writeups/<YYYYMMDD-HHMMSS>-<task_type>-<hash>/` 配下に 4 ファイルで保存される。

| ファイル | 内容 |
| --- | --- |
| `manifest.yml` | 実行メタ (秘匿キーはマスク) |
| `report.md` | 人間可読レポート |
| `evidence.jsonl` | 観察記録の追記ログ |
| `result.json` | 機械可読 payload |

## ドキュメント

| リンク | 内容 |
| --- | --- |
| [CLAUDE.md](CLAUDE.md) | Claude Agent SDK が自動ロードするプロジェクトガイド |
| [.claude/skills/README.md](.claude/skills/README.md) | skill フォーマット仕様 |

## ライセンスと利用条件

[MIT License](./LICENSE) © 2026 YukiIto1999

攻撃対象は明示的に許可された演習環境・CTF・自分の所有物に限定する。
OSINT は公開情報のみを対象とし、認証突破や非公開データへのアクセスは行わない。
対人 OSINT では対象への直接接触を行わない。
