<script lang="ts">
  import { TableProperties, ChevronDown, Check, Info } from "lucide-svelte";
  import type { ModelTier, ModelToolOption, StructuredOutputConfig } from "$lib/types";

  interface Props {
    config: StructuredOutputConfig;
    availableTools?: ModelToolOption[];
    disabled?: boolean;
    onConfigChange: (config: StructuredOutputConfig) => void;
  }

  let { config, availableTools = [], disabled = false, onConfigChange }: Props = $props();

  // Collapsed by default unless the user just enabled it. The body takes
  // significant vertical space, so we don't pin it open.
  let isExpanded = $state(false);
  let advancedOpen = $state(false);
  let showSchemaEditor = $state(false);
  let customSchemaText = $state("");
  let schemaError = $state<string | null>(null);

  // Schema-fill is a SEPARATE model pass that takes the agent's free-form
  // response and re-prompts a model to convert it to the requested JSON
  // schema. Empty string here means "use the agent's default tier".
  const modelChoices: Array<{ value: ModelTier | ""; label: string }> = [
    { value: "", label: "Use agent default" },
    { value: "fast", label: "fast" },
    { value: "balanced", label: "balanced" },
    { value: "max", label: "max" },
  ];

  function setStructuredModel(value: string): void {
    const next: ModelTier | undefined = value === "" ? undefined : (value as ModelTier);
    onConfigChange({ ...config, model: next });
  }

  $effect(() => {
    if (config.schema && !config.selectedTool) {
      customSchemaText = JSON.stringify(config.schema.schema, null, 2);
    }
  });

  function toggleEnabled(): void {
    if (config.enabled) {
      onConfigChange({
        enabled: false,
        selectedTool: undefined,
        schema: undefined,
      });
    } else {
      onConfigChange({ ...config, enabled: true });
      isExpanded = true;
    }
  }

  function selectTool(toolName: string | null) {
    if (toolName === null) {
      onConfigChange({
        ...config,
        selectedTool: undefined,
        schema: config.schema || {
          name: "custom_output",
          description: "Custom structured output",
          schema: { type: "object", properties: {} },
        },
      });
    } else {
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
  }

  function updateCustomSchema() {
    schemaError = null;
    try {
      const parsed = JSON.parse(customSchemaText);
      onConfigChange({
        ...config,
        selectedTool: undefined,
        schema: {
          name: "custom_output",
          description: "Custom structured output",
          schema: parsed,
        },
      });
    } catch {
      schemaError = "Invalid JSON schema";
    }
  }

  const isCustomMode = $derived(!config.selectedTool && config.enabled);
  const summaryText = $derived.by(() => {
    if (!config.enabled) return "off";
    if (config.selectedTool) return config.selectedTool;
    return "custom schema";
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
            <option value="">Custom JSON…</option>
            {#each availableTools as tool}
              <option value={tool.name}>{tool.name}</option>
            {/each}
          </select>
        </label>
      {/if}

      {#if !isCustomMode && config.selectedTool}
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

      {#if isCustomMode || availableTools.length === 0}
        <div class="field">
          <div class="field-label-row">
            <span class="field-label">JSON Schema</span>
            <button
              type="button"
              class="link-btn"
              onclick={() => (showSchemaEditor = !showSchemaEditor)}
            >
              {showSchemaEditor ? "Collapse" : "Edit"}
            </button>
          </div>

          {#if showSchemaEditor}
            <textarea
              bind:value={customSchemaText}
              aria-label="JSON Schema editor"
              class="schema-editor"
              placeholder={'{"type": "object", "properties": {...}}'}
              onblur={updateCustomSchema}
              {disabled}
            ></textarea>
            {#if schemaError}
              <p class="schema-error">{schemaError}</p>
            {/if}
          {:else}
            <div class="schema-preview">
              {config.schema?.name || "No schema defined"}
            </div>
          {/if}
        </div>
      {/if}

      <details bind:open={advancedOpen} class="advanced">
        <summary>
          <span>Advanced</span>
          <span class="advanced-hint">
            fill model: {config.model ?? "agent default"}
          </span>
          <ChevronDown size={12} class="advanced-chevron" />
        </summary>
        <div class="advanced-body">
          <label class="field">
            <span class="field-label">
              Schema-fill model
              <span
                class="info-icon"
                title="A second model pass converts the agent's free-form response into the requested JSON schema. Pin `max` when the schema is deep or the agent's default tier struggles to fill it reliably."
              >
                <Info size={11} />
              </span>
            </span>
            <select
              value={config.model ?? ""}
              onchange={(e) => setStructuredModel((e.target as HTMLSelectElement).value)}
              {disabled}
            >
              {#each modelChoices as choice (choice.value)}
                <option value={choice.value}>{choice.label}</option>
              {/each}
            </select>
          </label>
        </div>
      </details>
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
  .field-label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .field select,
  .schema-editor,
  .schema-preview {
    width: 100%;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-sm);
    background: var(--color-bg-secondary);
    color: var(--color-text);
    padding: 0.35rem 0.55rem;
    font-size: 0.78rem;
  }
  .field select:focus,
  .schema-editor:focus {
    outline: 1px solid color-mix(in srgb, var(--color-secondary) 60%, var(--color-outline));
    border-color: color-mix(in srgb, var(--color-secondary) 60%, var(--color-outline-variant));
  }
  .schema-editor {
    height: 8rem;
    font-family: "JetBrains Mono", "SF Mono", monospace;
    font-size: 0.7rem;
    resize: vertical;
  }
  .schema-preview {
    color: var(--color-text-tertiary);
    font-family: "JetBrains Mono", "SF Mono", monospace;
    font-size: 0.7rem;
  }
  .schema-error {
    margin: 0;
    font-size: 0.66rem;
    color: var(--color-error);
  }

  .link-btn {
    border: 0;
    background: transparent;
    color: var(--color-secondary);
    font-size: 0.66rem;
    font-weight: 600;
    cursor: pointer;
  }
  .link-btn:hover {
    text-decoration: underline;
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

  .info-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text-tertiary);
    cursor: help;
  }
  .info-icon:hover {
    color: var(--color-text-secondary);
  }

  /* Advanced sub-disclosure */
  .advanced {
    border-top: 1px dashed var(--color-outline-variant);
    margin-top: 0.15rem;
    padding-top: 0.4rem;
  }
  .advanced summary {
    list-style: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.7rem;
    color: var(--color-text-secondary);
    user-select: none;
  }
  .advanced summary::-webkit-details-marker {
    display: none;
  }
  .advanced summary > span:first-child {
    font-weight: 600;
  }
  .advanced-hint {
    flex: 1;
    text-align: right;
    font-size: 0.65rem;
    color: var(--color-text-tertiary);
    font-family: "JetBrains Mono", "SF Mono", monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  :global(.advanced-chevron) {
    color: var(--color-text-tertiary);
    transition: transform var(--transition-fast);
  }
  .advanced[open] > summary :global(.advanced-chevron) {
    transform: rotate(180deg);
  }
  .advanced-body {
    margin-top: 0.4rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }
</style>
