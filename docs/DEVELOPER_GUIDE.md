# Developer Guide

Use [STATUS.md](STATUS.md) for current verification results and [ARCHITECTURE.md](ARCHITECTURE.md) for contracts. The active product workflow is React → FastAPI → PlanningService. Streamlit and the optional research graph share the same approval writer.

## Setup and run

macOS/Linux, Python 3.11+, Node.js 22.12+ (Node 24 in CI). From the repository root:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix web ci
npm --prefix web run build
CALENDAR_MODE=mock LLM_PROVIDER=mock .venv/bin/python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Open [localhost:8000](http://127.0.0.1:8000). Building before starting the API mounts the bundled frontend. For development run the API with `--reload`, then `npm --prefix web run dev` in another terminal. Vite uses port 5173 and proxies `/api` to port 8000.

For the Streamlit compatibility UI:

```bash
CALENDAR_MODE=mock LLM_PROVIDER=mock .venv/bin/python -m streamlit run src/app.py
```

Both entry points use `.data/planner.sqlite3`. To isolate experiments, set `PLANNER_DB_PATH=/absolute/path/experiment.sqlite3` before starting either process. Preserve the database and associated SQLite files when backing up live write history; deleting the ledger loses approval/reconciliation history. Mock events are saved and count as busy in later plans.

`.env.example` defaults to mock LLM and calendar. Copy it to `.env` only if you do not already have a local configuration. Explicit shell variables take precedence. Keep `.env` and all credentials out of Git.

## Dependencies

`pyproject.toml` is the Python dependency source. `requirements.txt` installs the project with development dependencies instead of repeating ranges. Python transitive dependencies are not locked yet. `web/package-lock.json` locks the frontend; use `npm ci` for repeatable installation.

## Offline verification

```bash
CALENDAR_MODE=mock LLM_PROVIDER=mock .venv/bin/pytest tests/ -q --ignore=tests/llm_integration
npm --prefix web run build
.venv/bin/python -m pip check
git diff --check
```

`tests/programmatic/test_planning_service.py` exercises persistence, stale approvals, partial writes, lost responses, repeated approval, preflight changes, API boundaries, locks, and fail-closed behavior. `test_planning_correctness.py` covers task coverage/DAG and time/DST/calendar semantics. Older programmatic and pipeline tests remain in place. The mixed pipeline suite skips real-LLM fixtures when `LLM_PROVIDER=mock`; skips are not passing live tests.

Browser regression tests:

```bash
source .venv/bin/activate
npm --prefix web exec -- playwright install chromium
npm --prefix web run build
npm --prefix web run test:e2e
```

The Playwright configuration starts its own API on port 8010 with a temporary mock database. It runs edit/approve/reload and edit/reject flows at desktop and mobile sizes. It never uses the normal saved-plan database. CI installs Chromium with OS dependencies and runs these tests. Check STATUS for whether a particular browser run was actually executed; adding tests is not evidence of a passing run.

Manual acceptance flow:

1. Create a goal, edit a task name/duration/dependency, and generate all three candidates.
2. Switch strategies; verify coverage, dates, agenda, and week view update together in the selected timezone.
3. Return to editing, change a task, and regenerate; verify the revision changes.
4. Open the approval summary, inspect events/calendar/timezone, and explicitly acknowledge any violations.
5. Confirm in mock mode, reload, and inspect each saved write result. Repeating approval should preserve event identities.
6. Create another plan and reject it; verify zero writes. Repeat the comparison flow on a narrow viewport.

## Optional live evaluation

All providers continue through `src/llm_client/client.py`: `anthropic`, `gemini`, `vertex_ai`, `openai_compatible`, and `mock`. Configure the provider's key or Google ADC and model in your local `.env`. Calendar and LLM modes are independent: `CALENDAR_MODE=mock` alone does not disable paid LLM calls.

```bash
# Explicit opt-in: real provider calls, mock calendar
CALENDAR_MODE=mock LLM_PROVIDER=vertex_ai .venv/bin/pytest tests/llm_integration/ -v -m integration
```

Live Google Calendar uses the existing installed-app OAuth flow and local token file. Validate it against a dedicated test calendar before real use. Public deployment needs web OAuth, authentication, token isolation, and durable jobs; current container/AWS scaffolding is not a verified deployment of the new workspace.

## Change rules

- Change Python contracts in `src/domain/models.py` and update `web/src/types.ts` together. FastAPI exposes `/openapi.json`; TypeScript generation is a future improvement.
- Keep heuristics and validator pure; inject gateways/clocks/decomposers in service tests.
- Every write path must use the approval service, immutable snapshot identity, and per-event ledger. Never introduce Calendar update/delete calls.
- Validation violations are surfaced for user judgment. Do not introduce a scheduling repair loop.
- Update STATUS when actual behavior or verification changes. Historical experiment reports describe the research graph, not the current product call count or UI.
