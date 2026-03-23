<script lang="ts">
  import type { Message } from "$lib/types";
  import { ChartBar, Clock, Coins } from "lucide-svelte";

  interface Props {
    message: Message;
    formatDuration: (ms: number) => string;
    formatTokens: (count: number) => string;
  }

  let { message, formatDuration, formatTokens }: Props = $props();
</script>

<div class="session-details-section border-t border-[var(--color-outline-variant)]/50 bg-black/5">
  <div class="px-4 py-3">
    <div class="flex items-center gap-2 mb-3">
      <ChartBar size={16} class="text-[var(--color-primary)]" strokeWidth={1.5} />
      <span class="text-xs font-medium text-[var(--color-primary)]">Session Details</span>
    </div>

    <div class="grid grid-cols-2 gap-3">
      {#if message.sessionDetails?.duration_ms !== undefined}
        <div class="bg-[var(--color-bg-tertiary)] rounded-lg p-2.5 flex items-center gap-2.5">
          <div
            class="w-8 h-8 rounded-lg bg-[var(--color-tertiary)]/15 flex items-center justify-center"
          >
            <Clock size={16} class="text-[var(--color-tertiary)]" strokeWidth={1.5} />
          </div>
          <div>
            <span class="text-xs text-[var(--color-text-tertiary)] block">Duration</span>
            <span class="text-sm font-semibold text-[var(--color-text)] tabular-nums">
              {formatDuration(message.sessionDetails.duration_ms)}
            </span>
          </div>
        </div>
      {/if}

      {#if message.sessionDetails?.token_usage}
        <div class="bg-[var(--color-bg-tertiary)] rounded-lg p-2.5 flex items-center gap-2.5">
          <div
            class="w-8 h-8 rounded-lg bg-[var(--color-primary)]/15 flex items-center justify-center"
          >
            <Coins size={16} class="text-[var(--color-primary)]" strokeWidth={1.5} />
          </div>
          <div>
            <span class="text-xs text-[var(--color-text-tertiary)] block">Total Tokens</span>
            <span class="text-sm font-semibold text-[var(--color-text)] tabular-nums">
              {formatTokens(message.sessionDetails.token_usage.total_tokens)}
            </span>
          </div>
        </div>
      {/if}
    </div>

    {#if message.sessionDetails?.token_usage}
      <div class="mt-3 grid grid-cols-4 gap-2">
        <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
          <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase">Input</span>
          <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
            {formatTokens(message.sessionDetails.token_usage.input_tokens)}
          </span>
        </div>
        <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
          <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase">Output</span>
          <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
            {formatTokens(message.sessionDetails.token_usage.output_tokens)}
          </span>
        </div>
        {#if message.sessionDetails.token_usage.reasoning_tokens > 0}
          <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
            <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase">
              Reasoning
            </span>
            <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
              {formatTokens(message.sessionDetails.token_usage.reasoning_tokens)}
            </span>
          </div>
        {/if}
        <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
          <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase">
            Cache Read
          </span>
          <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
            {formatTokens(message.sessionDetails.token_usage.cache_read_tokens)}
          </span>
        </div>
        <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
          <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase">
            Cache Write
          </span>
          <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
            {formatTokens(message.sessionDetails.token_usage.cache_creation_tokens)}
          </span>
        </div>
      </div>
    {/if}
  </div>
</div>
