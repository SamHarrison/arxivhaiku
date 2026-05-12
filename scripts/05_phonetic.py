#!/usr/bin/env python3
"""Step 5: phonetic distinctness via Metaphone.

We compute metaphone codes for every kept candidate. Phonetic deduplication is
applied per-pool in Step 7 after pool assignment, because a word in 'both'
needs a single deduplication context (one pool, not both).

Output: data/05_phonetic.tsv — appends 'metaphone_code' column.

NOTE: CLAUDE.md says "Double Metaphone (jellyfish.metaphone)". jellyfish exposes
.metaphone() (the single-code, post-2012 implementation). The single-code
output is sufficient for the within-pool dedup goal and is what jellyfish
actually provides. See docs/PROCESS.md for the substitution rationale."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import jellyfish

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "04_quality_filtered.tsv"
OUT = ROOT / "data" / "05_phonetic.tsv"


def main() -> int:
    df = pd.read_csv(IN, sep="\t", keep_default_na=False)
    df["metaphone_code"] = df.word.apply(jellyfish.metaphone)
    df.to_csv(OUT, sep="\t", index=False)
    print(f"Wrote {OUT} ({len(df)} rows)")
    kept = df[df.drop_reason == ""]
    print(f"kept candidates: {len(kept)}")
    # Quick stats
    print(f"unique metaphone codes (kept): {kept.metaphone_code.nunique()}")
    print(f"collision groups (kept): {(kept.groupby('metaphone_code').size() > 1).sum()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
