<script lang="ts">
  import type { ScheduleConfig, ScheduleJobSummary } from "$lib/api_client/schedules";
  import type {
    BatchInvocationRow,
    DemoDetails,
    ModelToolOption,
    SavedPrompt,
    SendableMessageType,
    StructuredOutputConfig,
  } from "$lib/types";

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
  import ChatComposerScheduleActions from "./ChatComposerScheduleActions.svelte";
  import ChatComposerScheduleConfig from "./ChatComposerScheduleConfig.svelte";
  import ChatComposerToolbar from "./ChatComposerToolbar.svelte";

  type ComposerMode = "chat" | "schedule";

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
    demoTools?: DemoDetails["tools"];
    pendingAttachments: PendingAttachmentView[];
    formatAttachmentSize: (bytes: number) => string;
    canSubmitMessage: boolean;
    queueMode: boolean;
    batchMode?: boolean;
    batchRunsPerInput?: number;
    batchMaxConcurrency?: number;
    batchAsyncMode?: boolean;
    batchItemCount?: number;
    batchRows?: BatchInvocationRow[];
    inputValue?: string;
    selectedVariant?: string | undefined;
    localSystemMessage?: string;
    showSystemInput?: boolean;
    // Composer mode toggle. "chat" = current behavior (Send button). "schedule"
    // shows cadence config + schedule action bar; the textarea becomes the
    // prompt every fire sends.
    composerMode?: ComposerMode;
    scheduleSummary?: ScheduleJobSummary | null;
    scheduleConfig?: ScheduleConfig;
    scheduleBusy?: boolean;
    schedulePromptDirty?: boolean;
    promptOptions?: Array<{ id: string; name: string }>;
    structuredOutputConfig?: StructuredOutputConfig;
    availableModelTools?: ModelToolOption[];
    onStructuredOutputChange?: (config: StructuredOutputConfig) => void;
    onComposerModeChange?: (mode: ComposerMode) => void;
    onScheduleConfigChange?: (next: ScheduleConfig) => void;
    onScheduleStart?: () => void | Promise<void>;
    onSchedulePause?: () => void | Promise<void>;
    onScheduleResume?: () => void | Promise<void>;
    onScheduleTrigger?: () => void | Promise<void>;
    onScheduleStop?: () => void | Promise<void>;
    onScheduleRemove?: () => void | Promise<void>;
    onSelectedVariantChange?: (variant: string | undefined) => void;
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
    demoTools = [],
    pendingAttachments,
    formatAttachmentSize,
    canSubmitMessage,
    queueMode,
    batchMode = $bindable(false),
    batchRunsPerInput = $bindable(1),
    batchMaxConcurrency = $bindable(3),
    batchAsyncMode = $bindable(true),
    batchItemCount = 0,
    batchRows = $bindable<BatchInvocationRow[]>([]),
    inputValue = $bindable(""),
    selectedVariant = $bindable<string | undefined>(undefined),
    localSystemMessage = $bindable(""),
    showSystemInput = $bindable(false),
    composerMode = "chat",
    scheduleSummary = null,
    scheduleConfig,
    scheduleBusy = false,
    schedulePromptDirty = false,
    promptOptions = [],
    structuredOutputConfig,
    availableModelTools = [],
    onStructuredOutputChange,
    onComposerModeChange,
    onScheduleConfigChange,
    onScheduleStart,
    onSchedulePause,
    onScheduleResume,
    onScheduleTrigger,
    onScheduleStop,
    onScheduleRemove,
    onSelectedVariantChange,
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

<form onsubmit={onSubmit} class="composer-form">
  <div class="composer-content-lane">
    {#if composerMode === "schedule" && scheduleConfig}
      <ChatComposerScheduleConfig
        config={scheduleConfig}
        onChange={(next) => onScheduleConfigChange?.(next)}
        {promptOptions}
        summary={scheduleSummary}
      />
    {:else}
      <ChatComposerAdvancedOptions
        {hasDemo}
        {hasActiveSession}
        bind:showSystemInput
        bind:selectedVariant
        bind:localSystemMessage
        bind:batchMode
        bind:batchRunsPerInput
        bind:batchMaxConcurrency
        bind:batchAsyncMode
        bind:batchRows
        {batchItemCount}
        {demoTools}
        {variants}
        {structuredOutputConfig}
        {availableModelTools}
        {onSelectedVariantChange}
        {onStructuredOutputChange}
      />
    {/if}

    <div
      class="composer-shell"
      class:drag-active={isDragActive}
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
        {composerMode}
        onOpenFilePicker={openFilePicker}
        {onMessageTypeChange}
        {onComposerModeChange}
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
            class="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-secondary)]/25
                   bg-[var(--color-secondary)]/10 px-2.5 py-1 text-[11px] font-medium
                   text-[var(--color-secondary)]"
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
        {batchMode}
        {batchItemCount}
        canSubmitMessage={composerMode === "chat" ? canSubmitMessage : false}
        bind:inputValue
        {onKeyDown}
        onPaste={handleTextareaPaste}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        {onCancel}
        hideSubmitControls={composerMode === "schedule"}
      />

      {#if composerMode === "schedule"}
        <ChatComposerScheduleActions
          summary={scheduleSummary}
          busy={scheduleBusy}
          canSubmit={!!inputValue.trim()}
          promptDirty={schedulePromptDirty}
          onStart={() => onScheduleStart?.()}
          onPause={() => onSchedulePause?.()}
          onResume={() => onScheduleResume?.()}
          onTrigger={() => onScheduleTrigger?.()}
          onStop={() => onScheduleStop?.()}
          onRemove={() => onScheduleRemove?.()}
        />
      {/if}
    </div>

    <div class="composer-hint-row">
      <span class="composer-hint">
        {#if batchMode && !hasActiveSession}
          Press
          <kbd>Ctrl+Enter</kbd>
          to send batch
        {:else}
          Press
          <kbd>Enter</kbd>
          to {queueMode ? "queue for next turn" : "send"}
        {/if}
      </span>
    </div>
  </div>
</form>

<style>
  .composer-form {
    position: relative;
    z-index: 70;
    flex-shrink: 0;
    border-top: 1px solid var(--color-outline-variant);
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--color-bg-secondary) 18%, var(--color-bg)) 0%,
      var(--color-bg) 42%
    );
    padding: 1rem;
  }

  .composer-content-lane {
    width: 100%;
    max-width: 64rem;
    margin-inline: auto;
  }

  .composer-shell {
    position: relative;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-bg-secondary) 86%, var(--color-bg));
    box-shadow: var(--shadow-sm);
    overflow: visible;
    transition:
      border-color var(--transition-fast),
      box-shadow var(--transition-fast),
      background-color var(--transition-fast);
  }

  .composer-shell:focus-within,
  .composer-shell.drag-active {
    border-color: color-mix(in srgb, var(--color-secondary) 58%, var(--color-outline-variant));
    box-shadow: var(--shadow-glow-secondary);
  }

  .composer-hint-row {
    display: flex;
    justify-content: flex-end;
    margin-top: 0.45rem;
  }

  .composer-hint {
    color: var(--color-text-tertiary);
    font-size: 0.72rem;
  }

  .composer-hint kbd {
    display: inline-flex;
    align-items: center;
    min-height: 1.25rem;
    margin-inline: 0.15rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-sm);
    background: var(--color-bg-secondary);
    padding: 0 0.35rem;
    color: var(--color-text-secondary);
  }

  @media (max-width: 640px) {
    .composer-form {
      padding: 0.75rem;
    }
  }
</style>
