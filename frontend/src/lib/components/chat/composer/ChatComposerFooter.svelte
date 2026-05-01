<script lang="ts">
  import { Layers3, Send, Square } from "lucide-svelte";

  interface Props {
    hasApp: boolean;
    hasActiveSession: boolean;
    canSend: boolean;
    canStageNext: boolean;
    loading: boolean;
    queueMode: boolean;
    batchMode?: boolean;
    batchItemCount?: number;
    canSubmitMessage: boolean;
    inputValue?: string;
    /** Hide the send/stop button slot. Used when the composer is in
     *  Schedule mode and a separate action bar drives submission. */
    hideSubmitControls?: boolean;
    onKeyDown: (event: KeyboardEvent) => void;
    onPaste: (event: ClipboardEvent) => void;
    onDragOver: (event: DragEvent) => void;
    onDragLeave: (event: DragEvent) => void;
    onDrop: (event: DragEvent) => void;
    onCancel?: () => void;
  }

  let {
    hasApp,
    hasActiveSession,
    canSend,
    canStageNext,
    loading,
    queueMode,
    batchMode = false,
    batchItemCount = 0,
    canSubmitMessage,
    inputValue = $bindable(""),
    hideSubmitControls = false,
    onKeyDown,
    onPaste,
    onDragOver,
    onDragLeave,
    onDrop,
    onCancel,
  }: Props = $props();
</script>

<div class="composer-footer">
  {#if batchMode && !hasActiveSession}
    <div class="batch-summary" aria-live="polite">
      <Layers3 size={16} />
      <span>{batchItemCount} {batchItemCount === 1 ? "batch item" : "batch items"}</span>
    </div>
  {:else}
    <textarea
      bind:value={inputValue}
      placeholder={hasApp ? "Type your message..." : "Select an app first"}
      disabled={!hasApp ||
        (hasActiveSession && !canSend && !canStageNext) ||
        (loading && !queueMode)}
      rows={1}
      class="composer-textarea"
      style="field-sizing: content;"
      onkeydown={onKeyDown}
      onpaste={onPaste}
      ondragover={onDragOver}
      ondragleave={onDragLeave}
      ondrop={onDrop}
    ></textarea>
  {/if}

  {#if hideSubmitControls}
    <!-- Schedule mode owns its own action bar. Render nothing here. -->
  {:else if loading && onCancel && !queueMode}
    <button
      type="button"
      onclick={() => onCancel?.()}
      class="composer-action stop"
      title="Stop execution"
    >
      <Square size={20} fill="currentColor" />
    </button>
  {:else}
    <button
      type="submit"
      disabled={!hasApp ||
        !canSubmitMessage ||
        (hasActiveSession && !canSend && !canStageNext) ||
        (loading && !queueMode)}
      aria-label={queueMode ? "Send next" : "Send message"}
      title={queueMode ? "Send next" : "Send message"}
      class="composer-action send"
      class:queue={queueMode}
    >
      {#if queueMode}
        <span class="send-next-label">Send next</span>
        <Send size={16} />
      {:else}
        <Send size={20} />
      {/if}
    </button>
  {/if}
</div>

<style>
  .composer-footer {
    display: flex;
    align-items: flex-end;
    gap: 0.75rem;
    min-height: 4.6rem;
    padding: 0.85rem;
  }

  .composer-textarea {
    min-height: 2.35rem;
    max-height: 12rem;
    flex: 1;
    resize: none;
    border: 0;
    background: transparent;
    color: var(--color-text);
    font-size: 0.92rem;
    line-height: 1.55;
  }

  .composer-textarea::placeholder {
    color: var(--color-text-tertiary);
  }

  .composer-textarea:focus {
    outline: none;
  }

  .composer-textarea:disabled {
    opacity: 0.5;
  }

  .composer-action {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    min-width: 2.65rem;
    height: 2.65rem;
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      box-shadow var(--transition-fast),
      transform var(--transition-fast);
  }

  .composer-action:hover:not(:disabled) {
    transform: translateY(-1px);
  }

  .composer-action:disabled {
    cursor: not-allowed;
    opacity: 0.42;
  }

  .composer-action.send {
    background: var(--color-secondary);
    color: var(--color-on-secondary);
    box-shadow: 0 6px 16px color-mix(in srgb, var(--color-secondary) 22%, transparent);
  }

  .composer-action.send:hover:not(:disabled) {
    background: var(--color-accent-hover);
  }

  .composer-action.send.queue {
    gap: 0.45rem;
    padding-inline: 0.85rem;
  }

  .send-next-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
  }

  .composer-action.stop {
    background: var(--color-error);
    color: var(--color-on-error);
    box-shadow: 0 6px 16px color-mix(in srgb, var(--color-error) 18%, transparent);
  }

  .composer-action.stop:hover:not(:disabled) {
    border-color: color-mix(in srgb, var(--color-error) 40%, transparent);
    background: color-mix(in srgb, var(--color-error) 84%, var(--color-bg));
  }

  :global(.composer-action svg) {
    transition: transform var(--transition-fast);
  }

  .composer-action.send:hover:not(:disabled) :global(svg) {
    transform: translateX(1px);
  }

  .batch-summary {
    display: inline-flex;
    flex: 1;
    min-height: 2.5rem;
    align-items: center;
    gap: 0.5rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    padding: 0.55rem 0.75rem;
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-tertiary) 42%, transparent);
    font-size: 0.8125rem;
    font-weight: 650;
  }

  @media (max-width: 520px) {
    .composer-footer {
      min-height: 4.25rem;
      padding: 0.7rem;
    }

    .composer-action {
      min-width: 2.45rem;
      height: 2.45rem;
    }
  }
</style>
