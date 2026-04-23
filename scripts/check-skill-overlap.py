#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed.", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "from", "by", "as", "is", "are", "be", "been", "being", "this", "that",
    "these", "those", "it", "its", "their", "them", "they", "can", "use",
    "using", "used", "when", "which", "what", "who", "how", "why", "has",
    "have", "had", "do", "does", "did", "should", "would", "could",
    "may", "might", "must", "will", "shall",
    "skill", "task", "tasks", "work", "works", "process", "processes",
    "system", "systems", "data", "information", "security",
}


def load_skills() -> list[tuple[str, str, str, str]]:
    """skill 一覧の読込

    Returns:
        (name, category, source, description) のタプル列
    """
    results = []
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir():
            continue
        f = d / "SKILL.md"
        if not f.exists():
            continue
        t = f.read_text()
        if not t.startswith("---"):
            continue
        end = t.find("\n---\n", 4)
        fm = yaml.safe_load(t[4:end]) or {}
        results.append((
            fm.get("name", d.name),
            fm.get("category", "?"),
            fm.get("source", "?"),
            fm.get("description", "") or "",
        ))
    return results


def tokenize(text: str) -> set[str]:
    """英数 token 集合への分解

    Args:
        text: 対象テキスト

    Returns:
        STOPWORDS 除外済 token の集合
    """
    tokens = re.findall(r"[a-z][a-z0-9]{2,}", text.lower())
    return {t for t in tokens if t not in STOPWORDS}


def bigrams(tokens: list[str]) -> set[tuple[str, str]]:
    """token 列からの bigram 集合化

    Args:
        tokens: token リスト

    Returns:
        隣接 token 対の集合
    """
    return set(zip(tokens[:-1], tokens[1:]))


def jaccard(a: set, b: set) -> float:
    """Jaccard 類似度

    Args:
        a: 集合 A
        b: 集合 B

    Returns:
        Jaccard 係数 0.0 から 1.0
    """
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def main() -> None:
    """重複 description の検出エントリ"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.35,
                    help="Jaccard similarity threshold (0-1)")
    ap.add_argument("--top", type=int, default=30,
                    help="Top N overlapping pairs to print")
    args = ap.parse_args()

    skills = load_skills()
    print(f"Loaded {len(skills)} skills from {SKILLS}")

    pairs: list[tuple[float, str, str, str, str, set[str]]] = []
    token_sets = [(n, c, s, tokenize(d)) for n, c, s, d in skills]

    for i in range(len(token_sets)):
        name_i, cat_i, src_i, ts_i = token_sets[i]
        for j in range(i + 1, len(token_sets)):
            name_j, cat_j, src_j, ts_j = token_sets[j]
            if not ts_i or not ts_j:
                continue
            j_sim = jaccard(ts_i, ts_j)
            if j_sim >= args.threshold:
                shared = ts_i & ts_j
                pairs.append((j_sim, name_i, name_j, cat_i, cat_j, shared))

    pairs.sort(reverse=True)

    print(f"\n=== {len(pairs)} pair(s) with Jaccard >= {args.threshold} ===\n")
    for sim, n1, n2, c1, c2, shared in pairs[: args.top]:
        marker = "⚠" if c1 == c2 else "•"
        shared_str = ", ".join(sorted(shared)[:6])
        print(f"{marker} {sim:.2f}  [{c1}] {n1}")
        print(f"       [{c2}] {n2}")
        print(f"       shared: {shared_str}")
        print()

    from collections import Counter
    cat_counter = Counter(c for _, c, _, _ in skills)
    print("=== category distribution ===")
    for cat, n in cat_counter.most_common():
        print(f"  {cat}: {n}")

    src_counter = Counter(s for _, _, s, _ in skills)
    print("\n=== source distribution ===")
    for src, n in src_counter.most_common():
        print(f"  {src}: {n}")


if __name__ == "__main__":
    main()
