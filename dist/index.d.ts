declare const ADJECTIVES_SHA256: "34d4edb55d168968dc9b4018a745633b3c782048cfdb99d93b586d8fc36ba905";
declare const NOUNS_SHA256: "965033026a676a90bcc7315a55fbd149e4d6dd55d03781a4eb77ec6bbd41ba35";

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

declare const ADJ_BITS: 12;
declare const NOUN_BITS: 13;
declare const CANON_BITS: 25;
declare const ADJ_COUNT: number;
declare const NOUN_COUNT: number;
declare const CANON_MAX: number;
declare const CANON_CHARS: "0123456789ABCDEFGHJKMNPQRSTVWXYZ";

declare class InvalidAliasError extends Error {
    readonly name = "InvalidAliasError";
}
declare class InvalidCanonicalError extends Error {
    readonly name = "InvalidCanonicalError";
}
/** Return a copy of the sorted adjective list (safe to mutate). */
declare function listAdjectives(): string[];
/** Return a copy of the sorted noun list (safe to mutate). */
declare function listNouns(): string[];
/**
 * Encode an integer canonical (0 ≤ canonical ≤ 33,554,431) as an alias.
 * @example encode(1234567) === 'alpine-pixel'
 */
declare function encode(canonical: number, separator?: string): string;
/**
 * Decode an alias string back to its integer canonical.
 * @example decode('alpine-pixel') === 1234567
 */
declare function decode(alias: string, separator?: string): number;
/**
 * Encode a canonical as a 5-character Crockford Base32 string. Always
 * uppercase canonical form; round-trips with decodeCrockford.
 */
declare function encodeCrockford(canonical: number): string;
/**
 * Decode a Crockford Base32 string to its canonical integer. Accepts:
 *   - Mixed case ("15NM7" or "15nm7")
 *   - Crockford normalization: I → 1, L → 1, O → 0
 *   - Embedded hyphens (stripped before decode)
 */
declare function decodeCrockford(token: string): number;
/**
 * Generate a uniformly-random alias using cryptographic-grade entropy.
 * @example haiku() === 'frosty-meadow'
 */
declare function haiku(separator?: string): string;
/**
 * Generate a uniformly-random 5-char Crockford canonical token using
 * cryptographic-grade entropy.
 * @example haikuCrockford() === 'K3X9P'
 */
declare function haikuCrockford(): string;
interface HaikunatorOptions {
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
declare class Haikunator {
    readonly separator: string;
    private readonly nextU32;
    constructor(options?: HaikunatorOptions);
    haikunate(): string;
    encode(canonical: number): string;
    decode(alias: string): number;
}

/**
 * arxivhaiku — Heroku-haikunator-style two-word identifiers.
 *
 * Pairs an adjective with a noun to produce friendly aliases like
 * "frosty-meadow" or "alpine-pixel". Built on a clean bijection: every
 * alias maps to exactly one 25-bit canonical integer (also expressible
 * as a 5-character Crockford Base32 token).
 *
 * Quick start:
 *
 *   import { haiku, encode, decode } from "arxivhaiku";
 *
 *   haiku();                // 'frosty-meadow'
 *   encode(1234567);        // 'alpine-pixel'
 *   decode('alpine-pixel'); // 1234567
 *
 * Runtime support: Node ≥ 18, Vercel Edge, browsers, Deno, Bun.
 * No runtime dependencies, no filesystem I/O — wordlists are inlined.
 *
 * See https://github.com/SamHarrison/arxivhaiku for the full README.
 */

declare const VERSION: "1.0.1";

export { ADJECTIVES_SHA256, ADJ_BITS, ADJ_COUNT, CANON_BITS, CANON_CHARS, CANON_MAX, Haikunator, type HaikunatorOptions, InvalidAliasError, InvalidCanonicalError, NOUNS_SHA256, NOUN_BITS, NOUN_COUNT, VERSION, decode, decodeCrockford, encode, encodeCrockford, haiku, haikuCrockford, listAdjectives, listNouns };
