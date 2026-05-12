# CLAUDE.md — Heroku-Style Adjective-Noun Alias Wordlist Construction

## Project goal

Produce two curated, vetted wordlists for a corporate file identifier system:

- **Adjective pool**: exactly **4,096** words, 4–6 letters, playful tone
- **Noun pool**: exactly **8,192** words, 4–6 letters, concrete nouns

Plus full documentation of how the lists were built.

Example aliases the production system will eventually produce: `sleepy-panda`, `brave-otter`, `crimson-eagle`, `frosty-anchor`. Order is always **adjective-noun**.

## The deliverables

1. **`adjectives.txt`** — exactly 4,096 vetted adjectives, one per line, sorted alphabetically
2. **`nouns.txt`** — exactly 8,192 vetted nouns, one per line, sorted alphabetically
3. **Process documentation in `docs/`** — auditable record of every decision

The two wordlists must be **disjoint** (no word appears in both).

## Why these sizes (context — read carefully)

The wordlists pair with a 5-character Crockford Base32 canonical identifier scheme:

- **Canonical ID**: 5-char Crockford Base32 (e.g., `K3X9P`) — 32⁵ = 33,554,432 unique IDs (25 bits)
- **Alias**: `<adjective>-<noun>` (e.g., `sleepy-panda`)

The pool sizes are chosen for **exact bit alignment** with the canonical:

- 4,096 adjectives = 2¹² (12 bits)
- 8,192 nouns = 2¹³ (13 bits)
- 12 + 13 = 25 bits = 32⁵ canonicals exactly

This means every canonical ID maps to exactly one adjective-noun pair and vice versa — no overshoot, no undershoot, no cycle-walking. The bijection is clean.

**Do not deliver different counts.** Exact sizes are required for the bijection math.

## Hard constraints (non-negotiable)

### Both pools must satisfy:

1. Word length 4, 5, or 6 letters
2. Lowercase a–z only (no apostrophes, hyphens, accents, numbers, proper nouns)
3. Common enough that a typical English-speaking adult recognizes the word when heard
4. Not profanity, slurs, or otherwise offensive
5. Not a trademarked brand, drug name, or major product name
6. Not phonetically near-identical to another word in the same pool (Double Metaphone distinct within pool)
7. Disjoint across pools: no word appears in both `adjectives.txt` and `nouns.txt`

### Adjective pool specifically:

8. Word must function as an adjective in modern English (WordNet adjective synset present)
9. Tone: **playful, evocative, Heroku-style** — favor mood/sensory/nature descriptors over formal/technical terms
10. Drop comparatives (`bigger`) and superlatives (`biggest`) — base form is preferred
11. Drop participial adjectives that are obvious past tenses of verbs (`baked`, `fried`) unless the adjectival usage is dominant (`tired`, `fancy`, `aged`)

### Noun pool specifically:

12. Word must function as a noun in modern English (WordNet noun synset present)
13. Concrete over abstract — `eagle`, `river`, `lantern` are great; `truth`, `merit`, `nexus` are not
14. Drop plurals where singular exists (`eagles` if `eagle` is in)
15. Drop mass nouns that don't pair naturally with adjectives in a Heroku-style name (`milk`, `air`, `dust` — produces weird aliases like `sleepy-air`)
16. Drop body parts, medical conditions, and human-anatomy terms — too easy to create offensive pairings
17. Drop terms strongly associated with specific demographics, religions, or political identities

## Tone target (playful, Heroku-style)

The aesthetic to aim for: aliases should feel like names from a children's book or a fantasy world, not a corporate compliance document. Reference points:

- **Good adjective examples**: `sleepy`, `brave`, `crimson`, `frosty`, `gentle`, `wild`, `silent`, `silly`, `merry`, `cosmic`, `dusty`, `lucky`, `noble`, `tiny`, `swift`, `golden`, `hidden`, `bright`, `velvet`, `lunar`
- **Good noun examples**: `panda`, `otter`, `eagle`, `river`, `lantern`, `anchor`, `meadow`, `comet`, `acorn`, `harbor`, `feather`, `pebble`, `compass`, `willow`

- **Bad adjective examples (too formal/technical)**: `viable`, `optimal`, `nominal`, `legal`, `fiscal`, `urban`, `civil`, `axial`, `modal`
- **Bad noun examples (too abstract/clinical)**: `factor`, `system`, `method`, `policy`, `region`, `entity`, `concept`, `metric`

Gut check: would this word feel at home in *Wind in the Willows*, *Studio Ghibli*, or an indie video game? If yes, it's playful. If it sounds like a quarterly business review, it's not.

This is necessarily subjective. Document the tone calls made and trust the human reviewer in Step 9 to calibrate.

## Inputs (open-source sources)

Download these at the start of work. Record URL, license, SHA-256, and download timestamp for each in `data/raw/SOURCES.md`.

### Primary sources

| Source | URL | Purpose | License |
|---|---|---|---|
| WordNet (via NLTK) | `nltk.download('wordnet')` | POS classification + synset filtering | WordNet License (permissive) |
| Heroku haikunator (Ruby) | `https://github.com/usmanbashir/haikunator/blob/master/lib/haikunator.rb` | Reference adjective + noun lists | MIT |
| haikunatorjs | `https://github.com/Atrox/haikunatorjs/blob/master/src/haikunator.ts` | Alternative reference list | MIT |
| Docker moby names-generator | `https://github.com/moby/moby/blob/master/pkg/namesgenerator/names-generator.go` | Reference adjectives | Apache 2.0 |
| Wordle answers | `https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/wordle-answers-alphabetical.txt` | ~2,315 vetted 5-letter words | De facto public domain |
| Wordle allowed guesses | `https://gist.githubusercontent.com/cfreshman/cdcdf777450c5b5301e439061d29694c/raw/wordle-allowed-guesses.txt` | ~10,657 additional 5-letter words | De facto public domain |
| SCOWL | `http://wordlist.aspell.net/` | Comprehensive English word source by frequency tier | BSD-like |
| google-10000-english | `https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa.txt` | Frequency ranking | MIT |
| LDNOOBW | `https://raw.githubusercontent.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/master/en` | Profanity blocklist | CC-BY 4.0 |

### Secondary sources (use if pool sizes fall short)

| Source | URL | Purpose |
|---|---|---|
| EFF Large Wordlist | `https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt` | Backup curated 4–9 letter words |
| BIP-39 English | `https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt` | Backup vetted 3–8 letter words |
| SUBTLEX-US | search: `subtlex-us frequency list github` | Frequency by spoken usage |

If any URL fails, find a canonical mirror and document the substitution.

## Directory structure to create

```
.
├── CLAUDE.md                   (this file — do not modify)
├── adjectives.txt              (FINAL: 4,096 adjectives)
├── nouns.txt                   (FINAL: 8,192 nouns)
├── data/
│   ├── raw/                    (downloads + SOURCES.md)
│   ├── 01_candidates.tsv
│   ├── 02_pos_tagged.tsv
│   ├── 03_length_filtered.tsv
│   ├── 04_quality_filtered.tsv
│   ├── 05_phonetic.tsv
│   ├── 06_tone_scored.tsv
│   ├── 07_selected_adj.txt
│   ├── 07_selected_nouns.txt
│   ├── 08_pair_audit.tsv
│   └── 08_flagged_words.txt
├── scripts/
│   ├── 01_acquire.py
│   ├── 02_pos_tag.py
│   ├── 03_length_filter.py
│   ├── 04_quality_filter.py
│   ├── 05_phonetic.py
│   ├── 06_tone_score.py
│   ├── 07_select.py
│   ├── 08_pair_audit.py
│   └── 10_finalize.py
└── docs/
    ├── PROCESS.md
    ├── SOURCES.md
    ├── STATISTICS.md
    ├── BLOCKLIST.md
    ├── EXTENSION.md
    ├── TONE.md
    └── CHANGELOG.md
```

## Pipeline (execute in order)

Each step writes intermediate files so the process is auditable. Every script must be idempotent — re-running produces identical output (set random seeds).

### Step 1 — Acquire raw sources
- Download all primary sources to `data/raw/`
- Install and load WordNet: `python -c "import nltk; nltk.download('wordnet')"`
- Install SCOWL package or download size tiers 35, 40, 50
- Record SHA-256, URL, timestamp, license for each in `data/raw/SOURCES.md`
- Verify each file is non-empty and well-formed

### Step 2 — Build candidate pool and POS-tag
- Union all words from: Heroku adjectives, Heroku nouns, Docker adjectives, Wordle answers, Wordle guesses, SCOWL size 40 (4–6 letter subset)
- Normalize: lowercase, strip whitespace, filter to `^[a-z]{4,6}$`
- Deduplicate
- For each candidate, query WordNet:
  - `is_adjective`: True if `wordnet.synsets(word, pos=wn.ADJ)` is non-empty
  - `is_noun`: True if `wordnet.synsets(word, pos=wn.NOUN)` is non-empty
  - `is_other`: True if only verb/adverb synsets exist
- Output: `data/02_pos_tagged.tsv` with columns: `word`, `length`, `is_adjective`, `is_noun`, `is_other`, `source_set`

Expected: ~15,000–20,000 candidates.

### Step 3 — Length filter
- Confirm 4–6 letters (fast double-check)
- Drop anything where `is_adjective=False AND is_noun=False` (pure verbs/adverbs)
- Output: `data/03_length_filtered.tsv`

### Step 4 — Quality filters
Drop words matching any of:
- LDNOOBW profanity (case-insensitive)
- Manual brand blocklist (see below; extend during work)
- Ends in `s` AND a 3–5 letter singular form exists → drop plural
- Ends in `ed` AND base verb exists → drop past-tense (EXCEPT WordNet-marked adjectival: `tired`, `fancy`, `aged`)
- Ends in `ing` AND base verb exists → drop gerund (EXCEPT adjectival: `loving`, `daring`)
- Ends in `er` or `est` AND base form exists → drop comparative/superlative
- Body parts and medical terms (build a small list: `liver`, `colon`, `tumor`, `ulcer`, etc.)
- Words strongly associated with demographics/religion/politics

Every dropped word logged in `BLOCKLIST.md` with word, reason, source. No silent drops.

Output: `data/04_quality_filtered.tsv` with `drop_reason` column.

### Step 5 — Phonetic distinctness (per pool)
Apply Double Metaphone (`jellyfish.metaphone(word)`).

Done **independently per pool** since disjointness will eventually separate them:
- For adjective-only candidates: group by Metaphone, keep one per group
- For noun-only candidates: group by Metaphone, keep one per group
- For candidates that are both: defer assignment to Step 7

Output: `data/05_phonetic.tsv` with `metaphone_code` and `phonetic_kept`.

### Step 6 — Tone scoring (Heroku-style playfulness)

**Playfulness score for adjective candidates:**
- **+3** if in Heroku haikunator adjective list
- **+2** if in Docker's adjective list
- **+2** if WordNet synset includes sensory/aesthetic categories (colors, mood, weather, texture, size, light, sound)
- **+1** if in google-10000-english top 20k
- **−2** if WordNet domain is primarily business/legal/medical/technical
- **−3** if on the manual "formal/clinical" blocklist (see below)

**Concreteness score for noun candidates:**
- **+3** if in Heroku noun list
- **+2** if in WordNet concrete-noun hierarchies (animals, plants, natural-objects, artifacts)
- **+1** if in google-10000-english top 20k
- **−2** if in abstract-noun WordNet hierarchies (cognition, attribute, state)
- **−3** if on the manual "clinical/corporate" blocklist (see below)

These are heuristics. Step 9 hand review is where real tone calibration happens.

Output: `data/06_tone_scored.tsv` with `playfulness_score` and `concreteness_score` columns.

### Step 7 — Select 4,096 adjectives + 8,192 nouns
For words tagged both adjective and noun (e.g., `golden`, `silver`, `iron`):
- **Default**: assign to the pool where it scores higher (playfulness vs concreteness)
- **Tie-breaker**: prefer noun (noun pool is larger and harder to fill)
- **Override**: if Heroku haikunator uses the word in a specific pool, follow that

To populate:
1. Sort adjective candidates by playfulness score descending; take top 4,096
2. Sort noun candidates by concreteness score descending; take top 8,192
3. Verify disjointness: no word in both lists (the assignment rule should guarantee this; verify anyway)
4. If either pool falls short, expand source set (EFF, BIP-39) and re-run from Step 2

Output: `data/07_selected_adj.txt` (4,096 lines) and `data/07_selected_nouns.txt` (8,192 lines).

### Step 8 — Pair audit
Generate adj-noun pairs and check for problems:

- Generate **10,000 uniformly random adj-noun pairs**
- For each pair, check:
  - LDNOOBW on hyphenated, spaced, and concatenated forms
  - Profanity substring check
  - Levenshtein-1 distance from known profanity
  - **Demographic slur formation**: extended slur list (ethnic, religious, sexuality, disability)
  - **Sexual phrase detection**: manually-curated list
  - **Violence phrase detection**: manually-curated list

Generate **300 random pairs** for human review regardless of automated flags.

Outputs:
- `data/08_pair_audit.tsv` (all 10,000 pairs with flags)
- `data/08_flagged_words.txt` (union of words in flagged pairs, with counts)
- `data/08_human_sample.txt` (300 random pairs formatted for review)

### Step 9 — Human review checkpoint (MANDATORY STOP)

Before continuing, present to the human:
1. Flagged words from Step 8 with the specific pairs that flagged them
2. The 300-pair random sample
3. A random sample of 100 adjectives and 100 nouns from the selected pools
4. Selected words with playfulness or concreteness scores below the median (likely tone outliers)
5. Statistics: tier breakdown, length distribution, average score per pool

**Wait for explicit human approval or list of words to remove.** Do not finalize without this checkpoint.

Expect 50–200 word removals and 5–20 pair concerns.

### Step 10 — Finalize
- Apply human-requested removals (each logged in `BLOCKLIST.md` with reason "human review")
- If counts fall below targets, backfill from next-best candidates in `data/06_tone_scored.tsv`
- Re-verify disjointness after backfilling
- Sort alphabetically
- Verify exact counts: `wc -l adjectives.txt` = 4,096, `wc -l nouns.txt` = 8,192
- Run full constraint check
- Compute SHA-256 of both files

Output: `adjectives.txt` and `nouns.txt`.

### Step 11 — Documentation
Generate all files in `docs/`. See next section.

## Documentation requirements

### `docs/PROCESS.md`
Narrative of the build:
- What problem the wordlists solve, why 4,096 + 8,192
- Each pipeline step in plain English with counts at each stage
- Decisions (POS tagging library, tone scoring weights, disjointness assignment)
- Honest limitations ("the tone target is subjective; reviewer X made the calls on date Y")

### `docs/SOURCES.md`
Per input: URL, version/date, SHA-256, license, attribution, usage.

### `docs/STATISTICS.md`
- Length distribution per pool
- Score histograms (playfulness for adj, concreteness for nouns)
- POS overlap statistics (how many candidates were both; how disjointness was resolved)
- Metaphone group analysis per pool
- Sample of 50 random adjectives, 50 random nouns, 100 random pairs

### `docs/BLOCKLIST.md`
Every word dropped, with reason and pool. Sorted alphabetically. ~10,000+ entries expected.

### `docs/EXTENSION.md`
How to grow without breaking existing IDs:
- The immutability rule (below)
- v2 as superset of v1 (every v1 word at the same index)
- Deprecation, not removal, for problematic words
- Relationship to canonical Crockford space: if it grows to 6 chars (1B IDs), suggested v2 sizes are 16,384 adj × 65,536 noun = 2³⁰. Adjective pool 4× harder to fill — likely needs 3–8 letter range and looser tone.

### `docs/TONE.md`
Subjective tone calls deserve their own document:
- What "Heroku-style playful" means in practice with examples
- Reference systems (Heroku haikunator, Docker names)
- Edge cases encountered and how resolved
- Words the reviewer wanted to include but couldn't
- Words included with reservation

### `docs/CHANGELOG.md`
Start with v1.0.0:
```
## v1.0.0 — YYYY-MM-DD
- Initial release. 4,096 adjectives + 8,192 nouns.
- adjectives.txt SHA-256: <hash>
- nouns.txt SHA-256: <hash>
- Built per CLAUDE.md pipeline. Human review by <name>.
- Tone target: Heroku-style playful.
```

## Brand blocklist (starter — extend during work)

Drop these even though valid English. Add more as encountered:

```
apple, delta, prime, dodge, tesla, shell, total, sharp, sears,
kraft, cisco, intel, adobe, lotus, pixar, nokia, mazda, lexus,
honda, virgin, target, mango, ralph, prada, gucci, tommy, omega,
rolex, swiss, fiber, fanta, smart, vichy, bayer, basic, motel,
exxon, dupont, abbey, swatch, casio, kodak, atari, sanyo,
amazon, google, oracle, redhat, vmware, twitch, twitter, reddit,
fender, gibson, marlin, ranger, bronco, taurus, corona, modelo,
patron, dewars, smirnoff, absolut, prozac, xanax, viagra,
lipitor, tylenol, advil, motrin, boeing, airbus, lockheed
```

Judgment required. `apple` is dropped (Apple Inc.); `apply` is fine. `target` is dropped (Target Corp.); when in doubt, drop. The cost of dropping a borderline word is one less candidate from a pool with thousands; the cost of including one is real-world ambiguity.

## Formal/clinical blocklist for adjectives (starter)

Drop from adjective pool even though valid — too corporate for Heroku tone:

```
viable, optimal, nominal, fiscal, axial, modal, civic, urban,
legal, formal, lateral, neutral, partial, mutual, valid,
robust, dynamic, static, generic, atomic, kinetic, organic,
synthetic, systemic, chronic, acute, latent, manifest,
implicit, explicit, abstract, concrete, definite, indefinite,
relative, absolute, finite, infinite, discrete, continuous
```

These can still be nouns if they have noun synsets (`vector`, `matrix`); as adjectives they break the tone.

## Abstract/corporate blocklist for nouns (starter)

Drop from noun pool — too clinical:

```
factor, system, method, policy, region, entity, concept,
metric, vector, matrix, module, schema, vendor, client,
server, agent, action, status, output, input, format,
record, search, source, target, sample, sector, segment,
budget, profit, margin, asset, share, equity
```

## Versioning rules (CRITICAL — do not skip)

Once v1.0.0 is published and any production IDs are issued, **words can never be removed**. They can be marked deprecated in a separate file (preventing future aliases) but must continue to resolve for existing aliases.

For v2 (e.g., 6-char Crockford expansion), v2 wordlists **must be supersets** of v1. Every v1 word retains its position; new words append.

Document this prominently in `EXTENSION.md`.

## Quality gates (acceptance checklist)

Before declaring done, programmatically verify:

- [ ] `adjectives.txt` has exactly 4,096 lines
- [ ] `nouns.txt` has exactly 8,192 lines
- [ ] Every line in both matches `^[a-z]{4,6}$`
- [ ] No duplicates within each file
- [ ] No word in both files (disjointness)
- [ ] Zero LDNOOBW matches in either file
- [ ] Every adjective has a WordNet adjective synset
- [ ] Every noun has a WordNet noun synset
- [ ] Double Metaphone unique within each pool
- [ ] All words appear in at least one documented source
- [ ] Human-review checkpoint (Step 9) completed with explicit sign-off
- [ ] All `docs/` files exist (each > 500 words except CHANGELOG)
- [ ] All `data/` intermediate files preserved
- [ ] SHA-256 of both deliverables recorded in `CHANGELOG.md`

If any check fails, fix and re-verify.

## What NOT to do

- Don't substitute creative reasoning for the documented pipeline. Follow steps, write intermediates, make it auditable.
- Don't invent words. Every entry must trace to a documented source.
- Don't apply silent removals. Every drop goes in `BLOCKLIST.md` with reason.
- Don't skip Step 9 (human review). Pause and request review.
- Don't rely solely on automated tone scoring. The score is a *prior*, not a *decision*.
- Don't claim the lists are "safe" without the pair audit. Adj-noun pairings have less combinatorial risk than noun-noun but new failure modes (adjective modifying slur, etc.).
- Don't oversell in documentation. "Vetted using public sources, automated filters, and human review" — not "comprehensively safe."
- Don't break disjointness when backfilling. Verify after every backfill.

## Working environment

- Python 3.11+
- Required libraries: `requests`, `jellyfish`, `pandas`, `nltk`
- Install: `pip install requests jellyfish pandas nltk` then `python -c "import nltk; nltk.download('wordnet')"`
- Each script in `scripts/` takes no arguments; reads/writes canonical paths
- Scripts log to stdout with timestamps and counts
- Use fixed random seeds (e.g., `random.seed(42)`) so pair-audit samples are reproducible

## Starting prompt for the session

When kicking off the work, the human will say something like: "Build the wordlists per CLAUDE.md."

The first actions should be:
1. Acknowledge the goal, two-pool structure, and tone target in one short paragraph
2. Create the directory structure
3. Begin Step 1 (acquire), installing NLTK and downloading WordNet
4. Proceed through Steps 2–8 with progress updates after each step
5. **Stop at Step 9** and present the review materials clearly
6. After human approval, complete Steps 10–11
7. Run the quality-gate checklist and report results
8. Present `adjectives.txt`, `nouns.txt`, and the `docs/` directory

## Final note

The goal is not just two wordlists — it's **two defensible wordlists with a coherent voice**. Five years from now, when someone asks "why is `viable` not an adjective in this list?" or "why is `panda` a noun?", the answer should be in the documentation. The tone calls especially deserve to be written down: subjective decisions that aren't documented become arbitrary in retrospect.
