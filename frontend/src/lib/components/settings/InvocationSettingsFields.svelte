<script lang="ts">
  import type { InvocationConfig, InvocationMode, ModelTier, ReasoningLevel } from "$lib/types";

  interface ChoiceOption<T> {
    value: T;
    label: string;
  }

  interface Props {
    config: InvocationConfig;
    invocationMode: InvocationMode;
    invocationModes: ChoiceOption<InvocationMode>[];
    modelTiers: ChoiceOption<ModelTier | undefined>[];
    reasoningLevels: ChoiceOption<ReasoningLevel | undefined>[];
    availableTools?: string[];
    disabled?: boolean;
    structuredOutputEnabled?: boolean;
    statusMessagesDisabled: boolean;
    modal?: boolean;
    onUpdate: (partial: Partial<InvocationConfig>) => void;
    onUpdateInvocationMode: (mode: InvocationMode) => void;
    onToggleTargetedTool: (toolName: string) => void;
    isToolSelected: (toolName: string) => boolean;
  }

  let {
    config,
    invocationMode,
    invocationModes,
    modelTiers,
    reasoningLevels,
    availableTools = [],
    disabled = false,
    structuredOutputEnabled = false,
    statusMessagesDisabled,
    modal = false,
    onUpdate,
    onUpdateInvocationMode,
    onToggleTargetedTool,
    isToolSelected,
  }: Props = $props();
</script>

<div class="settings-fields">
  <div class="setting-group">
    <div class="group-header">
      <span class="field-label">Invocation Mode</span>
      <span class="value-pill">{invocationMode}</span>
    </div>
    <div class="choice-grid">
      {#each invocationModes as mode}
        <button
          type="button"
          class="choice-btn"
          class:active={invocationMode === mode.value}
          onclick={() => onUpdateInvocationMode(mode.value)}
          disabled={disabled || structuredOutputEnabled}
        >
          {mode.label}
        </button>
      {/each}
    </div>
    <p class="field-helper">
      {#if structuredOutputEnabled}
        Structured output uses invoke mode so the final schema result arrives once complete.
      {:else if invocationMode === "stream"}
        Stream incremental assistant and tool updates while execution is running.
      {:else}
        Invoke waits for completion before surfacing internal nested and system-agent output.
      {/if}
    </p>
  </div>

  <div class="setting-group">
    <div class="group-header">
      <span class="field-label">Model Tier</span>
      <span class="value-pill">{config.model ?? "auto"}</span>
    </div>
    <div class="choice-grid">
      {#each modelTiers as tier}
        <button
          type="button"
          class="choice-btn"
          class:active={config.model === tier.value}
          onclick={() => onUpdate({ model: tier.value })}
          {disabled}
        >
          {tier.label}
        </button>
      {/each}
    </div>
  </div>

  <div class="setting-group">
    <div class="group-header">
      <span class="field-label">Reasoning Level</span>
      <span class="value-pill">{config.reasoning ?? "auto"}</span>
    </div>
    <div class="choice-grid">
      {#each reasoningLevels as level}
        <button
          type="button"
          class="choice-btn"
          class:active={config.reasoning === level.value}
          onclick={() => onUpdate({ reasoning: level.value })}
          {disabled}
        >
          {level.label}
        </button>
      {/each}
    </div>
  </div>

  <div class="setting-group toggle-stack">
    <label class="toggle-row" class:is-disabled={disabled}>
      <div class="toggle-copy">
        <span class="toggle-title">Force final tool</span>
        <span class="toggle-description">
          Requires running the designated final tool before completing.
        </span>
      </div>
      <div class="switch-shell">
        <input
          type="checkbox"
          class="peer sr-only"
          checked={config.force_final_tool}
          onchange={(e) => onUpdate({ force_final_tool: (e.target as HTMLInputElement).checked })}
          {disabled}
        />
        <span class="switch-track"></span>
        <span class="switch-thumb"></span>
      </div>
    </label>

    <label class="toggle-row" class:is-disabled={statusMessagesDisabled}>
      <div class="toggle-copy">
        <span class="toggle-title">Status messages</span>
        <span class="toggle-description">
          {#if structuredOutputEnabled}
            Disabled when structured output is active.
          {:else if invocationMode === "invoke"}
            Disabled in invoke mode.
          {:else}
            Emit status messages at key lifecycle milestones while the runtime is still working.
          {/if}
        </span>
      </div>
      <div class="switch-shell">
        <input
          type="checkbox"
          class="peer sr-only"
          checked={!statusMessagesDisabled && (config.status_messages ?? false)}
          onchange={(e) => onUpdate({ status_messages: (e.target as HTMLInputElement).checked })}
          disabled={statusMessagesDisabled}
        />
        <span class="switch-track"></span>
        <span class="switch-thumb"></span>
      </div>
    </label>

    <label class="toggle-row" class:is-disabled={disabled}>
      <div class="toggle-copy">
        <span class="toggle-title">Allow private data in system tools</span>
        <span class="toggle-description">
          Permits system tools to receive private values when explicitly needed.
        </span>
      </div>
      <div class="switch-shell">
        <input
          type="checkbox"
          class="peer sr-only"
          checked={config.allow_private_in_system_tools ?? false}
          onchange={(e) =>
            onUpdate({ allow_private_in_system_tools: (e.target as HTMLInputElement).checked })}
          {disabled}
        />
        <span class="switch-track"></span>
        <span class="switch-thumb"></span>
      </div>
    </label>
  </div>

  {#if availableTools.length > 0}
    <div class="setting-group">
      <div class="group-header">
        <span class="field-label">Targeted Tools</span>
        <div class="tools-meta">
          {#if config.targeted_tools && config.targeted_tools.length > 0}
            <span class="value-pill">{config.targeted_tools.length} selected</span>
            <button
              type="button"
              class="clear-btn"
              onclick={() => onUpdate({ targeted_tools: undefined })}
              {disabled}
            >
              Clear
            </button>
          {:else}
            <span class="value-pill">Auto</span>
          {/if}
        </div>
      </div>
      <div class="tool-grid" class:modal-tool-grid={modal}>
        {#each availableTools as tool}
          <button
            type="button"
            class="tool-pill"
            class:selected={isToolSelected(tool)}
            onclick={() => onToggleTargetedTool(tool)}
            {disabled}
          >
            {tool}
          </button>
        {/each}
      </div>
      <p class="field-helper">
        Pick specific tools to narrow execution. Leave unselected to let routing stay automatic.
      </p>
    </div>
  {/if}
</div>

<style>
  .settings-fields {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }

  .setting-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .group-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .tools-meta {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
  }

  .field-label {
    display: block;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .field-helper {
    margin-top: 0.15rem;
    font-size: 0.6875rem;
    line-height: 1.35;
    color: var(--color-text-tertiary);
  }

  .value-pill {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-full);
    padding: 0.125rem 0.5rem;
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-secondary) 70%, transparent);
  }

  .choice-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(4.75rem, 1fr));
    gap: 0.375rem;
  }

  .choice-btn {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    padding: 0.5rem 0.625rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-align: center;
    background: color-mix(in srgb, var(--color-bg-tertiary) 44%, transparent);
    color: var(--color-text-secondary);
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast),
      opacity var(--transition-fast);
  }

  .choice-btn:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-surface-variant) 40%, transparent);
  }

  .choice-btn.active {
    background: color-mix(in srgb, var(--color-tertiary) 22%, var(--color-bg-tertiary));
    color: var(--color-tertiary);
    border-color: color-mix(in srgb, var(--color-tertiary) 50%, var(--color-outline-variant));
  }

  .choice-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .toggle-stack {
    gap: 0.5rem;
  }

  .toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.875rem;
    padding: 0.5rem 0;
    cursor: pointer;
  }

  .toggle-row.is-disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .toggle-copy {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .toggle-title {
    font-size: 0.75rem;
    line-height: 1.2;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .toggle-description {
    font-size: 0.6875rem;
    line-height: 1.3;
    color: var(--color-text-tertiary);
  }

  .switch-shell {
    position: relative;
    width: 2.125rem;
    height: 1.25rem;
    flex-shrink: 0;
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

  .tool-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .modal-tool-grid {
    max-height: 14rem;
    overflow-y: auto;
    padding: 0.125rem;
  }

  .tool-pill {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-full);
    padding: 0.3rem 0.625rem;
    font-size: 0.75rem;
    line-height: 1.2;
    font-weight: 500;
    background: color-mix(in srgb, var(--color-bg-tertiary) 44%, transparent);
    color: var(--color-text-secondary);
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast),
      opacity var(--transition-fast);
    white-space: nowrap;
  }

  .tool-pill:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-surface-variant) 42%, transparent);
  }

  .tool-pill.selected {
    background: color-mix(in srgb, var(--color-tertiary) 18%, var(--color-bg-secondary));
    border-color: color-mix(in srgb, var(--color-tertiary) 50%, var(--color-outline-variant));
    color: var(--color-tertiary);
  }

  .tool-pill:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .clear-btn {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-full);
    background: transparent;
    color: var(--color-text-secondary);
    font-size: 0.6875rem;
    font-weight: 600;
    padding: 0.125rem 0.5rem;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      opacity var(--transition-fast);
  }

  .clear-btn:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-surface-variant) 42%, transparent);
    border-color: color-mix(in srgb, var(--color-outline) 60%, var(--color-outline-variant));
  }

  .clear-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @media (max-width: 480px) {
    .choice-grid {
      grid-template-columns: repeat(auto-fit, minmax(4.25rem, 1fr));
    }
  }
</style>
