<script lang="ts">
  import type { InterruptCardStatus, InterruptChoice, InterruptData } from "$lib/types";
  import { Check, X, Loader2, ArrowRight } from "lucide-svelte";
  import { analyzePrompt } from "$lib/utils/interruptDetection";

  interface Props {
    interrupt: InterruptData;
    onSubmit: (value: string) => void;
    onCancel: () => void;
    compact?: boolean;
  }

  let { interrupt, onSubmit, onCancel, compact = false }: Props = $props();

  let inputValue = $state("");
  let inputElement: HTMLInputElement | null = $state(null);

  // Frozen submitted value - captured when status becomes completed
  // This prevents the displayed value from changing if the interrupt is reused
  let frozenSubmittedValue = $state<string | undefined>(undefined);

  // Freeze the submitted value when status becomes completed
  $effect(() => {
    if (
      interrupt.status === "completed" &&
      frozenSubmittedValue === undefined &&
      interrupt.submittedValue
    ) {
      frozenSubmittedValue = interrupt.submittedValue;
    }
  });

  // Analyze the prompt to detect input type
  const analysis = $derived(analyzePrompt(interrupt.prompt));
  // Use backend type if it's specific (not "text"), otherwise use frontend detection as fallback
  const inputType = $derived(
    interrupt.inputType && interrupt.inputType !== "text"
      ? interrupt.inputType
      : analysis.inputType,
  );
  // Use backend choices if provided, otherwise use detected choices
  const choices = $derived(
    interrupt.choices && interrupt.choices.length > 0 ? interrupt.choices : analysis.choices,
  );
  const cleanPrompt = $derived(analysis.cleanPrompt);

  // Focus input when component mounts and status is waiting
  $effect(() => {
    if (interrupt.status === "waiting" && inputElement) {
      inputElement.focus();
    }
  });

  function handleSubmit() {
    if (inputValue.trim() && interrupt.status === "waiting") {
      onSubmit(inputValue.trim());
    }
  }

  function handleChoiceSelect(choice: InterruptChoice) {
    if (interrupt.status === "waiting") {
      onSubmit(choice.value);
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    }
  }

  // Status configuration
  const statusConfig: Record<
    InterruptCardStatus,
    { color: string; bg: string; borderColor: string }
  > = {
    waiting: {
      color: "var(--color-warning)",
      bg: "rgba(245, 158, 11, 0.1)",
      borderColor: "rgb(245, 158, 11)",
    },
    submitting: {
      color: "var(--color-secondary)",
      bg: "color-mix(in srgb, var(--color-secondary) 10%, transparent)",
      borderColor: "rgb(96, 165, 250)",
    },
    completed: {
      color: "var(--color-success)",
      bg: "rgba(52, 211, 153, 0.1)",
      borderColor: "rgb(52, 211, 153)",
    },
    cancelled: {
      color: "var(--color-text-tertiary)",
      bg: "rgba(156, 163, 175, 0.1)",
      borderColor: "rgb(156, 163, 175)",
    },
  };

  const status = $derived(statusConfig[interrupt.status]);
  const isDisabled = $derived(interrupt.status !== "waiting");

  // Get the HTML input type based on detected type
  function getHtmlInputType(): string {
    switch (inputType) {
      case "number":
        return "number";
      case "email":
        return "email";
      case "password":
        return "password";
      default:
        return "text";
    }
  }

  // Check if we should show choice buttons instead of text input
  const showChoiceButtons = $derived(
    inputType === "boolean" || inputType === "confirmation" || inputType === "choice",
  );
</script>

<div class="interrupt-input" class:compact>
  <!-- Prompt -->
  <div
    class="prompt-text text-sm text-[var(--color-text)]"
    class:mb-3={!compact}
    class:mb-2={compact}
  >
    {cleanPrompt}
  </div>

  {#if interrupt.status === "completed"}
    <!-- Completed state: show submitted value -->
    <div class="completed-value px-3 py-2 rounded-lg" style="background: {status.bg}">
      <div
        class="text-[10px] uppercase tracking-wider mb-1 font-medium"
        style="color: {status.color}"
      >
        Submitted
      </div>
      <div class="text-sm text-[var(--color-text)] font-mono">
        {#if inputType === "password"}
          {"*".repeat(8)}
        {:else}
          {frozenSubmittedValue ?? interrupt.submittedValue}
        {/if}
      </div>
    </div>
  {:else if interrupt.status === "cancelled"}
    <!-- Cancelled state -->
    <div class="cancelled-value px-3 py-2 rounded-lg" style="background: {status.bg}">
      <div class="text-sm text-[var(--color-text-tertiary)] italic">Cancelled</div>
    </div>
  {:else if showChoiceButtons}
    <!-- Choice buttons for boolean/confirmation/choice types -->
    <div class="choice-buttons flex flex-wrap gap-2 mb-3">
      {#each choices as choice (choice.value)}
        <button
          type="button"
          onclick={() => handleChoiceSelect(choice)}
          disabled={isDisabled}
          class="choice-btn px-4 py-2 text-sm rounded-lg font-medium transition-all
                 border-2 hover:scale-[1.02] active:scale-[0.98]
                 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          class:confirm-btn={choice.value === "yes" ||
            choice.label.toLowerCase() === "confirm" ||
            choice.label.toLowerCase() === "yes"}
          class:cancel-btn={choice.value === "no" ||
            choice.label.toLowerCase() === "cancel" ||
            choice.label.toLowerCase() === "no"}
          class:choice-option-btn={inputType === "choice"}
        >
          {#if choice.value === "yes" || choice.label.toLowerCase() === "yes" || choice.label.toLowerCase() === "confirm"}
            <Check size={16} class="mr-1.5 inline" />
          {:else if choice.value === "no" || choice.label.toLowerCase() === "no" || choice.label.toLowerCase() === "cancel"}
            <X size={16} class="mr-1.5 inline" />
          {/if}
          {choice.label}
        </button>
      {/each}
    </div>

    <!-- Cancel button for choice inputs -->
    <div class="actions flex items-center justify-between">
      <div class="text-[11px] text-[var(--color-text-tertiary)]">
        {#if interrupt.totalInterrupts > 1}
          Interrupt {interrupt.interruptNumber} of {interrupt.totalInterrupts}
        {/if}
      </div>
      <button
        type="button"
        onclick={onCancel}
        disabled={isDisabled}
        class="px-3 py-1.5 text-sm rounded-lg transition-colors
               text-[var(--color-text-secondary)] hover:text-[var(--color-text)]
               hover:bg-[var(--color-bg-tertiary)]
               disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Skip
      </button>
    </div>
  {:else}
    <!-- Text/Number/Email/Password input field -->
    <div class="input-wrapper mb-3">
      <div class="relative">
        <input
          bind:this={inputElement}
          bind:value={inputValue}
          type={getHtmlInputType()}
          placeholder={inputType === "number"
            ? "Enter a number..."
            : inputType === "email"
              ? "Enter email address..."
              : inputType === "password"
                ? "Enter value..."
                : "Enter your response..."}
          disabled={isDisabled}
          onkeydown={handleKeyDown}
          class="w-full px-3 py-2 text-sm rounded-lg border transition-colors
                 bg-[var(--color-bg-primary)] text-[var(--color-text)]
                 placeholder-[var(--color-text-tertiary)]
                 focus:outline-none focus:ring-2"
          style="border-color: {isDisabled ? 'var(--color-outline-variant)' : status.borderColor};
                 --tw-ring-color: {status.borderColor};"
        />
        <!-- Input type indicator -->
        {#if inputType !== "text"}
          <div
            class="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] uppercase tracking-wider
                   px-1.5 py-0.5 rounded bg-[var(--color-bg-tertiary)] text-[var(--color-text-tertiary)]"
          >
            {inputType}
          </div>
        {/if}
      </div>
    </div>

    <!-- Actions -->
    <div class="actions flex items-center justify-between">
      <!-- Progress indicator -->
      <div class="text-[11px] text-[var(--color-text-tertiary)]">
        {#if interrupt.totalInterrupts > 1}
          Interrupt {interrupt.interruptNumber} of {interrupt.totalInterrupts}
        {/if}
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          onclick={onCancel}
          disabled={isDisabled}
          class="px-3 py-1.5 text-sm rounded-lg transition-colors
                 text-[var(--color-text-secondary)] hover:text-[var(--color-text)]
                 hover:bg-[var(--color-bg-tertiary)]
                 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>

        <button
          type="button"
          onclick={handleSubmit}
          disabled={isDisabled || !inputValue.trim()}
          class="px-4 py-1.5 text-sm rounded-lg font-medium transition-colors
                 bg-[var(--color-primary)] text-white
                 hover:bg-[var(--color-primary-hover)]
                 disabled:opacity-50 disabled:cursor-not-allowed
                 flex items-center gap-2"
        >
          {#if interrupt.status === "submitting"}
            <Loader2 size={16} class="animate-spin" />
            Submitting...
          {:else}
            Submit
            <ArrowRight size={16} />
          {/if}
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .interrupt-input {
    padding: 0;
  }

  .interrupt-input.compact .prompt-text {
    font-size: 0.8125rem;
  }

  .interrupt-input.compact input {
    padding: 0.375rem 0.625rem;
    font-size: 0.8125rem;
  }

  .interrupt-input.compact .actions button {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
  }

  /* Choice buttons styling */
  .choice-btn {
    min-width: 80px;
  }

  .confirm-btn {
    border-color: rgb(52, 211, 153);
    background: rgba(52, 211, 153, 0.1);
    color: rgb(52, 211, 153);
  }

  .confirm-btn:hover:not(:disabled) {
    background: rgba(52, 211, 153, 0.2);
  }

  .cancel-btn {
    border-color: rgb(239, 68, 68);
    background: rgba(239, 68, 68, 0.1);
    color: rgb(239, 68, 68);
  }

  .cancel-btn:hover:not(:disabled) {
    background: rgba(239, 68, 68, 0.2);
  }

  .choice-option-btn {
    border-color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 10%, transparent);
    color: var(--color-secondary);
  }

  .choice-option-btn:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-secondary) 20%, transparent);
  }

  :global(.animate-spin) {
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
