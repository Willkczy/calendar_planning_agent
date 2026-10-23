import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Layers3,
  Leaf,
  LoaderCircle,
  Plus,
  RotateCcw,
  Sparkles,
  Sunrise,
  Target,
} from "lucide-react";
import { api } from "./api";
import {
  Confirmation,
  PreferencesFields,
  SchedulePreview,
  TaskEditor,
  dateLabel,
  minutes,
  statusNames,
  strategyNames,
  violationText,
} from "./components";
import type {
  Candidate,
  Config,
  Plan,
  PlanSummary,
  Preferences,
  Strategy,
  Task,
} from "./types";

function defaultPreferences(timezone = "America/New_York"): Preferences {
  const date = new Date();
  date.setDate(date.getDate() + 14);
  return {
    deadline: new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(date),
    timezone,
    work_start: "09:00",
    work_end: "18:00",
    workdays: [0, 1, 2, 3, 4],
    max_session_minutes: 120,
    break_minutes: 10,
    energy_levels: { morning: "high", afternoon: "medium", evening: "low" },
  };
}

export default function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [history, setHistory] = useState<PlanSummary[]>([]);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [goal, setGoal] = useState("");
  const [context, setContext] = useState("");
  const [preferences, setPreferences] = useState(defaultPreferences);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [editing, setEditing] = useState(false);
  const [selected, setSelected] = useState<Strategy>("deadline_first");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  function applyPlan(value: Plan) {
    setPlan(value);
    setTasks(value.tasks);
    setPreferences(value.preferences);
    setEditing(false);
    setSelected(value.selected_candidate || "deadline_first");
    localStorage.setItem("planning:last-plan", value.id);
    window.history.replaceState(null, "", `?plan=${value.id}`);
    void api<PlanSummary[]>("/plans")
      .then(setHistory)
      .catch(() => {});
  }
  async function run(label: string, action: () => Promise<void>) {
    setBusy(label);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "The operation could not be completed. Please try again.",
      );
    } finally {
      setBusy("");
    }
  }
  async function initialize() {
    await run("Loading your workspace…", async () => {
      const [c, list] = await Promise.all([
        api<Config>("/config"),
        api<PlanSummary[]>("/plans"),
      ]);
      setConfig(c);
      setHistory(list);
      setPreferences(defaultPreferences(c.timezone));
      const id =
        new URLSearchParams(location.search).get("plan") ||
        localStorage.getItem("planning:last-plan");
      if (id) applyPlan(await api<Plan>(`/plans/${id}`));
    });
  }
  useEffect(() => {
    void initialize();
  }, []);

  function newPlan() {
    setPlan(null);
    setGoal("");
    setContext("");
    setTasks([]);
    setError("");
    setEditing(false);
    setPreferences(defaultPreferences(config?.timezone));
    localStorage.removeItem("planning:last-plan");
    window.history.replaceState(null, "", window.location.pathname);
  }
  async function create() {
    await run("Breaking your goal into editable tasks…", async () => {
      const created = await api<Plan>("/plans", { goal, context, preferences });
      applyPlan(created);
      applyPlan(
        await api<Plan>(`/plans/${created.id}/decompose`, {
          revision: created.revision,
        }),
      );
    });
  }
  async function generate() {
    if (!plan) return;
    await run(
      "Finding free time, building schedules, and checking constraints…",
      async () => {
        const saved = await api<Plan>(
          `/plans/${plan.id}/draft`,
          { revision: plan.revision, tasks, preferences },
          "PUT",
        );
        applyPlan(saved);
        applyPlan(
          await api<Plan>(`/plans/${saved.id}/generate`, {
            revision: saved.revision,
          }),
        );
      },
    );
  }
  async function approve(candidate: Candidate, ids: string[]) {
    if (!plan) return;
    await run(
      "Checking your calendar and saving each event result…",
      async () => {
        const result = await api<Plan>(`/plans/${plan.id}/approve`, {
          revision: plan.revision,
          candidate_id: candidate.id,
          snapshot_hash: candidate.snapshot_hash,
          acknowledged_violation_ids: ids,
        });
        applyPlan(result);
        setSelected(candidate.id);
      },
    );
  }

  const candidate = plan?.candidates.find((c) => c.id === selected);
  const closed =
    plan &&
    ["completed", "partial", "writing", "rejected"].includes(plan.status);
  const taskView = plan && !closed && (editing || !plan.candidates.length);
  const stage = !plan ? 1 : closed ? 4 : taskView ? 2 : 3;
  const dirty =
    plan &&
    (JSON.stringify(tasks) !== JSON.stringify(plan.tasks) ||
      JSON.stringify(preferences) !== JSON.stringify(plan.preferences));
  const icons = {
    deadline_first: Target,
    min_fragmentation: Layers3,
    energy_aware: Sunrise,
  };
  const identical =
    plan &&
    plan.candidates.length > 1 &&
    new Set(
      plan.candidates.map((c) =>
        JSON.stringify(c.events.map((e) => [e.task_id, e.start, e.end])),
      ),
    ).size === 1;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          href="/"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            if (!busy) newPlan();
          }}
        >
          <span className="brand-mark">
            <Layers3 size={22} />
          </span>
          <span>
            Calendar<small>PLANNING AGENT</small>
          </span>
        </a>
        <button className="button new-plan" onClick={newPlan} disabled={!!busy}>
          <Plus size={18} />
          New plan
        </button>
        <div className="sidebar-label">
          Your plans <span>{history.length}</span>
        </div>
        <nav className="plan-history" aria-label="Saved plans">
          {history.map((item) => (
            <button
              key={item.id}
              className={item.id === plan?.id ? "active" : ""}
              disabled={!!busy}
              onClick={() =>
                void run("Loading your plan…", async () =>
                  applyPlan(await api<Plan>(`/plans/${item.id}`)),
                )
              }
            >
              <span>{item.goal}</span>
              <small>
                <i
                  className={
                    item.status === "completed"
                      ? "status-dot done"
                      : "status-dot"
                  }
                />
                {statusNames[item.status]}
              </small>
            </button>
          ))}
          {!history.length && (
            <p className="history-empty">
              Start with your next goal.
              <br />
              Make a little time for it.
            </p>
          )}
        </nav>
        <div className="sidebar-footer">
          <Leaf size={18} />
          <span>
            Make room for what matters.<small>Plans saved on this device</small>
          </span>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <span className="breadcrumb">
            Workspace <span>/</span> {plan ? "My plan" : "Start a new plan"}
          </span>
          <div className="connection">
            <i className={config ? "status-dot done" : "status-dot"} />
            {(plan?.calendar_mode || config?.calendar_mode) === "mock"
              ? "Demo mode"
              : config
                ? "Google Calendar · Local"
                : "Connecting"}
            <span className="connection-zone">
              {plan?.preferences.timezone || config?.timezone}
            </span>
          </div>
        </header>
        {!!history.length && (
          <div className="mobile-history mobile-only">
            <label>
              Open a saved plan
              <select
                value={plan?.id || ""}
                disabled={!!busy}
                onChange={(e) => {
                  const id = e.target.value;
                  if (id)
                    void run("Loading your plan…", async () =>
                      applyPlan(await api<Plan>(`/plans/${id}`)),
                    );
                }}
              >
                <option value="">Choose a plan</option>
                {history.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.goal} · {statusNames[item.status]}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
        <div className="page">
          <ol className="steps" aria-label="Planning steps">
            {["Goal", "Tasks", "Compare", "Confirm"].map((label, i) => (
              <li
                key={label}
                aria-current={stage === i + 1 ? "step" : undefined}
                className={
                  stage > i + 1 ? "complete" : stage === i + 1 ? "current" : ""
                }
              >
                <span>{stage > i + 1 ? <Check size={13} /> : i + 1}</span>
                {label}
              </li>
            ))}
          </ol>
          {error && (
            <div className="error-banner" role="alert">
              <CircleAlert size={20} />
              <div>
                <strong>We could not complete this step</strong>
                <p>{error}</p>
                <button
                  disabled={!!busy}
                  onClick={() =>
                    void (plan
                      ? run("Reloading your plan…", async () =>
                          applyPlan(await api<Plan>(`/plans/${plan.id}`)),
                        )
                      : initialize())
                  }
                >
                  Reload saved plan
                </button>
              </div>
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                ×
              </button>
            </div>
          )}
          {!!busy && (
            <div className="progress-banner" role="status">
              <LoaderCircle className="spin" size={18} />
              {busy}
              <span>Your saved plan is safe</span>
            </div>
          )}

          {!plan && (
            <div className="intake-layout">
              <div className="intake-main">
                <div className="page-heading">
                  <span className="eyebrow">MAKE ROOM FOR WHAT MATTERS</span>
                  <h1>
                    Make time for
                    <br />
                    your goals.
                  </h1>
                  <p>
                    Start with something you want to accomplish.
                    <br className="desktop-only" />
                    Break it into steps and find a schedule that fits.
                  </p>
                </div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void create();
                  }}
                >
                  <fieldset
                    disabled={!!busy || !config}
                    className="form-fields"
                  >
                    <label className="goal-label">
                      What do you want to accomplish?
                      <textarea
                        className="goal-input"
                        required
                        minLength={3}
                        maxLength={2000}
                        rows={3}
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        placeholder="For example: build a portfolio with three projects and publish it in two weeks."
                      />
                    </label>
                    <div className="examples">
                      <span>Try a goal</span>
                      {[
                        "Build a portfolio",
                        "Prepare a 20-minute talk",
                        "Learn Python basics",
                      ].map((example) => (
                        <button
                          type="button"
                          key={example}
                          onClick={() =>
                            setGoal(`${example} in the next two weeks.`)
                          }
                        >
                          {example}
                          <Plus size={12} />
                        </button>
                      ))}
                    </div>
                    <PreferencesFields
                      value={preferences}
                      change={setPreferences}
                    />
                    <label>
                      Additional context{" "}
                      <span className="optional">Optional</span>
                      <textarea
                        rows={2}
                        value={context}
                        onChange={(e) => setContext(e.target.value)}
                        placeholder="Your progress so far, relevant experience, or anything to keep in mind…"
                      />
                    </label>
                    <div className="form-footer">
                      <p>
                        <CheckCircle2 size={15} />
                        Events are added only after you review and confirm.
                      </p>
                      <button className="button primary" type="submit">
                        Break down my goal <ArrowRight size={17} />
                      </button>
                    </div>
                  </fieldset>
                </form>
              </div>
              <aside className="intake-note">
                <span className="note-sun">
                  <Sunrise size={33} />
                </span>
                <span className="eyebrow">A LITTLE STRUCTURE, MORE SPACE</span>
                <h2>
                  A little structure.
                  <br />
                  More room for life.
                </h2>
                <p>
                  Turn a broad goal into practical steps that work with your
                  time and energy.
                </p>
                <div className="mini-schedule">
                  <div>
                    <span>09:00</span>
                    <i />
                    Focus on what matters
                  </div>
                  <div className="mini-break">
                    <span>10:00</span>
                    <i />
                    Take a break
                  </div>
                  <div>
                    <span>10:15</span>
                    <i />
                    Take the next step
                  </div>
                </div>
                <div className="note-footer">
                  Three options · Your choice · Your approval
                </div>
              </aside>
            </div>
          )}

          {plan && (
            <>
              <div className="plan-heading">
                <div>
                  <span className="eyebrow">
                    {taskView
                      ? "SHAPE YOUR PLAN"
                      : closed
                        ? "YOUR NEXT CHAPTER"
                        : "FIND YOUR RHYTHM"}
                  </span>
                  <h1>
                    {taskView
                      ? "Make the plan your own."
                      : closed
                        ? plan.status === "completed"
                          ? "Your time is set. Make it count."
                          : plan.status === "rejected"
                            ? "This plan is closed."
                            : "Pick up where you left off."
                        : "Find a rhythm that fits."}
                  </h1>
                  <p className="plan-goal">{plan.goal}</p>
                </div>
                <span className="saved-badge">
                  <CheckCircle2 size={14} />
                  {dirty ? "Unsaved changes" : `Saved · v${plan.revision}`}
                </span>
              </div>
              {taskView && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void generate();
                  }}
                >
                  <fieldset className="form-fields" disabled={!!busy}>
                    <div className="editor-layout">
                      <div>
                        <div className="section-caption">
                          <h2>
                            Your tasks <span>{tasks.length}</span>
                          </h2>
                          <p>
                            Edit task names, estimates, and prerequisites before
                            building schedules.
                          </p>
                        </div>
                        {config?.llm_provider === "mock" && (
                          <p className="mock-note">
                            These are example tasks. Adjust them to fit your
                            goal.
                          </p>
                        )}
                        <TaskEditor
                          tasks={tasks}
                          change={setTasks}
                          maxSession={preferences.max_session_minutes}
                        />
                        {!tasks.length && (
                          <div className="empty-state">
                            <Sparkles />
                            <h3>Your goal is saved</h3>
                            <p>
                              Continue to turn it into an editable task list.
                            </p>
                            <button
                              className="button primary"
                              type="button"
                              onClick={() =>
                                void run("Breaking down your goal…", async () =>
                                  applyPlan(
                                    await api<Plan>(
                                      `/plans/${plan.id}/decompose`,
                                      { revision: plan.revision },
                                    ),
                                  ),
                                )
                              }
                            >
                              Continue task breakdown
                            </button>
                          </div>
                        )}
                      </div>
                      <aside className="editor-aside panel">
                        <span className="eyebrow">PLAN SETTINGS</span>
                        <h2>Make space for your goal</h2>
                        <div className="time-total">
                          <strong>
                            {minutes(
                              tasks.reduce((n, t) => n + t.duration_minutes, 0),
                            )}
                          </strong>
                          <span>
                            Estimated focus time · {tasks.length} tasks
                          </span>
                        </div>
                        <PreferencesFields
                          value={preferences}
                          change={setPreferences}
                        />
                        <p className="small muted">
                          Estimates are a starting point. You can return to
                          adjust them.
                        </p>
                      </aside>
                    </div>
                    <div className="action-bar">
                      <p>
                        <Clock3 size={16} />
                        Saving your changes creates a new version.
                      </p>
                      <div>
                        {editing && (
                          <button
                            type="button"
                            className="button secondary"
                            onClick={() => {
                              setEditing(false);
                              setTasks(plan.tasks);
                              setPreferences(plan.preferences);
                            }}
                          >
                            Cancel edits
                          </button>
                        )}
                        <button
                          className="button primary"
                          type="submit"
                          disabled={!tasks.length}
                        >
                          Save and build schedules <ArrowRight size={17} />
                        </button>
                      </div>
                    </div>
                  </fieldset>
                </form>
              )}

              {!taskView && !closed && candidate && (
                <>
                  {plan.status === "needs_review" && (
                    <div className="warning-banner" role="alert">
                      <CircleAlert size={20} />
                      <div>
                        <strong>
                          Your calendar has changed. Please review again.
                        </strong>
                        <p>
                          The latest check is saved. Edit your plan or
                          acknowledge each issue in the summary to continue.
                        </p>
                      </div>
                    </div>
                  )}
                  {identical && (
                    <p className="info-note">
                      The current prerequisites and free time lead all three
                      strategies to the same schedule.
                    </p>
                  )}
                  <div className="review-layout">
                    <div className="candidate-column">
                      <div className="section-caption">
                        <h2>Compare your options</h2>
                        <p>
                          Select an option to see how your schedule changes.
                        </p>
                      </div>
                      <div
                        className="candidate-list"
                        role="group"
                        aria-label="Choose a schedule"
                      >
                        {plan.candidates.map((c, i) => {
                          const Icon = icons[c.id];
                          const selectedCard = c.id === selected;
                          return (
                            <button
                              className={`candidate-card ${selectedCard ? "selected" : ""}`}
                              key={c.id}
                              disabled={
                                !!busy ||
                                (!!plan.approval &&
                                  c.id !== plan.selected_candidate)
                              }
                              aria-pressed={selectedCard}
                              onClick={() => setSelected(c.id)}
                            >
                              <div className="candidate-title">
                                <span className={`strategy-icon strategy-${i}`}>
                                  <Icon size={21} />
                                </span>
                                <div>
                                  <small>OPTION 0{i + 1}</small>
                                  <h3>{strategyNames[c.id]}</h3>
                                </div>
                                <span className="radio-indicator">
                                  {selectedCard && <Check size={13} />}
                                </span>
                              </div>
                              <p>{c.explanation}</p>
                              <div className="candidate-metrics">
                                <span>
                                  <strong>
                                    {c.metrics.scheduled_tasks}/
                                    {c.metrics.total_tasks}
                                  </strong>
                                  Tasks scheduled
                                </span>
                                <span>
                                  <strong>
                                    {c.metrics.workdays}{" "}
                                    {c.metrics.workdays === 1 ? "day" : "days"}
                                  </strong>
                                  Work spread
                                </span>
                                <span>
                                  <strong>
                                    {c.metrics.energy_alignment === null
                                      ? "—"
                                      : `${c.metrics.energy_alignment}%`}
                                  </strong>
                                  Energy fit
                                </span>
                              </div>
                              <div
                                className={`candidate-bottom ${c.validation.passed ? "" : "has-issues"}`}
                              >
                                <span>
                                  {c.validation.passed ? (
                                    <CheckCircle2 size={14} />
                                  ) : (
                                    <CircleAlert size={14} />
                                  )}{" "}
                                  {c.validation.passed
                                    ? "Checks passed"
                                    : `${c.validation.violations.length} to review`}
                                </span>
                                <span>
                                  {c.metrics.finishes_at
                                    ? `Done ${dateLabel(c.metrics.finishes_at, plan.preferences.timezone)}`
                                    : "No events scheduled"}
                                </span>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                      <p className="rules-note">
                        Metrics come from the schedule. Energy fit weighs task
                        intensity against your preferences.
                      </p>
                    </div>
                    <SchedulePreview plan={plan} candidate={candidate} />
                  </div>
                  {!!candidate.validation.violations.length && (
                    <div className="issues panel">
                      <h2>
                        <CircleAlert size={20} />A few things to review
                      </h2>
                      {candidate.validation.violations.map((v) => (
                        <div key={v.id}>
                          <strong>{v.event_name}</strong>
                          <span>{violationText(v)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="action-bar">
                    <div className="action-summary">
                      <span>
                        Selected <strong>{strategyNames[candidate.id]}</strong>
                      </span>
                      <small>
                        {candidate.events.length} events ·{" "}
                        {minutes(candidate.metrics.scheduled_minutes)}
                      </small>
                    </div>
                    <div>
                      {!plan.approval && (
                        <>
                          <button
                            className="text-button"
                            disabled={!!busy}
                            onClick={() =>
                              void run("Closing your plan…", async () =>
                                applyPlan(
                                  await api<Plan>(`/plans/${plan.id}/reject`, {
                                    revision: plan.revision,
                                  }),
                                ),
                              )
                            }
                          >
                            Reject plan
                          </button>
                          <button
                            className="button secondary"
                            disabled={!!busy}
                            onClick={() => setEditing(true)}
                          >
                            <ArrowLeft size={16} />
                            Edit tasks
                          </button>
                        </>
                      )}
                      <Confirmation
                        key={`${plan.id}-${plan.revision}-${candidate.id}`}
                        plan={plan}
                        candidate={candidate}
                        busy={!!busy}
                        onApprove={(ids) => approve(candidate, ids)}
                      />
                    </div>
                  </div>
                </>
              )}

              {closed && (
                <section className="completion panel">
                  <div
                    className={`completion-icon ${plan.status === "completed" ? "" : "pending"}`}
                  >
                    {plan.status === "completed" ? (
                      <CheckCircle2 size={34} />
                    ) : plan.status === "rejected" ? (
                      <Leaf size={34} />
                    ) : (
                      <CircleAlert size={34} />
                    )}
                  </div>
                  <h2>
                    {plan.status === "completed"
                      ? `${plan.write_results.length} events added`
                      : plan.status === "rejected"
                        ? "No calendar events were added"
                        : "Your event progress is saved"}
                  </h2>
                  <p>
                    {plan.status === "completed"
                      ? plan.calendar_mode === "mock"
                        ? "Saved to your local demo calendar. Google Calendar has not changed."
                        : `Added to ${plan.calendar_id}.`
                      : plan.status === "rejected"
                        ? "Keep this record or start with a new goal."
                        : "Retry checks the calendar first and adds only the missing events."}
                  </p>
                  <div className="result-list">
                    {plan.status !== "rejected" &&
                      candidate?.events.map((event) => {
                        const result = plan.write_results.find(
                          (r) => r.task_id === event.task_id,
                        );
                        return (
                          <div key={event.id}>
                            <span>
                              {result?.status === "confirmed" ? (
                                <CheckCircle2 size={18} />
                              ) : (
                                <Clock3 size={18} />
                              )}
                              <strong>{event.name}</strong>
                            </span>
                            <span>
                              {result?.status === "confirmed"
                                ? "Added and confirmed"
                                : result?.status === "unknown"
                                  ? "Awaiting verification"
                                  : "Not yet added"}
                              {result?.response?.htmlLink && (
                                <a
                                  href={result.response.htmlLink}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Open calendar ↗
                                </a>
                              )}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                  <div className="completion-actions">
                    {candidate &&
                      ["partial", "writing"].includes(plan.status) && (
                        <button
                          disabled={!!busy}
                          className="button primary"
                          onClick={() =>
                            void approve(
                              candidate,
                              candidate.validation.violations.map((v) => v.id),
                            )
                          }
                        >
                          <RotateCcw size={17} />
                          Verify and continue
                        </button>
                      )}
                    <button
                      className="button secondary"
                      onClick={newPlan}
                      disabled={!!busy}
                    >
                      <Plus size={17} />
                      Start a new plan
                    </button>
                  </div>
                </section>
              )}
            </>
          )}
          <footer className="page-footer">
            <span>Calendar Planning Agent · Make time for your goals.</span>
            <span>
              {config?.calendar_mode === "mock"
                ? "Demo calendar · No changes to Google Calendar"
                : "Local workspace · Only approved events are added"}
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
