<script lang="ts">
  interface Props {
    saving?: boolean;
    error?: string;
    showActions?: boolean;
    saveDisabled?: boolean;
    discardDisabled?: boolean;
    onSave: () => void | Promise<void>;
    onDiscard: () => void;
  }

  let {
    saving = false,
    error = "",
    showActions = true,
    saveDisabled = false,
    discardDisabled = false,
    onSave,
    onDiscard,
  }: Props = $props();
</script>

{#if showActions}
  <div class="action-row">
    <button type="button" class="save-btn" onclick={() => onSave()} disabled={saveDisabled}>
      {saving ? "Saving..." : "Save changes"}
    </button>
    <button type="button" class="discard-btn" onclick={onDiscard} disabled={discardDisabled}>
      Discard
    </button>
  </div>
{/if}

{#if error}
  <p class="error-text">{error}</p>
{/if}

<style>
  .action-row {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0.5rem;
  }

  .save-btn,
  .discard-btn {
    border-radius: var(--radius-lg);
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.6rem 0.9rem;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast),
      opacity var(--transition-fast);
  }

  .save-btn {
    background: var(--color-secondary);
    color: var(--color-on-secondary);
    border: 1px solid color-mix(in srgb, var(--color-secondary) 74%, white);
  }

  .save-btn:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-secondary) 86%, white);
  }

  .discard-btn {
    border: 1px solid var(--color-outline-variant);
    color: var(--color-text-secondary);
    background: transparent;
  }

  .discard-btn:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-surface-variant) 40%, transparent);
  }

  .save-btn:disabled,
  .discard-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error-text {
    font-size: 0.75rem;
    color: var(--color-error);
  }

  @media (max-width: 768px) {
    .action-row {
      grid-template-columns: 1fr;
    }
  }
</style>
