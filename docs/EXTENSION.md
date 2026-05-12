# EXTENSION — How to grow the wordlists without breaking existing IDs

## The immutability rule

**Once v1.0.0 is published and any production aliases are issued, no word can ever be removed.**

A production system issuing `<adj>-<noun>` aliases stores those aliases as
foreign keys, mentions them in URLs, logs, audit trails, customer
communications. If the alias `sleepy-panda` resolves to canonical ID
`K3X9P` today, it must resolve to the same canonical ID forever.

If a word later proves problematic (e.g., a brand name we missed, a
demographic-adjacent term we want to retire), the word **must continue
to resolve for existing aliases** but should be marked deprecated to
prevent its use in future allocations.

## The deprecation file

Deprecation lives in a separate file, **never** by modifying `adjectives.txt`
or `nouns.txt`:

```
deprecated.txt
==============
# Format: <word>\t<deprecated-since-version>\t<reason>
amber  v1.1.0  unintended brand collision (Amber Heard, gemstone disambiguation)
```

The generator MUST NOT issue aliases containing deprecated words for new
allocations, but resolver tables must still recognize them.

## v2 must be a superset of v1

When the canonical ID space grows (e.g., 5-char → 6-char Crockford Base32,
yielding 32⁶ = ~1 billion IDs), the wordlists grow to keep the bijection.

Suggested v2 sizes for 6-char Crockford (30 bits):

| Pool | v1 (12+13 bits) | v2 (14+16 bits) |
|------|---------------:|----------------:|
| adj  | 4,096          | 16,384          |
| noun | 8,192          | 65,536          |

**The v2 wordlists must be supersets of the v1 wordlists.**
Every v1 word retains its **position** (index) in the v2 list. New words
append to the v2 list, never inserted into the middle.

Concretely:
```
v1 adj[0] = "abase"   →  v2 adj[0] = "abase"
v1 adj[1] = "abash"   →  v2 adj[1] = "abash"
                         ...
v1 adj[4095] = "zonal" →  v2 adj[4095] = "zonal"
                          v2 adj[4096] = <new word>  ← v2-only extension begins here
                          ...
                          v2 adj[16383] = <last new word>
```

Aliases generated under v1 will resolve identically under v2 because
their indices are preserved. v2 wordlists need this index-preservation
guarantee in their schema (e.g., a `version_introduced` column in
`adjectives_v2.tsv`).

## Filling the v2 expansion

The v2 adjective pool grows by 12,288 words (4× v1 size). The v1 build
already exhausted curated 4–6 letter adjective sources. Filling v2 will
require **relaxing the length constraint**: adopting 3–8 letter range
would yield enough adjective inventory.

Suggested approach for v2:

1. Replay the v1 pipeline with new constraints (e.g., length 3–8).
2. Remove all v1 words from the candidate set.
3. Run Steps 4–7 of the v1 pipeline on the remaining candidates,
   targeting the v2-only count (12,288 for adj, 57,344 for nouns).
4. Append v2-only words to the end of the v1 list (maintaining the
   alphabetical sort within the v2-only portion or not — but never
   re-sorting the combined list, which would shift v1 indices).
5. Run pair-audit on the **full** combined list, not just the new
   portion — v1×v2 cross-pairs may flag new issues.

## What never changes

- Pool sizes are tied to bit boundaries. 4,096 × 8,192 = 5-char Crockford.
  Future pool sizes must also align to power-of-2 boundaries.
- The encoding scheme: `<adjective>-<noun>` order, lowercase, ASCII hyphen.
- The mapping between canonical and alias is by **index**: alias index
  in pool ↔ canonical bit positions. The build pipeline does not encode
  this — it's the responsibility of the deployment-time mapping table.

## Operational guidance

When operating an alias-based system in production:

1. **Pin the wordlist SHA-256.** Record `adjectives.txt` and `nouns.txt`
   SHA-256 hashes in the deployment manifest. Refuse to start the
   resolver if hashes mismatch.
2. **Snapshot before upgrading.** Save a copy of v1 wordlists before
   moving to v2 — even if v2 is supposed to be a superset, verify it.
3. **Test the bijection.** A round-trip test (`encode(decode(alias)) == alias`)
   should run on every deploy with at least 10,000 random canonicals.
4. **Monitor for collisions.** If two canonicals ever produce the same
   alias or vice-versa, the bijection has broken — halt issuance.

## Relationship to the canonical Crockford Base32 space

The canonical 5-char Crockford alphabet is 32 characters:
`0123456789ABCDEFGHJKMNPQRSTVWXYZ` (excludes `ILOU`). 5 chars = 25 bits.

The 25-bit space is exactly the product 12 + 13:
- adj_index = first 12 bits = canonical >> 13
- noun_index = last 13 bits = canonical & 0x1FFF
- alias = `adj[adj_index] + "-" + noun[noun_index]`

The reverse mapping:
- adj_index = adjectives.index(adj_word)
- noun_index = nouns.index(noun_word)
- canonical = (adj_index << 13) | noun_index

See `arxivhaiku/codec.py` for the production implementation.
