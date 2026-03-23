<script lang="ts">
  import type { InterruptData } from "$lib/types";
  import { ChevronUp, ChevronDown, CircleHelp } from "lucide-svelte";
  import InterruptInput from "./InterruptInput.svelte";

  interface Props {
    interrupt: InterruptData;
    onSubmit: (interruptId: string, value: string) => void;
    onCancel: (interruptId: string) => void;
  }

  let { interrupt, onSubmit, onCancel }: Props = $props();

  let isMinimized = $state(false);

  function handleSubmit(value: string) {
    onSubmit(interrupt.interruptId, value);
  }

  function handleCancel() {
    onCancel(interrupt.interruptId);
  }

  function toggleMinimize() {
    isMinimized = !isMinimized;
  }
</script>

<!-- Bottom Drawer -->
<div
  class="interrupt-drawer fixed bottom-0 left-0 right-0 z-40 animate-slide-up
         bg-[var(--color-bg-secondary)] border-t border-[var(--color-outline-variant)]"
  class:minimized={isMinimized}
>
  <!-- Handle bar for dragging/minimize -->
  <button
    type="button"
    class="drawer-handle w-full flex items-center justify-center py-2 cursor-pointer hover:bg-[var(--color-bg-tertiary)] transition-colors"
    onclick={toggleMinimize}
    aria-label={isMinimized ? "Expand drawer" : "Minimize drawer"}
  >
    <div class="flex items-center gap-2">
      <div class="w-12 h-1 rounded-full bg-[var(--color-outline-variant)]"></div>
      <ChevronUp
        size={16}
        class="text-[var(--color-text-tertiary)] transition-transform {!isMinimized
          ? 'rotate-180'
          : ''}"
      />
    </div>
  </button>

  <!-- Minimized header -->
  {#if isMinimized}
    <div class="minimized-header px-4 py-2 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="w-2 h-2 rounded-full bg-[var(--color-warning)] animate-pulse"></div>
        <span class="text-sm font-medium text-[var(--color-text)]"> Input Required </span>
        <span class="text-xs text-[var(--color-text-secondary)] font-mono">
          {interrupt.toolName}
        </span>
      </div>
      <button
        type="button"
        onclick={toggleMinimize}
        class="text-xs text-[var(--color-primary)] hover:underline"
      >
        Expand
      </button>
    </div>
  {:else}
    <!-- Expanded content -->
    <div class="drawer-content">
      <!-- Header -->
      <div
        class="drawer-header px-4 py-3 border-b border-[var(--color-outline-variant)] flex items-center justify-between"
      >
        <div class="flex items-center gap-3">
          <div
            class="flex-shrink-0 w-8 h-8 rounded-lg bg-[var(--color-warning)]/10 flex items-center justify-center"
          >
            <CircleHelp size={16} class="text-[var(--color-warning)]" />
          </div>
          <div>
            <h3 class="text-sm font-semibold text-[var(--color-text)]">Input Required</h3>
            <p class="text-xs text-[var(--color-text-secondary)]">
              <span class="font-mono text-[var(--color-primary)]">{interrupt.toolName}</span>
              {#if interrupt.totalInterrupts > 1}
                <span class="ml-2"
                  >({interrupt.interruptNumber} of {interrupt.totalInterrupts})</span
                >
              {/if}
            </p>
          </div>
        </div>

        <button
          type="button"
          onclick={toggleMinimize}
          class="p-1.5 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors"
          aria-label="Minimize drawer"
        >
          <ChevronDown size={16} class="text-[var(--color-text-tertiary)]" />
        </button>
      </div>

      <!-- Body -->
      <div class="drawer-body px-4 py-4">
        <InterruptInput {interrupt} onSubmit={handleSubmit} onCancel={handleCancel} />
      </div>
    </div>
  {/if}
</div>

<style>
  .interrupt-drawer {
    border-top-left-radius: 1rem;
    border-top-right-radius: 1rem;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
    max-height: 50vh;
    overflow: hidden;
  }

  .interrupt-drawer.minimized {
    max-height: auto;
  }

  .drawer-handle:focus {
    outline: none;
  }

  .drawer-handle:focus-visible {
    background-color: var(--color-bg-tertiary);
  }

  @keyframes slide-up {
    from {
      transform: translateY(100%);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  .animate-slide-up {
    animation: slide-up 0.3s ease-out;
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
