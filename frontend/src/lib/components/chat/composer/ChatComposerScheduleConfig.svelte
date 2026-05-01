<script lang="ts">
  import { CalendarClock, ChevronDown, Settings2 } from "lucide-svelte";

  import {
    DEFAULT_SCHEDULE_CONFIG,
    type ScheduleConfig,
    type ScheduleJobSummary,
  } from "$lib/api_client/schedules";

  interface Props {
    config: ScheduleConfig;
    onChange: (next: ScheduleConfig) => void;
    promptOptions?: Array<{ id: string; name: string }>;
    /** Active schedule (if any). Drives the default collapse state — once a
     *  job is running, collapse to keep the composer compact. */
    summary?: ScheduleJobSummary | null;
  }

  let { config, onChange, promptOptions = [], summary = null }: Props = $props();

  // Default expanded for first-time setup, collapsed once a schedule exists
  // so the running config doesn't dominate the composer. Mid-session toggles
  // are user-controlled and stick until the schedule's job changes.
  let configOpen = $state(true);
  let lastSeenJobId = $state<string | null>(null);

  $effect(() => {
    const jobId = summary?.job_id ?? null;
    if (jobId !== lastSeenJobId) {
      // On the *transition* from "no job" → "job created", collapse so the
      // running config doesn't dominate the composer. Don't reopen on any
      // other transition — the user's manual choice wins.
      if (lastSeenJobId === null && jobId !== null) {
        configOpen = false;
      } else if (lastSeenJobId !== null && jobId === null) {
        // Schedule was removed; reopen for re-setup.
        configOpen = true;
      }
      lastSeenJobId = jobId;
    }
  });

  // Local mirrors of the bound config so we get reactive UI binding without
  // mutating the prop reference. Each handler emits a new object up.
  function update(patch: Partial<ScheduleConfig>): void {
    onChange({ ...config, ...patch });
  }

  type PresetKind = "every-minute" | "every-5" | "hourly" | "daily" | "weekly" | "custom";

  interface Preset {
    id: PresetKind;
    label: string;
    description: string;
    cron: string | null;
    type: "cron" | "interval" | "at";
    intervalSeconds?: number;
  }

  const presets: Preset[] = [
    {
      id: "every-minute",
      label: "Every minute",
      description: "Runs once per minute",
      cron: "* * * * *",
      type: "cron",
    },
    {
      id: "every-5",
      label: "Every 5 minutes",
      description: "Steady cadence — typical for polling",
      cron: "*/5 * * * *",
      type: "cron",
    },
    {
      id: "hourly",
      label: "Every hour",
      description: "On the hour",
      cron: "0 * * * *",
      type: "cron",
    },
    {
      id: "daily",
      label: "Daily at 9am",
      description: "Once per day in the configured timezone",
      cron: "0 9 * * *",
      type: "cron",
    },
    {
      id: "weekly",
      label: "Weekly (Mon 9am)",
      description: "Mondays at 09:00",
      cron: "0 9 * * 1",
      type: "cron",
    },
    {
      id: "custom",
      label: "Custom",
      description: "Cron, interval, or one-shot",
      cron: null,
      type: "cron",
    },
  ];

  function activePreset(c: ScheduleConfig): PresetKind {
    if (c.schedule_type === "interval") return "custom";
    if (c.schedule_type === "at") return "custom";
    const expr = (c.cron_expression ?? "").trim();
    const match = presets.find((p) => p.cron === expr);
    return (match?.id as PresetKind) ?? "custom";
  }

  function applyPreset(preset: Preset): void {
    if (preset.id === "custom") return;
    update({
      schedule_type: preset.type,
      cron_expression: preset.cron ?? config.cron_expression,
      interval_seconds: preset.intervalSeconds ?? config.interval_seconds,
    });
  }

  const currentPreset = $derived(activePreset(config));

  // Compact one-line summary for the collapsed state.
  const cadenceLabel = $derived.by(() => {
    if (config.schedule_type === "cron") {
      const expr = (config.cron_expression ?? "").trim() || "(unset)";
      const preset = presets.find((p) => p.cron === expr && p.id !== "custom");
      return preset ? preset.label : `cron ${expr}`;
    }
    if (config.schedule_type === "interval") {
      return `every ${config.interval_seconds ?? 0}s`;
    }
    return `at ${config.fire_at ?? "(unset)"}`;
  });

  let advancedOpen = $state({
    jitter: false,
    reliability: false,
    retry: false,
  });

  const advancedTouched = $derived.by(() => {
    let count = 0;
    const d = DEFAULT_SCHEDULE_CONFIG;
    if (config.jitter_min_seconds !== d.jitter_min_seconds) count++;
    if (config.jitter_max_seconds !== d.jitter_max_seconds) count++;
    if (config.jitter_distribution !== d.jitter_distribution) count++;
    if (config.jitter_align_seconds != null) count++;
    if (config.jitter_seed != null) count++;
    if (config.misfire !== d.misfire) count++;
    if (config.overlap_policy !== d.overlap_policy) count++;
    if (config.max_overlap !== d.max_overlap) count++;
    if (config.max_runs != null) count++;
    if (config.end_at != null) count++;
    if (config.retry_max_attempts !== d.retry_max_attempts) count++;
    if (config.retry_backoff !== d.retry_backoff) count++;
    return count;
  });
</script>

<div class="schedule-config" role="region" aria-label="Schedule configuration">
  <button
    type="button"
    class="schedule-config-toggle"
    onclick={() => (configOpen = !configOpen)}
    aria-expanded={configOpen}
  >
    <span class="schedule-config-toggle-left">
      <CalendarClock size={13} />
      <span class="toggle-label">Schedule config</span>
      <span class="toggle-summary">{cadenceLabel} · {config.tz || "UTC"} · {config.method}</span>
    </span>
    <ChevronDown
      size={14}
      class="schedule-config-chevron"
      style={configOpen ? "transform: rotate(180deg);" : ""}
    />
  </button>

  {#if configOpen}
    <section class="section">
      <h4 class="section-title">Cadence</h4>
      <div class="preset-grid">
        {#each presets as preset (preset.id)}
          <button
            type="button"
            class="preset-btn"
            class:active={currentPreset === preset.id}
            onclick={() => applyPreset(preset)}
          >
            <span class="preset-label">{preset.label}</span>
            <span class="preset-desc">{preset.description}</span>
          </button>
        {/each}
      </div>
    </section>

    {#if currentPreset === "custom"}
      <section class="section custom-block">
        <div class="grid two">
          <label class="field">
            <span>Schedule type</span>
            <select
              value={config.schedule_type}
              onchange={(e) =>
                update({ schedule_type: e.currentTarget.value as ScheduleConfig["schedule_type"] })}
            >
              <option value="cron">Cron expression</option>
              <option value="interval">Interval (seconds)</option>
              <option value="at">One-shot at time</option>
            </select>
          </label>

          {#if config.schedule_type === "cron"}
            <label class="field">
              <span>Cron expression</span>
              <input
                type="text"
                value={config.cron_expression ?? ""}
                placeholder="*/5 * * * *"
                spellcheck={false}
                oninput={(e) => update({ cron_expression: e.currentTarget.value })}
              />
            </label>
          {:else if config.schedule_type === "interval"}
            <label class="field">
              <span>Interval (seconds)</span>
              <input
                type="number"
                min="1"
                step="1"
                value={config.interval_seconds ?? 60}
                oninput={(e) => update({ interval_seconds: Number(e.currentTarget.value) })}
              />
            </label>
          {:else}
            <label class="field">
              <span>Fire at</span>
              <input
                type="datetime-local"
                value={(config.fire_at as unknown as string) ?? ""}
                oninput={(e) => update({ fire_at: e.currentTarget.value })}
              />
            </label>
          {/if}
        </div>
      </section>
    {/if}

    <section class="section">
      <div class="grid three">
        <label class="field">
          <span>Timezone</span>
          <input
            type="text"
            value={config.tz}
            placeholder="UTC"
            spellcheck={false}
            oninput={(e) => update({ tz: e.currentTarget.value })}
          />
        </label>
        <label class="field">
          <span>Method</span>
          <select
            value={config.method}
            onchange={(e) => update({ method: e.currentTarget.value as ScheduleConfig["method"] })}
          >
            <option value="invoke">invoke</option>
            <option value="ainvoke">ainvoke</option>
            <option value="stream">stream</option>
            <option value="astream">astream</option>
            <option value="batch">batch</option>
            <option value="abatch">abatch</option>
          </select>
        </label>
        {#if promptOptions.length}
          <label class="field">
            <span>Saved prompt (fallback)</span>
            <select
              value={config.prompt_id ?? ""}
              onchange={(e) => update({ prompt_id: e.currentTarget.value || null })}
            >
              <option value="">(use composer text)</option>
              {#each promptOptions as opt (opt.id)}
                <option value={opt.id}>{opt.name}</option>
              {/each}
            </select>
          </label>
        {/if}
      </div>
    </section>

    <section class="advanced">
      <div class="advanced-header">
        <span class="advanced-title">
          <Settings2 size={13} />
          Schedule advanced
        </span>
        {#if advancedTouched > 0}
          <span class="advanced-touched">{advancedTouched} customized</span>
        {/if}
      </div>

      <details bind:open={advancedOpen.jitter} class="disclosure">
        <summary>
          <span class="disclosure-label">Jitter</span>
          <span class="disclosure-hint">
            {config.jitter_min_seconds}–{config.jitter_max_seconds}s · {config.jitter_distribution}
          </span>
          <ChevronDown size={14} class="disclosure-chevron" />
        </summary>
        <div class="grid three">
          <label class="field">
            <span>Min (s)</span>
            <input
              type="number"
              step="0.1"
              value={config.jitter_min_seconds}
              oninput={(e) => update({ jitter_min_seconds: Number(e.currentTarget.value) })}
            />
          </label>
          <label class="field">
            <span>Max (s)</span>
            <input
              type="number"
              step="0.1"
              value={config.jitter_max_seconds}
              oninput={(e) => update({ jitter_max_seconds: Number(e.currentTarget.value) })}
            />
          </label>
          <label class="field">
            <span>Distribution</span>
            <select
              value={config.jitter_distribution}
              onchange={(e) =>
                update({
                  jitter_distribution: e.currentTarget
                    .value as ScheduleConfig["jitter_distribution"],
                })}
            >
              <option value="uniform">uniform</option>
              <option value="normal">normal</option>
              <option value="triangular">triangular</option>
            </select>
          </label>
        </div>
      </details>

      <details bind:open={advancedOpen.reliability} class="disclosure">
        <summary>
          <span class="disclosure-label">Reliability</span>
          <span class="disclosure-hint">
            misfire: {config.misfire} · overlap: {config.overlap_policy}
          </span>
          <ChevronDown size={14} class="disclosure-chevron" />
        </summary>
        <div class="grid three">
          <label class="field">
            <span>Misfire policy</span>
            <select
              value={config.misfire}
              onchange={(e) =>
                update({ misfire: e.currentTarget.value as ScheduleConfig["misfire"] })}
            >
              <option value="coalesce">coalesce</option>
              <option value="skip">skip</option>
              <option value="fire_now">fire now</option>
            </select>
          </label>
          <label class="field">
            <span>Overlap policy</span>
            <select
              value={config.overlap_policy}
              onchange={(e) =>
                update({
                  overlap_policy: e.currentTarget.value as ScheduleConfig["overlap_policy"],
                })}
            >
              <option value="skip">skip</option>
              <option value="queue">queue</option>
              <option value="replace">replace</option>
            </select>
          </label>
          <label class="field">
            <span>Max overlap</span>
            <input
              type="number"
              min="0"
              step="1"
              value={config.max_overlap}
              oninput={(e) => update({ max_overlap: Number(e.currentTarget.value) })}
            />
          </label>
          <label class="field">
            <span>Max runs (blank = ∞)</span>
            <input
              type="number"
              min="0"
              step="1"
              value={config.max_runs ?? ""}
              oninput={(e) =>
                update({
                  max_runs: e.currentTarget.value === "" ? null : Number(e.currentTarget.value),
                })}
            />
          </label>
        </div>
      </details>

      <details bind:open={advancedOpen.retry} class="disclosure">
        <summary>
          <span class="disclosure-label">Retry</span>
          <span class="disclosure-hint">
            {config.retry_max_attempts} attempts · {config.retry_backoff}
          </span>
          <ChevronDown size={14} class="disclosure-chevron" />
        </summary>
        <div class="grid three">
          <label class="field">
            <span>Max attempts</span>
            <input
              type="number"
              min="1"
              step="1"
              value={config.retry_max_attempts}
              oninput={(e) => update({ retry_max_attempts: Number(e.currentTarget.value) })}
            />
          </label>
          <label class="field">
            <span>Backoff</span>
            <select
              value={config.retry_backoff}
              onchange={(e) =>
                update({ retry_backoff: e.currentTarget.value as ScheduleConfig["retry_backoff"] })}
            >
              <option value="constant">constant</option>
              <option value="linear">linear</option>
              <option value="exponential">exponential</option>
            </select>
          </label>
          <label class="field">
            <span>Base (s)</span>
            <input
              type="number"
              min="0"
              step="0.5"
              value={config.retry_base_seconds}
              oninput={(e) => update({ retry_base_seconds: Number(e.currentTarget.value) })}
            />
          </label>
        </div>
      </details>
    </section>
  {/if}
</div>

<style>
  .schedule-config-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.4rem 0.55rem;
    margin: -0.35rem -0.45rem -0.1rem;
    border: 0;
    background: transparent;
    color: var(--color-text);
    cursor: pointer;
    border-radius: var(--radius-md);
    font: inherit;
  }
  .schedule-config-toggle:hover {
    background: color-mix(in srgb, var(--color-bg-tertiary) 50%, transparent);
  }
  .schedule-config-toggle-left {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
  }
  .toggle-label {
    font-size: 0.78rem;
    font-weight: 600;
  }
  .toggle-summary {
    font-size: 0.7rem;
    color: var(--color-text-tertiary);
    font-family: "JetBrains Mono", "SF Mono", monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  :global(.schedule-config-chevron) {
    color: var(--color-text-tertiary);
    transition: transform var(--transition-fast);
  }

  .schedule-config {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    padding: 0.75rem 0.85rem;
    margin-bottom: 0.75rem;
    border: 1px solid color-mix(in srgb, var(--color-tertiary) 30%, var(--color-outline-variant));
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-tertiary) 4%, var(--color-bg-secondary));
    color: var(--color-text);
  }
  .section {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
  }
  .section-title {
    margin: 0;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--color-text-tertiary);
  }
  .preset-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 0.4rem;
  }
  .preset-btn {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.15rem;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-bg-tertiary) 35%, transparent);
    color: var(--color-text-secondary);
    cursor: pointer;
    text-align: left;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast);
  }
  .preset-btn:hover {
    background: color-mix(in srgb, var(--color-bg-tertiary) 70%, transparent);
    color: var(--color-text);
  }
  .preset-btn.active {
    border-color: color-mix(in srgb, var(--color-tertiary) 50%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-tertiary) 18%, var(--color-bg-secondary));
    color: var(--color-tertiary);
  }
  .preset-label {
    font-size: 0.78rem;
    font-weight: 600;
  }
  .preset-desc {
    font-size: 0.68rem;
    color: var(--color-text-tertiary);
  }
  .preset-btn.active .preset-desc {
    color: color-mix(in srgb, var(--color-tertiary) 80%, var(--color-text-tertiary));
  }
  .custom-block {
    padding: 0.6rem 0.7rem;
    border: 1px solid color-mix(in srgb, var(--color-tertiary) 35%, var(--color-outline-variant));
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-tertiary) 6%, transparent);
  }
  .grid {
    display: grid;
    gap: 0.55rem 0.75rem;
  }
  .grid.two {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  }
  .grid.three {
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  }
  .field {
    display: flex;
    flex-direction: column;
    font-size: 0.7rem;
    color: var(--color-text-secondary);
    gap: 0.2rem;
  }
  .field input,
  .field select {
    padding: 0.35rem 0.5rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-sm);
    background: var(--color-bg-secondary);
    color: var(--color-text);
    font-size: 0.78rem;
  }

  .advanced {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-bg-secondary) 50%, transparent);
    overflow: hidden;
  }
  .advanced-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--color-outline-variant);
  }
  .advanced-title {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--color-text-secondary);
  }
  .advanced-touched {
    font-size: 0.65rem;
    padding: 0.1rem 0.45rem;
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-tertiary) 18%, transparent);
    color: var(--color-tertiary);
    font-weight: 600;
  }
  .disclosure {
    border-top: 1px solid var(--color-outline-variant);
  }
  .disclosure:first-of-type {
    border-top: 0;
  }
  .disclosure summary {
    list-style: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.55rem 0.75rem;
    font-size: 0.75rem;
    color: var(--color-text);
    user-select: none;
  }
  .disclosure summary::-webkit-details-marker {
    display: none;
  }
  .disclosure summary:hover {
    background: color-mix(in srgb, var(--color-bg-tertiary) 50%, transparent);
  }
  .disclosure-label {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-weight: 600;
  }
  .disclosure-hint {
    flex: 1;
    text-align: right;
    color: var(--color-text-tertiary);
    font-size: 0.68rem;
    font-family: "JetBrains Mono", "SF Mono", monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  :global(.disclosure-chevron) {
    color: var(--color-text-tertiary);
    transition: transform var(--transition-fast);
  }
  details[open] > summary :global(.disclosure-chevron) {
    transform: rotate(180deg);
  }
  .disclosure[open] > .grid {
    padding: 0.5rem 0.75rem 0.7rem;
    border-top: 1px dashed var(--color-outline-variant);
  }
</style>
