# Web app integration guide

This guide is for teams integrating `arxivhaiku` into a JavaScript /
TypeScript web application — Next.js most prominently, but the patterns
apply equally to Remix, SvelteKit, plain Node servers, or browser apps.

If you're using Python (Django / FastAPI / Flask), see the main
[README](../README.md) — the API is identical and the integration
patterns map directly.

---

## Table of contents

- [Install](#install)
- [Pick a canonical storage form](#pick-a-canonical-storage-form)
- [Next.js (App Router)](#nextjs-app-router)
  - [URL routing](#url-routing)
  - [Server Actions](#server-actions)
  - [Route Handlers](#route-handlers)
  - [Middleware](#middleware)
  - [Client Components](#client-components)
- [Database integration](#database-integration)
  - [Drizzle ORM (recommended)](#drizzle-orm-recommended)
  - [Prisma](#prisma)
  - [Raw SQL](#raw-sql)
- [ID allocation strategies](#id-allocation-strategies)
- [Runtime considerations](#runtime-considerations)
- [Common pitfalls](#common-pitfalls)
- [Updating to a new version](#updating-to-a-new-version)
- [Reference: full Next.js example](#reference-full-nextjs-example)

---

## Install

One command. No npm publish, no postinstall scripts, no allowlists.

```bash
pnpm add github:SamHarrison/arxivhaiku#semver:^1.0.2
```

(Works identically with `npm add` and `yarn add`. The `#semver:^1.0.2`
selector matches the latest tag satisfying SemVer `^1.0.2` —
typically the current `1.x.y` release.)

Pin to a specific commit SHA for stricter reproducibility:

```bash
pnpm add github:SamHarrison/arxivhaiku#<commit-sha>
```

The package ships a built `dist/` with ESM, CJS, and `.d.ts` types. No
runtime dependencies. ~150KB minified (~25KB gzipped) with both
wordlists inlined.

## Pick a canonical storage form

Decide this once, up front. The bijection lets you interchange three
forms — but only one should be the **storage truth**:

| Storage form | Type | Pro | Con |
|---|---|---|---|
| **Integer canonical** | `INTEGER` (4B) | smallest, fastest index, sortable | not human-shareable |
| **Crockford token** | `CHAR(5)` (5B) | compact, shareable, normalized | uppercase-only, slight index overhead |
| **Alias string** | `VARCHAR(15)` (9–15B) | most human-friendly | longest, ties schema to wordlist version |

**Recommended: store the integer canonical, display the alias.**

```ts
import { encode, decode, InvalidAliasError } from "arxivhaiku";

// reading: DB → human
const item = await db.query.items.findFirst({ where: eq(items.id, 1234567) });
return { id: item.id, alias: encode(item.id) };

// writing: human → DB
const id = decode(req.params.alias);  // throws InvalidAliasError on bad input
const item = await db.insert(items).values({ id, ...data }).returning();
```

The integer is the index. The alias is the badge. They're never out of sync.

## Next.js (App Router)

### URL routing

The natural URL form is `/items/[alias]`. The dynamic segment decodes
on the server, with a clean 404 on malformed input:

```ts
// app/items/[alias]/page.tsx
import { decode, InvalidAliasError } from "arxivhaiku";
import { notFound } from "next/navigation";
import { db } from "@/lib/db";
import { items } from "@/lib/schema";
import { eq } from "drizzle-orm";

export default async function ItemPage({
  params,
}: { params: Promise<{ alias: string }> }) {
  const { alias } = await params;

  let id: number;
  try {
    id = decode(alias);
  } catch (e) {
    if (e instanceof InvalidAliasError) notFound();
    throw e;
  }

  const item = await db.query.items.findFirst({ where: eq(items.id, id) });
  if (!item) notFound();

  return <ItemView item={item} />;
}

// Optional: generate static params for the most-visited items
export async function generateStaticParams() {
  const popular = await db.query.items.findMany({
    where: eq(items.featured, true),
    limit: 100,
  });
  return popular.map((item) => ({ alias: encode(item.id) }));
}
```

For Edge runtime (no DB pool, faster cold starts on edge functions):

```ts
export const runtime = "edge";
```

### Server Actions

Server Actions are the cleanest place to put `encode`/`decode` because
they keep the wordlist on the server while exposing a typed function
to client code:

```ts
// app/items/actions.ts
"use server";
import { encode, decode, InvalidAliasError } from "arxivhaiku";
import { db } from "@/lib/db";
import { items } from "@/lib/schema";
import { eq } from "drizzle-orm";
import { redirect } from "next/navigation";

export async function createItem(formData: FormData) {
  const id = await allocateUniqueId(); // see "ID allocation strategies" below
  const alias = encode(id);

  await db.insert(items).values({
    id,
    title: formData.get("title") as string,
  });

  redirect(`/items/${alias}`);
}

export async function aliasFor(id: number): Promise<string> {
  return encode(id);
}

export async function canonicalFor(alias: string): Promise<number> {
  try {
    return decode(alias);
  } catch (e) {
    if (e instanceof InvalidAliasError) throw new Error(`bad alias: ${alias}`);
    throw e;
  }
}
```

### Route Handlers

Useful when you need a JSON endpoint (e.g., for an external integration
or a mobile client). Edge-runtime-compatible:

```ts
// app/api/items/[alias]/route.ts
export const runtime = "edge";

import { decode, InvalidAliasError } from "arxivhaiku";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ alias: string }> },
) {
  const { alias } = await params;
  let id: number;
  try {
    id = decode(alias);
  } catch (e) {
    if (e instanceof InvalidAliasError) {
      return Response.json({ error: "not_found" }, { status: 404 });
    }
    throw e;
  }
  // ... look up item by id ...
  return Response.json({ id, alias });
}
```

### Middleware

Validate alias format in middleware to bounce malformed URLs before
they hit your route handlers. Edge-runtime-compatible:

```ts
// middleware.ts
import { NextResponse, type NextRequest } from "next/server";
import { decode, InvalidAliasError } from "arxivhaiku";

export const config = {
  matcher: ["/items/:alias*"],
};

export function middleware(req: NextRequest) {
  const alias = req.nextUrl.pathname.split("/").at(-1);
  if (!alias) return NextResponse.next();
  try {
    decode(alias);
    return NextResponse.next();
  } catch (e) {
    if (e instanceof InvalidAliasError) {
      return NextResponse.rewrite(new URL("/404", req.url));
    }
    throw e;
  }
}
```

### Client Components

If you only need to **display** an alias from a known integer (or
vice versa), the codec works in Client Components too — wordlists are
inlined in the bundle:

```tsx
"use client";
import { encode, haiku } from "arxivhaiku";

export function NewItemButton() {
  return (
    <button onClick={() => alert(haiku())}>
      Preview a random alias
    </button>
  );
}
```

**However:** this ships ~25KB gzipped of wordlists to every browser.
For most apps, prefer server-side encoding via a Server Action — the
client never needs the wordlist arrays in memory, only the resulting
alias string.

If you do need browser-side encoding, lazy-load it:

```tsx
"use client";
import { useState } from "react";

export function NewItemButton() {
  const [alias, setAlias] = useState<string | null>(null);
  return (
    <button onClick={async () => {
      const { haiku } = await import("arxivhaiku");
      setAlias(haiku());
    }}>
      {alias ?? "Generate"}
    </button>
  );
}
```

The dynamic import keeps `arxivhaiku` out of the initial bundle until
the user actually clicks.

## Database integration

### Drizzle ORM (recommended)

```ts
// schema.ts
import { pgTable, integer, text, timestamp } from "drizzle-orm/pg-core";

export const items = pgTable("items", {
  id: integer("id").primaryKey(),  // canonical, 0..33_554_431
  title: text("title").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export type Item = typeof items.$inferSelect;
export type NewItem = typeof items.$inferInsert;
```

Allocation helper:

```ts
// lib/allocate-id.ts
import { CANON_MAX } from "arxivhaiku";
import { db } from "./db";
import { items } from "./schema";
import { eq } from "drizzle-orm";

export async function allocateItemId(): Promise<number> {
  for (let attempt = 0; attempt < 8; attempt++) {
    const buf = new Uint32Array(1);
    crypto.getRandomValues(buf);
    const id = buf[0] & CANON_MAX;

    const existing = await db.query.items.findFirst({ where: eq(items.id, id) });
    if (!existing) return id;
    // collision (extremely rare below ~5,000 rows; retry)
  }
  throw new Error("could not allocate unique id after 8 attempts");
}
```

A SQL unique-constraint violation is also a fine signal to retry — see
[ID allocation strategies](#id-allocation-strategies) below for
non-collision-prone alternatives at scale.

### Prisma

```prisma
model Item {
  id        Int      @id        // canonical, 0..33_554_431 — NOT @default(autoincrement())
  title     String
  createdAt DateTime @default(now())
}
```

Allocation:

```ts
import { encode, CANON_MAX } from "arxivhaiku";
import { prisma } from "./prisma";

export async function createItem(title: string) {
  const buf = new Uint32Array(1);
  crypto.getRandomValues(buf);
  const id = buf[0] & CANON_MAX;
  const item = await prisma.item.create({ data: { id, title } });
  return { ...item, alias: encode(item.id) };
}
```

### Raw SQL

PostgreSQL:

```sql
CREATE TABLE items (
  id INTEGER PRIMARY KEY CHECK (id BETWEEN 0 AND 33554431),
  title TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX items_created_at_idx ON items (created_at DESC);
```

MySQL / MariaDB:

```sql
CREATE TABLE items (
  id INT UNSIGNED PRIMARY KEY,
  title TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT id_range CHECK (id <= 33554431)
);
```

SQLite (e.g., for Cloudflare D1, Vercel SQLite, Turso):

```sql
CREATE TABLE items (
  id INTEGER PRIMARY KEY,        -- max for SQLite INTEGER fits easily
  title TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
```

## ID allocation strategies

How you pick the integer ID for a new row matters more than you'd think
at small scale, because the alias is a deterministic function of the ID.

### Strategy 1 — Sequential counter (simplest, NOT recommended for aliases)

```sql
id SERIAL PRIMARY KEY  -- 1, 2, 3, ...
```

**Why it's bad for aliases:** the first 8,192 rows all share the same
adjective (`aaronic-aalii`, `aaronic-abaca`, ...). The next 8,192 share
`abandoned-`. Aliases of adjacent rows look near-identical, defeating the
"feels random" property that makes haikunators pleasant.

Use this only if you don't care about alias appearance — e.g., for an
internal ID where the alias is rarely surfaced to humans.

### Strategy 2 — Random with retry (recommended for most apps)

Pick a random 25-bit integer; retry if it collides:

```ts
import { CANON_MAX } from "arxivhaiku";

export async function allocateRandom<T>(
  insert: (id: number) => Promise<T>,
  maxAttempts = 8,
): Promise<T> {
  for (let i = 0; i < maxAttempts; i++) {
    const buf = new Uint32Array(1);
    crypto.getRandomValues(buf);
    const id = buf[0] & CANON_MAX;
    try {
      return await insert(id);
    } catch (e) {
      if (isUniqueViolation(e)) continue;
      throw e;
    }
  }
  throw new Error(`failed to allocate after ${maxAttempts} attempts`);
}
```

**Collision math:** the birthday bound for a 25-bit (33.5M) space is
roughly √33M ≈ 5,800 IDs before you hit your first collision. At 100K
issued IDs, ~0.3% of allocations will retry once.

Practical: fine up to ~1M rows.

### Strategy 3 — Counter + format-preserving permutation (no collisions, any scale)

If you have more than ~1M rows or want to avoid retries entirely, allocate
IDs from a sequential counter and apply a fixed-key Feistel cipher to
scramble them into a non-adjacent-looking integer:

```ts
// Sketch — 25-bit Feistel network with 4 rounds.
// Not cryptographically secure, but visually scrambles adjacent counters.
function scramble25(n: number, key = 0xDEADBE): number {
  let left = (n >> 12) & 0x1FFF;  // 13 bits
  let right = n & 0xFFF;          // 12 bits
  for (let i = 0; i < 4; i++) {
    [left, right] = [right, left ^ ((Math.imul(right, key ^ i) >>> 0) & 0xFFF)];
  }
  return ((left << 12) | right) & 0x1FFFFFF;
}
```

A counter (1, 2, 3, ...) scrambled with `scramble25(counter)` produces
unique 25-bit integers (no collisions, ever) that **look** random when
encoded as aliases. Round-trip with the inverse for decoding if needed.

This is the right pattern if you're at significant scale or want
deterministic test fixtures.

### Strategy 4 — `haiku()` for one-off IDs

If you don't need round-trippability and just want a random alias to
log/display once (e.g., debug session IDs, ephemeral correlation IDs):

```ts
import { haiku } from "arxivhaiku";
const sessionId = haiku();  // 'frosty-meadow'
```

`haiku()` calls `crypto.getRandomValues` internally. Same collision
math as Strategy 2 but you don't need to verify against a DB.

## Runtime considerations

| Runtime | Status | Notes |
|---|---|---|
| Node ≥ 18 | ✓ Tested | Primary target |
| Node 20, 22, 24 | ✓ Tested | CI matrix |
| Vercel Edge | ✓ Compatible | No filesystem, Web Crypto only |
| Cloudflare Workers | ✓ Compatible | Same constraints |
| Deno | ✓ Compatible | Web-standard imports work |
| Bun | ✓ Compatible | Pure ESM/CJS |
| Browser (modern) | ✓ Compatible | Web Crypto present; bundle size is ~25KB gzipped |
| Browser (IE11) | ✗ Unsupported | No `crypto.getRandomValues`, no `BigInt` (not used, but other parts may need polyfill) |

**Bundle size sensitivity.** The wordlists add ~150KB raw / ~25KB gzipped
to your bundle. If you only encode (never `decode` or look up by word),
you could theoretically tree-shake the noun reverse-index. In practice,
tsup's ESM output isn't quite tree-shakeable to that depth; if bundle
size matters, do encoding server-side and ship only the resulting alias
strings to the browser.

**Edge runtime gotchas.** No filesystem, no Node built-ins, no
`crypto.randomBytes`. `arxivhaiku` uses only `globalThis.crypto`
(Web Crypto API), which is present in all Edge runtimes. No special
configuration needed.

## Common pitfalls

### "Why are my early IDs all `aaronic-X`?"

You're using sequential allocation (`SERIAL` or auto-increment). See
[ID allocation strategies](#id-allocation-strategies) — switch to
random or scrambled allocation.

### "I get an `InvalidAliasError` but the alias looks fine"

Check for case mismatch (`Frosty-Meadow` won't decode — the wordlists
are lowercase only) or a non-hyphen separator. If a user typed it,
normalize first: `alias.toLowerCase().trim()`.

If the alias was generated from a newer arxivhaiku version, the
specific adj/noun may not be in your installed version. Verify
`ADJECTIVES_SHA256` / `NOUNS_SHA256` matches between writer and reader.

### "My SHA-256 check fails after `pnpm up`"

By design — `arxivhaiku@1.0.2` ships different wordlists than `1.0.1`.
Pin to an exact version (`#v1.0.2` or `#<commit-sha>`) if you need
bit-identical wordlists across deploys, and verify aliases issued under
one version still decode under the next.

The immutability rule (see `docs/EXTENSION.md`) holds **from v1.0.2
forward** — once you start issuing aliases in production, future
patches will only **append** new words, never remove or reindex.

### "How big is the wordlist in my bundle?"

```
ESM:    ~150KB raw, ~25KB gzipped, ~22KB brotli
CJS:    ~150KB raw, ~25KB gzipped
d.ts:    ~5KB
```

If you import only `encode`/`decode`/`encodeCrockford`, the wordlists
are still pulled in (they're a runtime constant). Tree-shaking won't
remove them. If you need a thinner bundle, encode server-side.

### "The Drizzle CHECK constraint fires on legitimate IDs"

Make sure you allow `0` as a valid ID — the canonical space is
`[0, 33_554_431]` inclusive. Some tutorials write `id > 0` which
disallows the canonical value for the alphabetically-first alias.

```sql
-- correct:
CHECK (id BETWEEN 0 AND 33554431)

-- WRONG:
CHECK (id > 0 AND id <= 33554431)
```

### "Server Component decodes work but Client Component imports fail"

Make sure the import path is `arxivhaiku`, not `arxivhaiku/codec` or
similar. Only the top-level export is part of the public API; deep
imports may break across versions.

## Updating to a new version

```bash
# from a specific version
pnpm up arxivhaiku@github:SamHarrison/arxivhaiku#semver:^1.0.3

# from any 1.x
pnpm up arxivhaiku@github:SamHarrison/arxivhaiku
```

Then re-run your tests. If you have aliases stored from a previous
version:

1. Read the new `CHANGELOG.md` for the list of removed/added words.
2. If any of your stored aliases reference removed words, you'll need
   to migrate. This shouldn't happen post-v1.0.2 due to the immutability
   rule, but pre-v1.0.2 patch versions did break compatibility.
3. Verify `ADJECTIVES_SHA256` / `NOUNS_SHA256` matches what you expect:

```ts
import { ADJECTIVES_SHA256, NOUNS_SHA256, VERSION } from "arxivhaiku";
console.log(`arxivhaiku ${VERSION}`);
console.log(`  adj  ${ADJECTIVES_SHA256}`);
console.log(`  noun ${NOUNS_SHA256}`);
```

Add this to a deploy-time smoke test if your app cares about wordlist
identity.

## Reference: full Next.js example

A complete minimal Next.js 16 + Drizzle setup using `arxivhaiku`:

```
app/
├── items/
│   ├── [alias]/
│   │   └── page.tsx          # /items/[alias]
│   ├── new/
│   │   └── page.tsx          # /items/new (form)
│   └── actions.ts            # server actions
├── api/
│   └── items/
│       └── [alias]/
│           └── route.ts      # GET /api/items/[alias]
└── layout.tsx
lib/
├── db.ts                     # drizzle client
├── schema.ts                 # items table
└── allocate-id.ts            # random-with-retry allocator
middleware.ts                 # alias-validation middleware
```

```ts
// lib/db.ts
import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";
import * as schema from "./schema";

export const db = drizzle(new Pool({ connectionString: process.env.DATABASE_URL }), { schema });
```

```ts
// lib/schema.ts
import { pgTable, integer, text, timestamp } from "drizzle-orm/pg-core";

export const items = pgTable("items", {
  id: integer("id").primaryKey(),
  title: text("title").notNull(),
  body: text("body"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});
```

```ts
// lib/allocate-id.ts
import { CANON_MAX } from "arxivhaiku";
import { db } from "./db";
import { items } from "./schema";
import { eq } from "drizzle-orm";

export async function allocateItemId(): Promise<number> {
  for (let i = 0; i < 8; i++) {
    const buf = new Uint32Array(1);
    crypto.getRandomValues(buf);
    const id = buf[0] & CANON_MAX;
    const existing = await db.query.items.findFirst({ where: eq(items.id, id) });
    if (!existing) return id;
  }
  throw new Error("could not allocate unique id");
}
```

```ts
// app/items/actions.ts
"use server";
import { encode } from "arxivhaiku";
import { redirect } from "next/navigation";
import { db } from "@/lib/db";
import { items } from "@/lib/schema";
import { allocateItemId } from "@/lib/allocate-id";

export async function createItem(formData: FormData) {
  const id = await allocateItemId();
  await db.insert(items).values({
    id,
    title: formData.get("title") as string,
    body: formData.get("body") as string,
  });
  redirect(`/items/${encode(id)}`);
}
```

```tsx
// app/items/new/page.tsx
import { createItem } from "../actions";

export default function NewItem() {
  return (
    <form action={createItem}>
      <input name="title" required />
      <textarea name="body" />
      <button type="submit">Create</button>
    </form>
  );
}
```

```tsx
// app/items/[alias]/page.tsx
import { decode, encode, InvalidAliasError } from "arxivhaiku";
import { notFound } from "next/navigation";
import { db } from "@/lib/db";
import { items } from "@/lib/schema";
import { eq } from "drizzle-orm";

export default async function ItemPage({
  params,
}: { params: Promise<{ alias: string }> }) {
  const { alias } = await params;
  let id: number;
  try {
    id = decode(alias);
  } catch (e) {
    if (e instanceof InvalidAliasError) notFound();
    throw e;
  }
  const item = await db.query.items.findFirst({ where: eq(items.id, id) });
  if (!item) notFound();
  return (
    <article>
      <h1>{item.title}</h1>
      <p>{item.body}</p>
      <footer>
        ID: {item.id} · Alias: {encode(item.id)}
      </footer>
    </article>
  );
}
```

```ts
// middleware.ts
import { NextResponse, type NextRequest } from "next/server";
import { decode, InvalidAliasError } from "arxivhaiku";

export const config = {
  matcher: "/items/:alias((?!new$).*)",  // skip /items/new
};

export function middleware(req: NextRequest) {
  const alias = req.nextUrl.pathname.split("/").at(-1);
  if (!alias) return NextResponse.next();
  try {
    decode(alias);
    return NextResponse.next();
  } catch (e) {
    if (e instanceof InvalidAliasError) {
      return NextResponse.rewrite(new URL("/404", req.url));
    }
    throw e;
  }
}
```

That's the whole integration. Three files import from `arxivhaiku`:
the Server Action (`encode`), the route handler / page (`decode`), and
the allocator (`CANON_MAX`). Everything else is your normal Next.js
+ Drizzle code.

---

## See also

- [README](../README.md) — package overview, full API reference
- [`docs/PROCESS.md`](PROCESS.md) — how the wordlists were built
- [`docs/EXTENSION.md`](EXTENSION.md) — immutability rules, v2 path
- [`docs/CHANGELOG.md`](CHANGELOG.md) — release notes + SHA-256 pins
