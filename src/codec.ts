/**
 * arxivhaiku.codec — alias generation and canonical-ID bijection.
 *
 * The bijection: every alias maps to exactly one 25-bit canonical integer,
 * and vice versa. Three interchangeable surface forms:
 *   - integer canonical          ∈ [0, 33_554_431]
 *   - alias string               e.g. "alpine-pixel"
 *   - 5-char Crockford Base32    e.g. "15NM7"
 *
 * Math:
 *   adjIndex  = canonical >>> 13              (top 12 bits → 4,096 adjectives)
 *   nounIndex = canonical & 0x1FFF            (bottom 13 bits → 8,192 nouns)
 *   canonical = (adjIndex << 13) | nounIndex
 *
 * The Crockford alphabet excludes I, L, O, U. Decoder normalizes I/L → 1,
 * O → 0 per the Crockford spec; encoder always emits uppercase canonical form.
 *
 * Runtime: pure ESM, Web-Crypto-only. Works on Node ≥ 18, Vercel Edge,
 * browsers, Deno, Bun. No filesystem I/O — wordlists are inlined via
 * `wordlists.generated.ts`.
 */
import {
  ADJECTIVES,
  NOUNS,
  ADJECTIVES_SHA256,
  NOUNS_SHA256,
} from "./wordlists.generated.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const ADJ_BITS = 12 as const;
export const NOUN_BITS = 13 as const;
export const CANON_BITS = 25 as const;
export const ADJ_COUNT = 1 << ADJ_BITS; // 4,096
export const NOUN_COUNT = 1 << NOUN_BITS; // 8,192
export const CANON_MAX = (1 << CANON_BITS) - 1; // 33_554_431

export const CANON_CHARS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ" as const;

// SHA-256 of the source wordlist files at build time — exposed so consumers
// can verify they're using the version they expect.
export { ADJECTIVES_SHA256, NOUNS_SHA256 };

// Internal: reverse-lookup maps for decode(). Built once at module init,
// O(1) per lookup thereafter.
const ADJ_INDEX = new Map<string, number>();
for (let i = 0; i < ADJECTIVES.length; i++) {
  ADJ_INDEX.set(ADJECTIVES[i]!, i);
}
const NOUN_INDEX = new Map<string, number>();
for (let i = 0; i < NOUNS.length; i++) {
  NOUN_INDEX.set(NOUNS[i]!, i);
}

// Crockford decode table
const CROCKFORD_DECODE = new Map<string, number>();
for (let i = 0; i < CANON_CHARS.length; i++) {
  CROCKFORD_DECODE.set(CANON_CHARS[i]!, i);
}

// Sanity at module load — assertion is cheap and catches a corrupted bundle.
if (ADJECTIVES.length !== ADJ_COUNT) {
  throw new Error(
    `arxivhaiku: adjective pool size mismatch (${ADJECTIVES.length} != ${ADJ_COUNT})`,
  );
}
if (NOUNS.length !== NOUN_COUNT) {
  throw new Error(
    `arxivhaiku: noun pool size mismatch (${NOUNS.length} != ${NOUN_COUNT})`,
  );
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export class InvalidAliasError extends Error {
  override readonly name = "InvalidAliasError";
}

export class InvalidCanonicalError extends Error {
  override readonly name = "InvalidCanonicalError";
}

// ---------------------------------------------------------------------------
// Wordlist accessors
// ---------------------------------------------------------------------------

/** Return a copy of the sorted adjective list (safe to mutate). */
export function listAdjectives(): string[] {
  return ADJECTIVES.slice();
}

/** Return a copy of the sorted noun list (safe to mutate). */
export function listNouns(): string[] {
  return NOUNS.slice();
}

// ---------------------------------------------------------------------------
// Bijection: integer ↔ alias
// ---------------------------------------------------------------------------

function assertCanonical(canonical: number): void {
  if (!Number.isInteger(canonical) || canonical < 0 || canonical > CANON_MAX) {
    throw new InvalidCanonicalError(
      `canonical must be integer in [0, ${CANON_MAX}], got ${canonical}`,
    );
  }
}

/**
 * Encode an integer canonical (0 ≤ canonical ≤ 33,554,431) as an alias.
 * @example encode(1234567) === 'alpine-pixel'
 */
export function encode(canonical: number, separator = "-"): string {
  assertCanonical(canonical);
  const adjIdx = canonical >>> NOUN_BITS;
  const nounIdx = canonical & (NOUN_COUNT - 1);
  return `${ADJECTIVES[adjIdx]}${separator}${NOUNS[nounIdx]}`;
}

/**
 * Decode an alias string back to its integer canonical.
 * @example decode('alpine-pixel') === 1234567
 */
export function decode(alias: string, separator = "-"): number {
  if (typeof alias !== "string") {
    throw new InvalidAliasError(`alias must be a string, got ${typeof alias}`);
  }
  const parts = alias.split(separator);
  if (parts.length !== 2) {
    throw new InvalidAliasError(
      `alias must be exactly '<adj>${separator}<noun>', got ${JSON.stringify(alias)}`,
    );
  }
  const adjWord = parts[0]!;
  const nounWord = parts[1]!;
  const adjIdx = ADJ_INDEX.get(adjWord);
  if (adjIdx === undefined) {
    throw new InvalidAliasError(`unknown adjective: ${JSON.stringify(adjWord)}`);
  }
  const nounIdx = NOUN_INDEX.get(nounWord);
  if (nounIdx === undefined) {
    throw new InvalidAliasError(`unknown noun: ${JSON.stringify(nounWord)}`);
  }
  return (adjIdx << NOUN_BITS) | nounIdx;
}

// ---------------------------------------------------------------------------
// Crockford Base32
// ---------------------------------------------------------------------------

/**
 * Encode a canonical as a 5-character Crockford Base32 string. Always
 * uppercase canonical form; round-trips with decodeCrockford.
 */
export function encodeCrockford(canonical: number): string {
  assertCanonical(canonical);
  let out = "";
  let n = canonical;
  for (let i = 0; i < 5; i++) {
    out = CANON_CHARS[n & 0x1f]! + out;
    n >>>= 5;
  }
  return out;
}

/**
 * Decode a Crockford Base32 string to its canonical integer. Accepts:
 *   - Mixed case ("15NM7" or "15nm7")
 *   - Crockford normalization: I → 1, L → 1, O → 0
 *   - Embedded hyphens (stripped before decode)
 */
export function decodeCrockford(token: string): number {
  if (typeof token !== "string") {
    throw new InvalidCanonicalError(
      `token must be a string, got ${typeof token}`,
    );
  }
  const norm = token
    .toUpperCase()
    .replace(/[IL]/g, "1")
    .replace(/O/g, "0")
    .replace(/-/g, "");
  if (norm.length !== 5) {
    throw new InvalidCanonicalError(
      `expected 5 chars after normalization, got ${norm.length}: ${JSON.stringify(token)}`,
    );
  }
  let n = 0;
  for (const ch of norm) {
    const v = CROCKFORD_DECODE.get(ch);
    if (v === undefined) {
      throw new InvalidCanonicalError(
        `invalid Crockford character ${JSON.stringify(ch)} in ${JSON.stringify(token)}`,
      );
    }
    n = (n << 5) | v;
  }
  return n;
}

// ---------------------------------------------------------------------------
// Random generation
// ---------------------------------------------------------------------------

/**
 * Cryptographically-strong random canonical in [0, CANON_MAX].
 * Uses Web Crypto (`crypto.getRandomValues`) — works on Node ≥ 18, Edge,
 * browsers, Deno, Bun.
 */
function randomCanonical(): number {
  // Web Crypto: read 4 bytes (32 bits) and mask to 25 bits.
  // The masking is uniform because 2^25 divides 2^32 evenly (well, it
  // doesn't divide it but masking to the low 25 bits IS uniform when
  // the source is uniform 32-bit).
  const buf = new Uint32Array(1);
  globalThis.crypto.getRandomValues(buf);
  return buf[0]! & CANON_MAX;
}

/**
 * Generate a uniformly-random alias using cryptographic-grade entropy.
 * @example haiku() === 'frosty-meadow'
 */
export function haiku(separator = "-"): string {
  return encode(randomCanonical(), separator);
}

/**
 * Generate a uniformly-random 5-char Crockford canonical token using
 * cryptographic-grade entropy.
 * @example haikuCrockford() === 'K3X9P'
 */
export function haikuCrockford(): string {
  return encodeCrockford(randomCanonical());
}

// ---------------------------------------------------------------------------
// Class-based interface (parity with Python)
// ---------------------------------------------------------------------------

export interface HaikunatorOptions {
  separator?: string;
  /** Optional seed for deterministic output. DO NOT use for production IDs. */
  seed?: number;
}

/**
 * Stateful, optionally seeded generator. Use `seed` for reproducible
 * test fixtures only — the PRNG used when seeded is `mulberry32`, which
 * is fast but not cryptographically secure.
 *
 * Without `seed`, falls back to Web Crypto (same as `haiku()`).
 */
export class Haikunator {
  readonly separator: string;
  private readonly nextU32: () => number;

  constructor(options: HaikunatorOptions = {}) {
    this.separator = options.separator ?? "-";
    if (options.seed !== undefined) {
      this.nextU32 = mulberry32(options.seed >>> 0);
    } else {
      this.nextU32 = () => {
        const buf = new Uint32Array(1);
        globalThis.crypto.getRandomValues(buf);
        return buf[0]!;
      };
    }
  }

  haikunate(): string {
    return encode(this.nextU32() & CANON_MAX, this.separator);
  }

  encode(canonical: number): string {
    return encode(canonical, this.separator);
  }

  decode(alias: string): number {
    return decode(alias, this.separator);
  }
}

/**
 * mulberry32 — a small, fast, deterministic 32-bit PRNG. Not cryptographic.
 * Used only when Haikunator is constructed with an explicit seed.
 */
function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return function next(): number {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return (t ^ (t >>> 14)) >>> 0;
  };
}
