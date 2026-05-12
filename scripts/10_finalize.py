#!/usr/bin/env python3
"""Step 10: apply self-review removals, backfill, verify, sort, write final
adjectives.txt and nouns.txt with SHA-256.

Backfill source: data/07_selection_log.tsv (rows with outcome=overflow_*).
We walk overflow in priority order (quality_tier asc, primary_score desc,
g_rank asc, word asc) and accept the first N words that aren't in the
HARD_REMOVE set, aren't already in the other pool, and pass a final
substring-profanity check.

After backfill, re-verify all hard constraints from CLAUDE.md §Quality Gates."""
from __future__ import annotations
import hashlib
import re
import sys
from pathlib import Path
import pandas as pd
import jellyfish
from nltk.corpus import wordnet as wn

ROOT = Path(__file__).resolve().parent.parent
ADJ_SEL = ROOT / "data" / "07_selected_adj.txt"
NOUN_SEL = ROOT / "data" / "07_selected_nouns.txt"
LOG = ROOT / "data" / "07_selection_log.tsv"
REMOVED = ROOT / "data" / "09_removed.txt"
LDNOOBW = ROOT / "data" / "raw" / "ldnoobw_en.txt"

OUT_ADJ = ROOT / "adjectives.txt"
OUT_NOUN = ROOT / "nouns.txt"
SHA_FILE = ROOT / "data" / "10_sha256.txt"

ADJ_TARGET = 4096
NOUN_TARGET = 8192

# Augmented substring blocklist for final pair safety. A word containing one
# of these substrings is rejected outright at finalize time.
DANGEROUS_SUBSTRINGS = (
    "rape", "kill", "shit", "fuck", "cunt", "spic", "chink", "gook",
    "wank", "boob", "cock", "bitch", "anal", "anus", "tits", "porn",
    "klan", "nazi", "kkk", "qaeda", "dyke", "fag",
    "scat", "horny",
    "negro", "darkie", "wetb",
    # NOTE: 'isis' deliberately omitted from individual-word substring check
    # because it false-positives on 'crisis'. The standalone word 'isis' is
    # blocked by the demographic blocklist in Step 4 and by pair audit.
)


def load_removals() -> set[str]:
    rows = REMOVED.read_text().splitlines()[1:]  # skip header
    return {row.split("\t")[0] for row in rows if row.strip()}


def load_ldnoobw() -> set[str]:
    return {line.strip().lower() for line in LDNOOBW.read_text().splitlines() if line.strip()}


def has_dangerous_substring(word: str) -> str | None:
    for sub in DANGEROUS_SUBSTRINGS:
        if sub in word:
            return sub
    return None


def main() -> int:
    removed = load_removals()
    ldnoobw_exact = {w for w in load_ldnoobw() if " " not in w}
    print(f"removals: {len(removed)}, ldnoobw exact entries: {len(ldnoobw_exact)}")

    adj = [w for w in ADJ_SEL.read_text().split() if w]
    nouns = [w for w in NOUN_SEL.read_text().split() if w]
    print(f"input adj: {len(adj)}, nouns: {len(nouns)}")

    # Apply removals + dangerous-substring + ldnoobw-exact catch-all
    def final_filter(word: str, pool: str) -> str | None:
        if word in removed: return "self_review"
        if word in ldnoobw_exact: return "ldnoobw"
        sub = has_dangerous_substring(word)
        if sub: return f"substring:{sub}"
        if not re.match(r"^[a-z]{4,7}$", word): return "regex"
        return None

    adj_kept = [w for w in adj if final_filter(w, "adj") is None]
    noun_kept = [w for w in nouns if final_filter(w, "noun") is None]
    adj_dropped = len(adj) - len(adj_kept)
    noun_dropped = len(nouns) - len(noun_kept)
    print(f"after final filter: adj {len(adj_kept)} (-{adj_dropped}), "
          f"noun {len(noun_kept)} (-{noun_dropped})")

    # Backfill from overflow log
    log = pd.read_csv(LOG, sep="\t", keep_default_na=False)
    # Overflow rows ordered by quality tier then score
    log["quality_tier"] = log.quality_tier.astype(int)

    def backfill(pool_kept: list[str], target: int, pool_name: str) -> list[str]:
        """Walk all candidates that could feed this pool, in priority order.

        Includes overflow, dedup-dropped (own and opposite pool), and any
        word in the selection log whose POS column allows this pool.
        """
        kept_set = set(pool_kept)
        other_set = set(noun_kept) if pool_name == "adj" else set(adj_kept)
        # All log rows where the word is attested for this POS
        if pool_name == "adj":
            candidates = log[log.is_adjective == 1].copy()
        else:
            candidates = log[log.is_noun == 1].copy()
        candidates = candidates.sort_values(
            ["quality_tier", "primary_score", "g_rank", "word"],
            ascending=[True, False, True, True],
        )
        seen = set()
        for _, r in candidates.iterrows():
            if len(pool_kept) >= target:
                break
            w = r["word"]
            if w in seen: continue
            seen.add(w)
            if w in kept_set or w in other_set:
                continue
            if final_filter(w, pool_name) is not None:
                continue
            pool_kept.append(w)
            kept_set.add(w)
        return pool_kept

    adj_kept = backfill(adj_kept, ADJ_TARGET, "adj")
    noun_kept = backfill(noun_kept, NOUN_TARGET, "noun")
    print(f"after backfill: adj {len(adj_kept)}, noun {len(noun_kept)}")

    # If still short, the candidate-pool was insufficient — print a warning
    # but proceed; the quality-gate check will fail and force resolution.
    if len(adj_kept) < ADJ_TARGET:
        print(f"!! WARNING: adj short by {ADJ_TARGET - len(adj_kept)}", file=sys.stderr)
    if len(noun_kept) < NOUN_TARGET:
        print(f"!! WARNING: noun short by {NOUN_TARGET - len(noun_kept)}", file=sys.stderr)

    # Final disjointness check
    overlap = set(adj_kept) & set(noun_kept)
    if overlap:
        # Remove from noun (adj has stricter supply); document
        print(f"!! disjoint violation: {len(overlap)} overlap. Removing from noun.")
        noun_kept = [w for w in noun_kept if w not in overlap]
        noun_kept = backfill(noun_kept, NOUN_TARGET, "noun")

    # Sort alphabetically
    adj_kept = sorted(set(adj_kept))[:ADJ_TARGET]
    noun_kept = sorted(set(noun_kept))[:NOUN_TARGET]

    # Re-verify constraints
    print("\n=== Final constraint verification ===")
    checks = {
        "adj count == 4096": len(adj_kept) == ADJ_TARGET,
        "noun count == 8192": len(noun_kept) == NOUN_TARGET,
        "adj all 4-7 lowercase": all(re.match(r"^[a-z]{4,7}$", w) for w in adj_kept),
        "noun all 4-7 lowercase": all(re.match(r"^[a-z]{4,7}$", w) for w in noun_kept),
        "adj no dupes": len(set(adj_kept)) == len(adj_kept),
        "noun no dupes": len(set(noun_kept)) == len(noun_kept),
        "disjoint": not (set(adj_kept) & set(noun_kept)),
        "adj no ldnoobw exact": not (set(adj_kept) & ldnoobw_exact),
        "noun no ldnoobw exact": not (set(noun_kept) & ldnoobw_exact),
        "adj sorted": adj_kept == sorted(adj_kept),
        "noun sorted": noun_kept == sorted(noun_kept),
    }
    for k, v in checks.items():
        print(f"  [{'OK' if v else 'FAIL'}] {k}")
    if not all(checks.values()):
        print("FAILED constraint checks", file=sys.stderr)
        return 1

    # WordNet synset check (warn-only, since we documented adj backfill exceptions)
    n_adj_no_wn = sum(1 for w in adj_kept
                      if not (wn.synsets(w, pos=wn.ADJ) or wn.synsets(w, pos=wn.ADJ_SAT)))
    n_noun_no_wn = sum(1 for w in noun_kept if not wn.synsets(w, pos=wn.NOUN))
    print(f"  [warn] adj without WordNet adj synset: {n_adj_no_wn} (morph-backfilled)")
    print(f"  [warn] noun without WordNet noun synset: {n_noun_no_wn}")

    # Write outputs
    OUT_ADJ.write_text("\n".join(adj_kept) + "\n")
    OUT_NOUN.write_text("\n".join(noun_kept) + "\n")

    # SHA-256
    sha_adj = hashlib.sha256(OUT_ADJ.read_bytes()).hexdigest()
    sha_noun = hashlib.sha256(OUT_NOUN.read_bytes()).hexdigest()
    with SHA_FILE.open("w") as f:
        f.write(f"adjectives.txt  {sha_adj}\n")
        f.write(f"nouns.txt       {sha_noun}\n")
    print(f"\nadjectives.txt SHA-256: {sha_adj}")
    print(f"nouns.txt      SHA-256: {sha_noun}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
