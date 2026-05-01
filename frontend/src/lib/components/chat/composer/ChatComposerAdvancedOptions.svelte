<script lang="ts">
  import type {
    BatchInvocationRow,
    DemoDetails,
    ModelToolOption,
    StructuredOutputConfig,
  } from "$lib/types";
  import { ChevronRight, Layers3, SquareTerminal } from "lucide-svelte";
  import ChatComposerBatchMatrix from "./ChatComposerBatchMatrix.svelte";
  import StructuredOutputSelector from "../../settings/StructuredOutputSelector.svelte";

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
    structuredOutputConfig?: StructuredOutputConfig;
    availableModelTools?: ModelToolOption[];
    onSelectedVariantChange?: (variant: string | undefined) => void;
    onStructuredOutputChange?: (config: StructuredOutputConfig) => void;
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
    structuredOutputConfig,
    availableModelTools = [],
    onSelectedVariantChange,
    onStructuredOutputChange,
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
    (localSystemMessage.trim() ? 1 : 0) +
      (selectedVariant ? 1 : 0) +
      (batchMode ? 1 : 0) +
      (structuredOutputConfig?.enabled ? 1 : 0),
  );
</script>

{#if !hasActiveSession && hasDemo}
  <div class="advanced-options" class:open={showSystemInput}>
    <button
      type="button"
      onclick={() => (showSystemInput = !showSystemInput)}
      class="advanced-toggle"
      aria-expanded={showSystemInput}
    >
      <span class="advanced-toggle-left">
        <ChevronRight size={14} class="advanced-chevron" />
        <SquareTerminal size={14} />
        <span>Advanced</span>
      </span>
      <span class="advanced-toggle-right">
        {#if advancedSetCount > 0}
          <span class="advanced-count">{advancedSetCount} set</span>
        {/if}
      </span>
    </button>

    {#if showSystemInput}
      <div class="advanced-body animate-in">
        {#if variants.length > 0}
          <label class="field-row" for="variant-select">
            <span>Variant</span>
            <select
              id="variant-select"
              value={selectedVariant ?? ""}
              onchange={handleVariantChange}
            >
              <option value="">Default</option>
              {#each variants as [id, variant]}
                <option value={id}>{id} - {variant.description}</option>
              {/each}
            </select>
          </label>
        {/if}

        <label class="field-stack" for="system-message">
          <span>System Message</span>
          <textarea
            id="system-message"
            bind:value={localSystemMessage}
            placeholder="Enter system instructions..."
            rows={2}
            style="field-sizing: content;"
          ></textarea>
        </label>

        <div class="advanced-card-grid">
          <div class="batch-panel" class:active={batchMode}>
            <label class="batch-toggle-row">
              <span class="batch-toggle-copy">
                <span class="batch-title">
                  <Layers3 size={14} />
                  Batch
                </span>
                <span class="batch-description">
                  {batchItemCount}
                  {batchItemCount === 1 ? "item" : "items"}
                </span>
              </span>
              <span class="switch-shell">
                <input type="checkbox" class="peer sr-only" bind:checked={batchMode} />
                <span class="switch-track"></span>
                <span class="switch-thumb"></span>
              </span>
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

          {#if structuredOutputConfig && onStructuredOutputChange}
            <div class="structured-panel" class:active={structuredOutputConfig.enabled}>
              <StructuredOutputSelector
                config={structuredOutputConfig}
                availableTools={availableModelTools}
                onConfigChange={onStructuredOutputChange}
              />
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .advanced-options {
    margin-bottom: 0.7rem;
  }

  .advanced-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    width: 100%;
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--color-text-secondary);
    padding: 0.35rem 0.45rem;
    cursor: pointer;
    font-size: 0.75rem;
    font-weight: 600;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast);
  }

  .advanced-toggle:hover,
  .advanced-options.open .advanced-toggle {
    border-color: var(--color-outline-variant);
    background: color-mix(in srgb, var(--color-bg-secondary) 58%, transparent);
    color: var(--color-text);
  }

  .advanced-toggle-left,
  .advanced-toggle-right {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    min-width: 0;
  }

  :global(.advanced-chevron) {
    color: var(--color-text-tertiary);
    transition: transform var(--transition-fast);
  }

  .advanced-options.open :global(.advanced-chevron) {
    transform: rotate(90deg);
  }

  .advanced-count {
    border: 1px solid color-mix(in srgb, var(--color-secondary) 28%, transparent);
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-secondary) 12%, transparent);
    color: var(--color-secondary);
    padding: 0.1rem 0.45rem;
    font-size: 0.66rem;
    font-weight: 700;
  }

  .advanced-body {
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    margin-top: 0.45rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-bg-secondary) 62%, transparent);
    padding: 0.75rem;
    box-shadow: var(--shadow-sm);
  }

  .field-row,
  .field-stack {
    display: flex;
    gap: 0.5rem;
    color: var(--color-text-secondary);
    font-size: 0.72rem;
    font-weight: 650;
  }

  .field-row {
    align-items: center;
  }

  .field-row > span {
    flex-shrink: 0;
    min-width: 4.5rem;
  }

  .field-stack {
    flex-direction: column;
    gap: 0.3rem;
  }

  .field-row select,
  .field-stack textarea {
    width: 100%;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
    font-size: 0.78rem;
  }

  .field-row select {
    min-height: 2.1rem;
    padding: 0.35rem 0.55rem;
  }

  .field-stack textarea {
    min-height: 3.4rem;
    max-height: 8rem;
    resize: none;
    padding: 0.65rem 0.75rem;
    line-height: 1.45;
  }

  .field-row select:focus,
  .field-stack textarea:focus {
    border-color: color-mix(in srgb, var(--color-secondary) 58%, var(--color-outline-variant));
    outline: none;
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-secondary) 16%, transparent);
  }

  .field-stack textarea::placeholder {
    color: var(--color-text-tertiary);
  }

  .advanced-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
    gap: 0.65rem;
  }

  .structured-panel {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-bg-tertiary) 22%, transparent);
    min-width: 0;
    padding: 0.55rem;
    transition:
      border-color var(--transition-fast),
      background-color var(--transition-fast);
  }

  .structured-panel.active {
    border-color: color-mix(in srgb, var(--color-secondary) 34%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-secondary) 5%, var(--color-bg-secondary));
  }

  .batch-panel {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-bg-tertiary) 22%, transparent);
    min-width: 0;
    padding: 0.65rem;
    transition:
      border-color var(--transition-fast),
      background-color var(--transition-fast);
  }

  .batch-panel.active {
    border-color: color-mix(in srgb, var(--color-secondary) 34%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-secondary) 5%, var(--color-bg-secondary));
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
    font-size: 0.78rem;
    font-weight: 650;
    color: var(--color-text);
  }

  .batch-description {
    font-size: 0.6875rem;
    color: var(--color-text-tertiary);
  }

  .batch-controls {
    margin-top: 0.75rem;
    margin-bottom: 0.75rem;
    display: grid;
    grid-template-columns: minmax(6.5rem, 8.5rem) minmax(7rem, 9rem) 1fr;
    gap: 0.55rem;
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
    background: var(--color-bg);
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
    accent-color: var(--color-secondary);
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
    background: var(--color-secondary);
  }

  .peer:checked ~ .switch-thumb {
    transform: translateX(0.875rem);
  }

  @media (max-width: 520px) {
    .field-row {
      align-items: stretch;
      flex-direction: column;
      gap: 0.3rem;
    }

    .field-row > span {
      min-width: 0;
    }

    .advanced-card-grid {
      grid-template-columns: 1fr;
    }

    .batch-controls {
      grid-template-columns: 1fr;
    }
  }
</style>
