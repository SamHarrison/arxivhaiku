#!/usr/bin/env python3
"""Step 3: confirm 4-6 letters; drop pure verbs/adverbs (is_adj=0 AND is_noun=0)."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "02_pos_tagged.tsv"
OUT = ROOT / "data" / "03_length_filtered.tsv"


def main() -> int:
    df = pd.read_csv(IN, sep="\t")
    n0 = len(df)
    df = df[df.length.between(4, 7)]
    n1 = len(df)
    # Drop words with no adj/noun synset (and no reference assertion)
    df = df[(df.is_adjective == 1) | (df.is_noun == 1)]
    n2 = len(df)
    df = df.sort_values("word").reset_index(drop=True)
    df.to_csv(OUT, sep="\t", index=False)
    print(f"length filter: {n0} -> {n1} (length 4-7) -> {n2} (adj or noun)")
    print(f"adjectives: {(df.is_adjective==1).sum()}, nouns: {(df.is_noun==1).sum()}, both: {((df.is_adjective==1)&(df.is_noun==1)).sum()}")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
