# ctf-sleuth アーキテクチャ設計書

本プロジェクトの構造設計と規律の正本。実装の突き合わせ基準。

## 位置付け

- 参照: ワークスペース暫定標準 [`/home/nixos/projects/architecture-unification/docs/standard.md`](/home/nixos/projects/architecture-unification/docs/standard.md)
- 将来目標: [`/home/nixos/templates/architecture/docs/canonical-logic.md`](/home/nixos/templates/architecture/docs/canonical-logic.md)
- 本プロジェクトは canonical-logic の **構造骨格のみ** を取込み、Effect-TS / IDM / CDC / Formal Spec / DST 等の装備は採用しない

## 採用する規律

### 構造パターン
- **VSlice 骨格**: `contexts/[BC]/[slice]/` で 1 slice = 1 変更理由
- **Hexagonal 依存方向**: port (契約) と adapter (実装) を物理分離、port は `contexts/[BC]/services/` と `shared/sandbox/`、adapter は `layers/`
- **Composition Root**: `cli/bootstrap.py` で port 実装を組立て BC runner に注入

### 16 原則の適用
canonical-logic の 3 公理 + 16 原則 (P1-P16) をコード構造で満たす。P12 (集約=トランザクション) は DB 非使用のため N/A。

### 機械検証 (P15)
- `ruff` — lint
- `ty` — 型検査
- `import-linter` — 依存方向契約
- `pytest` — 自動テスト

## トップレベル構造

```
src/
├── contexts/     # Bounded Context (業務単位)
├── workflows/    # BC 横断ユースケース
├── foundation/   # 技術基盤 (canonical-logic の platform 相当、Python stdlib 衝突回避で改名)
├── layers/       # adapter 実装 (canonical-logic の layers)
├── shared/       # BC 横断純粋値 + 横断 port
└── cli/          # Composition Root + エントリ
```

各層の責務:

| 層 | 責務 | 純粋性 |
| --- | --- | --- |
| `shared` | BC 横断値オブジェクト・全 BC が使う port・エラー基底 | 副作用なし (Protocol は型のみ) |
| `foundation` | 横断技術基盤 (metrics 等) | 副作用あり (ContextVar 等) |
| `layers` | port 実装 (Claude SDK / Docker / HTTP / CTFd / HTB / 永続化) | 副作用あり |
| `contexts/[BC]` | BC 内の集約・ポリシー・サービス契約・ユースケース slice | domain/policies/services は副作用なし、slice は合成点 |
| `workflows` | BC 横断合成 (dispatch) | 合成点 |
| `cli` | 入出力 + Composition Root | 合成点 |

## BC 内部構造 (共通テンプレート)

```
contexts/<bc>/
├── __init__.py          # BC public 面: runner を __all__ で露出
├── runner.py            # BC エントリ (port 実装を受け取る高階関数)
├── domain/              # BC 内集約・値オブジェクト (副作用なし)
│   ├── __init__.py
│   └── <concept>.py     # 1 概念 1 ファイル、集約構成値は同ファイル可
├── policies/            # BC 内共有純関数 (省略可)
│   ├── __init__.py
│   └── <rule>.py
├── services/            # BC 固有 port (Protocol) (省略可)
│   ├── __init__.py
│   └── <port>.py
└── <slice>/             # 1 slice = 1 変更理由
    ├── __init__.py      # slice public 面
    ├── handler.py       # ユースケース本体 (必須)
    ├── schema.py        # 入出力型 (必須、空でも配置)
    ├── prompts.py       # Claude prompt 生成 (省略可)
    ├── strategies/      # slice 固有サブポリシー (省略可)
    └── errors.py        # slice 固有エラー (省略可)
```

### slice の必須ファイル
- `handler.py` - ユースケース本体
- `schema.py` - 入出力型 (slice で schema を持たなくても空ファイルを配置し、粒度整合を維持)
- `__init__.py` - 公開面

### BC 同定
本プロジェクトの 4 BC:

| BC | domain 中核 | policies | slice |
| --- | --- | --- | --- |
| `ctf_challenge` | Challenge / ChallengeSet / SolveAttempt | category (normalize_category) / slug (slugify) / distfile (filename_from_url) | solve, coordinate, archive |
| `htb_machine` | Machine / HtbAttempt | attack |
| `artifact_analysis` | Artifact | analyze |
| `osint_investigation` | Target | investigate |

## ファイル粒度規律

### 1 ファイル 1 概念 (基本)
- 1 class = 1 ファイル
- 1 Enum = 1 ファイル
- 1 Protocol = 1 ファイル
- ユーティリティ関数群は 1 関数 = 1 ファイル

### 集約構成値の同居許容
集約 (entity/aggregate) とその構成値型 (value object) が密結合で単独使用されない場合は同ファイル可。

例: `Challenge` と `ChallengeId`, `Hint` は `domain/challenge.py` に同居。

### layers 内の粒度
layer 内部も 1 ファイル 1 責務。大きい adapter (例: writeups persister) は処理責務単位で分割。

例: `layers/writeups/` は以下の 5 ファイル構成 (manifest/report/evidence/result_json を 1 ファイル集約せず責務別分割):
- `persister.py` - 公開関数 `persist_task_result`
- `manifest.py` - manifest.yml 書出
- `report.py` - report.md 書出 (variant 別 render)
- `evidence.py` - evidence.jsonl 書出
- `result_json.py` - result.json 書出

### 粒度整合
同階層のエントリはディレクトリ / ファイルの混在を避ける:

- `layers/` 直下は全てサブディレクトリ
- `shared/` 直下は全てサブディレクトリ
- `contexts/<bc>/` 直下: `__init__.py` と `runner.py` 以外は全てサブディレクトリ (domain / policies / services / <slice>)
- slice 内は `__init__.py` `handler.py` `schema.py` + オプション

## 依存方向の規律

### 許可される依存 (概念)
```
slice       → services, domain, policies, shared, foundation
services    → domain, shared
policies    → domain, shared
domain      → shared のみ
runner      → <slice>, services, domain, policies, layers, shared
layers      → <BC>.domain, <BC>.services, <BC>.policies, shared, foundation
workflows   → contexts.<bc> (runner 経由), services (workflows 内), policies (workflows 内), layers (layers 内 adapter), shared, foundation
cli         → workflows, layers, contexts, foundation, shared
```

### 禁止される依存
- `shared → 他の全て` (shared は何にも依存しない)
- `foundation → contexts, workflows, layers, cli`
- `layers → slice, runner, workflows, cli` (slice 内部への依存禁止)
- `contexts.<bc>.domain → layers, foundation, workflows, cli` (domain は純粋)
- `contexts.<bc>.services → layers, foundation, workflows, cli` (services は純粋 Protocol)
- `contexts.<bc_a> → contexts.<bc_b>` (BC 独立、dispatch 経由)
- `workflows → cli`

### CI 強制 (import-linter)
`pyproject.toml` の `[tool.importlinter.contracts]` で下記 7 契約を固定:

1. `shared has no outgoing deps`
2. `foundation only depends on shared`
3. `layers must not depend on slices or runners`
4. `domain purity`
5. `services must be pure interfaces`
6. `BC independence`
7. `workflows must not depend on cli`

## エラー階層

### 4 カテゴリ
canonical-logic の 5 大カテゴリから `AuthorizationError` を除外 (認可要件なし):

| 基底 | デフォルト metadata | 配下の具象 |
| --- | --- | --- |
| `DomainError` | retryable=False, severity=error | `ClassificationUnderconfidentError`, `AmbiguousClassificationError` |
| `InfrastructureError` | retryable=True, severity=error | `NonInteractiveShellError`, `SandboxError` (+派生) |
| `IntegrationError` | retryable=True, severity=error | `CtfdError`, `HtbError` |
| `ValidationError` | retryable=False, severity=warning | `MissingRequiredParamError` |

全基底は `AppError(Exception)` を継承。

### ErrorMetadata
```python
@dataclass(frozen=True, slots=True)
class ErrorMetadata:
    retryable: bool
    severity: Literal["error", "warning"]
```

各例外クラスに `metadata: ClassVar[ErrorMetadata]` を付与。

### 実装形式の採用理由
canonical-logic は **Tagged Union** (dataclass variant + match) を前提とする。本プロジェクトは Python の既存 `raise/except` 文化との整合を優先し、**class 継承階層 + ClassVar メタデータ** で代用。

match 文による型絞込みは `match` の `case` ブロックで利用可能 (`case DomainError():`)。Tagged Union への完全移行は Result 型ライブラリ導入を要するため非採用。

## Composition Root

### 位置
`cli/bootstrap.py` に集約。

### 責務
1. `make_runners() -> dict[TaskType, TaskRunner]` — TaskType 別 runner の組立
2. `make_config(non_interactive) -> DispatchConfig` — dispatch 設定の組立

### runner の高階関数化
各 BC の `runner.py` は layers の具象実装を引数で受け取る。具象生成は `cli/bootstrap.py` に集約し、runner 内部では生成しない。

例:
```python
# contexts/ctf_challenge/runner.py
async def run_ctf_challenge(
    request: ExecutionRequest,
    *,
    ctfd_gateway_factory: Callable[..., AsyncContextManager[CtfdGateway]],
    sandbox_factory: Callable[[Challenge], Sandbox],
    challenges_dir: Path = DEFAULT_CHALLENGES_DIR,
    max_challenges: int | None = None,
) -> AnalysisReport:
    ...

# cli/bootstrap.py
def make_runners() -> dict[TaskType, TaskRunner]:
    return {
        TaskType.CTF_CHALLENGE: partial(
            run_ctf_challenge,
            ctfd_gateway_factory=lambda cfg: CtfdClient(cfg),
            sandbox_factory=lambda ch: _make_ctf_sandbox(ch),
        ),
        ...
    }
```

### dispatch の注入経由
```python
# workflows/dispatch/handler.py
async def execute(request, *, runners: dict[TaskType, TaskRunner]) -> TaskResult:
    runner = runners.get(request.task_type)
    if runner is None:
        raise AppError(f"unknown task type: {request.task_type}")
    return await runner(request)
```

## 命名規約

- モジュール・ディレクトリ名: **業務語彙**。技術名 (`util`, `helper`, `common`, `manager`, `service`) 接頭辞禁止
- Python 識別子: snake_case (関数・変数・モジュール) / PascalCase (class / TypeAlias)
- 例外名: `<業務概念>Error` (e.g., `CtfdError`, `MissingRequiredParamError`)

## docstring 規約

- Google Style (Args / Returns / Attributes / Raises)
- 日本語
- **体言止め (名詞終わり)**、句点なし
- モジュールレベル docstring は付けない
- 全 class / 関数 / 型定義に付与
- 用法・変更履歴・補足括弧内注記を混ぜない

## テスト配置

### 配置規律

- `tests/` は `src/` と**完全対称配置** (ディレクトリ構造を 1:1 で反映)
- **挙動あり 1 src ファイル = 1 test ファイル** (src/a/b/foo.py ↔ tests/a/b/test_foo.py)
- 構造宣言のみの src ファイル (Protocol only / dataclass frozen only / Enum only / ClassVar metadata only) は**テスト免除**。型検査 (`ty`) が仕様を機械検証済のため二重記述を避ける
- 免除判定は `scripts/check-test-layout.py` が AST で自動分類。手書き allowlist は置かない
- 1 src ファイルに複数 class/関数が同居する場合、テストは `TestFoo` / `TestBar` の class で分離した上で同じ test ファイルに置く (集約構成値の同居許容に対応)
- test 間依存は禁止。テストは DUT と DUT の collaborator 型のみを import し、**他の test ファイルや test helper モジュールへの依存は作らない**
- 共通ヘルパ (例: `_probe`, `_shape`, `_req`) は各 test ファイル内に**重複配置**し、ファイル自己完結を優先

### import 可能範囲 (test から src)

test ファイルは対応 src モジュールとその collaborator のみを参照できる:

| test 位置 | 直接参照可 | 参照不可 |
| --- | --- | --- |
| `tests/shared/<sub>/test_x.py` | `shared.<sub>.x` のみ | 他 shared 内別モジュールや上位層 |
| `tests/foundation/<sub>/test_x.py` | `foundation.<sub>.x`, `shared.*` | `contexts / workflows / layers / cli` |
| `tests/layers/<adapter>/test_x.py` | `layers.<adapter>.x`, 依存 BC の `domain/services/policies`, `shared.*`, `foundation.*` | 他 BC, slice, runner, workflows, cli |
| `tests/contexts/<bc>/<sub>/test_x.py` | BC 内の domain / policies / services / slice 内実装, `shared.*` | 他 BC, `layers.*` (slice 純粋性), workflows, cli |
| `tests/contexts/<bc>/test_runner.py` | 当該 BC の runner, slice, domain, `shared.*`, `layers.*` (runner 高階関数化により factory 検証で参照可) | 他 BC, workflows, cli |
| `tests/workflows/<sub>/test_x.py` | `workflows.<sub>.*`, `shared.*`, `foundation.*`, `contexts.*` (runner 参照) | `cli.*` |
| `tests/cli/test_x.py` | `cli.*` および下位層全 | — |

### 対称構造



```
tests/
├── shared/
│   ├── errors/test_*.py
│   ├── task/test_*.py
│   ├── probe/test_*.py
│   ├── result/test_*.py
│   └── sandbox/test_*.py
├── foundation/
│   └── metrics/test_*.py
├── layers/
│   ├── sandbox/test_*.py
│   ├── claude_sdk/test_*.py
│   ├── probe/test_*.py
│   ├── ctfd/test_*.py
│   ├── htb/test_*.py
│   ├── llm_classifier/test_*.py
│   ├── artifact_inspector/test_*.py
│   └── writeups/test_*.py
├── workflows/
│   └── dispatch/test_*.py
├── contexts/
│   ├── ctf_challenge/
│   │   ├── domain/test_*.py
│   │   ├── policies/test_*.py
│   │   ├── solve/test_*.py
│   │   ├── coordinate/test_*.py
│   │   ├── archive/test_*.py
│   │   └── test_runner.py
│   ├── htb_machine/ (同様)
│   ├── artifact_analysis/ (同様)
│   └── osint_investigation/ (同様)
└── cli/test_*.py
```

## 非採用装備 (明示)

canonical-logic から以下は**取り込まない**:

| 装備 | 取り込まない理由 |
| --- | --- |
| Effect-TS / `Effect<A, E, R>` | Python には同等の型システムなし |
| DST (Deterministic Simulation Testing) | Effect-TS ネイティブ装備 |
| Formal Spec (TLA+ / Alloy) | 本プロジェクトの状態機械は小規模で回収されない |
| IDM (Immutable Data Model) on PostgreSQL | DB 非使用 (filesystem `writeups/` のみ) |
| CDC Stream | 同上 |
| F6 Biscuit Capability | 認可要件なし |
| BC 間 Event (events/) | BC 間通信なし (dispatch で runner 選択のみ) |
| AuthorizationError カテゴリ | 認可なし |
| OTel 3 本柱 | 観測要件小 (metrics のみ自前実装) |
| `layers/` 技術軸並列配置 | 1 技術要素 = 1 ディレクトリ構造は採用、DST 用 simulation Layer は非採用 |

## 物理資産の配置

| 資産 | 配置 | 理由 |
| --- | --- | --- |
| Docker image 定義 (`Dockerfile.sandbox`, `sandbox-tools.txt`) | root `sandbox/` | 言語外の物理資産、standard.md の `engine/` 同格扱い |
| smoke test (integration 確認) | root `scripts/smoke/` | pytest 範疇外 (実 Claude / 実 Docker 依存、非決定的) |
| プロジェクト運営 script (skill importer 等) | root `scripts/` | `src/` 非依存のインフラ操作 |
