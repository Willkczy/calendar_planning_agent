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
  deadline_first: "Finish early",
  min_fragmentation: "Group work",
  energy_aware: "Match energy",
};
export const statusNames = {
  draft: "Task draft",
  review: "Ready to review",
  needs_review: "Needs review",
  writing: "Awaiting verification",
  partial: "Partially complete",
  completed: "Completed",
  rejected: "Closed",
};
export const minutes = (n: number) =>
  n >= 60
    ? `${Math.floor(n / 60)} hr${n % 60 ? ` ${n % 60} min` : ""}`
    : `${n} min`;
export function dateLabel(value: string, tz: string, withTime = false) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    month: "short",
    day: "numeric",
    weekday: "short",
    ...(withTime ? { hour: "2-digit", minute: "2-digit", hour12: false } : {}),
  }).format(new Date(value));
}
export function clock(value: string, tz: string) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}
export function violationText(v: Violation) {
  const messages: Record<string, string> = {
    UNSCHEDULED: "This task could not fit in the available time",
    DEPENDENCY: "A prerequisite is missing or scheduled too late",
    OVERLAP: "Overlaps an existing calendar event",
    SELF_OVERLAP: "Overlaps another proposed task",
    OUT_OF_HOURS: "Outside your preferred working hours",
    NON_WORKDAY: "Falls on a non-working day",
    DEADLINE_EXCEEDED: "Ends after the deadline",
    SESSION_TOO_LONG: "Exceeds your maximum session length",
    BREAK_TOO_SHORT: "Not enough break time between sessions",
    IN_PAST: "The start time has passed; consider editing the plan",
    DURATION_MISMATCH: "Scheduled duration differs from the task estimate",
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
          Deadline
          <input
            type="date"
            required
            value={value.deadline}
            onChange={(e) => set("deadline", e.target.value)}
          />
        </label>
        <label>
          Time zone
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
          Work hours and energy{" "}
          <span>
            {value.work_start}–{value.work_end} · {value.break_minutes} min
            breaks
          </span>
        </summary>
        <div className="field-grid">
          <label>
            Start time
            <input
              required
              type="time"
              value={value.work_start}
              onChange={(e) => set("work_start", e.target.value)}
            />
          </label>
          <label>
            End time
            <input
              required
              type="time"
              value={value.work_end}
              onChange={(e) => set("work_end", e.target.value)}
            />
          </label>
          <label>
            Max session (minutes)
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
            Breaks (minutes)
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
          <legend>Working days</legend>
          {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day, i) => (
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
              <span>{day}</span>
            </label>
          ))}
        </fieldset>
        <div className="field-grid energy-fields">
          {(["morning", "afternoon", "evening"] as const).map((period, i) => (
            <label key={period}>
              {["Morning energy", "Afternoon energy", "Evening energy"][i]}
              <select
                value={value.energy_levels[period]}
                onChange={(e) =>
                  set("energy_levels", {
                    ...value.energy_levels,
                    [period]: e.target.value as Level,
                  })
                }
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
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
              Task {i + 1} name
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
              Task {i + 1} description
            </label>
            <textarea
              id={`description-${task.id}`}
              rows={2}
              value={task.description}
              onChange={(e) => update(i, { description: e.target.value })}
            />
            <details className="dependencies">
              <summary>
                Prerequisites{" "}
                <span>
                  {task.depends_on.length
                    ? `${task.depends_on.length}`
                    : "None"}
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
              Minutes
              <input
                aria-label={`Task ${i + 1} estimate (minutes)`}
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
              Focus level
              <select
                value={task.complexity}
                onChange={(e) =>
                  update(i, { complexity: e.target.value as Level })
                }
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <button
              type="button"
              className="icon-button"
              aria-label={`Remove task ${i + 1}`}
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
              <small className="warning-text">Over session limit</small>
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
              name: "New task",
              description: "",
              duration_minutes: 30,
              complexity: "medium",
              depends_on: [],
            },
          ])
        }
      >
        <Plus size={16} />
        Add task
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
                  Draft ·{" "}
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
          <h3>No tasks fit yet</h3>
          <p>
            Adjust your deadline, work hours, or task estimates, then build
            schedules again.
          </p>
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
          <h2>Your time, mapped out</h2>
        </div>
        <div className="segmented desktop-only" aria-label="Schedule view">
          <button
            aria-pressed={view === "agenda"}
            onClick={() => setView("agenda")}
          >
            <List size={16} />
            Agenda
          </button>
          <button
            aria-pressed={view === "week"}
            onClick={() => setView("week")}
          >
            <CalendarDays size={16} />
            Week
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
          Draft <i className="legend-dot busy-dot" />
          Busy
        </span>
      </div>
      <div className={view === "week" ? "mobile-only" : ""}>
        <Agenda plan={plan} candidate={candidate} />
      </div>
      {view === "week" && (
        <div className="calendar-shell desktop-only">
          <Suspense
            fallback={<p className="calendar-loading">Loading week view…</p>}
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
          Review events <ArrowRight size={17} />
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
              aria-label="Close summary"
              disabled={busy}
            >
              <X size={20} />
            </button>
          </Dialog.Close>
          <span className="eyebrow">ONE LAST LOOK</span>
          <Dialog.Title>Confirm your schedule</Dialog.Title>
          <Dialog.Description>
            Add {candidate.events.length} events to{" "}
            {plan.calendar_mode === "mock"
              ? "the demo calendar"
              : plan.calendar_id}
            .{" "}
            {plan.calendar_mode === "mock"
              ? "Google Calendar will not be changed."
              : "Confirming will add these events to your Google Calendar."}
          </Dialog.Description>
          <div className="confirmation-stats">
            <span>
              Schedule<strong>{strategyNames[candidate.id]}</strong>
            </span>
            <span>
              Focus time
              <strong>{minutes(candidate.metrics.scheduled_minutes)}</strong>
            </span>
            <span>
              Version<strong>v{plan.revision}</strong>
            </span>
          </div>
          <p className="muted small">
            All times are in {plan.preferences.timezone}.
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
              <strong>Please acknowledge each issue</strong>
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
                    {issue.event_name}: {violationText(issue)}. I understand and
                    still want to add the scheduled events.
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
              ? "Checking calendar and adding events…"
              : plan.calendar_mode === "mock"
                ? "Add to demo calendar"
                : "Add to Google Calendar"}
          </button>
          <p className="small muted">
            We check your calendar again before adding events. New conflicts
            return you to review.
          </p>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
