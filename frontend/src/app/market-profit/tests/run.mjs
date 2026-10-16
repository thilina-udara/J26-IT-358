/**
 * Self-contained test runner for Component 1 frontend library.
 * Executes native TypeScript unit & integration tests without third-party dependencies.
 */

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const testFile = path.join(here, "client.test.ts");

const inlineLoader = `data:text/javascript,export async function resolve(specifier, context, nextResolve) {
  if ((specifier.startsWith("./") || specifier.startsWith("../")) && !specifier.endsWith(".ts") && !specifier.endsWith(".js") && !specifier.endsWith(".json")) {
    try {
      return await nextResolve(specifier + ".ts", context);
    } catch {}
  }
  return nextResolve(specifier, context);
}`;

const result = spawnSync(
  process.execPath,
  [
    "--no-warnings",
    "--experimental-strip-types",
    "--loader",
    inlineLoader,
    testFile,
  ],
  {
    stdio: "inherit",
  }
);

process.exit(result.status ?? 1);
