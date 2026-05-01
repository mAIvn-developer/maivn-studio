<script lang="ts">
  import type { Message } from "$lib/types";
  import { copyToClipboard } from "$lib/utils/clipboard";
  import { formatDuration, formatTokens } from "$lib/utils/format";
  import { ChartColumn, Check, Clock, Copy, FileText, Palette } from "lucide-svelte";
  import KeyValueDisplay from "../KeyValueDisplay.svelte";

  interface Props {
    aiMessage: Message;
    structuredOutputPayload: unknown;
    hasSessionDetails: boolean;
    autoShowSessionDetails?: boolean;
  }

  let {
    aiMessage,
    structuredOutputPayload,
    hasSessionDetails,
    autoShowSessionDetails = false,
  }: Props = $props();

  let showStructuredSessionDetails = $state(false);
  let copiedStructured = $state(false);

  const payloadSummary = $derived(describePayload(structuredOutputPayload));

  $effect(() => {
    if (autoShowSessionDetails && hasSessionDetails) {
      showStructuredSessionDetails = true;
    }
  });

  async function copyStructuredOutput() {
    if (!structuredOutputPayload) return;
    const raw =
      typeof structuredOutputPayload === "string"
        ? structuredOutputPayload
        : JSON.stringify(structuredOutputPayload, null, 2);
    const success = await copyToClipboard(raw);
    if (success) {
      copiedStructured = true;
      setTimeout(() => (copiedStructured = false), 2000);
    }
  }

  function describePayload(value: unknown): {
    kind: string;
    countLabel: string;
    keys: string[];
    remainingKeys: number;
  } {
    if (Array.isArray(value)) {
      return {
        kind: "Array",
        countLabel: `${value.length} ${value.length === 1 ? "item" : "items"}`,
        keys: [],
        remainingKeys: 0,
      };
    }

    if (value && typeof value === "object") {
      const keys = Object.keys(value as Record<string, unknown>);
      return {
        kind: "Object",
        countLabel: `${keys.length} ${keys.length === 1 ? "key" : "keys"}`,
        keys: keys.slice(0, 4),
        remainingKeys: Math.max(0, keys.length - 4),
      };
    }

    if (value === null || value === undefined) {
      return {
        kind: "Empty",
        countLabel: "No payload",
        keys: [],
        remainingKeys: 0,
      };
    }

    return {
      kind: typeof value === "string" ? "String" : "Scalar",
      countLabel: "1 value",
      keys: [],
      remainingKeys: 0,
    };
  }
</script>

<section class="structured-output-card" aria-label="Structured output response">
  <header class="structured-output-header">
    <div class="structured-title-group">
      <div class="structured-icon-shell" aria-hidden="true">
        <FileText size={16} />
      </div>
      <div class="structured-title-copy">
        <div class="structured-title-row">
          <h3>Structured Output</h3>
          <span class="response-chip">AI Response</span>
        </div>
        <p>{payloadSummary.kind} payload</p>
      </div>
    </div>

    <div class="structured-actions">
      {#if structuredOutputPayload}
        <button
          type="button"
          class="icon-button"
          onclick={copyStructuredOutput}
          title="Copy structured output"
          aria-label="Copy structured output"
        >
          {#if copiedStructured}
            <Check size={16} />
          {:else}
            <Copy size={16} />
          {/if}
        </button>
      {/if}
      {#if hasSessionDetails}
        <button
          type="button"
          class="icon-button"
          class:active={showStructuredSessionDetails}
          onclick={() => (showStructuredSessionDetails = !showStructuredSessionDetails)}
          title="Toggle session details"
          aria-label="Toggle session details"
          aria-pressed={showStructuredSessionDetails}
        >
          <ChartColumn size={16} />
        </button>
      {/if}
      <time class="structured-time" datetime={new Date(aiMessage.timestamp).toISOString()}>
        {new Date(aiMessage.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}
      </time>
    </div>
  </header>

  <div class="structured-summary">
    <span class="summary-pill">{payloadSummary.kind}</span>
    <span class="summary-pill">{payloadSummary.countLabel}</span>
    {#if payloadSummary.keys.length > 0}
      <div class="summary-keys" aria-label="Top-level output keys">
        {#each payloadSummary.keys as key (key)}
          <code>{key}</code>
        {/each}
        {#if payloadSummary.remainingKeys > 0}
          <span class="more-keys">+{payloadSummary.remainingKeys}</span>
        {/if}
      </div>
    {/if}
  </div>

  <div class="structured-body">
    {#if structuredOutputPayload}
      <div class="json-viewer">
        <KeyValueDisplay data={structuredOutputPayload} initialExpanded={true} />
      </div>
    {:else}
      <p class="empty-output">No output available</p>
    {/if}
  </div>

  {#if hasSessionDetails && showStructuredSessionDetails}
    <div class="structured-session-details">
      <div class="session-heading">
        <ChartColumn size={16} />
        <span>Session Details</span>
      </div>

      <div class="session-metrics">
        {#if aiMessage.sessionDetails?.duration_ms !== undefined}
          <div class="session-metric">
            <div class="metric-icon">
              <Clock size={16} />
            </div>
            <div>
              <span>Duration</span>
              <strong>{formatDuration(aiMessage.sessionDetails.duration_ms)}</strong>
            </div>
          </div>
        {/if}

        {#if aiMessage.sessionDetails?.token_usage}
          <div class="session-metric">
            <div class="metric-icon primary">
              <Palette size={16} />
            </div>
            <div>
              <span>Total Tokens</span>
              <strong>{formatTokens(aiMessage.sessionDetails.token_usage.total_tokens)}</strong>
            </div>
          </div>
        {/if}
      </div>

      {#if aiMessage.sessionDetails?.token_usage}
        <div class="token-grid">
          <div>
            <span>Input</span>
            <strong>{formatTokens(aiMessage.sessionDetails.token_usage.input_tokens)}</strong>
          </div>
          <div>
            <span>Output</span>
            <strong>{formatTokens(aiMessage.sessionDetails.token_usage.output_tokens)}</strong>
          </div>
          {#if aiMessage.sessionDetails.token_usage.reasoning_tokens > 0}
            <div>
              <span>Reasoning</span>
              <strong>
                {formatTokens(aiMessage.sessionDetails.token_usage.reasoning_tokens)}
              </strong>
            </div>
          {/if}
          <div>
            <span>Cache Read</span>
            <strong>
              {formatTokens(aiMessage.sessionDetails.token_usage.cache_read_tokens)}
            </strong>
          </div>
          <div>
            <span>Cache Write</span>
            <strong>
              {formatTokens(aiMessage.sessionDetails.token_usage.cache_creation_tokens)}
            </strong>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .structured-output-card {
    width: min(85%, 64rem);
    margin-inline: auto;
    animation: slideIn 0.2s ease-out;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--color-secondary) 28%, var(--color-outline-variant));
    border-radius: var(--radius-md);
    background:
      linear-gradient(
        180deg,
        color-mix(in srgb, var(--color-secondary) 7%, transparent),
        transparent 9rem
      ),
      color-mix(in srgb, var(--color-bg-secondary) 94%, var(--color-bg));
    box-shadow: var(--shadow-sm);
  }

  .structured-output-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.875rem 1rem;
    border-bottom: 1px solid color-mix(in srgb, var(--color-secondary) 20%, transparent);
  }

  .structured-title-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    min-width: 0;
  }

  .structured-icon-shell {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    flex: 0 0 auto;
    border: 1px solid color-mix(in srgb, var(--color-secondary) 34%, transparent);
    border-radius: var(--radius-md);
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 14%, transparent);
  }

  .structured-title-copy {
    min-width: 0;
  }

  .structured-title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
  }

  .structured-title-row h3 {
    margin: 0;
    color: var(--color-text);
    font-size: 0.9375rem;
    font-weight: 700;
    line-height: 1.3;
    letter-spacing: 0;
  }

  .structured-title-copy p {
    margin: 0.125rem 0 0;
    color: var(--color-text-tertiary);
    font-size: 0.75rem;
    line-height: 1.35;
  }

  .response-chip,
  .summary-pill,
  .more-keys {
    display: inline-flex;
    align-items: center;
    height: 1.35rem;
    border-radius: var(--radius-full);
    padding: 0 0.5rem;
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0;
    white-space: nowrap;
  }

  .response-chip {
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 13%, transparent);
  }

  .structured-actions {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    flex: 0 0 auto;
  }

  .icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    background: transparent;
    transition:
      background var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast);
  }

  .icon-button:hover,
  .icon-button.active {
    border-color: color-mix(in srgb, var(--color-secondary) 28%, transparent);
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 12%, transparent);
  }

  .structured-time {
    margin-left: 0.25rem;
    color: var(--color-text-tertiary);
    font-size: 0.6875rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .structured-summary {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--color-outline-variant);
    background: color-mix(in srgb, var(--color-bg) 30%, transparent);
  }

  .summary-pill {
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-surface-variant) 46%, transparent);
  }

  .summary-keys {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.35rem;
    min-width: 0;
  }

  .summary-keys code {
    max-width: 13rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    border: 1px solid color-mix(in srgb, var(--color-outline-variant) 76%, transparent);
    border-radius: var(--radius-sm);
    padding: 0.15rem 0.45rem;
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-tertiary) 72%, transparent);
    font-size: 0.72rem;
  }

  .more-keys {
    color: var(--color-text-tertiary);
    background: color-mix(in srgb, var(--color-bg-tertiary) 58%, transparent);
  }

  .structured-body {
    padding: 1rem;
  }

  .json-viewer {
    max-height: min(34rem, 58vh);
    overflow: auto;
    border: 1px solid color-mix(in srgb, var(--color-outline-variant) 72%, transparent);
    border-radius: var(--radius-md);
    padding: 0.875rem;
    background: color-mix(in srgb, var(--color-bg) 55%, var(--color-bg-secondary));
  }

  .empty-output {
    margin: 0;
    padding: 1rem;
    border: 1px dashed var(--color-outline-variant);
    border-radius: var(--radius-md);
    color: var(--color-text-tertiary);
    font-size: 0.875rem;
  }

  .structured-session-details {
    padding: 0.875rem 1rem 1rem;
    border-top: 1px solid var(--color-outline-variant);
    background: color-mix(in srgb, var(--color-bg) 28%, transparent);
  }

  .session-heading {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    color: var(--color-primary);
    font-size: 0.75rem;
    font-weight: 700;
  }

  .session-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
  }

  .session-metric {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    min-width: 0;
    border: 1px solid color-mix(in srgb, var(--color-outline-variant) 58%, transparent);
    border-radius: var(--radius-md);
    padding: 0.65rem 0.75rem;
    background: color-mix(in srgb, var(--color-bg-tertiary) 48%, transparent);
  }

  .metric-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.875rem;
    height: 1.875rem;
    flex: 0 0 auto;
    border-radius: var(--radius-md);
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 14%, transparent);
  }

  .metric-icon.primary {
    color: var(--color-primary);
    background: color-mix(in srgb, var(--color-primary) 14%, transparent);
  }

  .session-metric span,
  .token-grid span {
    display: block;
    color: var(--color-text-tertiary);
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0;
    text-transform: uppercase;
  }

  .session-metric strong,
  .token-grid strong {
    color: var(--color-text);
    font-size: 0.8125rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .token-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.5rem;
    margin-top: 0.75rem;
  }

  .token-grid > div {
    min-width: 0;
    border: 1px solid color-mix(in srgb, var(--color-outline-variant) 50%, transparent);
    border-radius: var(--radius-md);
    padding: 0.55rem 0.65rem;
    background: color-mix(in srgb, var(--color-bg-tertiary) 34%, transparent);
  }

  @media (max-width: 760px) {
    .structured-output-card {
      width: 100%;
    }

    .structured-output-header {
      align-items: flex-start;
      flex-direction: column;
    }

    .structured-actions {
      width: 100%;
      justify-content: flex-end;
    }

    .session-metrics,
    .token-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
