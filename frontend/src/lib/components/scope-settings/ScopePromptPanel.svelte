<script lang="ts">
  import { ChevronRight } from "lucide-svelte";

  interface Props {
    value?: string;
    disabled?: boolean;
    rows?: number;
    placeholder?: string;
    title?: string;
    hint?: string;
    accent?: string;
    onInput: (value: string) => void;
  }

  let {
    value = "",
    disabled = false,
    rows = 5,
    placeholder = "System prompt...",
    title = "System Prompt",
    hint = "Advanced",
    accent = "var(--color-primary)",
    onInput,
  }: Props = $props();
</script>

<details class="prompt-panel" style={`--scope-prompt-accent: ${accent};`}>
  <summary class="prompt-summary">
    <div class="summary-left">
      <ChevronRight size={13} class="summary-icon" />
      <span>{title}</span>
    </div>
    <span class="summary-hint">{hint}</span>
  </summary>
  <textarea
    class="field-input textarea-input"
    class:disabled
    {disabled}
    {rows}
    {placeholder}
    {value}
    oninput={(e) => onInput((e.target as HTMLTextAreaElement).value)}
  ></textarea>
</details>

<style>
  .field-input {
    width: 100%;
    padding: 0.5625rem 0.75rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-outline-variant);
    background-color: var(--color-bg);
    font-size: 0.875rem;
    line-height: 1.35;
    color: var(--color-text);
    transition:
      border-color var(--transition-fast),
      box-shadow var(--transition-fast),
      background-color var(--transition-fast);
  }

  .field-input::placeholder {
    color: color-mix(in srgb, var(--color-text-tertiary) 88%, transparent);
  }

  .field-input:focus {
    outline: none;
    border-color: color-mix(in srgb, var(--scope-prompt-accent) 70%, white);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--scope-prompt-accent) 20%, transparent);
  }

  .field-input.disabled {
    opacity: 0.55;
    cursor: not-allowed;
    background-color: color-mix(in srgb, var(--color-bg-secondary) 72%, transparent);
  }

  .textarea-input {
    margin-top: 0.625rem;
    resize: vertical;
    min-height: 6.5rem;
    line-height: 1.45;
  }

  .prompt-panel {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    padding: 0.625rem 0.625rem 0.5rem;
    background: color-mix(in srgb, var(--color-bg-tertiary) 60%, transparent);
  }

  .prompt-summary {
    list-style: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .prompt-summary::-webkit-details-marker {
    display: none;
  }

  .summary-left {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
  }

  :global(.summary-icon) {
    color: var(--color-text-tertiary);
    transition: transform var(--transition-fast);
  }

  .summary-hint {
    font-size: 0.625rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--color-text-tertiary);
  }

  .prompt-panel[open] :global(.summary-icon) {
    transform: rotate(90deg);
  }
</style>
