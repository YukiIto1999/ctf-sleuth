
# Ethereum Smart Contract Vulnerability Analysis

`blockchain-security` から呼ばれる variant 別 deep dive

## When to Use

- Ethereum / EVM 互換 chain の Solidity contract を audit
- DeFi protocol の脆弱性 hunting
- CTF blockchain 系問題 (Damn Vulnerable DeFi / Capture-the-Ether / Ethernaut)

**使わない場面**: Bitcoin script (UTXO 系)、Solana / Move 系 (→ `blockchain-security` 内の言語別 sub-section)。

## Approach / Workflow

### Phase 1 — input

```
- source code (Solidity / Vyper / Yul) があれば 最良
- bytecode のみ → panoramix / heimdall で decompile
- contract address + chain id → etherscan / blockscout で source 取得 (verified contract)
```

```bash
slither <contract.sol>
# または
slither <address> --rpc <rpc_url>
```

### Phase 2 — 主要脆弱性 class

| class | 例 |
|---|---|
| reentrancy | call.value() 後の state 更新 / cross-function reentrancy |
| integer overflow / underflow | (Solidity < 0.8 では SafeMath なしで脆弱) |
| access control | onlyOwner 抜け / tx.origin の使用 / public selfdestruct |
| oracle manipulation | spot price 直読み / 単一 source / TWAP 不在 |
| front-running / MEV | mempool 公開で先回り / sandwich attack |
| flash loan | 単 block で巨大 loan + 価格操作 |
| signature replay | nonce / chainid / domain separator 不在 (EIP-712) |
| delegatecall | proxy 用法を混同し storage collision |
| denial of service | gas limit / 配列 push 無制限 / push 経由失敗 |
| randomness | block.timestamp / blockhash で予測可 |
| unchecked low-level call | call の戻り値確認なし |
| upgradability bug | proxy initializer / storage layout 不一致 |

### Phase 3 — slither

```bash
slither contract.sol --print human-summary
slither contract.sol --detect reentrancy-eth,arbitrary-send,unchecked-transfer,...
slither contract.sol --print inheritance-graph
slither contract.sol --print function-summary
```

slither の各 detector は ATT&CK 風に lib 化されている。CI に組込み可能。

### Phase 4 — mythril (symbolic)

```bash
myth analyze contract.sol
myth analyze --rpc infura --code 0x60...
```

EVM symbolic execution で reentrancy / unprotected selfdestruct / arbitrary jump 等を発見。

### Phase 5 — fuzz / property-based test

```bash
echidna contract.sol --contract MyContract
foundry: forge test --fuzz-runs 10000
```

invariant ('always: totalSupply == sum(balances)') を定義し fuzz で 違反例を探す。

### Phase 6 — 動的 simulation / 攻撃 PoC

```
hardhat / foundry で fork mainnet → 攻撃 transaction を simulate
flashbots simulator (mev-boost) で sandwich / arbitrage の検証
tenderly で trace
```

### Phase 7 — 既知 incident pattern

```
The DAO (2016) reentrancy
Parity Multi-Sig (2017) initializer 自動 call で kill 不能
bZx flash loan (2020) oracle manipulation
Cream / Yearn / Wormhole / Nomad (各種 bridge bug)
Sushi MISO (2021) auction front-running
Beanstalk (2022) governance flash loan attack
Ronin (2022) bridge multi-sig 脆弱
```

過去の有名 hack / writeup と pattern match して 自分の audit 対象を再 review。

### Phase 8 — レポート

```
- 対象 contract / version / chain
- 検出脆弱性 (severity 別)
- exploit chain (PoC 付き)
- 推奨修正 (code snippet diff)
- 関連の確認ツール
```

## Tools

```
slither / mythril / echidna
foundry / hardhat / brownie
panoramix / heimdall (bytecode decompile)
solc / etherscan / blockscout
WebFetch / WebSearch
Bash (sandbox)
```
