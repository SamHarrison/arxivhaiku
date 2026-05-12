# SOURCES — Inputs to the wordlist build

All sources fetched on 2026-05-12. Re-run `scripts/01_acquire.py` to refresh
(existing files are not re-downloaded; delete a file to force re-fetch).
The machine-generated metadata table with per-file SHA-256 hashes lives at
`data/raw/SOURCES.md`. The block below is the human-readable narrative.

## Primary reference lists (curated, small)

### Heroku haikunator (`heroku_haikunator.rb`)
- **URL**: <https://github.com/usmanbashir/haikunator/blob/master/lib/haikunator.rb>
- **License**: MIT
- **Why we use it**: This is the canonical source of "Heroku-style" adjective
  and noun choices. Every word in this file gets tone-score credit
  (+3 playfulness for adj, +3 concreteness for nouns).
- **Words**: 64 adjectives, 64 nouns.

### haikunatorjs (`haikunatorjs.ts`)
- **URL**: <https://github.com/Atrox/haikunatorjs/blob/master/src/index.ts>
- **License**: MIT
- **Why we use it**: Independent re-implementation with its own curated word
  lists. CLAUDE.md cites this as `haikunator.ts`; the upstream file was
  renamed to `index.ts` between CLAUDE.md authorship and 2026-05-12.
- **Words**: 91 adjectives, 96 nouns.

### Docker moby names-generator (`moby_names_generator.go`)
- **URL**: <https://github.com/moby/moby/blob/v24.0.0/pkg/namesgenerator/names-generator.go>
- **License**: Apache-2.0
- **Why we use it**: Docker's container-name adjective list (`left[]` array)
  is a third reference for "Heroku-style" curation. We use only `left[]`
  (the adjective array); `right[]` is mostly famous-scientist names
  (proper nouns) and unsuitable.
- **Note**: CLAUDE.md cites `master/...`; the moby project deleted this
  file from main and the latest tagged release that still contains it
  is v24.0.0.

## Curated wordlists (large)

### Wordle answers (`wordle_answers.txt`)
- **URL**: <https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/wordle-answers-alphabetical.txt>
- **License**: De facto public domain (Wordle answer list, widely mirrored).
- **Why we use it**: ~2,315 5-letter words vetted by the NYT Wordle editors
  for English commonness. Excellent corroboration signal.

### Wordle allowed guesses (`wordle_allowed_guesses.txt`)
- **URL**: <https://gist.githubusercontent.com/cfreshman/cdcdf777450c5b5301e439061d29694c/raw/wordle-allowed-guesses.txt>
- **License**: De facto public domain.
- **Why we use it**: ~10,657 5-letter words accepted by Wordle (broader than
  answers; still curated for common English).

### Google top 10,000 (`google_10000.txt`)
- **URL**: <https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa.txt>
- **License**: MIT.
- **Why we use it**: Frequency ranking. Used both as inclusion signal and
  as protection against the proper-noun heuristic (a `noun.person` word in
  google-10000 is treated as common, not proper).

### EFF large wordlist (`eff_large_wordlist.txt`)
- **URL**: <https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt>
- **License**: CC-BY 3.0.
- **Why we use it**: 7,776 hand-vetted words (4–9 letter); designed for
  passphrase use, so already filtered for clarity and inoffensiveness.

### BIP-39 English (`bip39_english.txt`)
- **URL**: <https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt>
- **License**: BSD-2-Clause / public domain.
- **Why we use it**: 2,048 words used in Bitcoin mnemonic seed phrases.
  Hand-vetted for unambiguity.

### SimpleWordlists adjectives (`simple_adjectives.txt`)
- **URL**: <https://raw.githubusercontent.com/taikuukaits/SimpleWordlists/master/Wordlist-Adjectives-All.txt>
- **License**: Public domain (Project Gutenberg-derived POS-tagged data).
- **Why we use it**: WordNet adjective coverage in 4–6 letters is only ~3,255
  words — below the 4,096 target. SimpleWordlists categorizes ~28k English
  words as adjectives based on Project Gutenberg POS-tagged corpora. We
  treat membership in this list as adjectival evidence and extract ~4,127
  4–6 letter candidates from it.
- **CLAUDE.md substitution**: CLAUDE.md specifies SCOWL via aspell.net.
  SCOWL is distributed as a tarball with per-tier word lists; it lacks a
  single-file canonical URL. SimpleWordlists is the closest
  single-file equivalent for POS-tagged English adjectives.

### dwyl/english-words (`english_words_alpha.txt`)
- **URL**: <https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt>
- **License**: Unlicense (public domain).
- **Why we use it**: Comprehensive 370,105-word English wordlist. Used as
  the broadest source. Words appearing only in this source (not in any
  curated list above) carry a −10 score penalty (effectively a soft drop).
- **CLAUDE.md substitution**: CLAUDE.md specifies SCOWL as the comprehensive
  source; dwyl/english-words is the standard single-file equivalent.

## Profanity blocklist

### LDNOOBW English (`ldnoobw_en.txt`)
- **URL**: <https://raw.githubusercontent.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/master/en>
- **License**: CC-BY 4.0.
- **Why we use it**: 403 dirty/naughty/obscene/bad-words. We exact-match
  individual words against this list in Step 4 and run substring matches
  on pair concatenations in Step 8.
- **Important note on usage**: We use **exact match only** at the per-word
  filter level (Step 4) — substring matches at this level produced massive
  false positives (e.g., `class` matching `ass`). Substring checks happen
  at pair audit time (Step 8) and at finalize (Step 10) against a smaller
  curated `DANGEROUS_SUBSTRINGS` set that excludes substrings like `isis`
  (false-positives `crisis`).

## Source-to-tier mapping

For ranking candidates during selection, we group sources into quality
tiers (lower = better):

| Tier | Sources |
|-----:|---------|
| 0    | Heroku haikunator (adj+noun), haikunatorjs (adj+noun), moby (adj) |
| 1    | Curated wordlist (`simple_adjectives`, `wordle_answers`, `eff`, `bip39`) AND `google_10000` |
| 2    | Curated wordlist (any of the above) |
| 3    | `wordle_guesses` only, OR `google_10000` only |
| 4    | `english_alpha` only (long tail) |

A candidate's tier is computed in `scripts/06_tone_score.py` as
`source_quality_tier(source_set)` and stored in `data/06_tone_scored.tsv`.
Step 7 selects within each pool by `(quality_tier asc, primary_score desc,
google_rank asc, word asc)`.
