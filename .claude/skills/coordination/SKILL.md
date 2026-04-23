---
name: coordination
description: pentest / CTF / IR で 複数 sub-agent や workflow を連携し、executor / validator / dispatcher pattern で進捗管理する meta skill。複雑 engagement の整理に発火。
category: general
tags:
  - coordination
  - orchestration
  - sub-agent
  - workflow
  - executor
  - validator
---

# Coordination (Multi-step Orchestration)

## When to Use

- 複数 sub-agent / workflow が並走する複雑 engagement
- CTF で多 challenge を 並列 / 段階 attack
- IR で 多 host を並走 triage
- bug bounty で 多 program を継続 hunt

**使わない場面**: 単一 task / 単一 agent の作業 (→ 該当 skill 直接)。

## Approach / Workflow

### Phase 1 — orchestration pattern

```
executor:    具体的な task を実行 (run nuclei / exploit PoC / triage memory)
validator:   結果を verify (出力の妥当性 / scope 内か / false positive 仕分け)
dispatcher:  入力を分類 + 適切な executor / validator に振り分け
journal:     進捗 / 結果 / 学習を記録
```

### Phase 2 — sub-agent の使い方 (本プロジェクト)

```
- 4 BC: ctf_challenge / htb_machine / artifact_analysis / osint_investigation
- runner が claude_sdk 経由で sub-process 起動
- skill (`.claude/skills/`) は auto-surface して文脈で発火
- 結果は writeups/<run_id>/ に persist
```

### Phase 3 — task 分解の原則

```
1. atomic にする (1 step 1 result)
2. 並列可能性を identify
3. 依存関係を DAG で可視化
4. retry policy / timeout
5. validation criteria
6. rollback / cleanup
```

### Phase 4 — 並列 vs 直列

```
並列に向く:
  - 多 host nmap
  - 多 program subfinder
  - 多 file yara scan
直列に向く:
  - exploit chain (前 step の output が次 step の input)
  - phishing email → user click → C2 → priv esc
  - reverse engineering の iterative review
```

### Phase 5 — error handling

```
- transient error: retry (exponential backoff)
- permanent error: alert + 別 path 試行
- partial success: 結果を記録、後で resume
- abort condition: 残り task をどうするか (best-effort vs fail-fast)
```

### Phase 6 — communication

```
- agent 間 message bus (Redis / NATS / Kafka)
- shared state (S3 / GCS / DB)
- TTL / cleanup
- observability (log / trace / metric)
```

### Phase 7 — human-in-the-loop

```
- 重要 decision (destructive / 公開 / payment) は human approval
- approve / reject UI (slack interactive / Web)
- timeout (4h で auto reject)
- audit trail
```

### Phase 8 — 結果 aggregation / report

```
- finding を 1 つの DB に集約
- duplicate dedup
- severity 計算
- 優先順位付け
- レポート生成
```

## Tools

```
LangChain / LangGraph / autogen (LLM orchestration)
Apache Airflow / Dagster (data pipeline)
Temporal / Cadence (workflow)
GitHub Actions / GitLab CI (CI workflow)
Claude Agent SDK (本プロジェクト)
WebFetch
Bash (sandbox)
```

## Related Skills

- `essential-tools`, `script-generator`, `patt-fetcher`
- `red-teamer`, `bug-bounter`, `dfir`, `blue-teamer`

## Rules

1. **atomic task design**
2. **graceful degradation** — partial failure で全体停止しない
3. **observability** — 全 task の log / trace
4. **human approval point** — 重要 decision に human-in-the-loop
