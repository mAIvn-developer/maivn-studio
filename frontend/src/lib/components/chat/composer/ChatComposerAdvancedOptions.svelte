<script lang="ts">
  import type { BatchInvocationRow, DemoDetails } from "$lib/types";
  import { ChevronRight, Layers3, SquareTerminal } from "lucide-svelte";
  import ChatComposerBatchMatrix from "./ChatComposerBatchMatrix.svelte";

  interface Props {
    hasDemo: boolean;
    hasActiveSession: boolean;
    showSystemInput?: boolean;
    selectedVariant?: string | undefined;
    localSystemMessage?: string;
    batchMode?: boolean;
    batchRunsPerInput?: number;
    batchMaxConcurrency?: number;
    batchAsyncMode?: boolean;
    batchItemCount?: number;
    batchRows?: BatchInvocationRow[];
    demoTools?: DemoDetails["tools"];
    variants: Array<[string, DemoDetails["variants"][string]]>;
    onSelectedVariantChange?: (variant: string | undefined) => void;
  }

  let {
    hasDemo,
    hasActiveSession,
    showSystemInput = $bindable(false),
    selectedVariant = $bindable<string | undefined>(undefined),
    localSystemMessage = $bindable(""),
    batchMode = $bindable(false),
    batchRunsPerInput = $bindable(1),
    batchMaxConcurrency = $bindable(3),
    batchAsyncMode = $bindable(true),
    batchItemCount = 0,
    batchRows = $bindable<BatchInvocationRow[]>([]),
    demoTools = [],
    variants,
    onSelectedVariantChange,
  }: Props = $props();

  function handleVariantChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value || undefined;
    selectedVariant = value;
    onSelectedVariantChange?.(selectedVariant);
  }

  function handleMaxConcurrencyChange(event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    batchMaxConcurrency = Number.isFinite(value) ? Math.max(1, Math.floor(value)) : 1;
  }

  function handleRunsPerInputChange(event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    batchRunsPerInput = Number.isFinite(value) ? Math.max(1, Math.floor(value)) : 1;
  }

  const advancedSetCount = $derived(
    (localSystemMessage.trim() ? 1 : 0) + (selectedVariant ? 1 : 0) + (batchMode ? 1 : 0),
  );
</script>

{#if !hasActiveSession && hasDemo}
  <div class="mb-3">
    <button
      type="button"
      onclick={() => (showSystemInput = !showSystemInput)}
      class="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]
           hover:text-[var(--color-text-secondary)] transition-colors"
      aria-expanded={showSystemInput}
    >
      <ChevronRight
        size={14}
        class="transition-transform duration-200 {showSystemInput ? 'rotate-90' : ''}"
      />
      <SquareTerminal size={14} />
      <span>Advanced</span>
      {#if advancedSetCount > 0}
        <span
          class="px-1.5 py-0.5 rounded-full text-[10px] bg-[var(--color-tertiary)]/20 text-[var(--color-tertiary)]"
        >
          {advancedSetCount} set
        </span>
      {/if}
    </button>

    {#if showSystemInput}
      <div class="mt-2 animate-in space-y-3">
        {#if variants.length > 0}
          <div class="flex items-center gap-2">
            <label for="variant-select" class="text-xs text-[var(--color-text-secondary)] shrink-0"
              >Variant</label
            >
            <select
              id="variant-select"
              value={selectedVariant ?? ""}
              onchange={handleVariantChange}
              class="flex-1 rounded-lg border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]
                   px-2.5 py-1.5 text-xs text-[var(--color-text)]
                   focus:outline-none focus:border-[var(--color-tertiary)]/50"
            >
              <option value="">Default</option>
              {#each variants as [id, variant]}
                <option value={id}>{id} - {variant.description}</option>
              {/each}
            </select>
          </div>
        {/if}

        <div>
          <label for="system-message" class="text-xs text-[var(--color-text-secondary)] block mb-1"
            >System Message</label
          >
          <textarea
            id="system-message"
            bind:value={localSystemMessage}
            placeholder="Enter system instructions..."
            rows={2}
            class="w-full rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-outline-variant)]
                 px-3 py-2 text-xs text-[var(--color-text)] placeholder-[var(--color-text-tertiary)]
                 focus:outline-none focus:border-[var(--color-tertiary)]/50
                 resize-none min-h-[48px] max-h-[120px]"
            style="field-sizing: content;"
          ></textarea>
        </div>

        <div class="batch-panel">
          <label class="batch-toggle-row">
            <div class="batch-toggle-copy">
              <span class="batch-title">
                <Layers3 size={14} />
                Batch
              </span>
              <span class="batch-description">
                {batchItemCount}
                {batchItemCount === 1 ? "item" : "items"}
              </span>
            </div>
            <div class="switch-shell">
              <input type="checkbox" class="peer sr-only" bind:checked={batchMode} />
              <span class="switch-track"></span>
              <span class="switch-thumb"></span>
            </div>
          </label>

          {#if batchMode}
            <div class="batch-controls">
              <label class="batch-field">
                <span>Instances</span>
                <input
                  type="number"
                  min="1"
                  max="24"
                  value={batchRunsPerInput}
                  onchange={handleRunsPerInputChange}
                />
              </label>

              <label class="batch-field">
                <span>Max concurrent</span>
                <input
                  type="number"
                  min="1"
                  max="24"
                  value={batchMaxConcurrency}
                  onchange={handleMaxConcurrencyChange}
                />
              </label>

              <label class="batch-check">
                <input type="checkbox" bind:checked={batchAsyncMode} />
                <span>Async batch</span>
              </label>
            </div>

            <ChatComposerBatchMatrix
              bind:rows={batchRows}
              {variants}
              tools={demoTools}
              {selectedVariant}
            />
          {/if}
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .batch-panel {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-bg-tertiary) 38%, transparent);
    padding: 0.75rem;
  }

  .batch-toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.875rem;
    cursor: pointer;
  }

  .batch-toggle-copy {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.125rem;
  }

  .batch-title {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.75rem;
    font-weight: 650;
    color: var(--color-text-secondary);
  }

  .batch-description {
    font-size: 0.6875rem;
    color: var(--color-text-tertiary);
  }

  .batch-controls {
    margin-top: 0.75rem;
    margin-bottom: 0.75rem;
    display: grid;
    grid-template-columns: minmax(7rem, 10rem) minmax(7rem, 10rem) 1fr;
    gap: 0.75rem;
    align-items: end;
  }

  .batch-field {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .batch-field input {
    width: 100%;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: var(--color-bg-secondary);
    color: var(--color-text);
    padding: 0.4rem 0.5rem;
    font-size: 0.75rem;
  }

  .batch-check {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    min-height: 2rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .batch-check input {
    accent-color: var(--color-tertiary);
  }

  .switch-shell {
    position: relative;
    width: 2.125rem;
    height: 1.25rem;
    flex-shrink: 0;
    pointer-events: none;
  }

  .switch-track {
    position: absolute;
    inset: 0;
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-outline) 36%, transparent);
    transition: background-color var(--transition-fast);
  }

  .switch-thumb {
    position: absolute;
    top: 0.125rem;
    left: 0.125rem;
    width: 1rem;
    height: 1rem;
    border-radius: var(--radius-full);
    background: #fff;
    transition: transform var(--transition-fast);
  }

  .peer:checked ~ .switch-track {
    background: var(--color-tertiary);
  }

  .peer:checked ~ .switch-thumb {
    transform: translateX(0.875rem);
  }

  @media (max-width: 520px) {
    .batch-controls {
      grid-template-columns: 1fr;
    }
  }
</style>
