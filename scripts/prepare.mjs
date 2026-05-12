#!/usr/bin/env node
/**
 * prepare hook — runs (1) after `pnpm install` in this repo, and (2) when a
 * consumer installs this package via `pnpm add github:SamHarrison/arxivhaiku`.
 *
 * In both cases, we want `dist/` to exist. The committed `dist/` covers the
 * consumer case so installs are instant; this script is a safety net that
 * rebuilds if `dist/` is missing or stale (which happens on a fresh clone
 * before `pnpm run build`).
 *
 * The script must be resilient: a consumer's GitHub install runs in a
 * partial environment. If anything fails, we skip rather than break.
 */
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

const distIndexJs = join(ROOT, "dist", "index.js");
const distIndexDts = join(ROOT, "dist", "index.d.ts");

if (existsSync(distIndexJs) && existsSync(distIndexDts)) {
  // dist/ is present — nothing to do. This is the common consumer-install path.
  process.exit(0);
}

// dist/ is missing — try to build. May fail in a consumer environment
// without dev deps; that's fine, fall through.
console.log("prepare: dist/ missing, attempting build...");
const result = spawnSync(
  process.platform === "win32" ? "pnpm.cmd" : "pnpm",
  ["run", "build"],
  { cwd: ROOT, stdio: "inherit" },
);
process.exit(result.status === 0 ? 0 : 0); // never fail
