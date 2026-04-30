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
}

export interface ScheduleJobSummary {
  job_id: string;
  demo_id: string;
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
  method: "invoke",
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

export async function listSchedules(): Promise<ScheduleJobSummary[]> {
  const res = await fetch(`${API_BASE}/schedules`);
  await ensureOk(res, "Failed to list schedules");
  return res.json();
}

export async function getSchedule(demoId: string): Promise<ScheduleJobSummary | null> {
  const res = await fetch(`${API_BASE}/schedules/${demoId}`);
  if (res.status === 404) return null;
  await ensureOk(res, `Failed to load schedule ${demoId}`);
  return res.json();
}

export async function upsertSchedule(
  demoId: string,
  config: ScheduleConfig,
): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${demoId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  await ensureOk(res, `Failed to start schedule for ${demoId}`);
  return res.json();
}

export async function stopSchedule(demoId: string, drain = true): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${demoId}/stop?drain=${drain}`, {
    method: "POST",
  });
  await ensureOk(res, `Failed to stop schedule for ${demoId}`);
  return res.json();
}

export async function pauseSchedule(demoId: string): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${demoId}/pause`, { method: "POST" });
  await ensureOk(res, `Failed to pause schedule for ${demoId}`);
  return res.json();
}

export async function resumeSchedule(demoId: string): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${demoId}/resume`, { method: "POST" });
  await ensureOk(res, `Failed to resume schedule for ${demoId}`);
  return res.json();
}

export async function triggerScheduleNow(demoId: string): Promise<ScheduleJobSummary> {
  const res = await fetch(`${API_BASE}/schedules/${demoId}/trigger`, { method: "POST" });
  await ensureOk(res, `Failed to trigger schedule for ${demoId}`);
  return res.json();
}

export async function deleteSchedule(demoId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/schedules/${demoId}`, { method: "DELETE" });
  if (res.status === 204) return;
  await ensureOk(res, `Failed to delete schedule for ${demoId}`);
}
