<script lang="ts">
  import { onDestroy } from "svelte";
  import { CalendarClock, ChevronDown, LoaderCircle } from "lucide-svelte";

  import { buildExchanges } from "../chat/chat-exchanges";
  import ChatExchangeList from "../chat/ChatExchangeList.svelte";
  import { createScheduleFireEventStream } from "./schedule-fire-events.svelte";
  import { deriveRunStatus, type ScheduleRun } from "./schedule-runs";

  interface Props {
    run: ScheduleRun;
    runIndex: number;
    expanded: boolean;
    appId: string;
    onToggle: () => void;
  }

  let { run, runIndex, expanded, appId, onToggle }: Props = $props();

  const status = $derived(deriveRunStatus(run));
  const isRunning = $derived(status === "running" || status === "pending");

  // Subscribe to the fire's event bridge once the backend has registered
  // it. Skipped fires never get a session id (they were rejected before
  // executing), so they fall through to the metadata-only render below.
  let stream = $state<ReturnType<typeof createScheduleFireEventStream> | null>(null);
  let lastSubscribedSessionId: string | null = null;

  $effect(() => {
    const sessionId = run.summary?.event_session_id ?? null;
    if (sessionId === lastSubscribedSessionId) return;

    if (stream) {
      stream.close();
      stream = null;
    }
    lastSubscribedSessionId = sessionId;
    if (!sessionId) return;

    stream = createScheduleFireEventStream(appId, run.fireId, sessionId);
  });

  onDestroy(() => {
    if (stream) stream.close();
  });

  // Live exchanges win when streaming; otherwise fall back to whatever the
  // grouper passed in (which is currently empty for cards rendered from
  // history alone, but reserves the door open for future static replays).
  const liveExchanges = $derived(stream ? buildExchanges(stream.chatFlowItems) : []);
  const exchangesToRender = $derived(liveExchanges.length > 0 ? liveExchanges : run.exchanges);

  function formatAbsolute(iso: string | null | undefined): string {
    if (!iso) return "";
    return new Date(iso).toLocaleString();
  }

  function formatTime(iso: string | null | undefined): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  const fireIdShort = $derived(run.fireId.slice(0, 8));

  const headerLabel = $derived.by(() => {
    const summary = run.summary;
    if (!summary) return `Run #${runIndex + 1}`;
    return `Run #${runIndex + 1} · attempt ${summary.attempt}`;
  });

  const hasExchanges = $derived(exchangesToRender.length > 0);
</script>

<article class="run-card" class:running={isRunning} data-status={status}>
  <header class="run-header">
    <button
      type="button"
      class="run-toggle"
      onclick={onToggle}
      aria-expanded={expanded}
      title={expanded ? "Collapse run" : "Expand run"}
    >
      <span class="run-toggle-left">
        {#if isRunning}
          <LoaderCircle size={13} class="run-spinner" />
        {:else}
          <CalendarClock size={13} />
        {/if}
        <span class="run-label">{headerLabel}</span>
        <span class="run-status-pill" data-status={status}>{status}</span>
      </span>
      <span class="run-toggle-right">
        <span class="run-time" title={formatAbsolute(run.summary?.fired_at ?? run.sortedAt)}>
          {formatTime(run.summary?.fired_at ?? run.sortedAt)}
        </span>
        <span class="run-fire-id" title={`fire ${run.fireId}`}>{fireIdShort}</span>
        <ChevronDown
          size={14}
          class="run-chevron"
          style={expanded ? "transform: rotate(180deg);" : ""}
        />
      </span>
    </button>
  </header>

  {#if expanded}
    <div class="run-body">
      {#if hasExchanges}
        <ChatExchangeList
          exchanges={exchangesToRender}
          loading={isRunning && stream?.isLive === true}
          hasWaitingInterrupts={false}
          chatFlowItemsLength={exchangesToRender.length}
          hasActiveSession={true}
        />
      {:else}
        <div class="run-empty">
          {#if run.summary?.error}
            <p class="run-error" title={run.summary.error}>{run.summary.error}</p>
          {:else if isRunning}
            <p>Waiting for run output…</p>
          {:else}
            <p>Run finished without captured output.</p>
          {/if}

          {#if run.summary}
            <dl class="run-metadata">
              <div>
                <dt>Scheduled</dt>
                <dd title={formatAbsolute(run.summary.scheduled_at)}>
                  {formatTime(run.summary.scheduled_at)}
                </dd>
              </div>
              <div>
                <dt>Fired</dt>
                <dd title={formatAbsolute(run.summary.fired_at)}>
                  {formatTime(run.summary.fired_at)}
                </dd>
              </div>
              <div>
                <dt>Finished</dt>
                <dd title={formatAbsolute(run.summary.finished_at)}>
                  {formatTime(run.summary.finished_at)}
                </dd>
              </div>
              <div>
                <dt>Jitter</dt>
                <dd>{run.summary.jitter_offset_seconds.toFixed(1)}s</dd>
              </div>
            </dl>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</article>

<style>
  .run-card {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-bg-secondary) 60%, transparent);
    overflow: hidden;
    transition: border-color var(--transition-fast);
  }

  .run-card.running {
    border-color: color-mix(in srgb, var(--color-secondary) 50%, var(--color-outline-variant));
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-secondary) 18%, transparent);
  }

  .run-card[data-status="failed"] {
    border-color: color-mix(in srgb, var(--color-error) 40%, var(--color-outline-variant));
  }

  .run-toggle {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    padding: 0.55rem 0.75rem;
    background: transparent;
    border: 0;
    color: var(--color-text);
    cursor: pointer;
    font: inherit;
  }

  .run-toggle:hover {
    background: color-mix(in srgb, var(--color-bg-tertiary) 50%, transparent);
  }

  .run-toggle-left,
  .run-toggle-right {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
  }

  .run-label {
    font-weight: 600;
    font-size: 0.8rem;
  }

  .run-status-pill {
    padding: 0.1rem 0.45rem;
    border-radius: var(--radius-full);
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    background: color-mix(in srgb, var(--color-bg-tertiary) 70%, transparent);
    color: var(--color-text-secondary);
  }
  .run-status-pill[data-status="ok"] {
    background: color-mix(in srgb, var(--color-success) 18%, transparent);
    color: var(--color-success);
  }
  .run-status-pill[data-status="failed"] {
    background: color-mix(in srgb, var(--color-error) 18%, transparent);
    color: var(--color-error);
  }
  .run-status-pill[data-status="skipped"] {
    background: color-mix(in srgb, var(--color-warning) 18%, transparent);
    color: var(--color-warning);
  }
  .run-status-pill[data-status="running"],
  .run-status-pill[data-status="pending"] {
    background: color-mix(in srgb, var(--color-secondary) 22%, transparent);
    color: var(--color-secondary);
  }

  .run-time {
    font-size: 0.7rem;
    color: var(--color-text-tertiary);
    font-variant-numeric: tabular-nums;
  }

  .run-fire-id {
    font-family: "JetBrains Mono", "SF Mono", monospace;
    font-size: 0.65rem;
    color: var(--color-text-tertiary);
    padding: 0.05rem 0.35rem;
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-bg-tertiary) 60%, transparent);
  }

  :global(.run-chevron) {
    color: var(--color-text-tertiary);
    transition: transform var(--transition-fast);
  }

  :global(.run-spinner) {
    animation: run-spin 1s linear infinite;
    color: var(--color-secondary);
  }

  @keyframes run-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .run-body {
    padding: 0.75rem 0.85rem 0.85rem;
    border-top: 1px solid var(--color-outline-variant);
    background: color-mix(in srgb, var(--color-bg) 50%, transparent);
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }

  .run-empty {
    font-size: 0.78rem;
    color: var(--color-text-secondary);
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
  }

  .run-empty p {
    margin: 0;
  }

  .run-error {
    color: var(--color-error);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .run-metadata {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.4rem 0.75rem;
    margin: 0;
  }

  .run-metadata div {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .run-metadata dt {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-tertiary);
  }

  .run-metadata dd {
    margin: 0;
    font-size: 0.78rem;
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }
</style>
