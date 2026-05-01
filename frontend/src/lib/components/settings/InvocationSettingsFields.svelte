<script lang="ts">
  import type {
    InvocationConfig,
    InvocationMemoryConfig,
    InvocationMode,
    InvocationOrchestrationConfig,
    ModelTier,
    ReasoningLevel,
  } from "$lib/types";
  import { ChevronDown } from "lucide-svelte";

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

  // MARK: - Nested config helpers
  // These knobs all live on `InvocationConfig` but under nested objects. The
  // SDK supports them; studio just hadn't exposed them yet. We merge partial
  // updates so the rest of each nested config stays intact.

  function updateMemory(partial: Partial<InvocationMemoryConfig>): void {
    onUpdate({
      memory_config: {
        ...(config.memory_config ?? {}),
        ...partial,
      },
    });
  }

  function updateMemoryRetrieval(
    partial: Partial<NonNullable<InvocationMemoryConfig["retrieval"]>>,
  ): void {
    updateMemory({
      retrieval: {
        ...(config.memory_config?.retrieval ?? {}),
        ...partial,
      },
    });
  }

  function updateMemorySkill(
    partial: Partial<NonNullable<InvocationMemoryConfig["skill_extraction"]>>,
  ): void {
    updateMemory({
      skill_extraction: {
        ...(config.memory_config?.skill_extraction ?? {}),
        ...partial,
      },
    });
  }

  function updateMemoryInsight(
    partial: Partial<NonNullable<InvocationMemoryConfig["insight_extraction"]>>,
  ): void {
    updateMemory({
      insight_extraction: {
        ...(config.memory_config?.insight_extraction ?? {}),
        ...partial,
      },
    });
  }

  function updateOrchestration(partial: Partial<InvocationOrchestrationConfig>): void {
    onUpdate({
      orchestration_config: {
        ...(config.orchestration_config ?? {}),
        ...partial,
      },
    });
  }

  function parseInteger(event: Event, min = 0): number | undefined {
    const raw = (event.target as HTMLInputElement).value.trim();
    if (!raw) return undefined;
    const parsed = Number.parseInt(raw, 10);
    if (!Number.isFinite(parsed)) return undefined;
    return Math.max(min, parsed);
  }

  function parseFloat01(event: Event): number | undefined {
    const raw = (event.target as HTMLInputElement).value.trim();
    if (!raw) return undefined;
    const parsed = Number.parseFloat(raw);
    if (!Number.isFinite(parsed)) return undefined;
    return Math.min(1, Math.max(0, parsed));
  }

  // PII whitelist is stored as JSON in `InvocationConfig.pii_whitelist` to
  // mirror the SDK's `PIIWhitelist`. We hold the raw text in component state
  // so partial edits don't get reformatted while the user is typing. Initial
  // hydration runs in `$effect.pre` so we read the current `config` (a Svelte
  // 5 prop) instead of capturing only its first value.
  let piiWhitelistText = $state("");
  let piiWhitelistError = $state<string | null>(null);
  let piiWhitelistHydrated = false;

  $effect.pre(() => {
    if (piiWhitelistHydrated) return;
    piiWhitelistHydrated = true;
    piiWhitelistText = config.pii_whitelist ? JSON.stringify(config.pii_whitelist, null, 2) : "";
  });

  function handlePiiWhitelistInput(event: Event): void {
    piiWhitelistText = (event.target as HTMLTextAreaElement).value;
  }

  function commitPiiWhitelist(): void {
    const raw = piiWhitelistText.trim();
    if (!raw) {
      piiWhitelistError = null;
      onUpdate({ pii_whitelist: undefined });
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
        piiWhitelistError = "Expected a JSON object keyed by entity type.";
        return;
      }
      // Validate that each value is an array of strings — PIIWhitelist shape.
      for (const [key, value] of Object.entries(parsed)) {
        if (!Array.isArray(value) || !value.every((v) => typeof v === "string")) {
          piiWhitelistError = `"${key}" must be an array of strings.`;
          return;
        }
      }
      piiWhitelistError = null;
      onUpdate({ pii_whitelist: parsed as Record<string, string[]> });
    } catch {
      piiWhitelistError = "Invalid JSON.";
    }
  }

  // MARK: - Customization summary for the disclosure header
  // Counts how many advanced fields differ from defaults so the user can tell
  // at a glance whether anything's been tuned.

  const memoryRetrievalSet = $derived(
    Object.values(config.memory_config?.retrieval ?? {}).filter((value) => value !== undefined)
      .length,
  );
  const memorySkillSet = $derived(
    Object.values(config.memory_config?.skill_extraction ?? {}).filter(
      (value) => value !== undefined,
    ).length,
  );
  const memoryInsightSet = $derived(
    Object.values(config.memory_config?.insight_extraction ?? {}).filter(
      (value) => value !== undefined,
    ).length,
  );
  const orchestrationSet = $derived(
    Object.values(config.orchestration_config ?? {}).filter((value) => value !== undefined).length,
  );
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

  <!--
    Advanced — progressive disclosure for SDK fields that aren't usually tuned
    but exist in `InvocationConfig`. Keeping these collapsed avoids overwhelming
    the inspector while still giving power users full granularity.
  -->
  <details class="advanced-disclosure" open={Boolean(config.max_results)}>
    <summary>
      <span class="disclosure-title">Tool selection</span>
      <span class="disclosure-hint">
        {config.max_results == null ? "auto" : `top ${config.max_results}`}
      </span>
      <ChevronDown size={14} class="advanced-chev" />
    </summary>
    <div class="advanced-body">
      <label class="field">
        <span class="field-label">Max semantic-search results</span>
        <input
          type="number"
          min="1"
          step="1"
          value={config.max_results ?? ""}
          placeholder="auto"
          {disabled}
          oninput={(e) => onUpdate({ max_results: parseInteger(e, 1) })}
        />
        <p class="field-helper">
          Caps how many tools the agent considers per turn after semantic search. Lower = focused,
          higher = broad. Maps to <code>SessionRequest.max_results</code>.
        </p>
      </label>
    </div>
  </details>

  <details class="advanced-disclosure" open={memoryRetrievalSet > 0}>
    <summary>
      <span class="disclosure-title">Memory retrieval</span>
      <span class="disclosure-hint">
        {memoryRetrievalSet > 0 ? `${memoryRetrievalSet} customized` : "auto"}
      </span>
      <ChevronDown size={14} class="advanced-chev" />
    </summary>
    <div class="advanced-body grid-two">
      <label class="field">
        <span class="field-label">top_k</span>
        <input
          type="number"
          min="1"
          step="1"
          value={config.memory_config?.retrieval?.top_k ?? ""}
          placeholder="default"
          {disabled}
          oninput={(e) => updateMemoryRetrieval({ top_k: parseInteger(e, 1) })}
        />
      </label>
      <label class="field">
        <span class="field-label">candidate_limit</span>
        <input
          type="number"
          min="1"
          step="1"
          value={config.memory_config?.retrieval?.candidate_limit ?? ""}
          placeholder="default"
          {disabled}
          oninput={(e) => updateMemoryRetrieval({ candidate_limit: parseInteger(e, 1) })}
        />
      </label>
      <label class="field-checkbox-row">
        <input
          type="checkbox"
          class="checkbox"
          checked={config.memory_config?.retrieval?.skills_enabled ?? true}
          {disabled}
          onchange={(e) =>
            updateMemoryRetrieval({
              skills_enabled: (e.target as HTMLInputElement).checked,
            })}
        />
        <span>Inject skills</span>
      </label>
      <label class="field-checkbox-row">
        <input
          type="checkbox"
          class="checkbox"
          checked={config.memory_config?.retrieval?.insights_enabled ?? true}
          {disabled}
          onchange={(e) =>
            updateMemoryRetrieval({
              insights_enabled: (e.target as HTMLInputElement).checked,
            })}
        />
        <span>Inject insights</span>
      </label>
      <label class="field-checkbox-row">
        <input
          type="checkbox"
          class="checkbox"
          checked={config.memory_config?.retrieval?.resources_enabled ?? true}
          {disabled}
          onchange={(e) =>
            updateMemoryRetrieval({
              resources_enabled: (e.target as HTMLInputElement).checked,
            })}
        />
        <span>Inject resources</span>
      </label>
    </div>
  </details>

  <details class="advanced-disclosure" open={memorySkillSet > 0 || memoryInsightSet > 0}>
    <summary>
      <span class="disclosure-title">Memory extraction quality</span>
      <span class="disclosure-hint">
        {#if memorySkillSet || memoryInsightSet}
          {memorySkillSet + memoryInsightSet} customized
        {:else}
          defaults
        {/if}
      </span>
      <ChevronDown size={14} class="advanced-chev" />
    </summary>
    <div class="advanced-body grid-two">
      <label class="field">
        <span class="field-label">Skill confidence floor (0–1)</span>
        <input
          type="number"
          min="0"
          max="1"
          step="0.05"
          value={config.memory_config?.skill_extraction?.confidence_threshold ?? ""}
          placeholder="default"
          {disabled}
          oninput={(e) => updateMemorySkill({ confidence_threshold: parseFloat01(e) })}
        />
      </label>
      <label class="field">
        <span class="field-label">Skills max per turn</span>
        <input
          type="number"
          min="1"
          step="1"
          value={config.memory_config?.skill_extraction?.max_count ?? ""}
          placeholder="default"
          {disabled}
          oninput={(e) => updateMemorySkill({ max_count: parseInteger(e, 1) })}
        />
      </label>
      <label class="field">
        <span class="field-label">Insight relevance floor (0–1)</span>
        <input
          type="number"
          min="0"
          max="1"
          step="0.05"
          value={config.memory_config?.insight_extraction?.min_relevance_score ?? ""}
          placeholder="default"
          {disabled}
          oninput={(e) => updateMemoryInsight({ min_relevance_score: parseFloat01(e) })}
        />
      </label>
      <label class="field">
        <span class="field-label">Insights max per turn</span>
        <input
          type="number"
          min="1"
          step="1"
          value={config.memory_config?.insight_extraction?.max_count ?? ""}
          placeholder="default"
          {disabled}
          oninput={(e) => updateMemoryInsight({ max_count: parseInteger(e, 1) })}
        />
      </label>
      <p class="field-helper full-row">
        Quality gates on what the memory pipeline writes back. Floors below the threshold are
        dropped silently — useful for sparse domains where the SDK defaults extract too eagerly.
      </p>
    </div>
  </details>

  <details class="advanced-disclosure" open={Boolean(config.pii_whitelist)}>
    <summary>
      <span class="disclosure-title">PII whitelist</span>
      <span class="disclosure-hint">
        {config.pii_whitelist
          ? `${Object.keys(config.pii_whitelist).length} entity type${Object.keys(config.pii_whitelist).length === 1 ? "" : "s"}`
          : "redact everything"}
      </span>
      <ChevronDown size={14} class="advanced-chev" />
    </summary>
    <div class="advanced-body">
      <textarea
        rows="5"
        spellcheck="false"
        class="pii-textarea"
        value={piiWhitelistText}
        placeholder={'{\n  "PERSON": ["Alice", "Bob"],\n  "EMAIL": ["alice@example.com"]\n}'}
        {disabled}
        oninput={handlePiiWhitelistInput}
        onblur={commitPiiWhitelist}
      ></textarea>
      {#if piiWhitelistError}
        <p class="field-helper error-text">{piiWhitelistError}</p>
      {/if}
      <p class="field-helper">
        Suppresses redaction for approved spans on a per-entity basis. Maps to
        <code>SessionRequest.pii_whitelist</code>. Keys are entity types (<code>PERSON</code>,
        <code>EMAIL</code>, <code>PHONE_NUMBER</code>, etc.); values are exact strings allowed
        through unredacted. Leave empty for the SDK default of "redact everything".
      </p>
    </div>
  </details>

  <details class="advanced-disclosure" open={orchestrationSet > 0}>
    <summary>
      <span class="disclosure-title">Orchestration</span>
      <span class="disclosure-hint">
        {orchestrationSet > 0 ? `${orchestrationSet} customized` : "defaults"}
      </span>
      <ChevronDown size={14} class="advanced-chev" />
    </summary>
    <div class="advanced-body grid-two">
      <label class="field">
        <span class="field-label">Max cycles</span>
        <input
          type="number"
          min="1"
          step="1"
          value={config.orchestration_config?.max_cycles ?? ""}
          placeholder="default"
          {disabled}
          oninput={(e) => updateOrchestration({ max_cycles: parseInteger(e, 1) })}
        />
      </label>
      <label class="field-checkbox-row">
        <input
          type="checkbox"
          class="checkbox"
          checked={config.orchestration_config?.allow_reevaluate_loop ?? false}
          {disabled}
          onchange={(e) =>
            updateOrchestration({
              allow_reevaluate_loop: (e.target as HTMLInputElement).checked,
            })}
        />
        <span>Allow re-evaluate loop</span>
      </label>
      <p class="field-helper full-row">
        Re-evaluate lets the orchestrator revisit prior steps when a tool result changes the
        situation. Off by default — turn on for plan-revision flows.
      </p>
    </div>
  </details>
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
    background: color-mix(in srgb, var(--color-secondary) 22%, var(--color-bg-tertiary));
    color: var(--color-secondary);
    border-color: color-mix(in srgb, var(--color-secondary) 50%, var(--color-outline-variant));
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
    background: var(--color-secondary);
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
    background: color-mix(in srgb, var(--color-secondary) 18%, var(--color-bg-secondary));
    border-color: color-mix(in srgb, var(--color-secondary) 50%, var(--color-outline-variant));
    color: var(--color-secondary);
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

  /* Advanced disclosures — wrap each SDK-native config group in a thin
     collapsible row so power users get full granularity without overwhelming
     the default inspector view. */
  .advanced-disclosure {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-bg-secondary) 50%, transparent);
    margin-top: 0.4rem;
    overflow: hidden;
  }

  .advanced-disclosure summary {
    list-style: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.5rem 0.7rem;
    font-size: 0.75rem;
    color: var(--color-text);
    user-select: none;
  }

  .advanced-disclosure summary::-webkit-details-marker {
    display: none;
  }

  .advanced-disclosure summary:hover {
    background: color-mix(in srgb, var(--color-bg-tertiary) 50%, transparent);
  }

  .disclosure-title {
    font-weight: 600;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-secondary);
  }

  .disclosure-hint {
    flex: 1;
    text-align: right;
    color: var(--color-text-tertiary);
    font-size: 0.66rem;
    font-family: "JetBrains Mono", "SF Mono", monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :global(.advanced-chev) {
    color: var(--color-text-tertiary);
    transition: transform var(--transition-fast);
    flex-shrink: 0;
  }

  details[open] > summary :global(.advanced-chev) {
    transform: rotate(180deg);
  }

  .advanced-body {
    padding: 0.55rem 0.7rem 0.7rem;
    border-top: 1px dashed var(--color-outline-variant);
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    background: color-mix(in srgb, var(--color-bg) 35%, transparent);
  }

  /* Two-column grid where every cell is the same min-height so number
     inputs (with their label above) line up with checkbox-only rows. */
  .advanced-body.grid-two {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.6rem 0.65rem;
    align-items: stretch;
  }

  .advanced-body .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
  }

  .advanced-body .field .field-label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-tertiary);
  }

  .advanced-body input[type="number"] {
    width: 100%;
    padding: 0.35rem 0.5rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-sm);
    background: var(--color-bg-secondary);
    color: var(--color-text);
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
  }

  .advanced-body input[type="number"]:focus {
    outline: 1px solid color-mix(in srgb, var(--color-secondary) 60%, transparent);
    border-color: color-mix(in srgb, var(--color-secondary) 60%, var(--color-outline-variant));
  }

  .field-checkbox-row {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.45rem 0.55rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-bg-secondary) 70%, transparent);
    font-size: 0.74rem;
    font-weight: 500;
    color: var(--color-text-secondary);
    cursor: pointer;
    user-select: none;
    min-height: 2.25rem;
    align-self: end;
  }

  .field-checkbox-row:hover {
    background: color-mix(in srgb, var(--color-bg-tertiary) 65%, transparent);
  }

  .field-checkbox-row .checkbox {
    width: 0.9rem;
    height: 0.9rem;
    accent-color: var(--color-secondary);
    flex-shrink: 0;
  }

  .full-row {
    grid-column: 1 / -1;
    margin-top: 0;
  }

  .field-helper code {
    font-family: "JetBrains Mono", "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 0.95em;
    background: color-mix(in srgb, var(--color-bg-tertiary) 70%, transparent);
    padding: 0 0.25rem;
    border-radius: var(--radius-sm);
    color: var(--color-text-secondary);
  }

  .pii-textarea {
    width: 100%;
    padding: 0.5rem 0.6rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
    font-family: "JetBrains Mono", "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 0.72rem;
    line-height: 1.5;
    resize: vertical;
    min-height: 5rem;
    max-height: 12rem;
  }

  .pii-textarea:focus {
    outline: 1px solid color-mix(in srgb, var(--color-secondary) 60%, transparent);
    border-color: color-mix(in srgb, var(--color-secondary) 60%, var(--color-outline-variant));
  }

  .error-text {
    color: var(--color-error);
  }
</style>
