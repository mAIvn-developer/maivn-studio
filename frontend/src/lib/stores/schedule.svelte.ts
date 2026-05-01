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
} from "$lib/api_client/schedules";

// MARK: - Per-demo store registry

/**
 * One reactive store per demo so the inspector tab and the composer can
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
  /** True when a job exists for this demo (running, paused, or done). */
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

function createStore(demoId: string, pollIntervalMs: number): InternalStore {
  const state = $state({
    summary: null as ScheduleJobSummary | null,
    config: { ...DEFAULT_SCHEDULE_CONFIG } as ScheduleConfig,
    busy: false,
    lastError: null as string | null,
  });

  let pollHandle: ReturnType<typeof setInterval> | null = null;

  async function refresh(): Promise<void> {
    try {
      const next = await getSchedule(demoId);
      state.summary = next;
      if (next) {
        // Mirror server config into the working copy so the inspector and
        // composer stay in sync after start/update.
        state.config = { ...state.config, ...next.config };
      }
    } catch (err) {
      state.lastError = err instanceof Error ? err.message : String(err);
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
    const next = await action(() => upsertSchedule(demoId, state.config));
    if (next) state.summary = next;
  }

  async function stop(): Promise<void> {
    const next = await action(() => stopSchedule(demoId, true));
    if (next) state.summary = next;
  }

  async function pause(): Promise<void> {
    const next = await action(() => pauseSchedule(demoId));
    if (next) state.summary = next;
  }

  async function resume(): Promise<void> {
    const next = await action(() => resumeSchedule(demoId));
    if (next) state.summary = next;
  }

  async function trigger(): Promise<void> {
    const next = await action(() => triggerScheduleNow(demoId));
    if (next) state.summary = next;
  }

  async function remove(): Promise<void> {
    await action(() => deleteSchedule(demoId));
    state.summary = null;
    state.config = { ...DEFAULT_SCHEDULE_CONFIG };
  }

  void refresh();
  pollHandle = setInterval(() => void refresh(), pollIntervalMs);

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
      if (pollHandle !== null) {
        clearInterval(pollHandle);
        pollHandle = null;
      }
      stores.delete(demoId);
    },
  };
}

/**
 * Reference-counted accessor. The first caller for a demo creates the
 * store and starts polling; subsequent callers reuse it. When the last
 * caller releases via `dispose()`, polling stops.
 */
export function useSchedule(demoId: string, pollIntervalMs = 4000): ScheduleStore {
  let store = stores.get(demoId);
  if (!store) {
    store = createStore(demoId, pollIntervalMs);
    stores.set(demoId, store);
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
