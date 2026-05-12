#!/usr/bin/env python3
"""Step 2: union sources -> normalize -> dedupe -> POS-tag with WordNet.

Output: data/02_pos_tagged.tsv with columns
  word, length, is_adjective, is_noun, is_other, source_set
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
import csv
from collections import defaultdict

import nltk
from nltk.corpus import wordnet as wn

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "02_pos_tagged.tsv"

WORD_RE = re.compile(r"^[a-z]{4,7}$")


def extract_quoted(text: str) -> list[str]:
    """Return all single- or double-quoted tokens in text (Ruby/Go/TS sources)."""
    # %w(...) blocks (Ruby) → bare words
    out: list[str] = []
    for m in re.finditer(r"%w\(([^)]*)\)", text, flags=re.DOTALL):
        out.extend(m.group(1).split())
    # 'foo' (TS) and "foo" (Go/TS)
    for m in re.finditer(r"['\"]([a-zA-Z][a-zA-Z\-]*)['\"]", text):
        out.append(m.group(1))
    return out


def parse_heroku_rb() -> tuple[list[str], list[str]]:
    """Heroku haikunator.rb has two %w(...) blocks: adjectives, then nouns."""
    text = (RAW / "heroku_haikunator.rb").read_text()
    blocks = re.findall(r"%w\(([^)]*)\)", text, flags=re.DOTALL)
    if len(blocks) < 2:
        raise RuntimeError("expected 2 %w() blocks in heroku_haikunator.rb")
    adj = blocks[0].split()
    nouns = blocks[1].split()
    return adj, nouns


def parse_haikunatorjs() -> tuple[list[str], list[str]]:
    text = (RAW / "haikunatorjs.ts").read_text()
    # Two arrays: defaultAdjectives = [...], defaultNouns = [...]
    def grab(name: str) -> list[str]:
        m = re.search(rf"const\s+{name}\s*=\s*\[(.*?)\]", text, flags=re.DOTALL)
        if not m:
            return []
        return re.findall(r"'([a-z]+)'", m.group(1))
    return grab("defaultAdjectives"), grab("defaultNouns")


def parse_moby() -> list[str]:
    """Moby exposes `left` (adjectives) and `right` (names — mostly proper nouns).
    We use only `left`. Per CLAUDE.md."""
    text = (RAW / "moby_names_generator.go").read_text()
    m = re.search(r"left\s*=\s*\[\.\.\.\]string\{(.*?)\}", text, flags=re.DOTALL)
    if not m:
        raise RuntimeError("could not find `left` block in moby names-generator")
    return re.findall(r'"([a-z][a-z\-]+)"', m.group(1))


def load_wordlist(name: str, comment_chars: str = "#") -> list[str]:
    """Load a one-word-per-line file. EFF list has '11111\tword' format — strip leading tabs."""
    out: list[str] = []
    for raw in (RAW / name).read_text().splitlines():
        line = raw.strip()
        if not line or line[0] in comment_chars:
            continue
        # EFF format: <number>\t<word>
        if "\t" in line:
            parts = line.split("\t")
            line = parts[-1]
        out.append(line.lower())
    return out


def normalize_and_filter(words: list[str]) -> list[str]:
    out = []
    for w in words:
        w = w.strip().lower()
        if WORD_RE.match(w):
            out.append(w)
    return out


def main() -> int:
    sources: dict[str, list[str]] = {}

    # Reference Heroku-style sources (small, curated)
    h_adj, h_nouns = parse_heroku_rb()
    sources["heroku_adj"] = h_adj
    sources["heroku_nouns"] = h_nouns

    js_adj, js_nouns = parse_haikunatorjs()
    sources["haikunatorjs_adj"] = js_adj
    sources["haikunatorjs_nouns"] = js_nouns

    sources["moby_adj"] = parse_moby()

    # Larger curated sources
    sources["wordle_answers"] = load_wordlist("wordle_answers.txt")
    sources["wordle_guesses"] = load_wordlist("wordle_allowed_guesses.txt")
    sources["google_10000"] = load_wordlist("google_10000.txt")
    sources["eff"] = load_wordlist("eff_large_wordlist.txt")
    sources["bip39"] = load_wordlist("bip39_english.txt")
    sources["simple_adjectives"] = load_wordlist("simple_adjectives.txt")
    sources["english_alpha"] = load_wordlist("english_words_alpha.txt")

    # Sources that asserted-by-construction the word is an adjective. A word
    # in any of these is considered adjective even if WordNet lacks a synset
    # (WordNet missing-adj coverage is the documented reason — see PROCESS.md).
    REFERENCE_ADJ_SOURCES = {"heroku_adj", "haikunatorjs_adj", "moby_adj", "simple_adjectives"}
    REFERENCE_NOUN_SOURCES = {"heroku_nouns", "haikunatorjs_nouns"}

    # Track which sources each word came from. Reference sources earn tone-scoring credit.
    word_sources: dict[str, set[str]] = defaultdict(set)
    raw_counts = {}
    for src_name, words in sources.items():
        cleaned = normalize_and_filter(words)
        raw_counts[src_name] = (len(words), len(cleaned))
        for w in cleaned:
            word_sources[w].add(src_name)

    print("Source intake (raw → 4-6 letter lowercase):")
    for k, (raw_n, kept_n) in raw_counts.items():
        print(f"  {k:24s} {raw_n:>7} → {kept_n:>7}")
    print(f"Unique candidates (all sources): {len(word_sources)}")

    # POS-tag every candidate
    print("POS-tagging via WordNet...")
    rows = []
    pos_counts = defaultdict(int)
    for w in sorted(word_sources):
        srcs = word_sources[w]
        wn_adj = bool(wn.synsets(w, pos=wn.ADJ)) or bool(wn.synsets(w, pos=wn.ADJ_SAT))
        wn_noun = bool(wn.synsets(w, pos=wn.NOUN))
        is_verb = bool(wn.synsets(w, pos=wn.VERB))
        is_adv = bool(wn.synsets(w, pos=wn.ADV))
        ref_adj = bool(srcs & REFERENCE_ADJ_SOURCES)
        ref_noun = bool(srcs & REFERENCE_NOUN_SOURCES)
        is_adj = wn_adj or ref_adj
        is_noun = wn_noun or ref_noun
        is_other = (not is_adj and not is_noun) and (is_verb or is_adv)
        if is_adj:
            pos_counts["adj"] += 1
        if is_noun:
            pos_counts["noun"] += 1
        if is_adj and is_noun:
            pos_counts["both"] += 1
        if is_other:
            pos_counts["other"] += 1
        if not (is_adj or is_noun or is_verb or is_adv):
            pos_counts["unknown"] += 1
        rows.append({
            "word": w,
            "length": len(w),
            "is_adjective": int(is_adj),
            "is_noun": int(is_noun),
            "is_other": int(is_other),
            "wn_adj": int(wn_adj),
            "wn_noun": int(wn_noun),
            "ref_adj": int(ref_adj),
            "ref_noun": int(ref_noun),
            "source_set": ",".join(sorted(srcs)),
        })

    print(f"POS distribution: {dict(pos_counts)}")

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
