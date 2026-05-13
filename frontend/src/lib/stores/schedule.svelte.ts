import {
  DEFAULT_SCHEDULE_CONFIG,
  deleteSchedule,
  getSchedule,
  pauseSchedule,
  resumeSchedule,
  stopSchedule,
  triggerScheduleNow,
  upsertSchedule,
  type ScheduleConfig,
  type ScheduleJobSummary,
  type ScheduleRunSummary,
} from "$lib/api_client/schedules";
import { API_BASE } from "$lib/api_client/shared";

// MARK: - Per-app store registry

/**
 * One reactive store per app so the inspector tab and the composer can
 * share state (summary, config, busy, errors) without round-tripping
 * through the page-level component. Stores are cached so two consumers
 * get the same instance.
 */

interface ScheduleStore {
  /** Last known summary from the backend. `null` while loading or once removed. */
  readonly summary: ScheduleJobSummary | null;
  /** Working copy of the config — the composer edits this in place. */
  readonly config: ScheduleConfig;
  setConfig: (next: ScheduleConfig) => void;
  /** True while a write action (start/pause/...) is in flight. */
  readonly busy: boolean;
  readonly lastError: string | null;
  clearError: () => void;
  /** True when a job exists for this app (running, paused, or done). */
  readonly hasJob: boolean;

  refresh: () => Promise<void>;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  trigger: () => Promise<void>;
  remove: () => Promise<void>;

  /** Stop polling and detach. Call when no consumers remain. */
  dispose: () => void;
}

interface InternalStore extends ScheduleStore {
  _refCount: number;
}

const stores = new Map<string, InternalStore>();

// Polling is reconciliation only. The server pushes
// `schedule_fire_started` / `_completed` / `_skipped` over a per-app SSE
// bridge, so countdown->running and running->done land instantly without
// touching this loop. Polling stays as a safety net for missed events
// (server restart, dropped SSE) and out-of-band changes (pause/resume from
// another tab).
const POLL_ACTIVE_MS = 5000;
const POLL_RUNNING_MS = 30000;
const POLL_PAUSED_MS = 30000;
const POLL_NO_SCHEDULE_MS = 30000;
const POLL_DONE_MS: number | null = null;

function pickInterval(summary: ScheduleJobSummary | null): number | null {
  if (summary === null) return POLL_NO_SCHEDULE_MS;
  if (summary.is_done) return POLL_DONE_MS;
  if (summary.is_paused) return POLL_PAUSED_MS;
  const hasActiveFire = summary.history.some(
    (run) => run.fired_at !== null && run.finished_at === null,
  );
  if (hasActiveFire) return POLL_ACTIVE_MS;
  return POLL_RUNNING_MS;
}

function createStore(appId: string): InternalStore {
  const state = $state({
    summary: null as ScheduleJobSummary | null,
    config: { ...DEFAULT_SCHEDULE_CONFIG } as ScheduleConfig,
    busy: false,
    lastError: null as string | null,
  });

  let pollHandle: ReturnType<typeof setTimeout> | null = null;
  let pushEs: EventSource | null = null;
  let disposed = false;

  function openPushStream(): void {
    if (pushEs || disposed) return;
    pushEs = new EventSource(`${API_BASE}/schedules/${encodeURIComponent(appId)}/events`);
    const handle = (type: string, e: MessageEvent<string>): void => {
      if (!e.data) return;
      try {
        const payload = JSON.parse(e.data) as { type?: string; data?: unknown };
        const eventType =
          type === "message" && typeof payload?.type === "string" && payload.type.trim()
            ? payload.type.trim()
            : type;
        const eventData = (payload?.data ?? payload) as Record<string, unknown>;
        handlePushEvent(eventType, eventData);
      } catch {
        /* malformed JSON — ignore; reconciliation poll will catch up */
      }
    };
    pushEs.addEventListener("message", (e: MessageEvent<string>) => handle("message", e));
    for (const name of [
      "schedule_fire_started",
      "schedule_fire_completed",
      "schedule_fire_skipped",
    ]) {
      pushEs.addEventListener(name, (e: MessageEvent<string>) => handle(name, e));
    }
  }

  // ``next_run_at`` is included on every push event so the upcoming-card
  // countdown rolls over the moment a fire transitions, instead of waiting
  // for the next reconciliation poll. Backend may send a string, ``null``
  // (no future fires — one-shot done, max_runs reached), or omit the key
  // entirely on older builds.
  function pickNextRunAt(current: string | null, data: Record<string, unknown>): string | null {
    if (!("next_run_at" in data)) return current;
    const next = data.next_run_at;
    if (typeof next === "string") return next;
    if (next === null) return null;
    return current;
  }

  function handlePushEvent(type: string, data: Record<string, unknown>): void {
    if (disposed) return;
    const fireId = data.fire_id;
    if (typeof fireId !== "string") return;
    const summary = state.summary;
    // No summary loaded yet — let the in-flight refresh() pick the fire up.
    // Inserting into a record we don't have would race the snapshot.
    if (!summary) return;

    if (type === "schedule_fire_started") {
      const eventSessionId =
        typeof data.event_session_id === "string" ? data.event_session_id : null;
      const scheduledAt =
        typeof data.scheduled_at === "string" ? data.scheduled_at : new Date().toISOString();
      const firedAt = typeof data.fired_at === "string" ? data.fired_at : new Date().toISOString();
      const attempt = typeof data.attempt === "number" ? data.attempt : 1;
      const existingIdx = summary.history.findIndex((r) => r.fire_id === fireId);
      if (existingIdx >= 0) {
        // Replay of a buffered event for a fire we already know about. If
        // it's already terminal, ignore — the snapshot wins. Otherwise
        // backfill event_session_id if it was missing.
        const existing = summary.history[existingIdx];
        if (existing.finished_at !== null) return;
        if (existing.event_session_id) return;
        const nextHistory = summary.history.map((r, i) =>
          i === existingIdx ? { ...r, event_session_id: eventSessionId } : r,
        );
        state.summary = { ...summary, history: nextHistory };
        return;
      }
      const newRecord: ScheduleRunSummary = {
        fire_id: fireId,
        scheduled_at: scheduledAt,
        fired_at: firedAt,
        finished_at: null,
        // deriveRunStatus keys off `fired_at && !finished_at` for the
        // running pill — this string is just for dev-tools readability.
        status: "running",
        attempt,
        jitter_offset_seconds: 0,
        error: null,
        event_session_id: eventSessionId,
      };
      state.summary = {
        ...summary,
        next_run_at: pickNextRunAt(summary.next_run_at, data),
        fire_count: summary.fire_count + 1,
        history: [...summary.history, newRecord],
      };
      // Active-fire branch in pickInterval applies now — re-evaluate so
      // the safety-net poll cadence tightens until completion.
      scheduleNextPoll();
      return;
    }

    if (type === "schedule_fire_completed") {
      const idx = summary.history.findIndex((r) => r.fire_id === fireId);
      if (idx < 0) return;
      const existing = summary.history[idx];
      // Already terminal — buffered replay; nothing to do.
      if (existing.finished_at !== null) return;
      const finishedAt =
        typeof data.finished_at === "string" ? data.finished_at : new Date().toISOString();
      const status = typeof data.status === "string" ? data.status : "succeeded";
      const error = typeof data.error === "string" ? data.error : null;
      const isSuccess = status === "succeeded" || status === "success" || status === "ok";
      const isFailure = status === "failed" || status === "error" || error !== null;
      const nextHistory = summary.history.map((r, i) =>
        i === idx ? { ...r, finished_at: finishedAt, status, error } : r,
      );
      state.summary = {
        ...summary,
        next_run_at: pickNextRunAt(summary.next_run_at, data),
        success_count: isSuccess ? summary.success_count + 1 : summary.success_count,
        failure_count: isFailure ? summary.failure_count + 1 : summary.failure_count,
        history: nextHistory,
      };
      scheduleNextPoll();
      return;
    }

    if (type === "schedule_fire_skipped") {
      const idx = summary.history.findIndex((r) => r.fire_id === fireId);
      if (idx >= 0) return; // already accounted for
      const scheduledAt =
        typeof data.scheduled_at === "string" ? data.scheduled_at : new Date().toISOString();
      const status = typeof data.status === "string" ? data.status : "skipped";
      const skipped: ScheduleRunSummary = {
        fire_id: fireId,
        scheduled_at: scheduledAt,
        fired_at: null,
        finished_at: scheduledAt,
        status,
        attempt: 1,
        jitter_offset_seconds: 0,
        error: null,
        event_session_id: null,
      };
      state.summary = {
        ...summary,
        next_run_at: pickNextRunAt(summary.next_run_at, data),
        skip_count: summary.skip_count + 1,
        history: [...summary.history, skipped],
      };
      return;
    }
  }

  function scheduleNextPoll(): void {
    if (pollHandle !== null) {
      clearTimeout(pollHandle);
      pollHandle = null;
    }
    if (disposed) return;
    const interval = pickInterval(state.summary);
    if (interval === null) return; // is_done — don't reschedule
    pollHandle = setTimeout(() => void refresh(), interval);
  }

  async function refresh(): Promise<void> {
    try {
      const next = await getSchedule(appId);
      state.summary = next;
      if (next) {
        // Mirror server config into the working copy so the inspector and
        // composer stay in sync after start/update.
        state.config = { ...state.config, ...next.config };
      }
    } catch (err) {
      state.lastError = err instanceof Error ? err.message : String(err);
    } finally {
      scheduleNextPoll();
    }
  }

  async function action<T>(fn: () => Promise<T>): Promise<T | null> {
    state.busy = true;
    state.lastError = null;
    try {
      return await fn();
    } catch (err) {
      state.lastError = err instanceof Error ? err.message : String(err);
      return null;
    } finally {
      state.busy = false;
    }
  }

  async function start(): Promise<void> {
    const next = await action(() => upsertSchedule(appId, state.config));
    if (next) state.summary = next;
    // Lifecycle action just changed state — re-evaluate the cadence so we
    // don't sit on the old (possibly null) timer while a new fire is about
    // to land.
    scheduleNextPoll();
  }

  async function stop(): Promise<void> {
    const next = await action(() => stopSchedule(appId, true));
    if (next) state.summary = next;
    scheduleNextPoll();
  }

  async function pause(): Promise<void> {
    const next = await action(() => pauseSchedule(appId));
    if (next) state.summary = next;
    scheduleNextPoll();
  }

  async function resume(): Promise<void> {
    const next = await action(() => resumeSchedule(appId));
    if (next) state.summary = next;
    scheduleNextPoll();
  }

  async function trigger(): Promise<void> {
    const next = await action(() => triggerScheduleNow(appId));
    if (next) state.summary = next;
    scheduleNextPoll();
  }

  async function remove(): Promise<void> {
    await action(() => deleteSchedule(appId));
    state.summary = null;
    state.config = { ...DEFAULT_SCHEDULE_CONFIG };
    scheduleNextPoll();
  }

  void refresh();
  openPushStream();

  return {
    _refCount: 0,
    get summary() {
      return state.summary;
    },
    get config() {
      return state.config;
    },
    setConfig(next: ScheduleConfig) {
      state.config = next;
    },
    get busy() {
      return state.busy;
    },
    get lastError() {
      return state.lastError;
    },
    clearError() {
      state.lastError = null;
    },
    get hasJob() {
      return state.summary !== null;
    },
    refresh,
    start,
    stop,
    pause,
    resume,
    trigger,
    remove,
    dispose() {
      disposed = true;
      if (pollHandle !== null) {
        clearTimeout(pollHandle);
        pollHandle = null;
      }
      if (pushEs !== null) {
        pushEs.close();
        pushEs = null;
      }
      stores.delete(appId);
    },
  };
}

/**
 * Reference-counted accessor. The first caller for an app creates the
 * store and starts polling; subsequent callers reuse it. When the last
 * caller releases via `dispose()`, polling stops.
 *
 * Cadence is state-aware (see ``pickInterval`` above): tight while a fire
 * is mid-flight, slow while idle/paused, off entirely once ``is_done`` —
 * a stopped schedule produces zero requests. Every consumer
 * (ScheduleTab, ScheduleRunsView, ChatPanel) shares this single poll
 * loop via the refcount; there's no second timer running anywhere.
 */
export function useSchedule(appId: string): ScheduleStore {
  let store = stores.get(appId);
  if (!store) {
    store = createStore(appId);
    stores.set(appId, store);
  }
  store._refCount += 1;

  const release = () => {
    if (!store) return;
    store._refCount -= 1;
    if (store._refCount <= 0) {
      store.dispose();
    }
  };

  return {
    get summary() {
      return store!.summary;
    },
    get config() {
      return store!.config;
    },
    setConfig: (next) => store!.setConfig(next),
    get busy() {
      return store!.busy;
    },
    get lastError() {
      return store!.lastError;
    },
    clearError: () => store!.clearError(),
    get hasJob() {
      return store!.hasJob;
    },
    refresh: () => store!.refresh(),
    start: () => store!.start(),
    stop: () => store!.stop(),
    pause: () => store!.pause(),
    resume: () => store!.resume(),
    trigger: () => store!.trigger(),
    remove: () => store!.remove(),
    dispose: release,
  };
}
