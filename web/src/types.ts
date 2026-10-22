export type Level = "low" | "medium" | "high";
export type Strategy = "deadline_first" | "min_fragmentation" | "energy_aware";
export interface Preferences {
  deadline: string;
  timezone: string;
  work_start: string;
  work_end: string;
  workdays: number[];
  max_session_minutes: number;
  break_minutes: number;
  energy_levels: Record<"morning" | "afternoon" | "evening", Level>;
}
export interface Task {
  id: string;
  name: string;
  description: string;
  duration_minutes: number;
  complexity: Level;
  depends_on: string[];
}
export interface Event {
  id: string;
  task_id: string;
  name: string;
  description: string;
  start: string;
  end: string;
}
export interface Violation {
  id: string;
  task_id: string | null;
  event_name: string;
  violation_type: string;
  description: string;
}
export interface Candidate {
  id: Strategy;
  events: Event[];
  unscheduled: { task_id: string; name: string; reason: string }[];
  validation: { passed: boolean; violations: Violation[] };
  metrics: {
    scheduled_tasks: number;
    total_tasks: number;
    scheduled_minutes: number;
    total_minutes: number;
    workdays: number;
    finishes_at: string | null;
    energy_alignment: number | null;
  };
  explanation: string;
  explanation_source: "rules";
  snapshot_hash: string;
}
export type Status =
  | "draft"
  | "review"
  | "needs_review"
  | "writing"
  | "partial"
  | "completed"
  | "rejected";
export interface Plan {
  id: string;
  goal: string;
  context: string;
  revision: number;
  preferences: Preferences;
  status: Status;
  calendar_mode: "mock" | "live";
  calendar_id: string;
  tasks: Task[];
  candidates: Candidate[];
  busy_blocks: { start: string; end: string }[];
  calendar_snapshot_at: string | null;
  selected_candidate: Strategy | null;
  approval: { snapshot_hash: string } | null;
  write_results: {
    event_id: string;
    task_id: string;
    name: string;
    status: "unknown" | "confirmed";
    error: string | null;
    response: { htmlLink?: string } | null;
  }[];
}
export interface Config {
  calendar_mode: "mock" | "live";
  calendar_id: string;
  timezone: string;
  llm_provider: string;
}
export type PlanSummary = Pick<Plan, "id" | "goal" | "status" | "revision">;
