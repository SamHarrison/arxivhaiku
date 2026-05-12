#!/usr/bin/env python3
"""Step 6: tone scoring per CLAUDE.md.

Playfulness (adj):
  +3 in Heroku haikunator adj list
  +2 in Docker (moby) adj list
  +2 if WordNet synset includes sensory/aesthetic categories
  +1 if in google_10000 top 20k (we only have 10000; use that)
  -2 if WordNet domain is business/legal/medical/technical
  -3 if on manual formal/clinical blocklist

Concreteness (noun):
  +3 in Heroku noun list
  +2 in WordNet concrete-noun hierarchies (animals, plants, natural-objects, artifacts)
  +1 in google_10000
  -2 in abstract-noun hierarchies (cognition, attribute, state)
  -3 on manual clinical/corporate blocklist (already dropped in Step 4 mostly)

WordNet domain inspection: walk hypernyms up the lexicographer's category
('lex_name'). Lexnames like 'noun.animal', 'noun.plant', 'noun.artifact',
'noun.natural_object' are concrete; 'noun.cognition', 'noun.attribute',
'noun.state', 'noun.act' are abstract. Adjectives have 'adj.all', 'adj.pert',
'adj.ppl'.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
from nltk.corpus import wordnet as wn

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "05_phonetic.tsv"
OUT = ROOT / "data" / "06_tone_scored.tsv"

# WordNet lex_name categories — see https://wordnet.princeton.edu/documentation/lexnames5wn
CONCRETE_LEX = {
    "noun.animal", "noun.plant", "noun.artifact", "noun.body",
    "noun.food", "noun.object", "noun.substance", "noun.location",
    "noun.shape", "noun.plant", "noun.tree",
    "noun.natural_object",  # may not exist; will be tolerant
}
ABSTRACT_LEX = {
    "noun.cognition", "noun.attribute", "noun.state", "noun.act",
    "noun.event", "noun.feeling", "noun.relation", "noun.motive",
    "noun.process", "noun.communication", "noun.quantity", "noun.time",
    "noun.linkdef", "noun.tops",
}
# Adjective sensory/aesthetic indicators — WordNet doesn't subdivide adj well.
# We approximate by checking the noun.attribute that the adjective points to.
SENSORY_KEYWORDS = {
    # color words & gradients
    "color", "colour", "hue", "shade",
    # mood/weather/light
    "mood", "weather", "atmosphere", "light", "dark", "bright", "dim",
    "warmth", "temperature",
    # texture
    "texture", "softness", "hardness", "smoothness",
    # sound
    "sound", "noise", "quiet", "loud",
    # size/shape
    "size", "shape", "stature", "magnitude",
    # nature
    "nature", "wood", "forest", "meadow",
    # sensory
    "sense", "perceive",
}

# Lexnames for technical/clinical domains — penalize
TECHNICAL_ADJ_LEX = set()  # WordNet doesn't tag adj by domain reliably; use hand list
# Heroku haikunator adj list (from heroku_haikunator.rb)
HEROKU_ADJ_REF = {
    "autumn", "hidden", "bitter", "misty", "silent", "empty", "dry", "dark",
    "summer", "icy", "delicate", "quiet", "white", "cool", "spring", "winter",
    "patient", "twilight", "dawn", "crimson", "wispy", "weathered", "blue",
    "billowing", "broken", "cold", "damp", "falling", "frosty", "green",
    "long", "late", "lingering", "bold", "little", "morning", "muddy", "old",
    "red", "rough", "still", "small", "sparkling", "thrumming", "shy",
    "wandering", "withered", "wild", "black", "young", "holy", "solitary",
    "fragrant", "aged", "snowy", "proud", "floral", "restless", "divine",
    "polished", "ancient", "purple", "lively", "nameless",
}
HEROKU_NOUN_REF = {
    "waterfall", "river", "breeze", "moon", "rain", "wind", "sea", "morning",
    "snow", "lake", "sunset", "pine", "shadow", "leaf", "dawn", "glitter",
    "forest", "hill", "cloud", "meadow", "sun", "glade", "bird", "brook",
    "butterfly", "bush", "dew", "dust", "field", "fire", "flower", "firefly",
    "feather", "grass", "haze", "mountain", "night", "pond", "darkness",
    "snowflake", "silence", "sound", "sky", "shape", "surf", "thunder",
    "violet", "water", "wildflower", "wave", "resonance", "log", "dream",
    "cherry", "tree", "fog", "frost", "voice", "paper", "frog", "smoke",
    "star",
}
# haikunatorjs additions (from haikunatorjs.ts, already in candidates as ref_adj)
HAIKUNATORJS_ADJ = {
    "ancient", "autumn", "billowing", "bitter", "black", "blue", "bold",
    "broad", "broken", "calm", "cold", "cool", "crimson", "curly", "damp",
    "dark", "dawn", "delicate", "divine", "dry", "empty", "falling", "fancy",
    "flat", "floral", "fragrant", "frosty", "gentle", "green", "hidden",
    "holy", "icy", "jolly", "late", "lingering", "little", "lively", "long",
    "lucky", "misty", "morning", "muddy", "mute", "nameless", "noisy", "odd",
    "old", "orange", "patient", "plain", "polished", "proud", "purple",
    "quiet", "rapid", "raspy", "red", "restless", "rough", "round", "royal",
    "shiny", "shrill", "shy", "silent", "small", "snowy", "soft", "solitary",
    "sparkling", "spring", "square", "steep", "still", "summer", "super",
    "sweet", "throbbing", "tight", "tiny", "twilight", "wandering",
    "weathered", "white", "wild", "winter", "wispy", "withered", "yellow",
    "young", "aged",
}
HAIKUNATORJS_NOUN = {
    "art", "band", "bar", "base", "bird", "block", "boat", "bonus",
    "bread", "breeze", "brook", "bush", "butterfly", "cake", "cell", "cherry",
    "cloud", "credit", "darkness", "dawn", "dew", "disk", "dream", "dust",
    "feather", "field", "fire", "firefly", "flower", "fog", "forest", "frog",
    "frost", "glade", "glitter", "grass", "hall", "hat", "haze", "heart",
    "hill", "king", "lab", "lake", "leaf", "limit", "math", "meadow",
    "mode", "moon", "morning", "mountain", "mouse", "mud", "night", "paper",
    "pine", "poetry", "pond", "queen", "rain", "recipe", "resonance", "rice",
    "river", "salad", "scene", "sea", "shadow", "shape", "silence", "sky",
    "smoke", "snow", "snowflake", "sound", "star", "sun", "sunset", "surf",
    "term", "thunder", "tooth", "tree", "truth", "union", "unit",
    "violet", "voice", "water", "waterfall", "wave", "wildflower", "wind",
    "wood",
}


def load_google_top(n: int = 20000) -> set[str]:
    p = ROOT / "data" / "raw" / "google_10000.txt"
    words = [w.strip().lower() for w in p.read_text().splitlines() if w.strip()]
    return set(words[:n])  # only 10k available; we keep all of them


def load_moby_adj() -> set[str]:
    """Re-extract moby left[] adjectives."""
    import re
    text = (ROOT / "data" / "raw" / "moby_names_generator.go").read_text()
    m = re.search(r"left\s*=\s*\[\.\.\.\]string\{(.*?)\}", text, flags=re.DOTALL)
    return set(re.findall(r'"([a-z][a-z\-]+)"', m.group(1)))


def noun_lex_categories(word: str) -> set[str]:
    out = set()
    for s in wn.synsets(word, pos=wn.NOUN):
        out.add(s.lexname())
        # Walk up hypernyms a couple levels for category context
        for h in s.hypernyms()[:3]:
            out.add(h.lexname())
    return out


def adj_attribute_keywords(word: str) -> set[str]:
    """For each adj synset, look at its attribute() target and lemmas."""
    kw = set()
    for s in wn.synsets(word, pos=wn.ADJ) + wn.synsets(word, pos=wn.ADJ_SAT):
        kw.add(s.lexname())
        for attr in s.attributes():
            kw.add(attr.lexname())
            for lemma in attr.lemmas():
                kw.add(lemma.name().lower())
        # Definition string can hint at sensory content
        d = (s.definition() or "").lower()
        for kwd in SENSORY_KEYWORDS:
            if kwd in d:
                kw.add(kwd)
    return kw


def playfulness(word: str, row, google_top: set[str], moby_adj: set[str]) -> int:
    s = 0
    if word in HEROKU_ADJ_REF:
        s += 3
    if word in HAIKUNATORJS_ADJ:
        s += 2  # additional ref-pool credit
    if word in moby_adj:
        s += 2
    kw = adj_attribute_keywords(word)
    if kw & SENSORY_KEYWORDS:
        s += 2
    if word in google_top:
        s += 1
    # Penalize words whose only WordNet adj synsets are "adj.pert" (pertaining-to,
    # which is the technical/relational adjective lexname — feels formal)
    adj_synsets = wn.synsets(word, pos=wn.ADJ) + wn.synsets(word, pos=wn.ADJ_SAT)
    if adj_synsets and all(s_.lexname() == "adj.pert" for s_ in adj_synsets):
        s -= 1
    # Corroboration penalty: words known only from the long-tail english_alpha
    # wordlist are likely obscure (archaic, foreign-origin, technical jargon).
    if not getattr(row, "is_corroborated", 1):
        s -= 10  # near-hard drop: only used if corroborated supply runs out
    return s


def concreteness(word: str, row, google_top: set[str]) -> int:
    s = 0
    if word in HEROKU_NOUN_REF:
        s += 3
    if word in HAIKUNATORJS_NOUN:
        s += 2
    lex = noun_lex_categories(word)
    if lex & CONCRETE_LEX:
        s += 2
    if lex & ABSTRACT_LEX:
        s -= 2
    if word in google_top:
        s += 1
    if not getattr(row, "is_corroborated", 1):
        s -= 10  # near-hard drop: only used if corroborated supply runs out
    if getattr(row, "biology_obscure", 0):
        s -= 5  # likely a biology genus/species name
    return s


def source_quality_tier(source_set: str) -> int:
    """Rank candidates by source provenance. Lower = better.
    Tier 0: in any reference adj/noun (Heroku, haikunatorjs, moby) — gold standard.
    Tier 1: curated wordlist (simple_adjectives, wordle_answers, eff, bip39) +
            in google_10000 (frequency).
    Tier 2: in any curated source (wordle_guesses, simple_adjectives, eff, bip39)
            even without google.
    Tier 3: only in google_10000 (frequent but possibly noisy).
    Tier 4: only in english_alpha (long tail).
    """
    srcs = set(source_set.split(","))
    REF = {"heroku_adj", "heroku_nouns", "haikunatorjs_adj", "haikunatorjs_nouns", "moby_adj"}
    CURATED = {"simple_adjectives", "wordle_answers", "eff", "bip39"}
    CURATED2 = {"wordle_guesses"}
    if srcs & REF:
        return 0
    if (srcs & CURATED) and ("google_10000" in srcs):
        return 1
    if srcs & CURATED:
        return 2
    if (srcs & CURATED2) and ("google_10000" in srcs):
        return 2
    if srcs & CURATED2:
        return 3
    if "google_10000" in srcs:
        return 3
    return 4


def main() -> int:
    df = pd.read_csv(IN, sep="\t", keep_default_na=False)
    df["quality_tier"] = df.source_set.apply(source_quality_tier)
    google_top = load_google_top()
    moby_adj = load_moby_adj()

    play = []
    conc = []
    for row in df.itertuples():
        play.append(playfulness(row.word, row, google_top, moby_adj) if row.is_adjective else 0)
        conc.append(concreteness(row.word, row, google_top) if row.is_noun else 0)
    df["playfulness_score"] = play
    df["concreteness_score"] = conc

    df.to_csv(OUT, sep="\t", index=False)
    print(f"Wrote {OUT}")
    kept = df[df.drop_reason == ""]
    adj = kept[kept.is_adjective == 1]
    noun = kept[kept.is_noun == 1]
    print(f"Adj kept: {len(adj)}; score dist: "
          f"min={adj.playfulness_score.min()}, "
          f"median={adj.playfulness_score.median()}, "
          f"max={adj.playfulness_score.max()}")
    print(f"  histogram: {adj.playfulness_score.value_counts().sort_index().to_dict()}")
    print(f"Noun kept: {len(noun)}; score dist: "
          f"min={noun.concreteness_score.min()}, "
          f"median={noun.concreteness_score.median()}, "
          f"max={noun.concreteness_score.max()}")
    print(f"  histogram: {noun.concreteness_score.value_counts().sort_index().to_dict()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
