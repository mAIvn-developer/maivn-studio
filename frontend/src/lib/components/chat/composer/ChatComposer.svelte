<script lang="ts">
  import type { DemoDetails, SavedPrompt, SendableMessageType } from "$lib/types";
  import {
    extractFilesFromClipboardEvent,
    extractFilesFromDropEvent,
    extractFilesFromInputEvent,
    resetFileInputValue,
    shouldIgnoreDragLeave,
  } from "./chat-composer-files";
  import ChatComposerAdvancedOptions from "./ChatComposerAdvancedOptions.svelte";
  import ChatComposerAttachments from "./ChatComposerAttachments.svelte";
  import ChatComposerFooter from "./ChatComposerFooter.svelte";
  import ChatComposerToolbar from "./ChatComposerToolbar.svelte";

  interface PendingAttachmentView {
    id: string;
    name: string;
    size: number;
  }

  interface Props {
    hasDemo: boolean;
    hasActiveSession: boolean;
    canSend: boolean;
    canStageNext: boolean;
    loading: boolean;
    queuedMessageCount: number;
    messageType: SendableMessageType;
    discoveredPrompts: DemoDetails["prompts"];
    savedPrompts: SavedPrompt[];
    variants: Array<[string, DemoDetails["variants"][string]]>;
    pendingAttachments: PendingAttachmentView[];
    formatAttachmentSize: (bytes: number) => string;
    canSubmitMessage: boolean;
    queueMode: boolean;
    inputValue?: string;
    selectedVariant?: string | undefined;
    localSystemMessage?: string;
    showSystemInput?: boolean;
    onSubmit: (event: Event) => void | Promise<void>;
    onMessageTypeChange: (type: SendableMessageType) => void;
    onSavePrompt?: () => void;
    onSelectPrompt: (
      content: string,
      structuredOutputTool?: string,
      promptMessageType?: string,
      promptVariant?: string,
    ) => void;
    onFilesSelected: (files: File[]) => void;
    onRemoveAttachment: (attachmentId: string) => void;
    onClearAttachments: () => void;
    onKeyDown: (event: KeyboardEvent) => void;
    onCancel?: () => void;
  }

  let {
    hasDemo,
    hasActiveSession,
    canSend,
    canStageNext,
    loading,
    queuedMessageCount,
    messageType,
    discoveredPrompts,
    savedPrompts,
    variants,
    pendingAttachments,
    formatAttachmentSize,
    canSubmitMessage,
    queueMode,
    inputValue = $bindable(""),
    selectedVariant = $bindable<string | undefined>(undefined),
    localSystemMessage = $bindable(""),
    showSystemInput = $bindable(false),
    onSubmit,
    onMessageTypeChange,
    onSavePrompt,
    onSelectPrompt,
    onFilesSelected,
    onRemoveAttachment,
    onClearAttachments,
    onKeyDown,
    onCancel,
  }: Props = $props();

  let fileInputElement = $state<HTMLInputElement | undefined>(undefined);
  let isDragActive = $state(false);

  function openFilePicker(): void {
    fileInputElement?.click();
  }

  function handleFileInputChange(event: Event): void {
    const files = extractFilesFromInputEvent(event);
    if (files.length === 0) return;
    onFilesSelected(files);
    resetFileInputValue(event);
  }

  function handleTextareaPaste(event: ClipboardEvent): void {
    const files = extractFilesFromClipboardEvent(event);
    if (files.length === 0) return;
    event.preventDefault();
    onFilesSelected(files);
  }

  function handleDragOver(event: DragEvent): void {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "copy";
    }
    isDragActive = true;
  }

  function handleDragLeave(event: DragEvent): void {
    event.preventDefault();
    if (shouldIgnoreDragLeave(event)) {
      return;
    }
    isDragActive = false;
  }

  function handleDrop(event: DragEvent): void {
    event.preventDefault();
    isDragActive = false;
    const files = extractFilesFromDropEvent(event);
    if (files.length === 0) return;
    onFilesSelected(files);
  }
</script>

<form
  onsubmit={onSubmit}
  class="relative shrink-0 border-t border-[var(--color-outline-variant)] p-4 bg-[var(--color-bg)]"
>
  <div class="composer-content-lane">
    <ChatComposerAdvancedOptions
      {hasDemo}
      {hasActiveSession}
      bind:showSystemInput
      bind:selectedVariant
      bind:localSystemMessage
      {variants}
    />

    <div
      class="rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-outline-variant)]
           focus-within:border-[var(--color-tertiary)]/50 focus-within:shadow-[var(--shadow-glow-tertiary)]
           transition-all duration-200 {isDragActive
        ? 'border-[var(--color-tertiary)] shadow-[var(--shadow-glow-tertiary)]'
        : ''}"
      role="region"
      aria-label="Message composer and file drop zone"
      ondragover={handleDragOver}
      ondragleave={handleDragLeave}
      ondrop={handleDrop}
    >
      <ChatComposerToolbar
        {hasDemo}
        {hasActiveSession}
        {canSend}
        {loading}
        {messageType}
        {discoveredPrompts}
        {savedPrompts}
        {inputValue}
        onOpenFilePicker={openFilePicker}
        {onMessageTypeChange}
        {onSavePrompt}
        {onSelectPrompt}
        onFileInputChange={handleFileInputChange}
        bind:bindFileInput={fileInputElement}
      />

      <ChatComposerAttachments
        {pendingAttachments}
        {formatAttachmentSize}
        {onRemoveAttachment}
        {onClearAttachments}
      />

      {#if queuedMessageCount > 0}
        <div class="px-3 pt-1">
          <span
            class="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-tertiary)]/25
                   bg-[var(--color-tertiary)]/10 px-2.5 py-1 text-[11px] font-medium
                   text-[var(--color-tertiary)]"
          >
            Queued for next turn: {queuedMessageCount}
          </span>
        </div>
      {/if}

      <ChatComposerFooter
        {hasDemo}
        {hasActiveSession}
        {canSend}
        {canStageNext}
        {loading}
        {queueMode}
        {canSubmitMessage}
        bind:inputValue
        {onKeyDown}
        onPaste={handleTextareaPaste}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        {onCancel}
      />
    </div>

    <div class="mt-2 flex justify-end">
      <span class="text-xs text-[var(--color-text-tertiary)]">
        Press <kbd class="px-1.5 py-0.5 rounded bg-[var(--color-bg-tertiary)] font-mono text-[10px]"
          >Enter</kbd
        >
        to {queueMode ? "queue for next turn" : "send"}
      </span>
    </div>
  </div>
</form>

<style>
  .composer-content-lane {
    width: 100%;
    max-width: 62rem;
    margin-inline: auto;
  }
</style>
