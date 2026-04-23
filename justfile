set dotenv-load := true
set shell := ["bash", "-uc"]

# デフォルト: レシピ一覧
default:
    @just --list

# ---- sleuth CLI -----------------------------------------------------------------

# 汎用: sleuth <subcommand> を透過的に実行
sleuth *args:
    uv run sleuth {{args}}

# CTFd challenge を解く (sleuth run --type ctf_challenge の shortcut)
solve url token *args:
    uv run sleuth run --type ctf_challenge --url {{url}} --token {{token}} {{args}}

# 分類と ExecutionRequest の表示のみ (実行しない)
plan-task input *args:
    uv run sleuth plan "{{input}}" {{args}}

# ---- 開発 --------------------------------------------------------------------

# 自動テスト
test:
    uv run pytest tests -q

# lint
lint:
    uv run ruff check src tests

# 型チェック
typecheck:
    uv run ty check src

# アーキテクチャ依存方向検証
archcheck:
    uv run lint-imports

# test と src の 1:1 対称配置検証 (構造宣言のみの src は AST で自動免除)
testlayoutcheck:
    uv run python scripts/check-test-layout.py

# 全チェック (CI 相当)
check: lint typecheck archcheck testlayoutcheck test

# ---- skill / sandbox -------------------------------------------------------

# description の類似度スキャン (skill 発火衝突の検出)
skill-overlap-check:
    python3 scripts/check-skill-overlap.py

# 本番 sandbox build (pwntools/sage/radare2 等, 20-30 分)
sandbox-build:
    docker build -f sandbox/Dockerfile.sandbox -t ctf-sandbox .

# smoke 用最小 sandbox build (数分)
smoke-sandbox-build:
    docker build -f scripts/smoke/Dockerfile.minimal-sandbox -t sleuth-smoke-sandbox scripts/smoke

# smoke test 群
smoke-sdk:
    uv run python scripts/smoke/smoke_sdk.py

smoke-level2:
    uv run python scripts/smoke/smoke_level2.py

smoke-osint:
    uv run python scripts/smoke/smoke_osint.py

smoke-artifact:
    uv run python scripts/smoke/smoke_artifact.py

# 全 smoke を順次実行
smoke-all: smoke-sdk smoke-level2 smoke-osint smoke-artifact

# ---- 掃除 --------------------------------------------------------------------

clean:
    rm -rf challenges/*/.solved challenges/*/.running
