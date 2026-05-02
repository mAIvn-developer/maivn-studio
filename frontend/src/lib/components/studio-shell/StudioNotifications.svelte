<script lang="ts">
  import type { MemoryActivityData } from "$lib/types";
  import { AlertCircle, Database, X } from "lucide-svelte";

  interface Props {
    memoryIndexedToast: {
      message: string;
      timestamp: string;
      details?: MemoryActivityData;
    } | null;
    error: string | null;
    errorProgress: number;
    onDismissError: () => void;
    formatMemoryIndexedToastDetails: () => string;
  }

  let {
    memoryIndexedToast,
    error,
    errorProgress,
    onDismissError,
    formatMemoryIndexedToastDetails,
  }: Props = $props();
</script>

{#if memoryIndexedToast}
  <div
    class="fixed right-4 z-40 animate-in overflow-hidden rounded-xl shadow-lg
           bg-[var(--color-secondary-container)] border border-[var(--color-secondary)]/25"
    style="bottom: {error ? '6.5rem' : '1rem'}; min-width: 320px; max-width: 480px;"
  >
    <div class="flex items-start gap-3 p-4">
      <div
        class="flex-shrink-0 flex h-8 w-8 items-center justify-center rounded-lg
               bg-[var(--color-secondary)]/20"
      >
        <Database size={18} class="text-[var(--color-secondary)]" />
      </div>

      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-[var(--color-secondary)]">
          {#if memoryIndexedToast?.details?.mode === "extract_skills"}
            Skills Extracted
          {:else if memoryIndexedToast?.details?.mode === "extract_insights"}
            Insights Extracted
          {:else}
            Memory Indexed
          {/if}
        </p>
        <p class="mt-1 text-sm text-[var(--color-text-secondary)] break-words">
          {memoryIndexedToast.message}
        </p>
        {#if formatMemoryIndexedToastDetails()}
          <p class="mt-1 text-xs text-[var(--color-text-tertiary)] tabular-nums">
            {formatMemoryIndexedToastDetails()}
          </p>
        {/if}
      </div>
    </div>
  </div>
{/if}

{#if error}
  <div
    class="fixed bottom-4 right-4 z-50 animate-in overflow-hidden rounded-xl shadow-lg
           bg-[var(--color-error-container)] border border-[var(--color-error)]/20"
    style="min-width: 320px; max-width: 480px;"
  >
    <div class="flex items-start gap-3 p-4">
      <div
        class="flex-shrink-0 flex h-8 w-8 items-center justify-center rounded-lg
               bg-[var(--color-error)]/20"
      >
        <AlertCircle size={20} class="text-[var(--color-error)]" />
      </div>

      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-[var(--color-error)]">Error</p>
        <p class="mt-1 text-sm text-[var(--color-text-secondary)] break-words">{error}</p>
      </div>

      <button
        class="flex-shrink-0 p-1 rounded-md hover:bg-[var(--color-error)]/20 transition-colors"
        aria-label="Dismiss error"
        onclick={onDismissError}
      >
        <X size={20} class="text-[var(--color-error)]" />
      </button>
    </div>

    <div class="h-1 bg-[var(--color-error)]/20">
      <div
        class="h-full bg-[var(--color-error)] transition-all duration-100"
        style="width: {errorProgress}%"
      ></div>
    </div>
  </div>
{/if}
