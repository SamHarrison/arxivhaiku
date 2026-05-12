import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: true,
  clean: true,
  sourcemap: true,
  target: "es2022",
  // Keep wordlists inlined; no externals needed.
  external: [],
  // We expect to ship the codec; the gen step prebuilds wordlists.generated.ts.
  // tsup picks it up via the import chain.
});
