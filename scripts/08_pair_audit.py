#!/usr/bin/env python3
"""Step 8: pair audit.

Generate 10,000 random adj-noun pairs and flag any that look problematic.
Also produce a 300-pair random sample for human (or self-) review."""
from __future__ import annotations
import random
import sys
from pathlib import Path
from collections import Counter
import re
import jellyfish

ROOT = Path(__file__).resolve().parent.parent
ADJ_FILE = ROOT / "data" / "07_selected_adj.txt"
NOUN_FILE = ROOT / "data" / "07_selected_nouns.txt"
LDNOOBW_FILE = ROOT / "data" / "raw" / "ldnoobw_en.txt"
OUT_AUDIT = ROOT / "data" / "08_pair_audit.tsv"
OUT_FLAGGED = ROOT / "data" / "08_flagged_words.txt"
OUT_HUMAN = ROOT / "data" / "08_human_sample.txt"

random.seed(42)

# Extended slur list (manually curated)
SLURS = {
    "nig", "fag", "spic", "kik", "wop", "wog", "gook", "chink", "jap",
    "kraut", "nigg", "nazi", "kkk", "klan",
    "tranny", "retard", "spaz", "psycho",
    "queer", "homo", "lesbo", "dyke",
    "slut", "whore", "skank", "thot", "tart",
    "rape", "raped", "raper", "rapis",
    "kill", "killed", "murder", "shoot", "shot", "stab",
    "hitler", "stalin", "mao", "isis", "qaeda",
    "shit", "fuck", "cunt", "piss", "ass", "tits",
    "dick", "cock", "balls", "boner", "wank", "pee", "poo",
    "porn", "smut", "lust", "orgy",
}

# Phrases that, formed from adj+noun, sound offensive even if neither word is
# individually a slur. We check the hyphenated and concatenated forms.
PROBLEM_SUBSTRINGS = {
    "naked", "nude", "rape", "kill", "dead", "die",
    "horn", "boob", "butt", "anal", "anus", "rect",
    "shit", "fuck", "cunt", "piss", "puke",
    "tits", "dick", "cock", "cock",
    "wetb", "honky", "negro", "queer", "tranny",
    "klan", "kkk", "nazi", "isis",
    "porn", "slut", "whore", "hooker",
    "drugs", "crack", "meth",
    "bomb", "shoot",
}


def load_ldnoobw_full() -> set[str]:
    s = set()
    for line in LDNOOBW_FILE.read_text().splitlines():
        line = line.strip().lower()
        if line:
            s.add(line)
    return s


def check_pair(adj: str, noun: str, ldnoobw: set[str]) -> list[str]:
    """Return list of flag tags."""
    flags = []
    hy = f"{adj}-{noun}"
    sp = f"{adj} {noun}"
    cat = f"{adj}{noun}"

    # LDNOOBW substring on each form
    for form in (hy, sp, cat):
        for bad in ldnoobw:
            if len(bad) >= 4 and bad in form:
                flags.append(f"ldnoobw:{bad}")
                break

    # Manually-curated problem substring on cat form
    for sub in PROBLEM_SUBSTRINGS:
        if sub in cat:
            flags.append(f"substr:{sub}")
            break

    # Slurs: substring check
    for sl in SLURS:
        if len(sl) >= 4 and (sl in cat or sl == adj or sl == noun):
            flags.append(f"slur:{sl}")
            break

    # Lev-1 from known profanity (on each form)
    for form in (hy, cat):
        for bad in ldnoobw:
            if len(bad) >= 5 and abs(len(form) - len(bad)) <= 1:
                if jellyfish.damerau_levenshtein_distance(form, bad) <= 1:
                    flags.append(f"lev1:{bad}")
                    break
        else:
            continue
        break

    # Sexual phrase patterns
    SEXUAL_PATTERNS = [
        ("naked", "*"), ("*", "rape"), ("rape", "*"),
        ("wet", "*"), ("hot", "*"), ("tight", "*"),
        ("hard", "*"), ("long", "rod"), ("big", "rod"),
    ]
    for ap, np_ in SEXUAL_PATTERNS:
        if (ap == "*" or adj == ap) and (np_ == "*" or noun == np_):
            flags.append(f"sex_pattern:{ap}-{np_}")

    # Violence patterns
    VIOLENCE_PATTERNS = [
        ("dead", "*"), ("dying", "*"), ("bloody", "*"),
        ("*", "bomb"), ("*", "war"), ("*", "kill"),
    ]
    for ap, np_ in VIOLENCE_PATTERNS:
        if (ap == "*" or adj == ap) and (np_ == "*" or noun == np_):
            flags.append(f"violence_pattern:{ap}-{np_}")

    return flags


def main() -> int:
    adj = [w.strip() for w in ADJ_FILE.read_text().splitlines() if w.strip()]
    nouns = [w.strip() for w in NOUN_FILE.read_text().splitlines() if w.strip()]
    print(f"Loaded {len(adj)} adjectives, {len(nouns)} nouns")
    ldnoobw = load_ldnoobw_full()
    print(f"LDNOOBW entries: {len(ldnoobw)}")

    N_PAIRS = 10_000
    pairs = [(random.choice(adj), random.choice(nouns)) for _ in range(N_PAIRS)]

    # Audit
    flagged_count = 0
    word_flag_counter: Counter[str] = Counter()
    rows = []
    for a, n in pairs:
        flags = check_pair(a, n, ldnoobw)
        if flags:
            flagged_count += 1
            word_flag_counter[a] += 1
            word_flag_counter[n] += 1
        rows.append((a, n, "|".join(flags)))

    with OUT_AUDIT.open("w") as f:
        f.write("adjective\tnoun\tflags\n")
        for a, n, fl in rows:
            f.write(f"{a}\t{n}\t{fl}\n")
    print(f"Wrote {OUT_AUDIT}; {flagged_count}/{N_PAIRS} pairs flagged")

    # Words with the most flag occurrences (these are the prime candidates for removal)
    with OUT_FLAGGED.open("w") as f:
        f.write("word\tflag_count\n")
        for w, c in word_flag_counter.most_common():
            f.write(f"{w}\t{c}\n")
    print(f"Wrote {OUT_FLAGGED} ({len(word_flag_counter)} unique flagged words)")

    # Human sample: 300 random pairs (separate seed so they're stable)
    rnd2 = random.Random(7777)
    sample = [(rnd2.choice(adj), rnd2.choice(nouns)) for _ in range(300)]
    with OUT_HUMAN.open("w") as f:
        for a, n in sample:
            f.write(f"{a}-{n}\n")
    print(f"Wrote {OUT_HUMAN}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
