"""Tests for arxivhaiku.codec — alias generation and bijection.

Run with:
    python -m pytest tests/
or:
    python -m unittest discover tests
"""
from __future__ import annotations
import re
import unittest

from arxivhaiku import (
    haiku, encode, decode, Haikunator,
    ADJ_BITS, NOUN_BITS, CANON_BITS, CANON_CHARS,
    InvalidAliasError, InvalidCanonicalError,
    list_adjectives, list_nouns,
)
from arxivhaiku.codec import (
    encode_crockford, decode_crockford,
    ADJ_COUNT, NOUN_COUNT, CANON_MAX,
)


class TestConstants(unittest.TestCase):

    def test_bit_arithmetic(self):
        self.assertEqual(ADJ_BITS + NOUN_BITS, CANON_BITS)
        self.assertEqual(ADJ_COUNT, 1 << ADJ_BITS)
        self.assertEqual(NOUN_COUNT, 1 << NOUN_BITS)
        self.assertEqual(CANON_MAX + 1, ADJ_COUNT * NOUN_COUNT)

    def test_crockford_alphabet(self):
        self.assertEqual(len(CANON_CHARS), 32)
        # Excluded characters per Crockford
        for ch in "ILOU":
            self.assertNotIn(ch, CANON_CHARS)


class TestWordlists(unittest.TestCase):

    def test_adj_count(self):
        adj = list_adjectives()
        self.assertEqual(len(adj), 4096)
        self.assertEqual(len(set(adj)), 4096)

    def test_noun_count(self):
        nouns = list_nouns()
        self.assertEqual(len(nouns), 8192)
        self.assertEqual(len(set(nouns)), 8192)

    def test_sorted_alphabetically(self):
        adj = list_adjectives()
        nouns = list_nouns()
        self.assertEqual(adj, sorted(adj))
        self.assertEqual(nouns, sorted(nouns))

    def test_all_lowercase_4_6(self):
        word_re = re.compile(r"^[a-z]{4,7}$")
        for w in list_adjectives():
            self.assertTrue(word_re.match(w), f"bad adjective: {w!r}")
        for w in list_nouns():
            self.assertTrue(word_re.match(w), f"bad noun: {w!r}")

    def test_disjoint(self):
        adj = set(list_adjectives())
        nouns = set(list_nouns())
        self.assertEqual(adj & nouns, set())


class TestHaiku(unittest.TestCase):

    def test_haiku_format(self):
        for _ in range(50):
            h = haiku()
            self.assertRegex(h, r"^[a-z]{4,7}-[a-z]{4,7}$")
            adj, noun = h.split("-")
            self.assertIn(adj, list_adjectives())
            self.assertIn(noun, list_nouns())

    def test_haiku_separator(self):
        h = haiku(separator="_")
        self.assertRegex(h, r"^[a-z]{4,7}_[a-z]{4,7}$")

    def test_haikunator_class(self):
        h = Haikunator(seed=42)
        a1 = h.haikunate()
        a2 = h.haikunate()
        # With seed, output should be reproducible across runs
        h2 = Haikunator(seed=42)
        self.assertEqual(h2.haikunate(), a1)
        self.assertEqual(h2.haikunate(), a2)


class TestBijection(unittest.TestCase):

    def test_round_trip_int(self):
        # Round-trip every 2^15-th canonical (1024 samples across the space)
        for c in range(0, CANON_MAX + 1, max(1, (CANON_MAX // 1024))):
            alias = encode(c)
            self.assertEqual(decode(alias), c, f"failed round-trip at {c}")

    def test_boundary_values(self):
        for c in (0, 1, CANON_MAX - 1, CANON_MAX):
            alias = encode(c)
            self.assertEqual(decode(alias), c)

    def test_first_alias(self):
        # canonical 0 → adj[0] + '-' + noun[0]
        adj = list_adjectives()
        nouns = list_nouns()
        self.assertEqual(encode(0), f"{adj[0]}-{nouns[0]}")
        self.assertEqual(decode(f"{adj[0]}-{nouns[0]}"), 0)

    def test_last_alias(self):
        adj = list_adjectives()
        nouns = list_nouns()
        self.assertEqual(encode(CANON_MAX), f"{adj[-1]}-{nouns[-1]}")

    def test_custom_separator(self):
        alias = encode(42, separator="_")
        self.assertIn("_", alias)
        self.assertNotIn("-", alias)
        self.assertEqual(decode(alias, separator="_"), 42)

    def test_decode_unknown_adj(self):
        with self.assertRaises(InvalidAliasError):
            decode("xxxxx-eagle")

    def test_decode_unknown_noun(self):
        with self.assertRaises(InvalidAliasError):
            decode("brave-xxxxx")

    def test_decode_malformed(self):
        with self.assertRaises(InvalidAliasError):
            decode("just-one-extra-dash")
        with self.assertRaises(InvalidAliasError):
            decode("nodash")

    def test_encode_out_of_range(self):
        with self.assertRaises(InvalidCanonicalError):
            encode(-1)
        with self.assertRaises(InvalidCanonicalError):
            encode(CANON_MAX + 1)
        with self.assertRaises(InvalidCanonicalError):
            encode("not an int")  # type: ignore[arg-type]


class TestCrockford(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(encode_crockford(0), "00000")
        self.assertEqual(decode_crockford("00000"), 0)

    def test_max(self):
        self.assertEqual(encode_crockford(CANON_MAX), "ZZZZZ")
        self.assertEqual(decode_crockford("ZZZZZ"), CANON_MAX)

    def test_round_trip(self):
        for c in (0, 1, 31, 32, 1023, 1024, CANON_MAX // 2, CANON_MAX - 1, CANON_MAX):
            self.assertEqual(decode_crockford(encode_crockford(c)), c)

    def test_lowercase_accepted(self):
        encoded = encode_crockford(0xDEADBE & CANON_MAX)
        self.assertEqual(decode_crockford(encoded.lower()), decode_crockford(encoded))

    def test_normalization(self):
        # I → 1, L → 1, O → 0 (Crockford spec)
        # Build a known 5-char canonical: 0 = '00000'
        self.assertEqual(decode_crockford("OOOOO"), 0)  # all O → 0
        # 1 in pos 0: '00001'
        self.assertEqual(decode_crockford("0000L"), 1)
        self.assertEqual(decode_crockford("0000I"), 1)

    def test_alias_to_crockford_round_trip(self):
        for c in (0, 1, 4096, 1234567, CANON_MAX):
            alias = encode(c)
            ck = encode_crockford(c)
            self.assertEqual(decode(alias), c)
            self.assertEqual(decode_crockford(ck), c)
            self.assertEqual(encode_crockford(decode(alias)), ck)


class TestNoProfanityInAdjacentPairs(unittest.TestCase):
    """Spot-check: no individual word contains an obvious profanity substring."""

    DANGEROUS = (
        "rape", "kill", "shit", "fuck", "cunt", "spic", "chink", "gook",
        "wank", "boob", "cock", "bitch", "anal", "anus", "tits", "porn",
        "klan", "nazi", "kkk", "dyke", "scat", "negro",
    )

    def test_adj_no_dangerous_substr(self):
        for w in list_adjectives():
            for s in self.DANGEROUS:
                self.assertNotIn(s, w, f"adj {w!r} contains {s!r}")

    def test_noun_no_dangerous_substr(self):
        for w in list_nouns():
            for s in self.DANGEROUS:
                self.assertNotIn(s, w, f"noun {w!r} contains {s!r}")


if __name__ == "__main__":
    unittest.main()
