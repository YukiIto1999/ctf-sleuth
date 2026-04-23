# ctf-sleuth — プロジェクトガイド

プロジェクト概要は @README.md、skill フォーマット仕様は @.claude/skills/README.md を参照。

## アーキテクチャ

VSlice を骨格として Hexagonal 系の層分離を組み合わせた構造 (canonical-logic 準拠)。

```
src/
├── contexts/<bc>/{domain,policies,services,<slice>,runner}  # BC 単位
├── workflows/dispatch/                                       # BC 横断ユースケース
├── foundation/metrics/                                       # 技術基盤
├── layers/                                                   # adapter 実装
├── shared/                                                   # BC 横断純粋値 + 横断 port
└── cli/                                                      # Composition Root + エントリ
```

依存方向は `import-linter` で CI 強制 (`just archcheck`)。

## 主要コマンド

root の `justfile` から実行する。

| コマンド | 用途 |
| --- | --- |
| `just sleuth run "<入力>"` | タスク自動分類と実行 |
| `just check` | lint + typecheck + archcheck + test |
| `just test` / `just lint` / `just typecheck` | 個別実行 (pytest / ruff / ty) |
| `just archcheck` | 依存方向の検証 (import-linter) |
| `just smoke-sdk` | Claude SDK 認証確認 |

## 環境

- Python 3.14 + **uv** 管理 (`uv sync`)。`pip` 直接使用禁止
- 開発シェルは `devenv shell`。グローバルインストールを避ける
- 実行 sandbox は Docker (`sandbox/Dockerfile.sandbox`)。docker group 未所属の場合は `sudo chmod a+rw /var/run/docker.sock` で運用

## コード規約

- docstring は Google Style、日本語、**体言止め (名詞終わり)**、句点なし
- モジュールレベル docstring は付けない
- 全 class / 関数 / 型定義に漏れなく付与 (`Args` / `Returns` / `Attributes` / `Raises`)
- 用法・変更履歴・補足説明を括弧内で混ぜない
- 1 ファイル 1 概念を基本
- ファイル・モジュール名は業務語彙 (technical 名 `util` / `helper` / `manager` 等は使わない)

## 依存方向の規律

- `shared` は何にも依存しない
- `foundation` は shared のみに依存
- `layers` は slice / runner / policies / workflows / cli に依存しない
- `contexts/<bc>/domain` `services` は layers / foundation / workflows / cli に依存しない
- BC 同士は独立 (`contexts/<bc_a>` は `contexts/<bc_b>` を参照しない、dispatch 経由)
- `workflows` は cli に依存しない

## 運用方針

- LLM は Claude Max サブスクのみ (API 課金なし)
- skill は全件 MIT-original。許可 skill 名集合は `src/foundation/skills/registry.py` で単一情報源化し、disc との一致は `tests/foundation/skills/test_registry.py` で機械検証
- 新 skill 作成は skill-creator (Anthropic 公式 plugin) workflow、既存改善は empirical-prompt-tuning (mizchi/skills) を使用
- 成果物は `writeups/<session>/` に永続化。破壊的更新は行わない

## 倫理・安全

- 攻撃対象は **明示的に許可された演習環境・CTF・自分の所有物のみ**
- OSINT は公開情報に限定。認証突破や非公開データへのアクセスは行わない
- Trace Labs 等の対人 OSINT では行動規範 (対象への直接接触禁止等) を遵守
