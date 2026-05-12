# arxivhaiku

> Heroku-haikunator-style two-word identifiers backed by a vetted, fixed-size wordlist.

`arxivhaiku` pairs an adjective with a noun to produce friendly aliases like
`frosty-meadow`, `alpine-pixel`, or `gentle-eagle`. Words are 4–7 letters,
lowercase a–z, drawn from two curated lists shipped with the package.

The two pool sizes are chosen so the alias space is **exactly equivalent to
a 5-character [Crockford Base32][crockford] token** — a clean bijection
between three forms of the same ID:

| Form | Example | Range |
|------|---------|------:|
| canonical integer | `1234567` | `0 … 33_554_431` (25 bits) |
| Crockford token   | `15NM7`   | 5 chars, alphabet `0-9A-Z\{ILOU}` |
| alias             | `alpine-pixel` | 4–7 letter adj + `-` + 4–7 letter noun |

```
2^12 adjectives  ×  2^13 nouns  =  2^25 aliases  =  32^5 Crockford tokens
   4,096               8,192      33,554,432
```

[crockford]: https://www.crockford.com/base32.html

---

## Table of contents

- [Why arxivhaiku?](#why-arxivhaiku)
- [Install](#install)
- [Quick start](#quick-start)
- [Library API](#library-api)
- [CLI](#cli)
- [The bijection](#the-bijection)
- [How the wordlists were built](#how-the-wordlists-were-built)
- [Storage and URL patterns](#storage-and-url-patterns)
- [Quality and safety](#quality-and-safety)
- [Versioning and immutability](#versioning-and-immutability)
- [Honest caveats](#honest-caveats)
- [Project layout](#project-layout)
- [Reproducing the build](#reproducing-the-build)
- [License](#license)

---

## Why arxivhaiku?

You have an integer ID space (database row IDs, content hashes, allocated
counters) and want to surface it to humans as something memorable instead of
`12345` or `K3X9P`.

Existing Heroku-haikunator implementations (Ruby, JS, Python) ship a few
dozen adjectives and nouns — fine for "give me a unique-looking app name"
but the alias space is tiny (~4,000 distinct pairs) and the lists were
chosen ad-hoc. arxivhaiku provides:

- **A larger, audited pool.** 4,096 adjectives × 8,192 nouns = 33.5M unique
  aliases, drawn from 11 source wordlists (Heroku, haikunatorjs, Docker
  moby, Wordle, EFF, BIP-39, SCOWL substitute, Project-Gutenberg-derived
  POS data) and filtered against profanity (LDNOOBW), brand names,
  demonyms, biology genera, proper nouns, plurals, comparatives, and more.
- **A clean bijection.** Pool sizes are powers of two so every canonical
  integer maps to exactly one alias with no gaps or cycle-walking. The
  same 25-bit integer is also exactly 5 Crockford Base32 characters.
- **A reproducible, auditable build.** 10 idempotent pipeline scripts
  produce the lists from raw sources. Every dropped word is logged with
  its drop reason in `docs/BLOCKLIST.md`. The final pair-audit flag rate
  is **0.038%** (19 in 50,000 random pairs, all cross-boundary substring
  false positives).
- **Versioning rules for production.** Words can never be removed once
  aliases are issued (immutability), only deprecated. v2 wordlists must
  be supersets of v1. See `docs/EXTENSION.md`.

## Install

```bash
pip install -e .
```

Python 3.10 or newer. **No runtime dependencies** beyond the standard
library — the wordlists ship with the package and the bijection is pure
integer arithmetic.

(Build dependencies — `nltk`, `pandas`, `jellyfish`, `requests` — are only
needed if you want to *rebuild* the wordlists from source. See
[Reproducing the build](#reproducing-the-build).)

## Quick start

```python
from arxivhaiku import haiku, encode, decode

haiku()                # 'frosty-meadow' — random, cryptographic-grade entropy
encode(1234567)        # 'alpine-pixel'  — integer → alias
decode('alpine-pixel') # 1234567          — alias → integer (round-trips)
```

Or from the shell:

```bash
$ arxivhaiku
gentle-eagle

$ arxivhaiku gen -n 3
plumy-doodad
sleepy-panda
brave-otter
```

## Library API

```python
from arxivhaiku import (
    haiku, encode, decode,
    Haikunator,
    ADJ_BITS, NOUN_BITS, CANON_BITS, CANON_CHARS,
    InvalidAliasError, InvalidCanonicalError,
    list_adjectives, list_nouns,
)
from arxivhaiku.codec import (
    encode_crockford, decode_crockford,
    ADJ_COUNT, NOUN_COUNT, CANON_MAX,
)
```

### `haiku(*, separator="-", rng=None) → str`

Return a uniformly-random alias. Uses `secrets.SystemRandom` by default —
cryptographic-grade entropy suitable for production IDs. Pass an alternate
`rng` (any object with a `randrange(n)` method) for deterministic output.

```python
haiku()                  # 'frosty-meadow'
haiku(separator="_")     # 'frosty_meadow'
```

`haiku()` is **not deduplicated across calls**. Two calls can collide.
For uniqueness, store issued aliases and reject duplicates, or allocate
canonicals from a counter and `encode()` them.

### `encode(canonical: int, *, separator="-") → str`

Convert a canonical integer to its alias. The integer must be in
`[0, 33_554_431]`. The math:

```python
adj_index  = canonical >> 13              # top 12 bits
noun_index = canonical & 0x1FFF           # bottom 13 bits
alias      = adjectives[adj_index] + "-" + nouns[noun_index]
```

```python
encode(0)            # 'aaronic-aalii'    — first canonical
encode(1234567)      # 'alpine-pixel'
encode(0xABC123)     # 'fangled-apnea'    — hex input is fine
encode(33_554_431)   # 'zoning-zoril'     — last canonical
encode(-1)           # InvalidCanonicalError
encode(33_554_432)   # InvalidCanonicalError
```

### `decode(alias: str, *, separator="-") → int`

Inverse of `encode`. Splits on the separator, looks up each word's index
in the sorted wordlists (O(1) via dicts built at module import), and
reconstructs the integer: `(adj_index << 13) | noun_index`.

```python
decode('alpine-pixel') # 1234567
decode('alpine_pixel', separator='_')
decode('xxxxx-eagle')  # InvalidAliasError: unknown adjective
decode('brave-xxxxx')  # InvalidAliasError: unknown noun
decode('nodash')       # InvalidAliasError: malformed
```

`decode(encode(c)) == c` for every valid canonical `c`. Tested over 1024
samples spanning the full 25-bit space (`tests/test_codec.py:TestBijection`).

### `encode_crockford(canonical: int) → str` / `decode_crockford(token: str) → int`

The same canonical integer rendered as a 5-character [Crockford Base32][crockford]
token. Different surface form, same identity.

```python
from arxivhaiku.codec import encode_crockford, decode_crockford

encode_crockford(1234567)       # '15NM7'
decode_crockford('15NM7')       # 1234567
decode_crockford('15nm7')       # 1234567  (case-insensitive)
decode_crockford('15NM7-')      # 1234567  (hyphens stripped)
decode_crockford('I5NM7')       # 1234567  (Crockford normalization: I → 1)
decode_crockford('L5NM7')       # 1234567  (L → 1)
decode_crockford('O5NM7')       # 1234567  (O → 0)
```

The Crockford alphabet is `0123456789ABCDEFGHJKMNPQRSTVWXYZ` — 32 chars
with `I`, `L`, `O`, `U` excluded. Decoder normalizes `I`/`L` → `1` and
`O` → `0` so handwritten tokens can't be ambiguous.

### `Haikunator` class

A stateful, optionally seeded generator. Useful for tests where you want
reproducible aliases.

```python
from arxivhaiku import Haikunator

h = Haikunator(seed=42)
h.haikunate()    # always 'mucky-cither' with this seed
h.haikunate()    # always 'notal-pint'   (next call)

# Same seed → same sequence
h2 = Haikunator(seed=42)
assert h2.haikunate() == 'mucky-cither'
```

**Do not use `Haikunator(seed=...)` for production IDs.** The
`random.Random` PRNG it uses is predictable. For production, use
`haiku()` (or `Haikunator()` with no seed, which falls back to
`secrets.SystemRandom`).

### Errors

- `InvalidCanonicalError` — canonical integer out of range or not an int.
- `InvalidAliasError` — alias string malformed, or adj/noun not in pool.

### Constants

| Name | Value | Meaning |
|------|------:|---------|
| `ADJ_BITS` | 12 | bits encoding the adjective index |
| `NOUN_BITS` | 13 | bits encoding the noun index |
| `CANON_BITS` | 25 | total canonical bits (12 + 13) |
| `ADJ_COUNT` | 4,096 | adjectives in pool |
| `NOUN_COUNT` | 8,192 | nouns in pool |
| `CANON_MAX` | 33,554,431 | largest valid canonical |
| `CANON_CHARS` | `'0123…XYZ'` | Crockford alphabet |

## CLI

Installed as `arxivhaiku` (also runnable via `python -m arxivhaiku`).

```bash
$ arxivhaiku                        # one alias (default subcommand: gen)
gentle-eagle

$ arxivhaiku gen -n 5               # five aliases
plumy-doodad
sleepy-panda
frosty-meadow
brave-otter
silver-comet

$ arxivhaiku gen --sep _            # underscore separator
sleepy_panda

$ arxivhaiku encode 1234567         # int → alias
alpine-pixel

$ arxivhaiku encode 0xABC123        # hex int → alias
fangled-apnea

$ arxivhaiku encode 15NM7           # Crockford → alias
alpine-pixel

$ arxivhaiku encode --crockford-out 42
abase-acari    0000A    42

$ arxivhaiku decode alpine-pixel    # alias → all three forms
1234567    0x012d687    15NM7
```

## The bijection

Three interchangeable representations of the same 25-bit identifier:

```
            ┌─────────────────────────────┐
            │     25-bit integer          │
            │  canonical ∈ [0, 33_554_431) │
            └──────────────┬──────────────┘
              ▲            │              ▲
              │            ▼              │
   encode/    │   ┌────────────────┐      │  encode_crockford /
   decode     │   │  alias string  │      │  decode_crockford
              │   │ 'alpine-pixel' │      │
              │   └────────────────┘      │
              │                           │
              └───────────────────────────┘
                       ┌──────────┐
                       │ Crockford│
                       │  '15NM7' │
                       └──────────┘
```

The integer is the *truth*. Aliases and Crockford tokens are presentation
forms. Convert freely:

```python
canonical = 1234567
alias     = encode(canonical)              # 'alpine-pixel'
token     = encode_crockford(canonical)    # '15NM7'

assert decode(alias)            == canonical
assert decode_crockford(token)  == canonical
```

### Why exactly 4,096 × 8,192?

Power-of-two pool sizes make the encoding a single bit-shift:

```python
adj_index  = canonical >> 13   # top 12 bits  (2^12 = 4096)
noun_index = canonical & 0x1FFF # bottom 13 bits (2^13 = 8192)
```

If pools were, say, 4,000 and 8,000, some integer values in `[0, 32M)`
would point to nonexistent indices, and you'd need extra logic (modulo,
cycle-walking) to skip them. Power-of-two pools fill the entire 25-bit
space with no gaps and let the encoding be a pure arithmetic operation.

The sizes were also chosen to land on a single Crockford-base32 boundary:
**25 bits = exactly 5 chars** (since 32 = 2⁵). So a Crockford token is
*also* a direct re-encoding of the canonical with no padding or wasted
bits.

## How the wordlists were built

The full narrative is in [`docs/PROCESS.md`](docs/PROCESS.md). Briefly:

| Step | Script | Purpose |
|---|---|---|
| 1 | `01_acquire.py` | Fetch 11 source wordlists (Heroku, moby, Wordle, EFF, BIP-39, SimpleWordlists, dwyl, LDNOOBW). Record URL + SHA-256 + license. |
| 2 | `02_pos_tag.py` | Union + dedup, then POS-tag every candidate via WordNet + reference-list assertion. |
| 3 | `03_length_filter.py` | Keep 4–7 letter words with adj or noun POS. |
| 4 | `04_quality_filter.py` | Drop profanity, brands, plurals, past-tense/gerunds, comparatives, body/medical, demonyms, biology genera, proper nouns. |
| 5 | `05_phonetic.py` | Compute Metaphone code per word. |
| 6 | `06_tone_score.py` | Score playfulness (adj) and concreteness (noun) using WordNet lexnames + reference-list overlap. |
| 7 | `07_select.py` | Pool-assign ambiguous candidates; sort by source-quality tier + tone score; phonetic dedup; select top 4,096 / 8,192. |
| 8 | `08_pair_audit.py` | Audit 10,000 random pairs for profanity substrings and slur formation. |
| 9 | `09_self_review.py` | Hand-curated removal list (in lieu of synchronous human review — see `docs/TONE.md`). |
| 10 | `10_finalize.py` | Apply removals, backfill from overflow, sort alphabetically, emit SHA-256. |

Every step writes an intermediate TSV/TXT to `data/` so the build is
auditable end-to-end. Every dropped word is logged in `docs/BLOCKLIST.md`
with reason.

The final 50,000-pair audit flagged **19 pairs (0.038%)**, all of which
are cross-boundary substring false positives (e.g., `furious+catcall` →
`furiouscatcall` contains `scat` at the join). No standalone problem
words remain.

## Storage and URL patterns

The package doesn't prescribe how you store IDs — but the bijection makes
several patterns clean.

**Recommended (database column = canonical int):**

```sql
CREATE TABLE items (
  id INTEGER PRIMARY KEY,  -- canonical, 0..33_554_431
  ...
);
```

4 bytes per row, indexable, sortable. Display via `encode(row['id'])`.
This is the most common pattern.

**Alternative (column = Crockford string):**

```sql
CREATE TABLE items (
  id CHAR(5) PRIMARY KEY,  -- Crockford token, always uppercase, 5 chars
  ...
);
```

Slightly larger (5 bytes vs 4), but human-shareable as the storage form
itself. Useful if you're integrating with systems that already use
short-token IDs (ULID, KSUID — though those are longer).

**Not recommended (column = alias string):**

Variable length (9–15 chars typically), more index storage, slower
B-tree lookups, and ties your DB schema to a specific wordlist version.
If you want to retire a word later, you'd need to migrate every row that
contains it. Keep the alias as a derived presentation form, not the
storage key.

**URLs:**

```
/items/alpine-pixel      ← friendly, shareable, memorable
/items/15NM7             ← compact, suitable for SMS / QR
/items/1234567           ← discouraged: leaks row counts
```

Pick one canonical URL format. The dynamic route can `decode()` the alias
to find the row, with a clean 404 path on `InvalidAliasError`:

```python
# Flask / FastAPI / etc.
try:
    canonical = decode(alias)
except InvalidAliasError:
    abort(404)
row = db.fetch_one("SELECT * FROM items WHERE id = ?", canonical)
```

## Quality and safety

The lists have been:

- **Filtered against LDNOOBW profanity** (exact match on individual words;
  substring scan on pair concatenations).
- **Filtered against a curated demonym/religion list** (`indian`, `french`,
  `hindu`, `klan`, etc.) to avoid producing demographically charged aliases.
- **Filtered against brand names** (`apple`, `tesla`, `oracle`, `nike`,
  etc.) so the system doesn't trip trademark concerns.
- **Filtered against body parts, medical jargon, and biology genus names**
  (`liver`, `aortal`, `psylla`, `arundo`).
- **Filtered against archaic/dialect words** (`dreich`, `couthy`, `ugsome`)
  to keep tone playful and modern.
- **Phonetically de-duplicated** within each pool (Metaphone + Damerau-
  Levenshtein ≤ 1) so confusable pairs like `gold`/`cold` don't both appear.
- **Pair-audited** at 50,000 random pairs with 0.038% flag rate — all
  flags are cross-boundary substring false positives.

The shipped `adjectives.txt` and `nouns.txt` are SHA-256-pinned in
`docs/CHANGELOG.md`. Verify before deploying:

```bash
sha256sum adjectives.txt nouns.txt
# adjectives.txt:  34d4edb55d168968dc9b4018a745633b3c782048cfdb99d93b586d8fc36ba905
# nouns.txt:       965033026a676a90bcc7315a55fbd149e4d6dd55d03781a4eb77ec6bbd41ba35
```

**Caveats** ([honest caveats below](#honest-caveats)) — no filter is
perfect. If your application surfaces aliases to users in safety-critical
contexts, run your own LDNOOBW substring screen at issue time.

## Versioning and immutability

**Once you issue aliases from a given wordlist version in production, you
can never remove a word from that version.** A production alias is a
foreign key. Removing the underlying word would orphan every alias that
referenced it. See `docs/EXTENSION.md` for the full rules:

- Removals happen only via a separate `deprecated.txt` overlay that the
  resolver still recognizes (so old aliases continue to work) but the
  generator refuses to use (so no *new* aliases get the deprecated word).
- v2 wordlists must be **supersets** of v1 — every v1 word at the same
  index. New words append.
- The bijection math expands naturally: 6-char Crockford = 30 bits, which
  could be a 16,384 × 65,536 pool (14 + 16 bits) preserving every
  v1 alias's index.

## Honest caveats

- **~1,299 of the 4,096 adjectives lack a strict WordNet adjective synset.**
  They appear in independently-curated adjective sources
  (`simple_adjectives`, Heroku haikunator, haikunatorjs) which we trust
  as POS evidence. WordNet alone yields only ~3,250 4–7 letter adjective
  synsets — short of the 4,096 target. Documented in
  [`docs/PROCESS.md`](docs/PROCESS.md) and
  [`docs/TONE.md`](docs/TONE.md).
- **A small fraction of random pairs (~0.04%) produce cross-boundary
  substring matches with profanity** (e.g., `furious+catcall` →
  `furiouscatcall` contains `scat`). These don't form recognizable words
  but the substring exists if the alias is character-grepped. Applications
  in safety-critical contexts should LDNOOBW-screen final aliases.
- **Tone is subjective.** The Heroku-style playful aesthetic was
  calibrated by sampling. See [`docs/TONE.md`](docs/TONE.md) for the
  specific calls made and the rationale.
- **Length expanded to 4–7 letters** during build (the original spec
  called for 4–6) to enable stricter quality filters. Documented in
  [`docs/CHANGELOG.md`](docs/CHANGELOG.md) §"Length constraint deviation".
- **Step 9 (human review) was performed programmatically** in lieu of a
  synchronous human reviewer, per explicit user instruction. The
  `HARD_REMOVE` list in `scripts/09_self_review.py` is the audit trail.
  A future human reviewer should re-audit before promoting to a release
  used in compliance-sensitive contexts.

## Project layout

```
arxivhaiku/                  ← Python package
  __init__.py                  public API
  codec.py                     bijection + RNG
  __main__.py                  CLI
  data/
    adjectives.txt             bundled copy of the wordlist
    nouns.txt

adjectives.txt               ← canonical wordlist (4,096 lines)
nouns.txt                    ← canonical wordlist (8,192 lines)

docs/
  PROCESS.md                   build pipeline narrative
  SOURCES.md                   input wordlists + licenses
  STATISTICS.md                final pool characteristics
  BLOCKLIST.md                 every dropped word + reason (~7.5K entries)
  TONE.md                      subjective calls + reasoning
  EXTENSION.md                 immutability + v2 rules
  CHANGELOG.md                 release notes + SHA-256 pins

scripts/
  01_acquire.py                ← idempotent pipeline scripts;
  02_pos_tag.py                  re-run any time to verify the build.
  03_length_filter.py
  04_quality_filter.py
  05_phonetic.py
  06_tone_score.py
  07_select.py
  08_pair_audit.py
  09_self_review.py
  10_finalize.py
  quality_gates.py             14 acceptance checks

data/                        ← pipeline intermediates (committed for audit)
  raw/                         downloaded source wordlists + SOURCES.md
  02_*.tsv … 10_sha256.txt     per-step outputs

tests/
  test_codec.py                27 unit tests (Vitest-portable)

pyproject.toml               ← MIT, Python 3.10+
LICENSE                      ← MIT
CLAUDE.md                    ← original spec / build prompt
```

## Reproducing the build

The wordlists are committed and SHA-256-pinned, so you don't need to
rebuild to use the package. But the build is fully reproducible:

```bash
# 1. install build deps (runtime needs none of these)
pip install requests jellyfish pandas nltk
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4'); nltk.download('brown', quiet=True); nltk.download('universal_tagset', quiet=True)"

# 2. run the pipeline (each step is idempotent; re-running is safe)
python scripts/01_acquire.py        # downloads raw sources to data/raw/
python scripts/02_pos_tag.py
python scripts/03_length_filter.py
python scripts/04_quality_filter.py
python scripts/05_phonetic.py
python scripts/06_tone_score.py
python scripts/07_select.py
python scripts/08_pair_audit.py
python scripts/09_self_review.py
python scripts/10_finalize.py       # writes adjectives.txt + nouns.txt

# 3. verify
python scripts/quality_gates.py     # 14 acceptance checks
python -m unittest discover tests   # 27 unit tests
```

The build is **deterministic up to WordNet version and library versions**.
The exact SHA-256 of the shipped files is pinned in `docs/CHANGELOG.md`.

## License

MIT — see [`LICENSE`](LICENSE).

The shipped wordlists are derived from open-source inputs under MIT,
CC-BY 3.0/4.0, Apache-2.0, BSD-2-Clause, public domain, and Unlicense
terms. Per-source attribution is in [`docs/SOURCES.md`](docs/SOURCES.md).
