<script lang="ts">
  import type { MemoryConfig } from "$lib/types";

  interface Props {
    config: MemoryConfig;
    disabled?: boolean;
    onChange?: (config: MemoryConfig) => void;
  }

  let { config, disabled = false, onChange }: Props = $props();

  function update(partial: Partial<MemoryConfig>) {
    onChange?.({ ...config, ...partial });
  }
</script>

<div class="memory-settings">
  <!-- Master toggle -->
  <label class="toggle-row" class:is-disabled={disabled}>
    <span class="toggle-label primary">Memory Agent</span>
    <div class="switch-shell">
      <input
        type="checkbox"
        class="peer sr-only"
        checked={config.enabled}
        {disabled}
        onchange={(e) => update({ enabled: (e.target as HTMLInputElement).checked })}
      />
      <span class="switch-track"></span>
      <span class="switch-thumb"></span>
    </div>
  </label>

  {#if config.enabled}
    <div class="sub-settings animate-in">
      <div class="select-row">
        <span class="toggle-label">Memory Level</span>
        <select
          class="select-input"
          value={config.level}
          {disabled}
          onchange={(e) =>
            update({ level: (e.target as HTMLSelectElement).value as MemoryConfig["level"] })}
        >
          <option value="glimpse">Glimpse</option>
          <option value="focus">Focus</option>
          <option value="clarity">Clarity</option>
        </select>
      </div>

      <label class="toggle-row sub" class:is-disabled={disabled}>
        <span class="toggle-label">Summarization</span>
        <div class="switch-shell">
          <input
            type="checkbox"
            class="peer sr-only"
            checked={config.summarizationEnabled}
            {disabled}
            onchange={(e) =>
              update({ summarizationEnabled: (e.target as HTMLInputElement).checked })}
          />
          <span class="switch-track"></span>
          <span class="switch-thumb"></span>
        </div>
      </label>

      <label class="toggle-row sub" class:is-disabled={disabled}>
        <span class="toggle-label">Skill Extraction</span>
        <div class="switch-shell">
          <input
            type="checkbox"
            class="peer sr-only"
            checked={config.skillExtractionEnabled}
            {disabled}
            onchange={(e) =>
              update({ skillExtractionEnabled: (e.target as HTMLInputElement).checked })}
          />
          <span class="switch-track"></span>
          <span class="switch-thumb"></span>
        </div>
      </label>

      <label class="toggle-row sub" class:is-disabled={disabled}>
        <span class="toggle-label">Insight Extraction</span>
        <div class="switch-shell">
          <input
            type="checkbox"
            class="peer sr-only"
            checked={config.insightExtractionEnabled}
            {disabled}
            onchange={(e) =>
              update({ insightExtractionEnabled: (e.target as HTMLInputElement).checked })}
          />
          <span class="switch-track"></span>
          <span class="switch-thumb"></span>
        </div>
      </label>

      <label class="toggle-row sub" class:is-disabled={disabled}>
        <span class="toggle-label">Memory Retrieval</span>
        <div class="switch-shell">
          <input
            type="checkbox"
            class="peer sr-only"
            checked={config.retrievalEnabled}
            {disabled}
            onchange={(e) => update({ retrievalEnabled: (e.target as HTMLInputElement).checked })}
          />
          <span class="switch-track"></span>
          <span class="switch-thumb"></span>
        </div>
      </label>

      <div class="select-row">
        <span class="toggle-label">Persistence Mode</span>
        <select
          class="select-input"
          value={config.persistenceMode}
          {disabled}
          onchange={(e) => update({ persistenceMode: (e.target as HTMLSelectElement).value })}
        >
          <option value="vector_only">Vector Only</option>
          <option value="vector_plus_graph">Vector + Graph</option>
        </select>
      </div>
    </div>
  {/if}
</div>

<style>
  .memory-settings {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.375rem 0;
    cursor: pointer;
  }

  .toggle-row.sub {
    padding-left: 0.5rem;
  }

  .toggle-row.is-disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .toggle-label {
    font-size: 0.8125rem;
    color: var(--color-text);
  }

  .toggle-label.primary {
    font-weight: 600;
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

  .sub-settings {
    display: flex;
    flex-direction: column;
    border-top: 1px solid var(--color-outline-variant);
    margin-top: 0.375rem;
    padding-top: 0.375rem;
  }

  .select-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.375rem 0 0.375rem 0.5rem;
  }

  .select-input {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-sm);
    background: var(--color-bg-secondary);
    color: var(--color-text);
    cursor: pointer;
  }

  .select-input:focus {
    outline: 1px solid var(--color-secondary);
    border-color: var(--color-secondary);
  }
</style>
