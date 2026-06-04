import { API_BASE, extractErrorDetail } from "./shared";

export type ScheduleType = "cron" | "interval" | "at";
export type ScheduleMethod = "invoke" | "stream" | "batch" | "abatch" | "ainvoke" | "astream";
export type JitterDistribution = "uniform" | "normal" | "triangular";
export type Misfire = "skip" | "fire_now" | "coalesce";
export type OverlapPolicy = "skip" | "queue" | "replace";
export type RetryBackoff = "constant" | "linear" | "exponential";

export interface ScheduleConfig {
  schedule_type: ScheduleType;
  cron_expression?: string | null;
  interval_seconds?: number | null;
  fire_at?: string | null;
  tz: string;
  jitter_min_seconds: number;
  jitter_max_seconds: number;
  jitter_distribution: JitterDistribution;
  jitter_align_seconds?: number | null;
  jitter_seed?: number | null;
  jitter_skip_if_overruns_next: boolean;
  method: ScheduleMethod;
  /**
   * Inline prompt text. When set, this is the message every fire sends —
   * mirrors what the user typed into the composer's textarea while in
   * Schedule mode. Takes precedence over prompt_id.
   */
  prompt_text?: string | null;
  prompt_id?: string | null;
  misfire: Misfire;
  overlap_policy: OverlapPolicy;
  max_overlap: number;
  max_runs?: number | null;
  end_at?: string | null;
  retry_max_attempts: number;
  retry_backoff: RetryBackoff;
  retry_base_seconds: number;
  retry_factor: number;
  retry_max_delay_seconds?: number | null;
  name?: string | null;
}

export interface ScheduleRunSummary {
  fire_id: string;
  scheduled_at: string;
  fired_at: string | null;
  finished_at: string | null;
  status: string;
  attempt: number;
  jitter_offset_seconds: number;
  error: string | null;
  /**
   * Synthetic session id for this fire's event bridge. Set once the fire
   * has actually started executing (via the schedule manager's on_fire
   * callback). The frontend uses this to subscribe to the fire's chat-style
   * SSE stream at /api/schedules/{appId}/fires/{fire_id}/events.
   */
  event_session_id: string | null;
}

export interface ScheduleJobSummary {
  job_id: string;
  app_id: string;
  name: string;
  config: ScheduleConfig;
  is_running: boolean;
  is_paused: boolean;
  is_done: boolean;
  fire_count: number;
  success_count: number;
  failure_count: number;
  skip_count: number;
  next_run_at: string | null;
  upcoming: string[];
  history: ScheduleRunSummary[];
}

export const DEFAULT_SCHEDULE_CONFIG: ScheduleConfig = {
  schedule_type: "cron",
  cron_expression: "*/5 * * * *",
  interval_seconds: 60,
  fire_at: null,
  tz: "UTC",
  jitter_min_seconds: 0,
  jitter_max_seconds: 30,
  jitter_distribution: "uniform",
  jitter_align_seconds: null,
  jitter_seed: null,
  jitter_skip_if_overruns_next: true,
  method: "stream",
  prompt_text: null,
  prompt_id: null,
  misfire: "coalesce",
  overlap_policy: "skip",
  max_overlap: 1,
  max_runs: null,
  end_at: null,
  retry_max_attempts: 1,
  retry_backoff: "constant",
  retry_base_seconds: 5,
  retry_factor: 2,
  retry_max_delay_seconds: 600,
  name: null,
};

async function ensureOk(res: Response, fallback: string): Promise<void> {
  if (!res.ok) {
    const detail = await extractErrorDetail(res, fallback);
    throw new Error(detail);
  }
}

async function listSchedules(): Promise<ScheduleJobSummary[]> {
  const res = await fetch(`${API_BASE}/schedules`);
  await ensureOk(res, "Failed to list schedules");
  return res.json();
}

export async function getSchedule(appId: string): Promise<ScheduleJobSummary | null> {
  const schedules = await listSchedules();
  return schedules.find((schedule) => schedule.app_id === appId) ?? null;
}

export async function upsertSchedule(
  appId: string,
  config: ScheduleConfig,
): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${appId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  await ensureOk(res, `Failed to start schedule for ${appId}`);
  return res.json();
}

export async function stopSchedule(appId: string, drain = true): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${appId}/stop?drain=${drain}`, {
    method: "POST",
  });
  await ensureOk(res, `Failed to stop schedule for ${appId}`);
  return res.json();
}

export async function pauseSchedule(appId: string): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${appId}/pause`, { method: "POST" });
  await ensureOk(res, `Failed to pause schedule for ${appId}`);
  return res.json();
}

export async function resumeSchedule(appId: string): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${appId}/resume`, { method: "POST" });
  await ensureOk(res, `Failed to resume schedule for ${appId}`);
  return res.json();
}

export async function triggerScheduleNow(appId: string): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${appId}/trigger`, { method: "POST" });
  await ensureOk(res, `Failed to trigger schedule for ${appId}`);
  return res.json();
}

export async function deleteSchedule(appId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/schedules/${appId}`, { method: "DELETE" });
  if (res.status === 204) return;
  await ensureOk(res, `Failed to delete schedule for ${appId}`);
}
