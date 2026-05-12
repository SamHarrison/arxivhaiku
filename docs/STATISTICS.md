# STATISTICS — Final pool characteristics

## Pool sizes

| File             | Count | Target |  Status |
|------------------|------:|-------:|---------|
| `adjectives.txt` | 4,096 | 4,096  | ✓ exact |
| `nouns.txt`      | 8,192 | 8,192  | ✓ exact |

## Length distribution

### Adjectives
| Length | Count | %      |
|-------:|------:|-------:|
|      4 |   302 |   7.4% |
|      5 |   714 |  17.4% |
|      6 | 1,214 |  29.6% |
|      7 | 1,866 |  45.6% |


### Nouns
| Length | Count | %      |
|-------:|------:|-------:|
|      4 |   934 |  11.4% |
|      5 | 2,242 |  27.4% |
|      6 | 1,747 |  21.3% |
|      7 | 3,269 |  39.9% |



The longer-skewed adjective distribution reflects English's adjective
inventory: 4-letter adjectives are relatively rare (`good`, `tall`, `wide`,
`thin`...) compared to 4-letter nouns.

## Playfulness score histogram (adjectives)

| Score | Count | Notes |
|------:|------:|-------|
| 10    | 1     | Top playfulness — multi-source Heroku-style |
| 9     | 1     | |
| 8     | 15    | |
| 7     | 5     | |
| 6     | 16    | |
| 5     | 20    | |
| 4     | 10    | |
| 3     | 152   | |
| 2     | 451   | |
| 1     | 593   | |
| 0     | 2,830 | Bulk of pool — passes quality filters, no special signal |
| −1    | 2     | Penalized: technical/relational |

After the 4–7 letter expansion plus stricter quality filters, the
adjective pool no longer relies on heavily-penalized backfill candidates
(score < −1). The bulk are score-0 (passes filters with no special signal).

## Concreteness score histogram (nouns)

| Score | Count | Notes |
|------:|------:|-------|
| 8     | 13    | Highest concreteness |
| 7     | 3     | |
| 6     | 18    | |
| 5     | 12    | |
| 4     | 6     | |
| 3     | 634   | |
| 2     | 1,743 | |
| 1     | 890   | |
| 0     | 663   | |
| −1    | 582   | Slightly abstract |
| −2    | 703   | Abstract |
| −8    | 2,925 | Uncorroborated (english_alpha-only, concrete lexname) |

After hard-dropping `uncorroborated_abstract_noun` and `biology_genus`
candidates in Step 4, the lowest noun-pool tier (−8) is corroborated-only
concrete nouns. These are still real nouns from a vetted lexname
(`noun.artifact`, `noun.food`, `noun.substance`, etc.) — just not in any
curated frequency list. Score is not a quality verdict; it's the
selection-ranking signal.

## POS overlap

After Step 4 quality filter (4–7 letter expansion):

| Category | Count |
|----------|------:|
| Adjective-only candidates passing Step 4 | ~5,400 |
| Noun-only candidates passing Step 4      | ~10,100 |
| Both (adj+noun) candidates passing       | ~1,300  |

Of the "both" candidates, the higher-scoring pool wins; ties go to noun
(the larger pool). Color/material adjectives in this category
(`golden`, `silver`, `velvet`, `coral`) tend to score higher on
playfulness and end up in the adjective pool.

## Phonetic dedup outcome

With 4–7 letter inventory, **strict Metaphone+Lev1 dedup is sufficient**
for both pools — no relaxation needed. See `data/07_selection_log.tsv`.

| Pool | Candidates after Step 4 | After strict dedup | Selected |
|------|------------------------:|-------------------:|---------:|
| adj  | 6,727                   | 5,363              | 4,096    |
| noun | 11,608                  | 9,343              | 8,192    |

This is a substantial quality improvement over the initial 4–6 letter
build, which required morphological backfill and dedup relaxation to
hit the bijection targets.

## Pair audit summary

Final 50,000-pair random audit:

- Pairs flagged: **19 / 50,000 = 0.038%**
- All remaining flags are cross-boundary substring false positives
  (e.g., `furious+catcall` → "furiouscatcall" contains "scat" at the
  join; `protean+alumni` → contains "anal" at the join).
- No standalone problem words remain after Step 9 removals.

## Random samples

### 50 adjectives (seed 99)
```
rifled, protean, fuzzed, fizzing, hazelly, illicit, dogged, chloric,
incivil, puling, civil, under, fusible, scaldic, gowany, pompous,
quinate, gnarled, eleatic, spangly, flaccid, ocreate, charged, chromic,
squishy, monacid, ribbony, basal, kinless, adored, scurry, geared,
phlegmy, centum, sparse, funny, speedy, birchen, peaky, dilated, gorged,
eternal, singing, firm, filled, awheel, crumbly, anoetic, feeble, stickit
```

### 50 nouns (seed 99)
```
seesaws, cellars, sheep, chat, downers, neolith, aery, rarebit, ozonide,
dingo, saint, gneiss, bracers, guppy, souse, kummel, sacques, dasheen,
plateau, triumph, brahman, dentist, ears, sandpit, cytol, clique, cubit,
dragnet, mirrors, firebug, flip, satyr, drosky, grotto, oculars, zebra,
icbm, crowbar, poster, fugue, canines, matai, alundum, block, pattens,
handful, radar, rookie, patella, roper
```

### 25 pairs
```
pythian-scooter, plucked-circuit, fledged-bazar, podgy-romaine,
skeigh-hotcake, milled-hipbone, miffy-cookie, missing-hash,
implied-reamers, lumpy-smithy, cauline-smelter, savvy-knucks,
bullate-midden, mucic-trustee, deuced-koshers, serfish-menhir,
rotted-erica, lettic-raider, silicic-gesso, prolate-path, funest-phial,
acetose-plies, lozengy-gelly, fell-lanugo, sainted-hudud
```

(These were drawn with seed 99; see `data/08_human_sample.txt` for
the 300-pair Step 8 sample drawn with seed 7777.)
