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

export {
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
  // Build-time provenance
  ADJECTIVES_SHA256,
  NOUNS_SHA256,
} from "./codec.js";

export type { HaikunatorOptions } from "./codec.js";

export const VERSION = "1.0.2" as const;
