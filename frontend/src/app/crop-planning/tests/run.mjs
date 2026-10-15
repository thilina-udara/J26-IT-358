import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const frontend = path.resolve(here, "../../../..");
for (const args of [
  [path.join(frontend, "node_modules/typescript/bin/tsc"), "--project", path.join(here, "tsconfig.json")],
  ["--test", path.join(here, "../_test-build/tests/frontend.test.js")],
]) {
  const result = spawnSync(process.execPath, args, { cwd: frontend, stdio: "inherit" });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
