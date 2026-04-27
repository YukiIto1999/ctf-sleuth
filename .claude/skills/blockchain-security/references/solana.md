# Solana / Anchor Smart Contract Audit

`blockchain-security` から呼ばれる、Solana program (Rust + Anchor / native) の静的 + 動的 audit 深掘り。Sealevel attack categories に沿って account validation / signer / arithmetic / CPI / PDA / re-init を網羅する。

## いつ切替えるか

- Solana / Anchor program (DeFi / NFT / DAO / bridge) の audit
- Anchor framework の脆弱性を体系的に評価
- bug bounty (Immunefi / 公式 program) の Solana 案件

## Phase 1 — 対象把握

```bash
anchor --version
cat Anchor.toml                       # program ID / cluster
solana program show <program-id>      # on-chain hash
ls programs/<name>/src/                # instruction 列挙
```

`declare_id!` と渡された program ID の一致を確認。`anchor idl fetch <program-id>` でオンチェーン IDL とローカル build の diff を取り、undocumented instruction を検出。

## Phase 2 — 静的解析セットアップ

```bash
cargo build-bpf                                # コンパイル可能性
cargo clippy -- -D warnings                     # 基礎
soteria programs/<name>/src                     # Sec3 9 カテゴリ rule pack
x-ray programs/<name>/                          # IDL ベース account-flow 可視化
```

`sealevel-attacks` repo (Coral Xyz) の 9 カテゴリ rule を grep / pattern matching で適用。

## Phase 3 — Sealevel 9 attack categories

### (1) Missing signer check

```rust
// BAD
pub fn admin_only(ctx: Context<AdminOnly>) -> Result<()> {
    ctx.accounts.admin.key();   // signer 検証なし
}

// GOOD
#[derive(Accounts)]
pub struct AdminOnly<'info> {
    pub admin: Signer<'info>,   // 型レベルで強制
}
```

`Signer<'info>` 型を使わず生 `AccountInfo` で `is_signer` を手動チェックする箇所を全件列挙。

### (2) Missing owner check

```rust
// BAD: AccountInfo / UncheckedAccount は owner 自動検証なし
pub vault: AccountInfo<'info>,

// GOOD
pub vault: Account<'info, Vault>,                          // owner 検証付き
// or constraint
#[account(constraint = vault.owner == program_id)]
```

### (3) Missing rent-exempt check

`init` で創出した account は Anchor が自動で rent-exempt 化するが、`AccountInfo` 経由で受けた account に独自に転送する場合は確認必須。

### (4) Signed invocation

```rust
// invoke_signed の seeds が外部入力で操作可能か
let signer_seeds = &[b"vault", user.key().as_ref(), &[bump]];
invoke_signed(&ix, &accounts, &[signer_seeds])?;
```

`bump` を構造体 field から取らず直接渡している箇所、user input で seeds が組み立てられている箇所を audit。

### (5) Re-init (`init_if_needed` / `close → re-init`)

```rust
#[account(init_if_needed, payer = payer, space = ...)]
pub vault: Account<'info, Vault>,
```

`init_if_needed` は危険。既存 account が initialize 済かを再確認しないと旧 state を上書き / 二重初期化が発生。Anchor 0.29+ では default OFF だが explicit に有効化されている場合は finding 化。

`close = recipient` の指定漏れ + 後続 instruction での re-init で revival attack 成立。

### (6) Arithmetic / overflow

```toml
# Cargo.toml
[profile.release]
overflow-checks = true
```

`overflow-checks = false` (default) のままだと release ビルドで wrap-around。`+ - *` を grep し、`checked_add` / `checked_sub` / `checked_mul` / `saturating_*` の使用率を確認。token amount × price / decimals 変換の rounding direction が常に protocol 有利か (user 不利 = OK / protocol 不利 = NG)。

`as u64` での truncation も全件 review。

### (7) Account confusions / type cosplay

```rust
// 同 size の異 type account を入れ替えられる
pub a: Account<'info, TypeA>,
pub b: Account<'info, TypeB>,
```

Anchor の discriminator (8 bytes) で防ぐが、`AccountInfo` 直使用時は discriminator manual check 必須。

### (8) Bump seed canonicalization

```rust
// BAD: caller が任意 bump を渡せる
seeds = [b"vault"], bump

// GOOD: canonical bump を Anchor が見つけてくれる
seeds = [b"vault"], bump
// + 構造体 field に bump を保存し、後続 instruction で `bump = vault.bump` 参照
```

非 canonical bump で別 PDA を作る攻撃。

### (9) Closing accounts insecurely

```rust
// BAD: lamports 0 化のみで discriminator は残る
**ctx.accounts.vault.try_borrow_mut_lamports()? = 0;

// GOOD: Anchor の close 制約 or 8-byte zero-out
#[account(mut, close = recipient)]
pub vault: Account<'info, Vault>,
```

## Phase 4 — CPI risks

```rust
solana_program::program::invoke(
    &spl_token::instruction::transfer(...)?,
    &[from.to_account_info(), to.to_account_info(), authority.to_account_info()],
)?;
```

確認観点:

- `program_id` の固定 / 信頼 program のホワイトリスト (SPL Token / Associated Token Program 等)
- caller-side で受け取った account の owner / discriminator 検証
- CPI 再入: state 更新 **→** CPI ではなく CPI **→** state 更新になっていないか
- `with_signer` の seeds に user-controlled value が入っていないか

## Phase 5 — Anchor IDL diff

```bash
anchor idl fetch <program-id> > onchain.json
anchor idl build > local.json
diff <(jq -S . onchain.json) <(jq -S . local.json)
```

undocumented instruction (オンチェーンに存在するが source / IDL に無い) は backdoor 候補。

## Phase 6 — 動的検証

```bash
solana-test-validator
anchor test --skip-local-validator
# PoC test で finding を再現可能な test ケースを作成
```

PoC は localnet で再現。devnet / mainnet では試さない (Rules 1)。

## Phase 7 — 主要 incident pattern

```
Mango Markets (Oct 2022)        oracle manipulation で借入無限化
Cashio (Mar 2022)               saber LP token の owner 検証漏れで mint 任意化
Wormhole (Feb 2022)             signature account 検証 bug + signer = guardian でない
Saber decimal (2021)            decimal scaling での arithmetic
Crema Finance (Jul 2022)        Tick array spoof
```

audit 中に類似 pattern が出たら過去 incident と紐付けて severity 判定。

## Phase 8 — Findings template

```
## Finding #N: <title>
- Severity: Critical / High / Medium / Low
- Category: account-validation | signer | arithmetic | CPI | PDA | re-init
- File: programs/<x>/src/instructions/<y>.rs:<line>
- Code: <抜粋>
- Impact: <資金 / 権限 / 可用性>
- PoC: <test ファイルパス>
- Fix: <Anchor 制約 or checked_* で書き換え>
- 類似 incident: <Mango / Cashio / Wormhole 等>
```

## Tools

```
anchor cli
cargo clippy
soteria (Sec3 / static rule pack)
x-ray (Sec3 / IDL flow)
sealevel-attacks (Coral Xyz / 教育 + check list)
solana-test-validator
WebFetch
Bash (sandbox)
```
