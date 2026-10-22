import { defineConfig, devices } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

// Each run owns a disposable mock database; never target the user's saved plans.
const directory = mkdtempSync(join(tmpdir(), "calendar-planner-e2e-"));
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  use: { baseURL: "http://127.0.0.1:8010", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { viewport: { width: 375, height: 812 } } },
  ],
  webServer: {
    command: "python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8010",
    cwd: fileURLToPath(new URL("..", import.meta.url)),
    url: "http://127.0.0.1:8010/api/config",
    reuseExistingServer: false,
    env: {
      CALENDAR_MODE: "mock",
      LLM_PROVIDER: "mock",
      PLANNER_DB_PATH: join(directory, "plans.sqlite3"),
    },
  },
});
