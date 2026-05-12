/**
 * Mirrors tests/test_codec.py — 27 tests covering:
 *   - Constants and bit arithmetic
 *   - Wordlist invariants (count, regex, sorted, disjoint)
 *   - haiku() output format
 *   - Bijection round-trip across the full canonical space
 *   - Crockford encode/decode and Crockford normalization
 *   - Profanity-substring spot check
 */
import { describe, expect, test } from "vitest";
import {
  // Generation
  haiku,
  haikuCrockford,
  Haikunator,
  // Bijection
  encode,
  decode,
  encodeCrockford,
  decodeCrockford,
  // Wordlist accessors
  listAdjectives,
  listNouns,
  // Errors
  InvalidAliasError,
  InvalidCanonicalError,
  // Constants
  ADJ_BITS,
  NOUN_BITS,
  CANON_BITS,
  ADJ_COUNT,
  NOUN_COUNT,
  CANON_MAX,
  CANON_CHARS,
  // Provenance
  ADJECTIVES_SHA256,
  NOUNS_SHA256,
} from "../src/index.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

describe("constants", () => {
  test("bit arithmetic is internally consistent", () => {
    expect(ADJ_BITS + NOUN_BITS).toBe(CANON_BITS);
    expect(ADJ_COUNT).toBe(1 << ADJ_BITS);
    expect(NOUN_COUNT).toBe(1 << NOUN_BITS);
    expect(CANON_MAX + 1).toBe(ADJ_COUNT * NOUN_COUNT);
  });

  test("Crockford alphabet has exactly 32 chars and excludes I, L, O, U", () => {
    expect(CANON_CHARS.length).toBe(32);
    for (const ch of "ILOU") {
      expect(CANON_CHARS).not.toContain(ch);
    }
  });

  test("SHA-256 provenance constants are 64-char hex strings", () => {
    expect(ADJECTIVES_SHA256).toMatch(/^[0-9a-f]{64}$/);
    expect(NOUNS_SHA256).toMatch(/^[0-9a-f]{64}$/);
  });
});

// ---------------------------------------------------------------------------
// Wordlists
// ---------------------------------------------------------------------------

describe("wordlists", () => {
  test("adjective count is exactly 4,096", () => {
    const adj = listAdjectives();
    expect(adj.length).toBe(4096);
    expect(new Set(adj).size).toBe(4096); // no duplicates
  });

  test("noun count is exactly 8,192", () => {
    const nouns = listNouns();
    expect(nouns.length).toBe(8192);
    expect(new Set(nouns).size).toBe(8192);
  });

  test("both lists are sorted alphabetically", () => {
    const adj = listAdjectives();
    const nouns = listNouns();
    expect(adj).toEqual([...adj].sort());
    expect(nouns).toEqual([...nouns].sort());
  });

  test("every entry matches /^[a-z]{4,7}$/", () => {
    const re = /^[a-z]{4,7}$/;
    for (const w of listAdjectives()) {
      expect(re.test(w), `bad adjective: ${w}`).toBe(true);
    }
    for (const w of listNouns()) {
      expect(re.test(w), `bad noun: ${w}`).toBe(true);
    }
  });

  test("pools are disjoint", () => {
    const adj = new Set(listAdjectives());
    const nouns = new Set(listNouns());
    const overlap = [...adj].filter((w) => nouns.has(w));
    expect(overlap).toEqual([]);
  });

  test("returned arrays are copies (mutation-safe)", () => {
    const a1 = listAdjectives();
    a1.push("xxx");
    const a2 = listAdjectives();
    expect(a2.length).toBe(4096);
  });
});

// ---------------------------------------------------------------------------
// haiku()
// ---------------------------------------------------------------------------

describe("haiku()", () => {
  test("output format matches /^[a-z]{4,7}-[a-z]{4,7}$/", () => {
    const re = /^[a-z]{4,7}-[a-z]{4,7}$/;
    for (let i = 0; i < 50; i++) {
      const h = haiku();
      expect(h).toMatch(re);
      const [adj, noun] = h.split("-");
      expect(listAdjectives()).toContain(adj);
      expect(listNouns()).toContain(noun);
    }
  });

  test("custom separator", () => {
    const h = haiku("_");
    expect(h).toMatch(/^[a-z]{4,7}_[a-z]{4,7}$/);
  });

  test("haikuCrockford() emits 5 valid chars", () => {
    for (let i = 0; i < 20; i++) {
      const tok = haikuCrockford();
      expect(tok.length).toBe(5);
      expect(tok).toMatch(/^[0-9A-HJKMNP-TV-Z]{5}$/);
    }
  });
});

describe("Haikunator class", () => {
  test("seeded mode is deterministic and reproducible", () => {
    const h1 = new Haikunator({ seed: 42 });
    const h2 = new Haikunator({ seed: 42 });
    for (let i = 0; i < 5; i++) {
      expect(h1.haikunate()).toBe(h2.haikunate());
    }
  });

  test("different seeds produce different sequences", () => {
    const h1 = new Haikunator({ seed: 1 });
    const h2 = new Haikunator({ seed: 2 });
    expect(h1.haikunate()).not.toBe(h2.haikunate());
  });

  test("custom separator on Haikunator", () => {
    const h = new Haikunator({ seed: 42, separator: "_" });
    expect(h.haikunate()).toMatch(/^[a-z]{4,7}_[a-z]{4,7}$/);
  });

  test("Haikunator.encode/decode mirror module-level fns", () => {
    const h = new Haikunator({ separator: "/" });
    const alias = h.encode(123);
    expect(alias).toContain("/");
    expect(h.decode(alias)).toBe(123);
  });
});

// ---------------------------------------------------------------------------
// Bijection: int ↔ alias
// ---------------------------------------------------------------------------

describe("bijection", () => {
  test("round-trips ~1024 samples spanning the full canonical space", () => {
    const step = Math.max(1, Math.floor(CANON_MAX / 1024));
    for (let c = 0; c <= CANON_MAX; c += step) {
      const alias = encode(c);
      expect(decode(alias), `round-trip failed at ${c}`).toBe(c);
    }
  });

  test("boundary values round-trip", () => {
    for (const c of [0, 1, CANON_MAX - 1, CANON_MAX]) {
      expect(decode(encode(c))).toBe(c);
    }
  });

  test("encode(0) is the first adj + first noun (alphabetically)", () => {
    const adj = listAdjectives();
    const nouns = listNouns();
    expect(encode(0)).toBe(`${adj[0]}-${nouns[0]}`);
    expect(decode(`${adj[0]}-${nouns[0]}`)).toBe(0);
  });

  test("encode(CANON_MAX) is the last adj + last noun", () => {
    const adj = listAdjectives();
    const nouns = listNouns();
    expect(encode(CANON_MAX)).toBe(`${adj.at(-1)}-${nouns.at(-1)}`);
  });

  test("custom separator round-trips", () => {
    const alias = encode(42, "_");
    expect(alias).toContain("_");
    expect(alias).not.toContain("-");
    expect(decode(alias, "_")).toBe(42);
  });

  test("decode rejects unknown adjective", () => {
    expect(() => decode("xxxxx-fugue")).toThrow(InvalidAliasError);
  });

  test("decode rejects unknown noun", () => {
    expect(() => decode("brave-xxxxx")).toThrow(InvalidAliasError);
  });

  test("decode rejects malformed alias", () => {
    expect(() => decode("just-one-extra-dash")).toThrow(InvalidAliasError);
    expect(() => decode("nodash")).toThrow(InvalidAliasError);
  });

  test("encode rejects out-of-range canonicals", () => {
    expect(() => encode(-1)).toThrow(InvalidCanonicalError);
    expect(() => encode(CANON_MAX + 1)).toThrow(InvalidCanonicalError);
    // @ts-expect-error — intentionally bad type
    expect(() => encode("not an int")).toThrow(InvalidCanonicalError);
    expect(() => encode(1.5)).toThrow(InvalidCanonicalError);
  });

  test("known stable values (cross-checked against Python)", () => {
    // Cross-language sanity checks. These should ALSO produce the same
    // strings in the Python implementation — if they ever diverge, one
    // of the two ports has drifted from the shared wordlists.
    // Values valid for arxivhaiku v1.0.2 wordlists (SHA-pinned in
    // dist/index.d.ts as ADJECTIVES_SHA256 / NOUNS_SHA256).
    expect(encode(0)).toBe("aaronic-aalii");
    expect(encode(1234567)).toBe("alpine-pitprop");
    expect(encode(33554431)).toBe("zonary-zoril");
    expect(decode("alpine-pitprop")).toBe(1234567);
  });
});

// ---------------------------------------------------------------------------
// Crockford
// ---------------------------------------------------------------------------

describe("Crockford Base32", () => {
  test("encode(0) is '00000'", () => {
    expect(encodeCrockford(0)).toBe("00000");
    expect(decodeCrockford("00000")).toBe(0);
  });

  test("encode(CANON_MAX) is 'ZZZZZ'", () => {
    expect(encodeCrockford(CANON_MAX)).toBe("ZZZZZ");
    expect(decodeCrockford("ZZZZZ")).toBe(CANON_MAX);
  });

  test("round-trips selected values", () => {
    for (const c of [0, 1, 31, 32, 1023, 1024, Math.floor(CANON_MAX / 2), CANON_MAX - 1, CANON_MAX]) {
      expect(decodeCrockford(encodeCrockford(c))).toBe(c);
    }
  });

  test("decode is case-insensitive", () => {
    const upper = encodeCrockford(123456);
    expect(decodeCrockford(upper.toLowerCase())).toBe(decodeCrockford(upper));
  });

  test("decode normalizes I/L → 1 and O → 0", () => {
    // 0 in all 5 positions, with O substituted
    expect(decodeCrockford("OOOOO")).toBe(0);
    // canonical 1 = '00001' — I/L in position 5 should decode as 1
    expect(decodeCrockford("0000L")).toBe(1);
    expect(decodeCrockford("0000I")).toBe(1);
  });

  test("decode strips embedded hyphens", () => {
    expect(decodeCrockford("00-00-L")).toBe(1);
  });

  test("decode rejects invalid characters", () => {
    expect(() => decodeCrockford("ZZZZ?")).toThrow(InvalidCanonicalError);
  });

  test("decode rejects wrong length", () => {
    expect(() => decodeCrockford("ABCD")).toThrow(InvalidCanonicalError);
    expect(() => decodeCrockford("ABCDEF")).toThrow(InvalidCanonicalError);
  });

  test("alias ↔ Crockford ↔ canonical all round-trip", () => {
    for (const c of [0, 1, 4096, 1234567, CANON_MAX]) {
      const alias = encode(c);
      const tok = encodeCrockford(c);
      expect(decode(alias)).toBe(c);
      expect(decodeCrockford(tok)).toBe(c);
      expect(encodeCrockford(decode(alias))).toBe(tok);
    }
  });

  test("known stable values (Crockford form is wordlist-independent)", () => {
    // Crockford encoding doesn't depend on the wordlists — just integer
    // → base 32 → 5 chars. These values are stable across all versions.
    expect(encodeCrockford(0)).toBe("00000");
    expect(encodeCrockford(1234567)).toBe("15NM7");
    expect(encodeCrockford(33554431)).toBe("ZZZZZ");
    expect(decodeCrockford("15NM7")).toBe(1234567);
  });
});

// ---------------------------------------------------------------------------
// Profanity / safety spot check
// ---------------------------------------------------------------------------

describe("profanity safety spot check", () => {
  // Same blocklist as Python's TestNoProfanityInAdjacentPairs.
  const DANGEROUS = [
    "rape", "kill", "shit", "fuck", "cunt", "spic", "chink", "gook",
    "wank", "boob", "cock", "bitch", "anal", "anus", "tits", "porn",
    "klan", "nazi", "kkk", "dyke", "scat", "negro",
  ];

  test("no adjective contains a dangerous substring", () => {
    for (const w of listAdjectives()) {
      for (const sub of DANGEROUS) {
        expect(w, `adj ${w} contains ${sub}`).not.toContain(sub);
      }
    }
  });

  test("no noun contains a dangerous substring", () => {
    for (const w of listNouns()) {
      for (const sub of DANGEROUS) {
        expect(w, `noun ${w} contains ${sub}`).not.toContain(sub);
      }
    }
  });
});
