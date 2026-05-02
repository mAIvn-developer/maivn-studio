<script lang="ts">
  import { Pause, Play, Square, Trash2, Zap } from "lucide-svelte";

  import type { ScheduleJobSummary } from "$lib/api_client/schedules";

  interface Props {
    summary: ScheduleJobSummary | null;
    busy: boolean;
    canSubmit: boolean;
    promptDirty: boolean;
    onStart: () => void | Promise<void>;
    onPause: () => void | Promise<void>;
    onResume: () => void | Promise<void>;
    onTrigger: () => void | Promise<void>;
    onStop: () => void | Promise<void>;
    onRemove: () => void | Promise<void>;
  }

  let {
    summary,
    busy,
    canSubmit,
    promptDirty,
    onStart,
    onPause,
    onResume,
    onTrigger,
    onStop,
    onRemove,
  }: Props = $props();

  // No summary → first start. Existing job → "Update schedule" (highlights
  // when prompt was edited). is_done means the job ran out / was stopped;
  // re-applying restarts from the current config.
  const primaryLabel = $derived.by(() => {
    if (!summary) return "Schedule";
    if (summary.is_done) return "Restart schedule";
    return promptDirty ? "Update — apply new prompt" : "Update schedule";
  });
</script>

<div class="actions" role="group" aria-label="Schedule actions">
  <button
    type="submit"
    class="btn primary"
    class:dirty={promptDirty}
    disabled={busy || !canSubmit}
    onclick={onStart}
    title={primaryLabel}
  >
    <Play size={13} />
    {primaryLabel}
  </button>

  {#if summary && !summary.is_done}
    <button
      type="button"
      class="btn"
      disabled={busy}
      onclick={summary.is_paused ? onResume : onPause}
      title={summary.is_paused ? "Resume scheduled fires" : "Pause scheduled fires"}
    >
      {#if summary.is_paused}
        <Play size={13} /> Resume
      {:else}
        <Pause size={13} /> Pause
      {/if}
    </button>
    <button type="button" class="btn" disabled={busy} onclick={onTrigger} title="Run once now">
      <Zap size={13} /> Trigger now
    </button>
    <button
      type="button"
      class="btn"
      disabled={busy}
      onclick={onStop}
      title="Stop scheduling further fires"
    >
      <Square size={13} /> Stop
    </button>
  {/if}

  {#if summary}
    <button
      type="button"
      class="btn destructive"
      disabled={busy}
      onclick={onRemove}
      title="Remove schedule"
    >
      <Trash2 size={13} />
    </button>
  {/if}
</div>

<style>
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    padding: 0.6rem 0.75rem 0.7rem;
    border-top: 1px solid var(--color-outline-variant);
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.45rem 0.75rem;
    border-radius: var(--radius-md);
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--color-text);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-outline-variant);
    cursor: pointer;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      box-shadow var(--transition-fast);
  }
  .btn:hover:not(:disabled) {
    background: var(--color-bg-tertiary);
  }
  .btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .btn.primary {
    background: var(--color-secondary);
    color: var(--color-on-secondary);
    border-color: transparent;
  }
  .btn.primary:hover:not(:disabled) {
    filter: brightness(1.05);
  }
  .btn.primary.dirty {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-secondary) 35%, transparent);
  }
  .btn.destructive {
    color: var(--color-error);
    border-color: color-mix(in srgb, var(--color-error) 30%, var(--color-outline-variant));
    margin-left: auto;
  }
  .btn.destructive:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-error) 12%, transparent);
  }
</style>
