# Raw sources

Per-input metadata recorded at acquisition time. Re-run `scripts/01_acquire.py` to refresh; existing files are not re-downloaded.

| name | url | size | sha256 | license | fetched_at | status |
|------|-----|------|--------|---------|------------|--------|
| `heroku_haikunator.rb` | <https://raw.githubusercontent.com/usmanbashir/haikunator/master/lib/haikunator.rb> | 1643 | `435219e92a7f7f70...` | MIT | 2026-05-12T12:32:29Z | OK |
| `haikunatorjs.ts` | <https://raw.githubusercontent.com/Atrox/haikunatorjs/master/src/index.ts> | 3936 | `cdd12ddcec5d7ae2...` | MIT | 2026-05-12T12:32:29Z | OK |
| `moby_names_generator.go` | <https://raw.githubusercontent.com/moby/moby/v24.0.0/pkg/namesgenerator/names-generator.go> | 50988 | `aeeb39f862049aaf...` | Apache-2.0 | 2026-05-12T12:32:29Z | OK |
| `wordle_answers.txt` | <https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/wordle-answers-alphabetical.txt> | 13889 | `5209b35f823f8b80...` | Public domain (de facto) | 2026-05-12T12:32:29Z | OK |
| `wordle_allowed_guesses.txt` | <https://gist.githubusercontent.com/cfreshman/cdcdf777450c5b5301e439061d29694c/raw/wordle-allowed-guesses.txt> | 63941 | `99be2e38dadf3e26...` | Public domain (de facto) | 2026-05-12T12:32:29Z | OK |
| `google_10000.txt` | <https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa.txt> | 75879 | `981c776dc7e8996a...` | MIT | 2026-05-12T12:32:29Z | OK |
| `ldnoobw_en.txt` | <https://raw.githubusercontent.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/master/en> | 3777 | `af851ecef1d5f212...` | CC-BY 4.0 | 2026-05-12T12:32:29Z | OK |
| `eff_large_wordlist.txt` | <https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt> | 108800 | `addd35536511597a...` | CC-BY 3.0 | 2026-05-12T12:32:29Z | OK |
| `bip39_english.txt` | <https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt> | 13116 | `2f5eed53a4727b4b...` | BSD-2-Clause / public domain | 2026-05-12T12:32:29Z | OK |
| `simple_adjectives.txt` | <https://raw.githubusercontent.com/taikuukaits/SimpleWordlists/master/Wordlist-Adjectives-All.txt> | 286797 | `16dfee6336012aea...` | Public domain (Project Gutenberg-derived) | 2026-05-12T12:32:29Z | OK |
| `english_words_alpha.txt` | <https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt> | 4234910 | `3ed0c94610d8bcf7...` | Unlicense (public domain) | 2026-05-12T12:32:29Z | OK |

## Purposes

- **`heroku_haikunator.rb`** — Reference Heroku-style adjective + noun lists
- **`haikunatorjs.ts`** — Alternative Heroku-style reference list
- **`moby_names_generator.go`** — Docker reference adjectives + names
- **`wordle_answers.txt`** — ~2,315 vetted 5-letter words
- **`wordle_allowed_guesses.txt`** — ~10,657 additional 5-letter words
- **`google_10000.txt`** — Word frequency ranking
- **`ldnoobw_en.txt`** — Profanity blocklist
- **`eff_large_wordlist.txt`** — Backup curated 4-9 letter words
- **`bip39_english.txt`** — Backup vetted 3-8 letter words
- **`simple_adjectives.txt`** — Comprehensive adjective list (~28k) to backfill adjective pool
- **`english_words_alpha.txt`** — Comprehensive English wordlist (~370k); substitutes SCOWL
