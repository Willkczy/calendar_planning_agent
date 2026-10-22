import { lazy, Suspense, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ArrowRight,
  CalendarDays,
  Check,
  Clock3,
  List,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import type {
  Candidate,
  Level,
  Plan,
  Preferences,
  Task,
  Violation,
} from "./types";
const Calendar = lazy(() => import("./Calendar"));

export const strategyNames = {
  deadline_first: "提早完成",
  min_fragmentation: "集中安排",
  energy_aware: "配合精力",
};
export const statusNames = {
  draft: "任務草稿",
  review: "等待確認",
  needs_review: "需要重新檢視",
  writing: "寫入待核對",
  partial: "部分完成",
  completed: "已完成",
  rejected: "已結束",
};
export const minutes = (n: number) =>
  n >= 60
    ? `${Math.floor(n / 60)} 小時${n % 60 ? ` ${n % 60} 分` : ""}`
    : `${n} 分鐘`;
export function dateLabel(value: string, tz: string, withTime = false) {
  return new Intl.DateTimeFormat("zh-TW", {
    timeZone: tz,
    month: "short",
    day: "numeric",
    weekday: "short",
    ...(withTime ? { hour: "2-digit", minute: "2-digit", hour12: false } : {}),
  }).format(new Date(value));
}
export function clock(value: string, tz: string) {
  return new Intl.DateTimeFormat("zh-TW", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}
export function violationText(v: Violation) {
  const messages: Record<string, string> = {
    UNSCHEDULED: "可用時間不足，這項任務尚未排入",
    DEPENDENCY: "前置任務尚未完成或順序有衝突",
    OVERLAP: "與日曆中的既有行程重疊",
    SELF_OVERLAP: "與另一項提案任務重疊",
    OUT_OF_HOURS: "超出偏好的工作時段",
    NON_WORKDAY: "安排在非工作日",
    DEADLINE_EXCEEDED: "超過截止時間",
    SESSION_TOO_LONG: "超過單次專注時間上限",
    BREAK_TOO_SHORT: "兩次工作之間的休息不足",
    IN_PAST: "開始時間已經過去，建議返回調整",
    DURATION_MISMATCH: "排定時間與任務估時不一致",
  };
  return messages[v.violation_type] || v.description;
}

export function PreferencesFields({
  value,
  change,
}: {
  value: Preferences;
  change: (p: Preferences) => void;
}) {
  const set = <K extends keyof Preferences>(key: K, val: Preferences[K]) =>
    change({ ...value, [key]: val });
  return (
    <div className="preferences">
      <div className="field-grid">
        <label>
          截止日期
          <input
            type="date"
            required
            value={value.deadline}
            onChange={(e) => set("deadline", e.target.value)}
          />
        </label>
        <label>
          時區
          <input
            required
            value={value.timezone}
            list="timezones"
            onChange={(e) => set("timezone", e.target.value)}
          />
          <datalist id="timezones">
            <option>America/New_York</option>
            <option>Asia/Taipei</option>
            <option>Asia/Tokyo</option>
            <option>Europe/London</option>
            <option>UTC</option>
          </datalist>
        </label>
      </div>
      <details className="preferences-details">
        <summary>
          工作時段與精力偏好{" "}
          <span>
            {value.work_start}–{value.work_end} · 休息 {value.break_minutes} 分
          </span>
        </summary>
        <div className="field-grid">
          <label>
            開始時間
            <input
              required
              type="time"
              value={value.work_start}
              onChange={(e) => set("work_start", e.target.value)}
            />
          </label>
          <label>
            結束時間
            <input
              required
              type="time"
              value={value.work_end}
              onChange={(e) => set("work_end", e.target.value)}
            />
          </label>
          <label>
            單次上限（分鐘）
            <input
              required
              type="number"
              min="15"
              max="480"
              value={value.max_session_minutes}
              onChange={(e) => set("max_session_minutes", +e.target.value)}
            />
          </label>
          <label>
            休息間隔（分鐘）
            <input
              required
              type="number"
              min="0"
              max="120"
              value={value.break_minutes}
              onChange={(e) => set("break_minutes", +e.target.value)}
            />
          </label>
        </div>
        <fieldset className="days">
          <legend>可安排的日子</legend>
          {["一", "二", "三", "四", "五", "六", "日"].map((day, i) => (
            <label key={i}>
              <input
                type="checkbox"
                checked={value.workdays.includes(i)}
                onChange={(e) =>
                  set(
                    "workdays",
                    e.target.checked
                      ? [...value.workdays, i].sort()
                      : value.workdays.filter((d) => d !== i),
                  )
                }
              />
              <span>週{day}</span>
            </label>
          ))}
        </fieldset>
        <div className="field-grid energy-fields">
          {(["morning", "afternoon", "evening"] as const).map((period, i) => (
            <label key={period}>
              {["上午精力", "下午精力", "晚間精力"][i]}
              <select
                value={value.energy_levels[period]}
                onChange={(e) =>
                  set("energy_levels", {
                    ...value.energy_levels,
                    [period]: e.target.value as Level,
                  })
                }
              >
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </select>
            </label>
          ))}
        </div>
      </details>
    </div>
  );
}

export function TaskEditor({
  tasks,
  change,
  maxSession,
}: {
  tasks: Task[];
  change: (t: Task[]) => void;
  maxSession: number;
}) {
  const update = (index: number, patch: Partial<Task>) =>
    change(
      tasks.map((task, i) => (i === index ? { ...task, ...patch } : task)),
    );
  return (
    <div className="task-list">
      {tasks.map((task, i) => (
        <article className="task-card" key={task.id}>
          <span className="task-number">{String(i + 1).padStart(2, "0")}</span>
          <div className="task-fields">
            <label className="sr-only" htmlFor={`name-${task.id}`}>
              任務 {i + 1} 名稱
            </label>
            <input
              className="task-name"
              id={`name-${task.id}`}
              required
              maxLength={200}
              value={task.name}
              onChange={(e) => update(i, { name: e.target.value })}
            />
            <label className="sr-only" htmlFor={`description-${task.id}`}>
              任務 {i + 1} 說明
            </label>
            <textarea
              id={`description-${task.id}`}
              rows={2}
              value={task.description}
              onChange={(e) => update(i, { description: e.target.value })}
            />
            <details className="dependencies">
              <summary>
                前置任務{" "}
                <span>
                  {task.depends_on.length
                    ? `${task.depends_on.length} 項`
                    : "無"}
                </span>
              </summary>
              <div>
                {tasks
                  .filter((t) => t.id !== task.id)
                  .map((other) => (
                    <label key={other.id}>
                      <input
                        type="checkbox"
                        checked={task.depends_on.includes(other.id)}
                        onChange={(e) =>
                          update(i, {
                            depends_on: e.target.checked
                              ? [...task.depends_on, other.id]
                              : task.depends_on.filter((id) => id !== other.id),
                          })
                        }
                      />
                      {other.name}
                    </label>
                  ))}
              </div>
            </details>
          </div>
          <div className="task-settings">
            <label>
              估計分鐘
              <input
                aria-label={`任務 ${i + 1} 估計分鐘`}
                required
                type="number"
                min="1"
                max="480"
                value={task.duration_minutes}
                onChange={(e) =>
                  update(i, { duration_minutes: +e.target.value })
                }
              />
            </label>
            <label>
              專注強度
              <select
                value={task.complexity}
                onChange={(e) =>
                  update(i, { complexity: e.target.value as Level })
                }
              >
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
              </select>
            </label>
            <button
              type="button"
              className="icon-button"
              aria-label={`移除任務 ${i + 1}`}
              onClick={() =>
                change(
                  tasks
                    .filter((t) => t.id !== task.id)
                    .map((t) => ({
                      ...t,
                      depends_on: t.depends_on.filter((id) => id !== task.id),
                    })),
                )
              }
            >
              <Trash2 size={15} />
            </button>
            {task.duration_minutes > maxSession && (
              <small className="warning-text">超過單次上限</small>
            )}
          </div>
        </article>
      ))}
      <button
        type="button"
        className="button secondary add-task"
        onClick={() =>
          change([
            ...tasks,
            {
              id: crypto.randomUUID(),
              name: "新的任務",
              description: "",
              duration_minutes: 30,
              complexity: "medium",
              depends_on: [],
            },
          ])
        }
      >
        <Plus size={16} />
        新增任務
      </button>
    </div>
  );
}

export function Agenda({
  plan,
  candidate,
}: {
  plan: Plan;
  candidate: Candidate;
}) {
  const tz = plan.preferences.timezone;
  const groups: Record<string, typeof candidate.events> = {};
  candidate.events.forEach((event) => {
    const key = dateLabel(event.start, tz);
    (groups[key] ||= []).push(event);
  });
  return (
    <div className="agenda">
      {Object.entries(groups).map(([day, events]) => (
        <section key={day} className="agenda-day">
          <h3>
            {day}
            <span>
              {minutes(
                events.reduce(
                  (sum, e) =>
                    sum + (Date.parse(e.end) - Date.parse(e.start)) / 60000,
                  0,
                ),
              )}
            </span>
          </h3>
          {events.map((event, i) => (
            <div className="agenda-event" key={event.id}>
              <div className="event-time">
                {clock(event.start, tz)}
                <small>{clock(event.end, tz)}</small>
              </div>
              <span className="timeline-dot" />
              <div className="event-copy">
                <strong>{event.name}</strong>
                <p>{event.description}</p>
                <span className="event-tag">
                  草稿 ·{" "}
                  {minutes(
                    (Date.parse(event.end) - Date.parse(event.start)) / 60000,
                  )}
                </span>
              </div>
            </div>
          ))}
        </section>
      ))}
      {!candidate.events.length && (
        <div className="empty-state">
          <CalendarDays />
          <h3>目前沒有可排入的時段</h3>
          <p>調整截止日期、工作時間或任務估時，再建立方案。</p>
        </div>
      )}
    </div>
  );
}

export function SchedulePreview({
  plan,
  candidate,
}: {
  plan: Plan;
  candidate: Candidate;
}) {
  const [view, setView] = useState("agenda");
  return (
    <section className="preview panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">YOUR SCHEDULE</span>
          <h2>看看時間怎麼安排</h2>
        </div>
        <div className="segmented desktop-only" aria-label="檢視方式">
          <button
            aria-pressed={view === "agenda"}
            onClick={() => setView("agenda")}
          >
            <List size={16} />
            議程
          </button>
          <button
            aria-pressed={view === "week"}
            onClick={() => setView("week")}
          >
            <CalendarDays size={16} />
            週曆
          </button>
        </div>
      </div>
      <div className="preview-meta">
        <span>
          <Clock3 size={14} />
          {plan.preferences.timezone}
        </span>
        <span>
          <i className="legend-dot" />
          草稿 <i className="legend-dot busy-dot" />
          既有行程
        </span>
      </div>
      <div className={view === "week" ? "mobile-only" : ""}>
        <Agenda plan={plan} candidate={candidate} />
      </div>
      {view === "week" && (
        <div className="calendar-shell desktop-only">
          <Suspense
            fallback={<p className="calendar-loading">正在載入週曆…</p>}
          >
            <Calendar
              key={`${plan.id}-${plan.revision}-${candidate.id}`}
              plan={plan}
              candidate={candidate}
            />
          </Suspense>
        </div>
      )}
    </section>
  );
}

export function Confirmation({
  plan,
  candidate,
  busy,
  onApprove,
}: {
  plan: Plan;
  candidate: Candidate;
  busy: boolean;
  onApprove: (ids: string[]) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [ack, setAck] = useState<string[]>([]);
  const issues = candidate.validation.violations;
  const ready = issues.every((issue) => ack.includes(issue.id));
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(value) => {
        if (!busy) {
          setOpen(value);
          setAck([]);
        }
      }}
    >
      <Dialog.Trigger asChild>
        <button
          className="button primary"
          disabled={busy || !candidate.events.length}
        >
          查看新增摘要 <ArrowRight size={17} />
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content
          className="dialog-content"
          onEscapeKeyDown={(e) => {
            if (busy) e.preventDefault();
          }}
          onPointerDownOutside={(e) => {
            if (busy) e.preventDefault();
          }}
        >
          <Dialog.Close asChild>
            <button
              className="icon-button dialog-close"
              aria-label="關閉摘要"
              disabled={busy}
            >
              <X size={20} />
            </button>
          </Dialog.Close>
          <span className="eyebrow">ONE LAST LOOK</span>
          <Dialog.Title>確認這份安排</Dialog.Title>
          <Dialog.Description>
            將新增 {candidate.events.length} 個事件到{" "}
            {plan.calendar_mode === "mock" ? "示範日曆" : plan.calendar_id}。
            {plan.calendar_mode === "mock"
              ? "這次操作不會變更 Google Calendar。"
              : "確認後會新增到你的 Google Calendar。"}
          </Dialog.Description>
          <div className="confirmation-stats">
            <span>
              方案<strong>{strategyNames[candidate.id]}</strong>
            </span>
            <span>
              專注時間
              <strong>{minutes(candidate.metrics.scheduled_minutes)}</strong>
            </span>
            <span>
              版本<strong>v{plan.revision}</strong>
            </span>
          </div>
          <p className="muted small">
            所有時間皆為 {plan.preferences.timezone}。
          </p>
          <div className="confirmation-events">
            {candidate.events.map((e) => (
              <div key={e.id}>
                <strong>{e.name}</strong>
                <span>
                  {dateLabel(e.start, plan.preferences.timezone, true)}–
                  {clock(e.end, plan.preferences.timezone)}
                </span>
              </div>
            ))}
          </div>
          {!!issues.length && (
            <div className="issue-list">
              <strong>請逐項確認尚待處理的限制</strong>
              {issues.map((issue) => (
                <label key={issue.id}>
                  <input
                    type="checkbox"
                    checked={ack.includes(issue.id)}
                    onChange={(e) =>
                      setAck(
                        e.target.checked
                          ? [...ack, issue.id]
                          : ack.filter((id) => id !== issue.id),
                      )
                    }
                  />
                  <span>
                    {issue.event_name}：{violationText(issue)}
                    。我了解並仍要新增已排入的事件。
                  </span>
                </label>
              ))}
            </div>
          )}
          <button
            className="button primary full"
            disabled={busy || !ready}
            onClick={async () => {
              await onApprove(ack);
              setOpen(false);
            }}
          >
            <Check size={17} />
            {busy
              ? "正在核對日曆與新增…"
              : plan.calendar_mode === "mock"
                ? "確認新增至示範日曆"
                : "確認新增至 Google Calendar"}
          </button>
          <p className="small muted">
            新增前會重新檢查日曆。新的衝突會回到方案頁，讓你重新檢視。
          </p>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
