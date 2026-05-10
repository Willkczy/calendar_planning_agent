# Screenshots

End-to-end walkthrough of the Calendar Planning Agent, captured on
2026-05-09 against the mock calendar fixture (`CALENDAR_MODE=mock`)
with real Vertex AI handling decomposition, critic, candidate
review, and rationale generation.

## Files

| # | File | Phase | What it shows |
|---|------|-------|---------------|
| 1 | `01-intake-form.png` | intake | Goal, deadline, working hours, max session, break length, energy levels |
| 2 | `02-strategy-finish-earliest.png` | review | "Finish Earliest" candidate — front-load all work, maximise deadline buffer |
| 3 | `03-strategy-keep-time-contiguous.png` | review | "Keep Time Contiguous" candidate — largest slots first, minimise context switches |
| 4 | `04-strategy-energy-aware.png` | review | "Energy-Aware" candidate — heavy work in high-energy periods |
| 5 | `05-approval-confirmation.png` | done | Approval written, debug trace expandable |
| 6 | `06-google-calendar-live.png` | external | Live Google Calendar showing agent-tagged events after a live-mode write |

## How to reproduce

```bash
CALENDAR_MODE=mock LLM_PROVIDER=vertex_ai streamlit run src/app.py
```

Submit the intake form with a goal like:

```
Build a small Python script that summarizes expenses from a CSV
file by Friday.
```

with deadline `2026-05-16`, working hours `09:00–18:00`, max
session 120 min, 10-min breaks, and energy levels
`Morning=high, Afternoon=medium, Evening=low`.

For the live-write screenshot (6), set `CALENDAR_MODE=live` after
configuring Google OAuth — the agent will create the approved
events on the calendar identified by `GOOGLE_CALENDAR_ID`.

## Notes

- Existing busy blocks render gray. Agent proposals render in the
  selected strategy's color (blue / green / orange).
- The "Agent reviews" expander surfaces the multi-agent critic and
  per-candidate reviewer output that informed the rationale.
- The "Debug trace" expander on the review and done pages is
  designed to be copy-pasted into bug reports — see
  [`docs/TROUBLESHOOTING.md`](../TROUBLESHOOTING.md).
