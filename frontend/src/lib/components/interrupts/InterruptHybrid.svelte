<script lang="ts">
  import type { InterruptData } from "$lib/types";
  import { ChevronUp } from "lucide-svelte";

  interface Props {
    interrupts: InterruptData[];
    onSubmit: (interruptId: string, value: string) => void;
    onCancel: (interruptId: string) => void;
  }

  // Props are required by InterruptContainer interface but not used here
  // (inline cards are handled by ExchangeContainer)
  let { interrupts }: Props = $props();

  // Get queued interrupts (all waiting except the first one which is shown inline)
  const queuedInterrupts = $derived(interrupts.filter((i) => i.status === "waiting").slice(1));

  let showQueueDrawer = $state(false);

  // Auto-show drawer when queue has items
  $effect(() => {
    if (queuedInterrupts.length > 0) {
      showQueueDrawer = true;
    }
  });

  function toggleQueueDrawer() {
    showQueueDrawer = !showQueueDrawer;
  }
</script>

<!-- Hybrid: Queue drawer for pending interrupts (inline cards handled by ExchangeContainer) -->

<!-- Queue drawer shows when there are multiple pending interrupts -->
{#if queuedInterrupts.length > 0}
  <div
    class="queue-drawer fixed bottom-0 left-0 right-0 z-40 transition-transform duration-300"
    class:translate-y-full={!showQueueDrawer}
  >
    <!-- Toggle handle -->
    <button
      type="button"
      onclick={toggleQueueDrawer}
      class="queue-handle w-full flex items-center justify-center gap-2 py-2 bg-[var(--color-warning)]/10 hover:bg-[var(--color-warning)]/20 transition-colors cursor-pointer"
    >
      <div class="w-2 h-2 rounded-full bg-[var(--color-warning)] animate-pulse"></div>
      <span class="text-sm font-medium text-[var(--color-warning)]">
        {queuedInterrupts.length} more interrupt{queuedInterrupts.length > 1 ? "s" : ""} pending
      </span>
      <ChevronUp
        size={16}
        class="text-[var(--color-warning)] transition-transform {showQueueDrawer
          ? 'rotate-180'
          : ''}"
      />
    </button>

    <!-- Queue list -->
    {#if showQueueDrawer}
      <div
        class="queue-content bg-[var(--color-bg-secondary)] border-t border-[var(--color-outline-variant)] max-h-48 overflow-y-auto"
      >
        <div class="px-4 py-2 border-b border-[var(--color-outline-variant)]">
          <h4
            class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wider"
          >
            Upcoming Interrupts
          </h4>
        </div>

        <div class="divide-y divide-[var(--color-outline-variant)]">
          {#each queuedInterrupts as interrupt, index (interrupt.cardId)}
            <div class="px-4 py-3 flex items-center gap-3">
              <!-- Queue position -->
              <div
                class="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center"
              >
                <span class="text-xs font-medium text-[var(--color-text-secondary)]"
                  >{index + 2}</span
                >
              </div>

              <!-- Interrupt info -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-mono text-[var(--color-primary)]"
                    >{interrupt.toolName}</span
                  >
                </div>
                <p class="text-xs text-[var(--color-text-tertiary)] truncate mt-0.5">
                  {interrupt.prompt}
                </p>
              </div>

              <!-- Waiting indicator -->
              <div class="flex-shrink-0">
                <span
                  class="text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-warning)]/10 text-[var(--color-warning)] font-medium"
                >
                  Waiting
                </span>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .queue-drawer {
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.1);
    border-top-left-radius: 1rem;
    border-top-right-radius: 1rem;
    overflow: hidden;
  }

  .queue-handle:focus {
    outline: none;
  }

  .queue-handle:focus-visible {
    background-color: color-mix(in srgb, var(--color-warning) 20%, transparent);
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
  }

  .animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }
</style>
