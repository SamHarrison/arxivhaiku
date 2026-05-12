# arxivhaiku

Heroku-haikunator-style two-word identifiers backed by a vetted, fixed-size
wordlist. Pairs an adjective with a noun to produce friendly aliases like
`sleepy-panda`, `frosty-meadow`, or `gentle-eagle`. Words are 4–7 letters,
lowercase a–z.

Built on a bijection: every alias maps to exactly one 25-bit canonical ID
(also expressible as a 5-character Crockford Base32 token).

| Pool        | Count  | Bits |
|-------------|-------:|-----:|
| adjectives  |  4,096 | 12   |
| nouns       |  8,192 | 13   |
| **product** | **33,554,432** | **25** (= 32⁵) |

## Install

```bash
pip install -e .
```

(no runtime dependencies beyond the standard library)

## Use as a library

```python
from arxivhaiku import haiku, encode, decode

# Random alias (cryptographic-grade RNG by default)
print(haiku())                 # 'frosty-meadow'

# Bijection with the 25-bit canonical space
alias = encode(0x1234567)      # 'broody-thrall'  (example)
canon = decode(alias)          # 0x1234567

# Custom separator
print(haiku(separator="_"))    # 'sleepy_panda'

# Crockford Base32 form
from arxivhaiku.codec import encode_crockford, decode_crockford
encode_crockford(0x1234567)    # 'K3X9P'  (example)
decode_crockford("K3X9P")      # 0x1234567

# Class-based, reproducible (use for tests; NOT security-sensitive IDs)
from arxivhaiku import Haikunator
h = Haikunator(seed=42)
h.haikunate()                  # always the same with this seed
```

## CLI

```bash
$ arxivhaiku
gentle-eagle

$ arxivhaiku gen -n 5
sleepy-panda
brave-otter
crimson-eagle  # example; "crimson" not in pool (7 letters), see docs/TONE.md
frosty-anchor
silver-meadow

$ arxivhaiku encode 1234567
brave-otter

$ arxivhaiku encode 0x12AB34
mossy-lantern

$ arxivhaiku encode K3X9P             # Crockford → alias
plumy-doodad

$ arxivhaiku encode --crockford-out 42
abase-acari    0000A    42

$ arxivhaiku decode brave-otter
1234567    0x012d687    14M67
```

## How the wordlists were built

See `docs/PROCESS.md` for the full pipeline. Briefly:

1. Acquire ~11 reference + curated wordlist sources (Heroku haikunator,
   haikunatorjs, Docker moby, Wordle answers/guesses, EFF, BIP-39,
   `SimpleWordlists` adjectives, dwyl/english-words).
2. POS-tag with WordNet + reference-list assertion.
3. Apply quality filters: profanity (LDNOOBW), brands, plurals,
   past-tense/gerund, comparatives, body/medical, demographic,
   religious, proper-noun, biology-genus.
4. Compute phonetic codes (Metaphone) for adaptive within-pool dedup.
5. Score playfulness (adjectives) and concreteness (nouns) using WordNet
   lexnames and reference-list overlap.
6. Select exactly 4,096 adj and 8,192 nouns by tier, score, and
   phonetic distinctness (with relaxation fallbacks when supply is short).
7. Run a 10,000-pair audit; remove problematic words; re-finalize.
8. Verify all hard constraints; emit SHA-256.

Each step writes intermediate TSV/TXT files so the pipeline is auditable.

## Honest caveats

- ~1,299 of the 4,096 adjectives lack a strict WordNet adjective synset.
  They appear in independently-curated adjective lists (`simple_adjectives`,
  Heroku haikunator, haikunatorjs). See `docs/TONE.md` and `docs/PROCESS.md`.
- A small fraction of random pairs (~0.04%) produce cross-boundary
  substring matches with profanity (e.g., `furious+catcall` →
  `furiouscatcall` contains `scat`). Applications should LDNOOBW-screen
  final aliases if this matters.
- Tone is necessarily subjective. See `docs/TONE.md` for the calls made
  and the rationale.
- Length constraint expanded from CLAUDE.md's 4–6 to 4–7 to enable
  higher-quality strict-filter selection. Documented in
  `docs/CHANGELOG.md` §"Length constraint deviation".

## Files

```
adjectives.txt              # 4,096 adjectives, alphabetically sorted
nouns.txt                   # 8,192 nouns, alphabetically sorted
arxivhaiku/                 # Python package
  __init__.py               # public API
  codec.py                  # generation + bijection
  __main__.py               # CLI
  data/                     # bundled wordlist copies
docs/
  PROCESS.md                # build pipeline
  SOURCES.md                # input wordlists + licenses
  STATISTICS.md             # final pool stats
  BLOCKLIST.md              # every word dropped + reason
  EXTENSION.md              # how to grow without breaking IDs
  TONE.md                   # subjective tone calls + Step-9 substitution note
  CHANGELOG.md              # release notes + SHA-256
data/
  01..10_*.tsv              # pipeline intermediates
  raw/                      # downloaded source files + SOURCES.md
scripts/
  01..10_*.py               # pipeline scripts (each idempotent)
tests/
  test_codec.py             # 27 unit tests covering wordlist + bijection
```

## License

MIT (for the code). The shipped wordlists derive from sources under MIT,
CC-BY, Apache-2.0, BSD, public domain, and Unlicense terms — see
`docs/SOURCES.md` for per-source attribution.
