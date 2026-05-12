"""arxivhaiku — Heroku-haikunator-style two-word identifiers.

Generates `<adjective>-<noun>` aliases from a vetted, fixed-size wordlist.
Optionally maps to/from a 5-character Crockford Base32 canonical ID.

Quick start:
    >>> from arxivhaiku import haiku
    >>> haiku()
    'frosty-meadow'

    >>> from arxivhaiku import encode, decode
    >>> alias = encode(0x1234567)         # canonical → alias
    >>> canon = decode('frosty-meadow')   # alias → canonical (round-trips)
"""

from arxivhaiku.codec import (
    haiku,
    encode,
    decode,
    Haikunator,
    ADJ_BITS,
    NOUN_BITS,
    CANON_BITS,
    CANON_CHARS,
    InvalidAliasError,
    InvalidCanonicalError,
    list_adjectives,
    list_nouns,
)

__all__ = [
    "haiku",
    "encode",
    "decode",
    "Haikunator",
    "ADJ_BITS",
    "NOUN_BITS",
    "CANON_BITS",
    "CANON_CHARS",
    "InvalidAliasError",
    "InvalidCanonicalError",
    "list_adjectives",
    "list_nouns",
]

__version__ = "1.0.1"
