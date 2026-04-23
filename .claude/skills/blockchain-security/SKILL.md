---
name: blockchain-security
description: smart contract / DeFi / NFT / bridge / wallet 含む blockchain 全般のセキュリティ。Ethereum 以外 (Solana / Cosmos / Bitcoin / Move / Cairo) を含む横断 skill。CTF blockchain / bug bounty で発火。
category: crypto
tags:
  - blockchain
  - smart-contract
  - defi
  - bridge
  - wallet
  - solana
---

# Blockchain Security (cross-chain)

## When to Use

- Ethereum 以外 (Solana / Cosmos / Bitcoin / Aptos / Sui / StarkNet) の評価
- bridge / wallet / signing service の audit
- DeFi protocol の横断分析
- CTF blockchain で多 chain の知識が必要

**使わない場面**: 暗号 algorithm そのもの (→ `performing-cryptographic-audit-of-application`)。

Solidity / EVM smart contract 専用の static + symbolic 解析 (reentrancy / integer / access control 等) は `references/ethereum.md`。

## Approach / Workflow

### Phase 1 — chain 種別

```
EVM 系:        Ethereum / Polygon / BNB / Avalanche / Arbitrum / Optimism / Base
非 EVM:        Solana (BPF) / Cosmos (CosmWasm) / Bitcoin (Script) / Aptos / Sui (Move) / StarkNet (Cairo) / NEAR
private:       Hyperledger Fabric / Quorum / R3 Corda
```

### Phase 2 — Solana / Anchor

Rust BPF で書かれる:

```
- Anchor (framework) の account validation 不備
- signer check 不在
- PDA (program-derived address) 衝突
- CPI (cross-program invocation) re-entrancy
- close instruction で account を消す前の re-init bug
- account ownership check 抜け
```

```bash
anchor test                                # local
anchor verify                              # build verification
soteria / sealevel-attacks                 # static rule
```

### Phase 3 — Cosmos / CosmWasm

WASM smart contract:

```
- query / execute msg の replay
- IBC channel handshake / 信頼仮定
- cosmwasm storage 競合
- staking module の delegation 逆用
```

### Phase 4 — Bitcoin / UTXO

```
- script flexibility / Taproot
- multi-sig misuse
- timelock check (CSV / CLTV)
- transaction malleability (legacy)
- ordinals / inscription での dust attack
```

### Phase 5 — Move (Aptos / Sui)

```
- resource ownership semantics
- module init の 1 回性
- friend / public(friend) 制限
- generic 型の制約抜け
```

### Phase 6 — bridge

bridge は最も狙われる。共通 bug pattern:

```
- multi-sig keys の管理不備 (Ronin Network)
- merkle proof verification の bug (Wormhole)
- replay across chains
- pause function の権限濫用
- relayer の信頼仮定が deeper than expected
- 異 chain での transaction ID 衝突
```

### Phase 7 — wallet / DApp

```
- transaction signing UI の hide
- approve unlimited (ERC-20 spend) の罠
- phishing approval (revoke.cash で対策)
- WalletConnect session hijack
- hardware wallet と software の整合
- secret 輸出機能 / seed phrase 取扱い
```

### Phase 8 — DeFi 横断

```
- price oracle manipulation (TWAP / Chainlink-like)
- flash loan + 内部不変条件破り
- governance attack (low quorum / token holder buyout)
- 'no slippage' / 'no fee' の routing 抜け
- yield farm の reward 計算式
- AMM の K invariant 破壊
```

### Phase 9 — レポート

```
- 対象 protocol / chain
- contract / module 一覧
- 検出脆弱性 (severity 別)
- bridge / oracle / governance の信頼仮定
- 修正提案
- 既存 incident との類似度
```

## Tools

```
slither / mythril / foundry / hardhat (EVM)
soteria / sealevel-attacks / anchor-lint (Solana)
cw-storage-plus tests / cosmwasm fuzz (Cosmos)
move-prover / sui-move-cli (Move)
btc rpc / btcdeb (Bitcoin)
WebFetch / WebSearch
Bash (sandbox)
```

## Related Skills

- `performing-cryptographic-audit-of-application`
- `web-pentester`, `api-security` (Web3 frontend)
- `source-code-scanning`
- `bug-bounter`, `web-bounty`, `hackerone`
- `essential-tools`

## Rules

1. **隔離 testnet / fork**
2. **非破壊**
3. **bug bounty 経路** — Immunefi / Code4rena / 公式 program に通報
4. **金銭リスク**
