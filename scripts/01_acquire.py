#!/usr/bin/env python3
"""Step 1: download raw sources, record SHA-256 + license + URL + timestamp."""
from __future__ import annotations
import hashlib
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SOURCES = [
    {
        "name": "heroku_haikunator.rb",
        "url": "https://raw.githubusercontent.com/usmanbashir/haikunator/master/lib/haikunator.rb",
        "license": "MIT",
        "purpose": "Reference Heroku-style adjective + noun lists",
    },
    {
        "name": "haikunatorjs.ts",
        # NOTE: CLAUDE.md specifies haikunator.ts; upstream renamed it index.ts (verified 2026-05-12).
        "url": "https://raw.githubusercontent.com/Atrox/haikunatorjs/master/src/index.ts",
        "license": "MIT",
        "purpose": "Alternative Heroku-style reference list",
    },
    {
        "name": "moby_names_generator.go",
        # NOTE: CLAUDE.md specifies master HEAD; moby moved this file. Use tagged v24.0.0
        # which is the last release that still contains it. Verified 2026-05-12.
        "url": "https://raw.githubusercontent.com/moby/moby/v24.0.0/pkg/namesgenerator/names-generator.go",
        "license": "Apache-2.0",
        "purpose": "Docker reference adjectives + names",
    },
    {
        "name": "wordle_answers.txt",
        "url": "https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/wordle-answers-alphabetical.txt",
        "license": "Public domain (de facto)",
        "purpose": "~2,315 vetted 5-letter words",
    },
    {
        "name": "wordle_allowed_guesses.txt",
        "url": "https://gist.githubusercontent.com/cfreshman/cdcdf777450c5b5301e439061d29694c/raw/wordle-allowed-guesses.txt",
        "license": "Public domain (de facto)",
        "purpose": "~10,657 additional 5-letter words",
    },
    {
        "name": "google_10000.txt",
        "url": "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa.txt",
        "license": "MIT",
        "purpose": "Word frequency ranking",
    },
    {
        "name": "ldnoobw_en.txt",
        "url": "https://raw.githubusercontent.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/master/en",
        "license": "CC-BY 4.0",
        "purpose": "Profanity blocklist",
    },
    {
        "name": "eff_large_wordlist.txt",
        "url": "https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt",
        "license": "CC-BY 3.0",
        "purpose": "Backup curated 4-9 letter words",
    },
    {
        "name": "bip39_english.txt",
        "url": "https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt",
        "license": "BSD-2-Clause / public domain",
        "purpose": "Backup vetted 3-8 letter words",
    },
    # SCOWL: use scowl-wl JSON releases (size 35, 40, 50). The aspell.net distribution
    # is a tarball; we use the precompiled per-size text files mirrored on GitHub.
    {
        "name": "simple_adjectives.txt",
        # Added 2026-05-12 during build: WordNet alone yields only ~3,255 4-6 letter
        # adjective synsets, below the 4,096 target. CLAUDE.md Step 7 anticipates this
        # ("expand source set"). taikuukaits/SimpleWordlists is a well-known POS-tagged
        # English wordlist used as a Project Gutenberg / Princeton POS reference.
        "url": "https://raw.githubusercontent.com/taikuukaits/SimpleWordlists/master/Wordlist-Adjectives-All.txt",
        "license": "Public domain (Project Gutenberg-derived)",
        "purpose": "Comprehensive adjective list (~28k) to backfill adjective pool",
    },
    {
        "name": "english_words_alpha.txt",
        # NOTE: CLAUDE.md specifies SCOWL via aspell.net (a tarball, not single-file).
        # We substitute dwyl/english-words (~370k words, comprehensive) which is the
        # standard single-file mirror. Will be aggressively filtered downstream.
        "url": "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
        "license": "Unlicense (public domain)",
        "purpose": "Comprehensive English wordlist (~370k); substitutes SCOWL",
    },
]


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "arxivhaiku-build/1.0"})
    with urlopen(req, timeout=60) as r:
        return r.read()


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    rows = []
    for src in SOURCES:
        path = RAW / src["name"]
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if path.exists() and path.stat().st_size > 0:
            data = path.read_bytes()
            print(f"[skip] {src['name']} already present ({len(data)} bytes)")
        else:
            print(f"[fetch] {src['url']}")
            try:
                data = fetch(src["url"])
            except (URLError, HTTPError, TimeoutError) as e:
                print(f"  !! failed: {e}", file=sys.stderr)
                rows.append({**src, "status": "FAILED", "sha256": "", "size": 0, "fetched_at": ts})
                continue
            path.write_bytes(data)
            print(f"  wrote {path} ({len(data)} bytes)")
        rows.append({
            **src,
            "status": "OK",
            "sha256": sha256(data),
            "size": len(data),
            "fetched_at": ts,
        })

    sources_md = RAW / "SOURCES.md"
    with sources_md.open("w") as f:
        f.write("# Raw sources\n\n")
        f.write("Per-input metadata recorded at acquisition time. Re-run "
                "`scripts/01_acquire.py` to refresh; existing files are not re-downloaded.\n\n")
        f.write("| name | url | size | sha256 | license | fetched_at | status |\n")
        f.write("|------|-----|------|--------|---------|------------|--------|\n")
        for r in rows:
            f.write(f"| `{r['name']}` | <{r['url']}> | {r['size']} | "
                    f"`{r['sha256'][:16]}...` | {r['license']} | {r['fetched_at']} | {r['status']} |\n")
        f.write("\n## Purposes\n\n")
        for r in rows:
            f.write(f"- **`{r['name']}`** — {r['purpose']}\n")
    print(f"\n[done] wrote {sources_md}")
    failed = [r for r in rows if r["status"] != "OK"]
    if failed:
        print(f"WARNING: {len(failed)} source(s) failed:", file=sys.stderr)
        for r in failed:
            print(f"  - {r['name']}: {r['url']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
