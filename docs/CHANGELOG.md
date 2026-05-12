# CHANGELOG

## v1.0.1 — 2026-05-12

Patch release. Removes six demographic/religious terms that escaped
v1.0.0 filters and were caught during post-release alias sampling.

Removed nouns: `gentile`, `goyim`, `hadji`, `kafir`, `metis`, `paddy`.

Backfilled from the v1.0.0 overflow log; adjective pool unchanged.

| File             | SHA-256 |
|------------------|---------|
| `adjectives.txt` | `34d4edb55d168968dc9b4018a745633b3c782048cfdb99d93b586d8fc36ba905` (unchanged) |
| `nouns.txt`      | `965033026a676a90bcc7315a55fbd149e4d6dd55d03781a4eb77ec6bbd41ba35` |

This patch breaks the immutability rule documented in EXTENSION.md
because no production aliases had yet been issued from v1.0.0. Once
v1.0.x is deployed, the immutability rule applies — future fixes must
go through deprecation, not removal.

## v1.0.0 — 2026-05-12

Initial release.

- `adjectives.txt`: exactly 4,096 entries, alphabetically sorted
- `nouns.txt`: exactly 8,192 entries, alphabetically sorted
- Disjoint: no word appears in both files
- All entries are lowercase a–z, length 4–7

### File hashes

| File             | SHA-256 |
|------------------|---------|
| `adjectives.txt` | `34d4edb55d168968dc9b4018a745633b3c782048cfdb99d93b586d8fc36ba905` |
| `nouns.txt`      | `6447db4c3add61bed81d3736264716599e71ca52c3ca42137f66bafe478771ed` |

### Build summary

- Built per `CLAUDE.md` pipeline (Steps 1–11).
- Tone target: Heroku-style playful (see `docs/TONE.md`).
- Self-review by Claude Opus 4.7 (1M context) in lieu of the synchronous
  human checkpoint mandated by CLAUDE.md §Step 9 — per explicit user
  instruction. See `docs/TONE.md` and `data/09_review_notes.md`.

### Length constraint deviation from CLAUDE.md

CLAUDE.md §Hard constraints specifies "Word length 4, 5, or 6 letters". The
invoking user explicitly authorized expanding to 4–7 letters during build,
with the reasoning: "if we have to go up to some 7 letter words to make them
high quality then thats what we need to do. we need them all to be high
quality".

The 4–7 letter expansion yielded:
- ~8,400 raw WordNet adjective candidates (vs. ~3,250 at 4–6 letters)
- Sufficient slack to apply much stricter quality filters:
  - Hard-drop english_alpha-only nouns whose lexnames are all abstract
  - Hard-drop biology-genus words (noun.animal/noun.plant lexnames only)
  - Hard-drop demonym adjectives (comprehensive curated list)
  - Hard-drop proper nouns via WordNet `instance_hypernyms()` heuristic
- Result: both pools fit with **strict** Metaphone+Lev1 phonetic dedup
  (no relaxation needed), and the final pair audit flag rate is ~0.04%.

### Pair audit final result

- 50,000 random adj-noun pairs audited
- 19 flagged (0.038% flag rate) — all cross-boundary substring false
  positives at the join point (e.g., `furious+catcall` → "furiouscatcall"
  contains "scat")
- No standalone problem words remain after Step 9 removals.

### Length distribution

| Length | Adjectives | Nouns |
|-------:|-----------:|------:|
|      4 |        302 |    934 |
|      5 |        714 |  2,242 |
|      6 |      1,214 |  1,747 |
|      7 |      1,866 |  3,269 |

The longer-skewed distributions reflect that the 4–6 letter inventory
alone is supply-constrained for both pools at strict quality.

### Known limitations

- ~1,299 of the 4,096 adjectives lack a strict WordNet adjective synset
  (morphologically backfilled or sourced from reference adjective lists
  like `simple_adjectives`).  Documented in `docs/PROCESS.md` §"Honest
  limitations".
- A small set of cross-boundary substring matches remain (~19 in 50,000
  random pairs, ~0.04%). These do not produce recognizable profanity but
  the substring exists if the alias is character-grepped.

### Adopters' responsibilities

Per `docs/EXTENSION.md`:

- Pin both file hashes in deployment manifests.
- Do not modify either file once production aliases are issued; use a
  `deprecated.txt` overlay for retiring words.
- Re-run pair audit if either file is modified.
- v2 wordlists must be supersets of v1 (same word at same index).
