"""arxivhaiku.codec — alias generation and canonical-ID bijection.

This module loads the shipped `adjectives.txt` (4,096 entries) and
`nouns.txt` (8,192 entries) and exposes:

  haiku()           — return a uniformly-random `<adj>-<noun>` alias
  encode(canonical) — convert an int canonical (0..2^25-1) to alias
  decode(alias)     — convert an alias back to its int canonical

The mapping is a bijection:
  canonical = (adj_index << 13) | noun_index
  adj_index   = adjectives.index(adj_word)
  noun_index  = nouns.index(noun_word)

The 5-char Crockford Base32 representation is also supported via
`encode_crockford`/`decode_crockford`.
"""
from __future__ import annotations
import secrets
from pathlib import Path
from typing import Sequence

# --- Constants tied to the shipped wordlists -------------------------------

ADJ_BITS = 12              # 2**12 = 4,096 adjectives
NOUN_BITS = 13             # 2**13 = 8,192 nouns
CANON_BITS = ADJ_BITS + NOUN_BITS  # 25 bits = 32**5 = 33,554,432 canonicals
ADJ_COUNT = 1 << ADJ_BITS
NOUN_COUNT = 1 << NOUN_BITS
CANON_MAX = (1 << CANON_BITS) - 1

# Crockford Base32 alphabet (no I, L, O, U)
CANON_CHARS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
assert len(CANON_CHARS) == 32

_CROCKFORD_DECODE = {c: i for i, c in enumerate(CANON_CHARS)}
# Normalization per Crockford: I→1, L→1, O→0; lowercase accepted.
_CROCKFORD_NORM = str.maketrans({
    "i": "1", "I": "1",
    "l": "1", "L": "1",
    "o": "0", "O": "0",
})

# --- Errors ---------------------------------------------------------------

class InvalidAliasError(ValueError):
    """Raised when an alias string is malformed or its words aren't in the pools."""


class InvalidCanonicalError(ValueError):
    """Raised when a canonical value is out of range or malformed."""


# --- Wordlist loading -----------------------------------------------------

def _load_wordlist(filename: str, expected_count: int) -> list[str]:
    # Wordlists ship at the package data location, not the project root.
    here = Path(__file__).resolve().parent
    # Search a few sensible paths so the package works both installed
    # (data is in arxivhaiku/data/...) and in-repo (top-level *.txt).
    candidates = [
        here / "data" / filename,
        here.parent / filename,  # in-repo: project root
    ]
    for path in candidates:
        if path.exists():
            words = [line.strip() for line in path.read_text().splitlines() if line.strip()]
            if len(words) != expected_count:
                raise RuntimeError(
                    f"{path}: expected {expected_count} words, got {len(words)}"
                )
            return words
    raise FileNotFoundError(
        f"could not find {filename} in any of: {[str(p) for p in candidates]}"
    )


_ADJECTIVES = _load_wordlist("adjectives.txt", ADJ_COUNT)
_NOUNS = _load_wordlist("nouns.txt", NOUN_COUNT)

# Reverse-lookup dicts (built once at import time)
_ADJ_INDEX = {w: i for i, w in enumerate(_ADJECTIVES)}
_NOUN_INDEX = {w: i for i, w in enumerate(_NOUNS)}


def list_adjectives() -> Sequence[str]:
    """Return the immutable, sorted adjective list. Safe to mutate
    (returns a copy)."""
    return list(_ADJECTIVES)


def list_nouns() -> Sequence[str]:
    """Return the immutable, sorted noun list. Safe to mutate
    (returns a copy)."""
    return list(_NOUNS)


# --- Generation -----------------------------------------------------------

def haiku(*, separator: str = "-", rng: secrets.SystemRandom | None = None) -> str:
    """Generate a uniformly-random `<adj><sep><noun>` alias.

    Uses `secrets.SystemRandom` by default (cryptographic-grade entropy).
    Pass an alternate RNG implementing `randrange(n)` to override.
    """
    r = rng if rng is not None else secrets.SystemRandom()
    adj = _ADJECTIVES[r.randrange(ADJ_COUNT)]
    noun = _NOUNS[r.randrange(NOUN_COUNT)]
    return f"{adj}{separator}{noun}"


# --- Bijection: int canonical ↔ alias -------------------------------------

def encode(canonical: int, *, separator: str = "-") -> str:
    """Encode an integer canonical (0 ≤ canonical < 2**25) as an alias."""
    if not isinstance(canonical, int) or canonical < 0 or canonical > CANON_MAX:
        raise InvalidCanonicalError(
            f"canonical must be int in [0, {CANON_MAX}], got {canonical!r}"
        )
    adj_index = canonical >> NOUN_BITS
    noun_index = canonical & ((1 << NOUN_BITS) - 1)
    return f"{_ADJECTIVES[adj_index]}{separator}{_NOUNS[noun_index]}"


def decode(alias: str, *, separator: str = "-") -> int:
    """Decode an alias string to its integer canonical.

    The alias must be exactly `<adj><sep><noun>` where adj is in
    `adjectives.txt` and noun is in `nouns.txt`.
    """
    if not isinstance(alias, str):
        raise InvalidAliasError(f"alias must be str, got {type(alias).__name__}")
    parts = alias.split(separator)
    if len(parts) != 2:
        raise InvalidAliasError(
            f"alias must be exactly '<adj>{separator}<noun>', got {alias!r}"
        )
    adj_word, noun_word = parts
    if adj_word not in _ADJ_INDEX:
        raise InvalidAliasError(f"unknown adjective: {adj_word!r}")
    if noun_word not in _NOUN_INDEX:
        raise InvalidAliasError(f"unknown noun: {noun_word!r}")
    return (_ADJ_INDEX[adj_word] << NOUN_BITS) | _NOUN_INDEX[noun_word]


# --- Crockford Base32 helpers ---------------------------------------------

def encode_crockford(canonical: int) -> str:
    """Encode an integer canonical as a 5-char Crockford Base32 string."""
    if not isinstance(canonical, int) or canonical < 0 or canonical > CANON_MAX:
        raise InvalidCanonicalError(
            f"canonical must be int in [0, {CANON_MAX}], got {canonical!r}"
        )
    out = []
    n = canonical
    for _ in range(5):
        out.append(CANON_CHARS[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def decode_crockford(token: str) -> int:
    """Decode a 5-char Crockford Base32 string to its integer canonical.

    Crockford normalization: I/L → 1, O → 0; case-insensitive.
    """
    if not isinstance(token, str):
        raise InvalidCanonicalError(f"token must be str, got {type(token).__name__}")
    norm = token.translate(_CROCKFORD_NORM).upper().replace("-", "")
    if len(norm) != 5:
        raise InvalidCanonicalError(
            f"Crockford token must be 5 chars after normalization, got {len(norm)}: {token!r}"
        )
    n = 0
    for ch in norm:
        try:
            n = (n << 5) | _CROCKFORD_DECODE[ch]
        except KeyError:
            raise InvalidCanonicalError(
                f"invalid Crockford character {ch!r} in {token!r}"
            )
    return n


# --- Object-oriented interface --------------------------------------------

class Haikunator:
    """Customizable alias generator.

    Parameters:
      separator: separator between adj and noun (default '-').
      seed:      optional int seed for reproducibility (uses random.Random
                 under the hood; do not use for security-sensitive IDs).
    """

    def __init__(self, *, separator: str = "-", seed: int | None = None):
        self.separator = separator
        if seed is not None:
            import random
            self._rng = random.Random(seed)
        else:
            self._rng = secrets.SystemRandom()

    def haikunate(self) -> str:
        return haiku(separator=self.separator, rng=self._rng)

    def encode(self, canonical: int) -> str:
        return encode(canonical, separator=self.separator)

    def decode(self, alias: str) -> int:
        return decode(alias, separator=self.separator)
