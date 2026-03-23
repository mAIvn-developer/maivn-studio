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
</script>

<div
  class="structured-output-card max-w-[85%] rounded-2xl overflow-hidden
         bg-gradient-to-br from-[var(--color-tertiary-container)] to-[#1a3d4d]
         border border-[var(--color-tertiary)]/30"
>
  <div class="flex items-center gap-2 px-4 py-3 border-b border-[var(--color-tertiary)]/20">
    <div
      class="w-7 h-7 rounded-full bg-[var(--color-tertiary)]/25 flex items-center justify-center"
    >
      <FileText size={16} class="text-[var(--color-tertiary)]" />
    </div>
    <span class="text-sm font-semibold text-[var(--color-tertiary)]">Structured Output</span>
    <span
      class="ml-auto text-[10px] px-2 py-0.5 rounded-full
             bg-[var(--color-tertiary)]/20 text-[var(--color-tertiary)]"
    >
      AI Response
    </span>
    {#if structuredOutputPayload}
      <button
        type="button"
        onclick={copyStructuredOutput}
        class="ml-2 p-1.5 rounded-md hover:bg-white/10 transition-colors"
        title="Copy structured output"
      >
        {#if copiedStructured}
          <Check size={16} class="text-[var(--color-success)]" />
        {:else}
          <Copy size={16} class="text-[var(--color-text-secondary)]" />
        {/if}
      </button>
    {/if}
    {#if hasSessionDetails}
      <button
        type="button"
        onclick={() => (showStructuredSessionDetails = !showStructuredSessionDetails)}
        class="ml-2 p-1.5 rounded-md transition-colors
               {showStructuredSessionDetails
          ? 'bg-[var(--color-primary)]/20 text-[var(--color-primary)]'
          : 'hover:bg-white/10 text-[var(--color-text-secondary)]'}"
        title="Toggle session details"
      >
        <ChartColumn size={16} />
      </button>
    {/if}
  </div>

  <div class="p-4">
    {#if structuredOutputPayload}
      <KeyValueDisplay data={structuredOutputPayload} initialExpanded={true} />
    {:else}
      <p class="text-sm text-[var(--color-text-tertiary)] italic">No output available</p>
    {/if}
  </div>

  <div class="px-4 py-2 bg-black/10 border-t border-[var(--color-tertiary)]/10">
    <div class="flex items-center justify-between gap-2">
      <span class="text-[10px] text-[var(--color-text-tertiary)]">
        {new Date(aiMessage.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}
      </span>
      <div class="flex items-center gap-2">
        {#if structuredOutputPayload}
          <button
            type="button"
            onclick={copyStructuredOutput}
            class="p-1.5 rounded-md hover:bg-white/10 transition-colors"
            title="Copy structured output"
          >
            {#if copiedStructured}
              <Check size={16} class="text-[var(--color-success)]" />
            {:else}
              <Copy size={16} class="text-[var(--color-text-secondary)]" />
            {/if}
          </button>
        {/if}
        {#if hasSessionDetails}
          <button
            type="button"
            onclick={() => (showStructuredSessionDetails = !showStructuredSessionDetails)}
            class="p-1.5 rounded-md transition-colors
                   {showStructuredSessionDetails
              ? 'bg-[var(--color-primary)]/20 text-[var(--color-primary)]'
              : 'hover:bg-white/10 text-[var(--color-text-secondary)]'}"
            title="Toggle session details"
          >
            <ChartColumn size={16} />
          </button>
        {/if}
      </div>
    </div>
  </div>

  {#if hasSessionDetails && showStructuredSessionDetails}
    <div class="border-t border-[var(--color-tertiary)]/20 bg-black/5">
      <div class="px-4 py-3">
        <div class="flex items-center gap-2 mb-3">
          <ChartColumn size={16} class="text-[var(--color-primary)]" />
          <span class="text-xs font-medium text-[var(--color-primary)]">Session Details</span>
        </div>

        <div class="grid grid-cols-2 gap-3">
          {#if aiMessage.sessionDetails?.duration_ms !== undefined}
            <div class="bg-[var(--color-bg-tertiary)] rounded-lg p-2.5 flex items-center gap-2.5">
              <div
                class="w-8 h-8 rounded-lg bg-[var(--color-tertiary)]/15 flex items-center justify-center"
              >
                <Clock size={16} class="text-[var(--color-tertiary)]" />
              </div>
              <div>
                <span class="text-xs text-[var(--color-text-tertiary)] block">Duration</span>
                <span class="text-sm font-semibold text-[var(--color-text)] tabular-nums">
                  {formatDuration(aiMessage.sessionDetails.duration_ms)}
                </span>
              </div>
            </div>
          {/if}

          {#if aiMessage.sessionDetails?.token_usage}
            <div class="bg-[var(--color-bg-tertiary)] rounded-lg p-2.5 flex items-center gap-2.5">
              <div
                class="w-8 h-8 rounded-lg bg-[var(--color-primary)]/15 flex items-center justify-center"
              >
                <Palette size={16} class="text-[var(--color-primary)]" />
              </div>
              <div>
                <span class="text-xs text-[var(--color-text-tertiary)] block">Total Tokens</span>
                <span class="text-sm font-semibold text-[var(--color-text)] tabular-nums">
                  {formatTokens(aiMessage.sessionDetails.token_usage.total_tokens)}
                </span>
              </div>
            </div>
          {/if}
        </div>

        {#if aiMessage.sessionDetails?.token_usage}
          <div class="mt-3 grid grid-cols-4 gap-2">
            <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
              <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase"
                >Input</span
              >
              <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
                {formatTokens(aiMessage.sessionDetails.token_usage.input_tokens)}
              </span>
            </div>
            <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
              <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase"
                >Output</span
              >
              <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
                {formatTokens(aiMessage.sessionDetails.token_usage.output_tokens)}
              </span>
            </div>
            {#if aiMessage.sessionDetails.token_usage.reasoning_tokens > 0}
              <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
                <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase">
                  Reasoning
                </span>
                <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
                  {formatTokens(aiMessage.sessionDetails.token_usage.reasoning_tokens)}
                </span>
              </div>
            {/if}
            <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
              <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase">
                Cache Read
              </span>
              <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
                {formatTokens(aiMessage.sessionDetails.token_usage.cache_read_tokens)}
              </span>
            </div>
            <div class="text-center p-2 bg-[var(--color-bg-tertiary)] rounded-lg">
              <span class="text-[10px] text-[var(--color-text-tertiary)] block uppercase">
                Cache Write
              </span>
              <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
                {formatTokens(aiMessage.sessionDetails.token_usage.cache_creation_tokens)}
              </span>
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .structured-output-card {
    animation: slideIn 0.2s ease-out;
  }
</style>
