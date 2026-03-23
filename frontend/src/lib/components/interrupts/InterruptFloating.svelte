<script lang="ts">
  import type { InterruptData } from "$lib/types";
  import { ChevronUp, ChevronDown } from "lucide-svelte";
  import InterruptInput from "./InterruptInput.svelte";

  interface Props {
    interrupt: InterruptData;
    onSubmit: (interruptId: string, value: string) => void;
    onCancel: (interruptId: string) => void;
  }

  let { interrupt, onSubmit, onCancel }: Props = $props();

  let isExpanded = $state(true);

  function handleSubmit(value: string) {
    onSubmit(interrupt.interruptId, value);
  }

  function handleCancel() {
    onCancel(interrupt.interruptId);
  }

  function toggleExpanded() {
    isExpanded = !isExpanded;
  }
</script>

<!-- Floating Card -->
<div
  class="interrupt-floating fixed bottom-4 right-4 z-40 animate-slide-in"
  class:collapsed={!isExpanded}
>
  {#if !isExpanded}
    <!-- Collapsed state - just a notification badge -->
    <button
      type="button"
      onclick={toggleExpanded}
      class="collapsed-badge flex items-center gap-2 px-3 py-2 rounded-full shadow-lg transition-transform hover:scale-105
             bg-[var(--color-bg-secondary)] border border-[var(--color-outline-variant)]"
    >
      <div class="w-2 h-2 rounded-full bg-[var(--color-warning)] animate-pulse"></div>
      <span class="text-sm font-medium text-[var(--color-text)]">Input Required</span>
      <ChevronUp size={16} class="text-[var(--color-text-secondary)]" />
    </button>
  {:else}
    <!-- Expanded state -->
    <div
      class="floating-card bg-[var(--color-bg-secondary)] border border-[var(--color-outline-variant)]"
    >
      <!-- Header -->
      <div
        class="card-header px-4 py-3 flex items-center justify-between border-b border-[var(--color-outline-variant)]"
      >
        <div class="flex items-center gap-2">
          <div class="w-2 h-2 rounded-full bg-[var(--color-warning)] animate-pulse"></div>
          <span class="text-sm font-semibold text-[var(--color-text)]">INPUT REQUIRED</span>
        </div>

        <div class="flex items-center gap-1">
          <button
            type="button"
            onclick={toggleExpanded}
            class="p-1 rounded hover:bg-[var(--color-bg-tertiary)] transition-colors"
            aria-label="Minimize"
          >
            <ChevronDown size={16} class="text-[var(--color-text-tertiary)]" />
          </button>
        </div>
      </div>

      <!-- Tool info -->
      <div class="px-4 py-2 bg-[var(--color-bg-tertiary)]">
        <span class="text-xs text-[var(--color-text-secondary)]">Tool: </span>
        <span class="text-xs font-mono text-[var(--color-primary)]">{interrupt.toolName}</span>
        {#if interrupt.totalInterrupts > 1}
          <span class="text-xs text-[var(--color-text-tertiary)] ml-2">
            ({interrupt.interruptNumber} of {interrupt.totalInterrupts})
          </span>
        {/if}
      </div>

      <!-- Body -->
      <div class="card-body px-4 py-3">
        <InterruptInput
          {interrupt}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          compact={true}
        />
      </div>
    </div>
  {/if}
</div>

<style>
  .interrupt-floating {
    max-width: 360px;
    width: 100%;
  }

  .interrupt-floating.collapsed {
    max-width: none;
    width: auto;
  }

  .floating-card {
    border-radius: 0.75rem;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }

  @keyframes slide-in {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  .animate-slide-in {
    animation: slide-in 0.3s ease-out;
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
