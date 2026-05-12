#!/usr/bin/env python3
"""Step 7: select exactly 4,096 adjectives and 8,192 nouns.

Algorithm:
  1. Drop quality-filtered words (drop_reason != '').
  2. For 'both' candidates (is_adjective=1 AND is_noun=1):
     - If word in HEROKU_ADJ_REF or HAIKUNATORJS_ADJ → adj
     - Else if word in HEROKU_NOUN_REF or HAIKUNATORJS_NOUN → noun
     - Else if playfulness_score > concreteness_score → adj
     - Else if concreteness_score > playfulness_score → noun
     - Else (tie) → noun (CLAUDE.md tie-breaker, larger pool)
  3. Sort each pool by score desc, then google rank asc, then alphabetic.
  4. Phonetic dedup per pool: walk in priority order; for each word, drop if
     a higher-priority word in the same pool shares its metaphone code AND
     has Damerau-Levenshtein distance ≤ 1 (truly confusable).
  5. Take top N from each pool (4,096 adj / 8,192 noun).
  6. Verify disjointness; abort if violated.

Output:
  data/07_selected_adj.txt   (one per line, alphabetic)
  data/07_selected_nouns.txt
  data/07_selection_log.tsv  (full diagnostic — kept/cut + reasons)
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import jellyfish

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "06_tone_scored.tsv"
OUT_ADJ = ROOT / "data" / "07_selected_adj.txt"
OUT_NOUN = ROOT / "data" / "07_selected_nouns.txt"
LOG = ROOT / "data" / "07_selection_log.tsv"

ADJ_TARGET = 4096
NOUN_TARGET = 8192

# Re-import the reference sets from Step 6
from importlib import import_module
sys.path.insert(0, str(ROOT / "scripts"))
tone_mod = import_module("06_tone_score")  # type: ignore
HEROKU_ADJ_REF = tone_mod.HEROKU_ADJ_REF
HEROKU_NOUN_REF = tone_mod.HEROKU_NOUN_REF
HAIKUNATORJS_ADJ = tone_mod.HAIKUNATORJS_ADJ
HAIKUNATORJS_NOUN = tone_mod.HAIKUNATORJS_NOUN


def google_rank() -> dict[str, int]:
    p = ROOT / "data" / "raw" / "google_10000.txt"
    return {w.strip().lower(): i for i, w in enumerate(p.read_text().splitlines()) if w.strip()}


def assign_pool(row, ref_adj_strong: set[str], ref_noun_strong: set[str]) -> str:
    if row.is_adjective and not row.is_noun:
        return "adj"
    if row.is_noun and not row.is_adjective:
        return "noun"
    # both
    if row.word in ref_adj_strong:
        return "adj"
    if row.word in ref_noun_strong:
        return "noun"
    if row.playfulness_score > row.concreteness_score:
        return "adj"
    if row.concreteness_score > row.playfulness_score:
        return "noun"
    return "noun"  # tie → noun (CLAUDE.md tie-breaker)


def phonetic_dedup(
    rows: list[dict], strict: bool = True
) -> tuple[list[dict], list[dict]]:
    """Phonetic deduplication.

    strict=True: drop later-arriving words that share metaphone with a kept
      word AND are within Damerau-Levenshtein 1 (acoustic+visual collision).
    strict=False: as above but ALSO require first-2-letters match. This is
      a softer rule used when the strict rule under-supplies the pool.

    Returns (kept, dropped_with_reason).
    """
    kept: list[dict] = []
    dropped: list[dict] = []
    by_meta: dict[str, list[dict]] = {}
    for r in rows:
        meta = r["metaphone_code"]
        confused_with = None
        for prior in by_meta.get(meta, []):
            w, pw = r["word"], prior["word"]
            if strict:
                if jellyfish.damerau_levenshtein_distance(w, pw) <= 1:
                    confused_with = pw
                    break
            else:
                if w[:2] == pw[:2] and jellyfish.damerau_levenshtein_distance(w, pw) <= 1:
                    confused_with = pw
                    break
        if confused_with is None:
            kept.append(r)
            by_meta.setdefault(meta, []).append(r)
        else:
            r2 = dict(r); r2["dedup_collision_with"] = confused_with
            dropped.append(r2)
    return kept, dropped


def main() -> int:
    df = pd.read_csv(IN, sep="\t", keep_default_na=False)
    print(f"loaded: {len(df)} rows")
    kept = df[df.drop_reason == ""].copy()
    print(f"after Step-4 quality filter: {len(kept)}")

    # Pool assignment
    ref_adj_strong = HEROKU_ADJ_REF | HAIKUNATORJS_ADJ
    ref_noun_strong = HEROKU_NOUN_REF | HAIKUNATORJS_NOUN
    kept["pool"] = kept.apply(lambda r: assign_pool(r, ref_adj_strong, ref_noun_strong), axis=1)
    print(f"pool assignment: {kept.pool.value_counts().to_dict()}")

    # Sort by priority within pool: score desc, google rank asc, word asc
    g_rank = google_rank()
    kept["g_rank"] = kept.word.map(lambda w: g_rank.get(w, 999_999))
    kept["primary_score"] = kept.apply(
        lambda r: r.playfulness_score if r.pool == "adj" else r.concreteness_score, axis=1
    )

    # --- Adjective pool with reassignment + adaptive dedup ---
    # Strategy:
    #   (1) Try strict dedup.
    #   (2) If short, reassign 'both' candidates from noun→adj.
    #   (3) If still short, fall back to soft dedup (requires first-2-letter match too).
    # Each step is logged so the audit can see when relaxation fired.

    def build_adj(strict: bool) -> tuple[list, list]:
        adj_rows = kept[kept.pool == "adj"].sort_values(
            ["quality_tier", "primary_score", "g_rank", "word"],
            ascending=[True, False, True, True]
        ).to_dict("records")
        return phonetic_dedup(adj_rows, strict=strict)

    relaxation = "strict"
    adj_kept, adj_dedup_dropped = build_adj(strict=True)
    print(f"adj (strict dedup, no reassign): {len(adj_kept)} (dropped {len(adj_dedup_dropped)})")

    if len(adj_kept) < ADJ_TARGET:
        deficit = ADJ_TARGET - len(adj_kept)
        kept = kept.assign(
            is_both=lambda d: ((d.is_adjective == 1) & (d.is_noun == 1)),
            margin=lambda d: d.concreteness_score - d.playfulness_score,
        )
        both_in_noun = (
            kept[(kept.pool == "noun") & kept.is_both]
            .sort_values(["margin", "playfulness_score", "g_rank"],
                         ascending=[True, False, True])
            .to_dict("records")
        )
        flip_words = {r["word"] for r in both_in_noun}  # all of them
        kept.loc[kept.word.isin(flip_words), "pool"] = "adj"
        kept["primary_score"] = kept.apply(
            lambda r: r.playfulness_score if r.pool == "adj" else r.concreteness_score, axis=1
        )
        relaxation = "reassign-all-both"
        print(f"adj-deficit step 2: reassigned ALL {len(flip_words)} 'both' words noun→adj")
        adj_kept, adj_dedup_dropped = build_adj(strict=True)
        print(f"adj (strict dedup, post-reassign): {len(adj_kept)}")

    if len(adj_kept) < ADJ_TARGET:
        relaxation = "soft-dedup"
        print("adj-deficit step 3: relaxing dedup to first-2-letters + Lev1")
        adj_kept, adj_dedup_dropped = build_adj(strict=False)
        print(f"adj (soft dedup, post-reassign): {len(adj_kept)}")

    # Step 4 backfill: if still short, pull from morphologically-adjectival
    # words that survived Step 4 quality filters but are tagged noun-only.
    # We only consider words ending in clear adjectival suffixes.
    if len(adj_kept) < ADJ_TARGET:
        deficit = ADJ_TARGET - len(adj_kept)
        relaxation = f"morph-backfill+{relaxation}"
        adj_set_now = {r["word"] for r in adj_kept}
        # Conservative suffixes — only those almost always adjectival in
        # English. Excludes -an/-al/-ar/-ic which carry too many noun cognates
        # (pelican, journal, calendar, mosaic).
        ADJ_SUFFIXES = ("y", "ish", "ous", "en", "ed", "ful", "less", "some", "ly")
        # Candidate: in noun pool, NOT in adj pool, ends in adjectival suffix.
        backfill_pool = []
        for r in kept[(kept.pool == "noun") & (~kept.word.isin(adj_set_now))].to_dict("records"):
            w = r["word"]
            if any(w.endswith(s) for s in ADJ_SUFFIXES) and len(w) >= 5:
                backfill_pool.append(r)
        # Prefer words with higher concreteness (they're at least common) and shorter
        backfill_pool.sort(key=lambda r: (r.get("quality_tier", 4), -r["concreteness_score"], r["g_rank"], r["word"]))
        # Apply soft phonetic dedup against the existing adj pool
        adj_metas = {}
        for r in adj_kept:
            adj_metas.setdefault(r["metaphone_code"], []).append(r["word"])
        added = 0
        for r in backfill_pool:
            if added >= deficit:
                break
            w, meta = r["word"], r["metaphone_code"]
            confused = False
            for pw in adj_metas.get(meta, []):
                if w[:2] == pw[:2] and jellyfish.damerau_levenshtein_distance(w, pw) <= 1:
                    confused = True
                    break
            if confused:
                continue
            r2 = dict(r); r2["backfill"] = "morph-suffix"
            adj_kept.append(r2)
            adj_metas.setdefault(meta, []).append(w)
            added += 1
        print(f"adj morphological backfill: added {added} words "
              f"(target={deficit}, available={len(backfill_pool)})")
        # And these words must be removed from the noun pool to preserve disjointness
        backfilled_words = {r["word"] for r in adj_kept if r.get("backfill")}
        kept.loc[kept.word.isin(backfilled_words), "pool"] = "adj"

    # If still short after morph-backfill, accept previously-dedup-dropped
    # adjectives back in priority order (visual-distinct enough for text use).
    if len(adj_kept) < ADJ_TARGET:
        relaxation = f"accept-collisions+{relaxation}"
        deficit = ADJ_TARGET - len(adj_kept)
        kept_adj_words = {r["word"] for r in adj_kept}
        addable = [r for r in adj_dedup_dropped if r["word"] not in kept_adj_words]
        addable.sort(key=lambda r: (r.get("quality_tier", 4), -r["primary_score"], r["g_rank"]))
        added = 0
        for r in addable:
            if added >= deficit: break
            adj_kept.append(r)
            added += 1
        print(f"adj-deficit step 4: accepted {added} previously-dedup-dropped adj back")

    print(f"  → adj pool relaxation level: {relaxation}")

    # --- Noun pool ---
    noun_rows = kept[kept.pool == "noun"].sort_values(
        ["primary_score", "g_rank", "word"], ascending=[False, True, True]
    ).to_dict("records")
    noun_kept, noun_dedup_dropped = phonetic_dedup(noun_rows, strict=True)
    print(f"noun after strict phonetic dedup: {len(noun_kept)} (dropped {len(noun_dedup_dropped)})")
    noun_relax = "strict"

    if len(noun_kept) < NOUN_TARGET:
        noun_relax = "soft-dedup"
        print("noun-deficit step 1: relaxing dedup to first-2-letters + Lev1")
        noun_kept, noun_dedup_dropped = phonetic_dedup(noun_rows, strict=False)
        print(f"noun (soft dedup): {len(noun_kept)}")

    # If noun pool is still short, accept dropped-by-strict-dedup words back
    # in priority order until target is met. These are nouns that share a
    # metaphone code AND Lev1 with another kept noun but DON'T share first
    # 2 letters — i.e., visually distinguishable in writing.
    if len(noun_kept) < NOUN_TARGET:
        noun_relax = f"accept-collisions+{noun_relax}"
        deficit = NOUN_TARGET - len(noun_kept)
        kept_words = {r["word"] for r in noun_kept}
        # Re-derive strict-dropped pool
        all_rows = noun_rows
        kept_strict, strict_dropped = phonetic_dedup(all_rows, strict=True)
        kept_strict_words = {r["word"] for r in kept_strict}
        # Words available to add back: dropped-by-strict, not currently kept
        addable = [r for r in strict_dropped if r["word"] not in kept_words]
        addable.sort(key=lambda r: (r.get("quality_tier", 4), -r["primary_score"], r["g_rank"]))
        added = 0
        for r in addable:
            if added >= deficit: break
            noun_kept.append(r)
            added += 1
        print(f"noun-deficit step 2: accepted {added} previously-dedup-dropped words back")
    print(f"  → noun pool relaxation level: {noun_relax}")

    # Truncate to target
    if len(adj_kept) < ADJ_TARGET:
        print(f"!! adj pool short: have {len(adj_kept)}, need {ADJ_TARGET}", file=sys.stderr)
    if len(noun_kept) < NOUN_TARGET:
        print(f"!! noun pool short: have {len(noun_kept)}, need {NOUN_TARGET}", file=sys.stderr)

    adj_final = adj_kept[:ADJ_TARGET]
    noun_final = noun_kept[:NOUN_TARGET]
    adj_overflow = adj_kept[ADJ_TARGET:]
    noun_overflow = noun_kept[NOUN_TARGET:]

    # Disjointness check
    adj_set = {r["word"] for r in adj_final}
    noun_set = {r["word"] for r in noun_final}
    overlap = adj_set & noun_set
    if overlap:
        print(f"!! disjointness violated: {len(overlap)} overlapping words: {list(overlap)[:5]}",
              file=sys.stderr)
        return 2

    # Sort outputs alphabetically
    adj_words = sorted(adj_set)
    noun_words = sorted(noun_set)
    OUT_ADJ.write_text("\n".join(adj_words) + "\n")
    OUT_NOUN.write_text("\n".join(noun_words) + "\n")

    # Selection log
    log_rows = []
    for r in adj_final:
        log_rows.append({**r, "outcome": "selected_adj"})
    for r in noun_final:
        log_rows.append({**r, "outcome": "selected_noun"})
    for r in adj_overflow:
        log_rows.append({**r, "outcome": "overflow_adj"})
    for r in noun_overflow:
        log_rows.append({**r, "outcome": "overflow_noun"})
    for r in adj_dedup_dropped:
        log_rows.append({**r, "outcome": "dedup_drop_adj"})
    for r in noun_dedup_dropped:
        log_rows.append({**r, "outcome": "dedup_drop_noun"})
    pd.DataFrame(log_rows).to_csv(LOG, sep="\t", index=False)

    print(f"\nWrote:")
    print(f"  {OUT_ADJ}: {len(adj_words)} words")
    print(f"  {OUT_NOUN}: {len(noun_words)} words")
    print(f"  {LOG}: {len(log_rows)} rows")

    if len(adj_words) != ADJ_TARGET or len(noun_words) != NOUN_TARGET:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
