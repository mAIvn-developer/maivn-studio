<script lang="ts">
  import type { InterruptData } from "$lib/types";
  import { CircleHelp } from "lucide-svelte";
  import InterruptInput from "./InterruptInput.svelte";

  interface Props {
    interrupt: InterruptData;
    onSubmit: (interruptId: string, value: string) => void;
    onCancel: (interruptId: string) => void;
  }

  let { interrupt, onSubmit, onCancel }: Props = $props();

  function handleSubmit(value: string) {
    onSubmit(interrupt.interruptId, value);
  }

  function handleCancel() {
    onCancel(interrupt.interruptId);
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      // Don't close on backdrop click - require explicit cancel
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      handleCancel();
    }
  }
</script>

<svelte:window onkeydown={handleKeyDown} />

<!-- Modal Backdrop -->
<div
  class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in"
  onclick={handleBackdropClick}
  onkeydown={handleKeyDown}
  role="dialog"
  aria-modal="true"
  aria-labelledby="interrupt-modal-title"
  tabindex="-1"
>
  <!-- Modal Content -->
  <div
    class="interrupt-modal w-full max-w-md mx-4 animate-scale-in
              bg-[var(--color-bg-secondary)] border border-[var(--color-outline-variant)]"
  >
    <!-- Header -->
    <div class="modal-header px-5 py-4 border-b border-[var(--color-outline-variant)]">
      <div class="flex items-center gap-3">
        <!-- Icon -->
        <div
          class="flex-shrink-0 w-10 h-10 rounded-full bg-[var(--color-warning)]/10 flex items-center justify-center"
        >
          <CircleHelp size={20} class="text-[var(--color-warning)]" />
        </div>

        <div class="flex-1">
          <h2 id="interrupt-modal-title" class="text-lg font-semibold text-[var(--color-text)]">
            Input Required
          </h2>
          <p class="text-sm text-[var(--color-text-secondary)]">
            Tool: <span class="font-mono text-[var(--color-primary)]">{interrupt.toolName}</span>
          </p>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="modal-body px-5 py-4">
      <InterruptInput {interrupt} onSubmit={handleSubmit} onCancel={handleCancel} />
    </div>

    <!-- Footer with progress -->
    {#if interrupt.totalInterrupts > 1}
      <div
        class="modal-footer px-5 py-3 border-t border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs text-[var(--color-text-tertiary)]">
            Interrupt {interrupt.interruptNumber} of {interrupt.totalInterrupts}
          </span>
          <!-- Progress dots -->
          <div class="flex gap-1">
            {#each Array.from({ length: interrupt.totalInterrupts }, (__, idx) => idx) as i}
              <div
                class="w-2 h-2 rounded-full transition-colors"
                class:bg-[var(--color-warning)]={i < interrupt.interruptNumber}
                class:bg-[var(--color-bg-tertiary)]={i >= interrupt.interruptNumber}
              ></div>
            {/each}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .interrupt-modal {
    border-radius: 1rem;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
    overflow: hidden;
  }

  @keyframes fade-in {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @keyframes scale-in {
    from {
      opacity: 0;
      transform: scale(0.95);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  .animate-fade-in {
    animation: fade-in 0.2s ease-out;
  }

  .animate-scale-in {
    animation: scale-in 0.2s ease-out;
  }
</style>
