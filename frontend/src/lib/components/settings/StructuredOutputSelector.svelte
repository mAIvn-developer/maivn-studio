<script lang="ts">
  import { TableProperties, ChevronDown, Check } from "lucide-svelte";
  import type { ModelToolOption, StructuredOutputConfig } from "$lib/types";

  interface Props {
    config: StructuredOutputConfig;
    availableTools?: ModelToolOption[];
    disabled?: boolean;
    onConfigChange: (config: StructuredOutputConfig) => void;
  }

  let { config, availableTools = [], disabled = false, onConfigChange }: Props = $props();

  // Collapsed by default unless the user just enabled it. The body takes
  // vertical space, so we don't pin it open.
  let isExpanded = $state(false);

  function toggleEnabled(): void {
    if (config.enabled) {
      onConfigChange({ enabled: false, selectedTool: undefined, schema: undefined });
    } else {
      onConfigChange({ ...config, enabled: true });
      isExpanded = true;
    }
  }

  function selectTool(toolName: string | null): void {
    if (!toolName) {
      // "Auto": the backend resolves the app's final model tool.
      onConfigChange({ ...config, selectedTool: undefined, schema: undefined });
      return;
    }
    const tool = availableTools.find((t) => t.name === toolName);
    onConfigChange({
      ...config,
      selectedTool: toolName,
      schema: tool
        ? {
            name: tool.name,
            description: tool.description,
            schema: tool.schema || {},
          }
        : undefined,
    });
  }

  const summaryText = $derived.by(() => {
    if (!config.enabled) return "off";
    if (config.selectedTool) return config.selectedTool;
    return "auto (final tool)";
  });
</script>

<div class="so">
  <header class="so-header">
    <span class="so-icon" class:active={config.enabled}>
      <TableProperties size={13} />
    </span>
    <div class="so-title-block">
      <span class="so-title">Structured Output</span>
      <span class="so-summary">{summaryText}</span>
    </div>
    <label class="so-switch" class:disabled>
      <input
        type="checkbox"
        class="peer sr-only"
        checked={config.enabled}
        onchange={toggleEnabled}
        {disabled}
        aria-label="Toggle structured output"
      />
      <span class="switch-track"></span>
      <span class="switch-thumb"></span>
    </label>
    <button
      type="button"
      class="so-chevron"
      onclick={() => (isExpanded = !isExpanded)}
      aria-expanded={isExpanded}
      aria-label={isExpanded ? "Collapse" : "Expand"}
    >
      <ChevronDown size={14} style={isExpanded ? "transform: rotate(180deg);" : ""} />
    </button>
  </header>

  {#if isExpanded && config.enabled}
    <div class="so-body">
      {#if availableTools.length > 0}
        <label class="field">
          <span class="field-label">Schema source</span>
          <select
            value={config.selectedTool || ""}
            onchange={(e) => selectTool((e.target as HTMLSelectElement).value || null)}
            {disabled}
          >
            <option value="">Auto (use the app's final tool)</option>
            {#each availableTools as tool}
              <option value={tool.name}>{tool.name}</option>
            {/each}
          </select>
        </label>

        {#if config.selectedTool}
          <div class="selected-tool">
            <Check size={12} class="selected-check" />
            <div class="selected-text">
              <span class="selected-name">{config.selectedTool}</span>
              {#if config.schema?.description}
                <span class="selected-desc">{config.schema.description}</span>
              {/if}
            </div>
          </div>
        {/if}
      {:else}
        <p class="so-empty">
          This app exposes no tools to use as a schema. Structured output needs a model tool (a
          final tool backed by a Pydantic model).
        </p>
      {/if}
    </div>
  {/if}
</div>

<style>
  .so {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .so-header {
    display: grid;
    grid-template-columns: auto 1fr auto auto;
    align-items: center;
    gap: 0.6rem;
    padding: 0.1rem 0.05rem;
  }

  .so-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: var(--radius-sm);
    background: var(--color-bg);
    color: var(--color-text-tertiary);
  }
  .so-icon.active {
    background: color-mix(in srgb, var(--color-secondary) 18%, transparent);
    color: var(--color-secondary);
  }

  .so-title-block {
    display: flex;
    flex-direction: column;
    gap: 0.05rem;
    min-width: 0;
  }
  .so-title {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--color-text);
  }
  .so-summary {
    font-size: 0.66rem;
    color: var(--color-text-tertiary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Switch — same shape as the batch toggle so they read as one family. */
  .so-switch {
    position: relative;
    width: 2.125rem;
    height: 1.25rem;
    flex-shrink: 0;
    cursor: pointer;
  }
  .so-switch.disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .switch-track {
    position: absolute;
    inset: 0;
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-outline) 36%, transparent);
    transition: background-color var(--transition-fast);
    pointer-events: none;
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
    pointer-events: none;
  }
  .so-switch .peer:checked ~ .switch-track {
    background: var(--color-secondary);
  }
  .so-switch .peer:checked ~ .switch-thumb {
    transform: translateX(0.875rem);
  }
  .so-switch .peer:focus-visible ~ .switch-track {
    outline: 2px solid color-mix(in srgb, var(--color-secondary) 60%, transparent);
    outline-offset: 1px;
  }

  .so-chevron {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: var(--radius-sm);
    border: 0;
    background: transparent;
    color: var(--color-text-tertiary);
    cursor: pointer;
    transition: background-color var(--transition-fast);
  }
  .so-chevron:hover {
    background: color-mix(in srgb, var(--color-bg-tertiary) 60%, transparent);
    color: var(--color-text);
  }
  .so-chevron :global(svg) {
    transition: transform var(--transition-fast);
  }

  .so-body {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.6rem 0 0;
    border: 0;
    border-top: 1px dashed var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: transparent;
  }

  .so-empty {
    margin: 0;
    font-size: 0.7rem;
    line-height: 1.4;
    color: var(--color-text-tertiary);
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .field-label {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.66rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-tertiary);
  }
  .field select {
    width: 100%;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-sm);
    background: var(--color-bg-secondary);
    color: var(--color-text);
    padding: 0.35rem 0.55rem;
    font-size: 0.78rem;
  }
  .field select:focus {
    outline: 1px solid color-mix(in srgb, var(--color-secondary) 60%, var(--color-outline));
    border-color: color-mix(in srgb, var(--color-secondary) 60%, var(--color-outline-variant));
  }

  .selected-tool {
    display: flex;
    align-items: flex-start;
    gap: 0.4rem;
    padding: 0.4rem 0.5rem;
    border: 1px solid color-mix(in srgb, var(--color-secondary) 25%, var(--color-outline-variant));
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-secondary) 6%, transparent);
  }
  :global(.selected-check) {
    color: var(--color-secondary);
    margin-top: 0.15rem;
    flex-shrink: 0;
  }
  .selected-text {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
  }
  .selected-name {
    font-size: 0.74rem;
    font-weight: 600;
    color: var(--color-text);
  }
  .selected-desc {
    font-size: 0.66rem;
    color: var(--color-text-tertiary);
    line-height: 1.35;
  }
</style>
