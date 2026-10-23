# Calendar Planning Agent

Turn a goal into an editable task draft, compare three schedules, and add only the events you approve. The main workspace uses React + TypeScript with a FastAPI backend. Streamlit remains available through the same planning service.

![Guided planning workspace](docs/review-assets/refactored-workspace.png)

## Run locally

Requires Python 3.11+ and Node.js 22.12+ (CI uses Node 24). Run these commands from the repository root:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix web ci
npm --prefix web run build
CALENDAR_MODE=mock LLM_PROVIDER=mock .venv/bin/python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Open [the workspace](http://127.0.0.1:8000). Both mock settings are required for a walkthrough without Google credentials or hosted LLM calls. Mock decomposition uses clearly labeled example tasks; edit them to fit your goal.

Plans, revisions, approvals, write results, and mock events persist in `.data/planner.sqlite3`. Set `PLANNER_DB_PATH` to use a different database. Refreshing or restarting keeps saved plans. Unsubmitted form edits are not saved automatically.

This version is a **local, single-user application on macOS/Linux**. The API has no user authentication and the SQLite writer uses POSIX file locks. Keep it bound to localhost. Public or multi-user deployment requires authentication, per-user OAuth/storage, and a different deployment design.

## What changed

- **Guided workflow:** describe a goal → edit tasks and dependencies → compare schedules → review an explicit approval summary. Mobile uses an agenda; desktop can switch to a timezone-aware week calendar.
- **Shared backend:** Pydantic contracts and one application service power React, Streamlit, and the research graph's write adapter.
- **Correctness:** stable task IDs, dependency validation, coverage and duration checks, working days, breaks, local deadline boundaries, and daylight-saving handling.
- **Recoverable writes:** approval binds a revision and schedule hash. A fresh calendar check surfaces new conflicts. Stable event IDs and a persistent ledger allow retries to reconcile uncertain results and skip confirmed writes.
- **Lower LLM overhead:** the workspace uses one logical decomposition call, with provider retries if needed. Comparison metrics and explanations come from scheduling rules. The original multi-reviewer graph remains available for research.

Calendar operations remain add-only. A Google insert and a local database transaction cannot form one atomic transaction; external calendar changes can still race the final check. A partial write preserves successful events and never deletes them to roll back.

## Development and testing

For hot reload, run the API with `--reload`, then start Vite in another terminal:

```bash
npm --prefix web run dev
```

Vite serves [localhost:5173](http://127.0.0.1:5173) and proxies `/api` to port 8000. For the Streamlit compatibility interface:

```bash
CALENDAR_MODE=mock LLM_PROVIDER=mock .venv/bin/python -m streamlit run src/app.py
```

Offline verification:

```bash
CALENDAR_MODE=mock LLM_PROVIDER=mock .venv/bin/pytest tests/ -q --ignore=tests/llm_integration
npm --prefix web run build
```

Browser tests and optional live evaluations are documented in [the developer guide](docs/DEVELOPER_GUIDE.md). Read [STATUS.md](docs/STATUS.md) for actual verification results and remaining work; mock results do not establish live provider quality or behavior.

## Code map

| Area | Location |
|---|---|
| React workspace | `web/src/` |
| REST API | `src/api/app.py` |
| Validated contracts and time semantics | `src/domain/` |
| Planning workflow, storage, calendar gateway | `src/planning/` |
| Pure scheduling strategies | `src/orchestration/heuristics/` |
| Deterministic constraint validation | `src/validator/constraints.py` |
| Google Calendar read/insert adapters | `src/calendar_api/` |
| All provider calls | `src/llm_client/client.py` |
| Streamlit compatibility entry | `src/app.py` |
| Optional multi-reviewer research graph | `src/orchestration/graph.py` |

## References

- [Current status and remaining work](docs/STATUS.md)
- [Architecture and approval contract](docs/ARCHITECTURE.md)
- [Setup, local workflow, and testing](docs/DEVELOPER_GUIDE.md)
- [Original refactor and UX audit](docs/REFACTOR_UX_REVIEW.md)
- [Historical research report](GenAI_Report_Final.pdf) and [experiment setup](docs/EXPERIMENTAL_SETUP.md)

Never commit `.env`, OAuth tokens, credentials, or API keys. All LLM calls go through `client.py`; heuristics and validation remain pure Python. Validation issues are shown for explicit user judgment, with no automatic repair loop.
