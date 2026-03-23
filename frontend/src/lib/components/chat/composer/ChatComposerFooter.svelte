<script lang="ts">
  import { Send, Square } from "lucide-svelte";

  interface Props {
    hasDemo: boolean;
    hasActiveSession: boolean;
    canSend: boolean;
    canStageNext: boolean;
    loading: boolean;
    queueMode: boolean;
    canSubmitMessage: boolean;
    inputValue?: string;
    onKeyDown: (event: KeyboardEvent) => void;
    onPaste: (event: ClipboardEvent) => void;
    onDragOver: (event: DragEvent) => void;
    onDragLeave: (event: DragEvent) => void;
    onDrop: (event: DragEvent) => void;
    onCancel?: () => void;
  }

  let {
    hasDemo,
    hasActiveSession,
    canSend,
    canStageNext,
    loading,
    queueMode,
    canSubmitMessage,
    inputValue = $bindable(""),
    onKeyDown,
    onPaste,
    onDragOver,
    onDragLeave,
    onDrop,
    onCancel,
  }: Props = $props();
</script>

<div class="flex items-end gap-3 p-3">
  <textarea
    bind:value={inputValue}
    placeholder={hasDemo ? "Type your message..." : "Select a demo first"}
    disabled={!hasDemo ||
      (hasActiveSession && !canSend && !canStageNext) ||
      (loading && !queueMode)}
    rows={1}
    class="flex-1 bg-transparent resize-none placeholder-[var(--color-text-tertiary)]
         focus:outline-none disabled:opacity-50 text-[var(--color-text)]
         min-h-[24px] max-h-[200px] leading-relaxed"
    style="field-sizing: content;"
    onkeydown={onKeyDown}
    onpaste={onPaste}
    ondragover={onDragOver}
    ondragleave={onDragLeave}
    ondrop={onDrop}
  ></textarea>

  {#if loading && onCancel && !queueMode}
    <button
      type="button"
      onclick={() => onCancel?.()}
      class="relative flex items-center justify-center w-10 h-10 rounded-lg
           bg-[var(--color-error)] hover:bg-[var(--color-error)]/80
           transition-all duration-200 group"
      title="Stop execution"
    >
      <Square size={20} class="text-white" fill="currentColor" />
    </button>
  {:else}
    <button
      type="submit"
      disabled={!hasDemo ||
        !canSubmitMessage ||
        (hasActiveSession && !canSend && !canStageNext) ||
        (loading && !queueMode)}
      aria-label={queueMode ? "Send next" : "Send message"}
      title={queueMode ? "Send next" : "Send message"}
      class="relative flex h-10 items-center justify-center rounded-lg
           bg-[var(--color-tertiary)] hover:bg-[var(--color-accent-hover)]
           disabled:opacity-40 disabled:cursor-not-allowed
           transition-all duration-200 group {queueMode ? 'gap-1.5 px-3' : 'w-10'}"
    >
      {#if queueMode}
        <span class="text-xs font-semibold uppercase tracking-wide text-[var(--color-on-tertiary)]">
          Send next
        </span>
        <Send
          size={16}
          class="text-[var(--color-on-tertiary)] transform group-hover:translate-x-0.5 transition-transform"
        />
      {:else}
        <Send
          size={20}
          class="text-[var(--color-on-tertiary)] transform group-hover:translate-x-0.5 transition-transform"
        />
      {/if}
    </button>
  {/if}
</div>
