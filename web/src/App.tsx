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
      setError(e instanceof Error ? e.message : "操作未完成，請重試。");
    } finally {
      setBusy("");
    }
  }
  async function initialize() {
    await run("正在讀取工作區…", async () => {
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
    await run("正在拆解目標，整理可編輯的任務…", async () => {
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
    await run("正在讀取可用時間、建立方案並檢查限制…", async () => {
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
    });
  }
  async function approve(candidate: Candidate, ids: string[]) {
    if (!plan) return;
    await run("正在核對日曆並記錄每筆新增結果…", async () => {
      const result = await api<Plan>(`/plans/${plan.id}/approve`, {
        revision: plan.revision,
        candidate_id: candidate.id,
        snapshot_hash: candidate.snapshot_hash,
        acknowledged_violation_ids: ids,
      });
      applyPlan(result);
      setSelected(candidate.id);
    });
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
            日序<small>CALENDAR PLANNING</small>
          </span>
        </a>
        <button className="button new-plan" onClick={newPlan} disabled={!!busy}>
          <Plus size={18} />
          新的規劃
        </button>
        <div className="sidebar-label">
          你的計畫 <span>{history.length}</span>
        </div>
        <nav className="plan-history" aria-label="已保存的計畫">
          {history.map((item) => (
            <button
              key={item.id}
              className={item.id === plan?.id ? "active" : ""}
              disabled={!!busy}
              onClick={() =>
                void run("正在讀取計畫…", async () =>
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
              把下一個想完成的目標
              <br />
              留一點時間給它。
            </p>
          )}
        </nav>
        <div className="sidebar-footer">
          <Leaf size={18} />
          <span>
            給重要的事，留出空間。<small>計畫自動保存於此電腦</small>
          </span>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <span className="breadcrumb">
            工作區 <span>/</span> {plan ? "我的規劃" : "開始新的規劃"}
          </span>
          <div className="connection">
            <i className={config ? "status-dot done" : "status-dot"} />
            {(plan?.calendar_mode || config?.calendar_mode) === "mock"
              ? "示範模式"
              : config
                ? "Google Calendar · 本機"
                : "連線中"}
            <span className="connection-zone">
              {plan?.preferences.timezone || config?.timezone}
            </span>
          </div>
        </header>
        {!!history.length && (
          <div className="mobile-history mobile-only">
            <label>
              開啟已保存的計畫
              <select
                value={plan?.id || ""}
                disabled={!!busy}
                onChange={(e) => {
                  const id = e.target.value;
                  if (id)
                    void run("正在讀取計畫…", async () =>
                      applyPlan(await api<Plan>(`/plans/${id}`)),
                    );
                }}
              >
                <option value="">選擇計畫</option>
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
          <ol className="steps" aria-label="規劃步驟">
            {["描述目標", "確認任務", "比較方案", "確認新增"].map(
              (label, i) => (
                <li
                  key={label}
                  aria-current={stage === i + 1 ? "step" : undefined}
                  className={
                    stage > i + 1
                      ? "complete"
                      : stage === i + 1
                        ? "current"
                        : ""
                  }
                >
                  <span>{stage > i + 1 ? <Check size={13} /> : i + 1}</span>
                  {label}
                </li>
              ),
            )}
          </ol>
          {error && (
            <div className="error-banner" role="alert">
              <CircleAlert size={20} />
              <div>
                <strong>這次操作未完成</strong>
                <p>{error}</p>
                <button
                  disabled={!!busy}
                  onClick={() =>
                    void (plan
                      ? run("重新讀取計畫…", async () =>
                          applyPlan(await api<Plan>(`/plans/${plan.id}`)),
                        )
                      : initialize())
                  }
                >
                  重新讀取已保存的內容
                </button>
              </div>
              <button
                className="icon-button"
                aria-label="關閉錯誤訊息"
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
              <span>你已保存的內容會保留</span>
            </div>
          )}

          {!plan && (
            <div className="intake-layout">
              <div className="intake-main">
                <div className="page-heading">
                  <span className="eyebrow">MAKE ROOM FOR WHAT MATTERS</span>
                  <h1>
                    讓目標，
                    <br />
                    找到時間。
                  </h1>
                  <p>
                    從一件想完成的事開始。一起拆解步驟，
                    <br className="desktop-only" />
                    找到適合你的安排。
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
                      你想完成什麼？
                      <textarea
                        className="goal-input"
                        required
                        minLength={3}
                        maxLength={2000}
                        rows={3}
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        placeholder="例如：兩週內完成個人作品集，整理三個代表作並上線。"
                      />
                    </label>
                    <div className="examples">
                      <span>試試看</span>
                      {[
                        "完成個人作品集",
                        "準備一場 20 分鐘演講",
                        "學會 Python 基礎",
                      ].map((example) => (
                        <button
                          type="button"
                          key={example}
                          onClick={() => setGoal(`在兩週內${example}。`)}
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
                      補充背景 <span className="optional">選填</span>
                      <textarea
                        rows={2}
                        value={context}
                        onChange={(e) => setContext(e.target.value)}
                        placeholder="目前的進度、已具備的能力，或需要特別考慮的事…"
                      />
                    </label>
                    <div className="form-footer">
                      <p>
                        <CheckCircle2 size={15} />
                        選定方案並確認後，才會新增事件。
                      </p>
                      <button className="button primary" type="submit">
                        拆解我的目標 <ArrowRight size={17} />
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
                  好的安排，
                  <br />
                  也留得下生活。
                </h2>
                <p>
                  把模糊的目標拆成可執行的小步驟，讓進度與你的時間、精力一起前進。
                </p>
                <div className="mini-schedule">
                  <div>
                    <span>09:00</span>
                    <i />
                    專注一件重要的事
                  </div>
                  <div className="mini-break">
                    <span>10:00</span>
                    <i />
                    休息一下
                  </div>
                  <div>
                    <span>10:15</span>
                    <i />
                    再往前一步
                  </div>
                </div>
                <div className="note-footer">
                  三種安排 · 自由選擇 · 由你確認
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
                      ? "先把步驟，調整成你的樣子。"
                      : closed
                        ? plan.status === "completed"
                          ? "時間已留好，開始吧。"
                          : plan.status === "rejected"
                            ? "這份計畫已結束。"
                            : "接續完成你的安排。"
                        : "選一個適合你的節奏。"}
                  </h1>
                  <p className="plan-goal">{plan.goal}</p>
                </div>
                <span className="saved-badge">
                  <CheckCircle2 size={14} />
                  {dirty ? "有未儲存的修改" : `已保存 · v${plan.revision}`}
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
                            任務清單 <span>{tasks.length}</span>
                          </h2>
                          <p>修改名稱、估時與前置任務。完成後再建立方案。</p>
                        </div>
                        {config?.llm_provider === "mock" && (
                          <p className="mock-note">
                            目前使用固定的示範任務，請依照目標調整內容。
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
                            <h3>目標已保存</h3>
                            <p>繼續拆解，產生可以編輯的任務清單。</p>
                            <button
                              className="button primary"
                              type="button"
                              onClick={() =>
                                void run("正在拆解目標…", async () =>
                                  applyPlan(
                                    await api<Plan>(
                                      `/plans/${plan.id}/decompose`,
                                      { revision: plan.revision },
                                    ),
                                  ),
                                )
                              }
                            >
                              繼續拆解目標
                            </button>
                          </div>
                        )}
                      </div>
                      <aside className="editor-aside panel">
                        <span className="eyebrow">PLAN SETTINGS</span>
                        <h2>為目標留多少時間？</h2>
                        <div className="time-total">
                          <strong>
                            {minutes(
                              tasks.reduce((n, t) => n + t.duration_minutes, 0),
                            )}
                          </strong>
                          <span>預計專注時間 · {tasks.length} 項任務</span>
                        </div>
                        <PreferencesFields
                          value={preferences}
                          change={setPreferences}
                        />
                        <p className="small muted">
                          估時是起點。產生方案後，仍可回來調整。
                        </p>
                      </aside>
                    </div>
                    <div className="action-bar">
                      <p>
                        <Clock3 size={16} />
                        修改並保存後，會建立新版本。
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
                            取消修改
                          </button>
                        )}
                        <button
                          className="button primary"
                          type="submit"
                          disabled={!tasks.length}
                        >
                          儲存並建立方案 <ArrowRight size={17} />
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
                        <strong>日曆有新的變化，需要重新檢視。</strong>
                        <p>
                          已保存最新檢查結果。請調整計畫，或在摘要中逐項確認限制後再繼續。
                        </p>
                      </div>
                    </div>
                  )}
                  {identical && (
                    <p className="info-note">
                      目前的任務依賴與可用時段，讓三種策略得到相同安排。
                    </p>
                  )}
                  <div className="review-layout">
                    <div className="candidate-column">
                      <div className="section-caption">
                        <h2>比較三種安排</h2>
                        <p>時間表會隨選擇更新，方便比較不同安排。</p>
                      </div>
                      <div
                        className="candidate-list"
                        role="group"
                        aria-label="選擇排程方案"
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
                                  <small>方案 0{i + 1}</small>
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
                                  任務排入
                                </span>
                                <span>
                                  <strong>{c.metrics.workdays} 天</strong>
                                  工作分布
                                </span>
                                <span>
                                  <strong>
                                    {c.metrics.energy_alignment === null
                                      ? "—"
                                      : `${c.metrics.energy_alignment}%`}
                                  </strong>
                                  精力配合
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
                                    ? "檢查通過"
                                    : `${c.validation.violations.length} 項待確認`}
                                </span>
                                <span>
                                  {c.metrics.finishes_at
                                    ? `${dateLabel(c.metrics.finishes_at, plan.preferences.timezone)}完成`
                                    : "尚無安排"}
                                </span>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                      <p className="rules-note">
                        指標由實際排程計算。精力配合依任務強度與時段偏好加權，並非模型評分。
                      </p>
                    </div>
                    <SchedulePreview plan={plan} candidate={candidate} />
                  </div>
                  {!!candidate.validation.violations.length && (
                    <div className="issues panel">
                      <h2>
                        <CircleAlert size={20} />
                        有幾件事需要留意
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
                        已選擇 <strong>{strategyNames[candidate.id]}</strong>
                      </span>
                      <small>
                        {candidate.events.length} 個事件 ·{" "}
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
                              void run("正在結束計畫…", async () =>
                                applyPlan(
                                  await api<Plan>(`/plans/${plan.id}/reject`, {
                                    revision: plan.revision,
                                  }),
                                ),
                              )
                            }
                          >
                            不採用
                          </button>
                          <button
                            className="button secondary"
                            disabled={!!busy}
                            onClick={() => setEditing(true)}
                          >
                            <ArrowLeft size={16} />
                            調整任務
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
                      ? `已新增 ${plan.write_results.length} 個事件`
                      : plan.status === "rejected"
                        ? "沒有新增任何日曆事件"
                        : "已保存每一筆寫入進度"}
                  </h2>
                  <p>
                    {plan.status === "completed"
                      ? plan.calendar_mode === "mock"
                        ? "已儲存到本機示範日曆，Google Calendar 沒有變更。"
                        : `已新增至 ${plan.calendar_id}。`
                      : plan.status === "rejected"
                        ? "可以保留這份紀錄，或從新的目標開始。"
                        : "重試時會先核對日曆，只補建尚未完成的事件。"}
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
                                ? "已確認新增"
                                : result?.status === "unknown"
                                  ? "待核對"
                                  : "尚未寫入"}
                              {result?.response?.htmlLink && (
                                <a
                                  href={result.response.htmlLink}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  開啟日曆 ↗
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
                          核對並繼續新增
                        </button>
                      )}
                    <button
                      className="button secondary"
                      onClick={newPlan}
                      disabled={!!busy}
                    >
                      <Plus size={17} />
                      開始新的規劃
                    </button>
                  </div>
                </section>
              )}
            </>
          )}
          <footer className="page-footer">
            <span>日序 · 一步一步，把想法放進生活。</span>
            <span>
              {config?.calendar_mode === "mock"
                ? "示範日曆 · 不會寫入 Google Calendar"
                : "本機工作區 · 只新增已確認的事件"}
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
