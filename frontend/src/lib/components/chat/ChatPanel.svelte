<script lang="ts">
  import type {
    BatchInvocationConfig,
    BatchInvocationRow,
    ChatFlowItem,
    AppDetails,
    HookFiring,
    InterruptData,
    InterruptStyle,
    MessageAttachmentPayload,
    ModelToolOption,
    SavedPrompt,
    SendableMessageType,
    StructuredOutputConfig,
  } from "$lib/types";
  import { ChevronDown } from "lucide-svelte";
  import { onDestroy } from "svelte";

  import { useSchedule } from "$lib/stores/schedule.svelte";

  import InterruptContainer from "../interrupts/InterruptContainer.svelte";
  import ScheduleRunsView from "../schedule/ScheduleRunsView.svelte";
  import type { PendingAttachment } from "./chat-attachments";
  import {
    buildAttachmentPayloads,
    clearPendingAttachments,
    dedupeAndAppendFiles,
    formatAttachmentSize,
    removePendingAttachment,
  } from "./chat-attachments";
  import { buildExchanges } from "./chat-exchanges";
  import {
    jumpContainerToBottom,
    scrollContainerToBottom,
    shouldShowScrollToBottom,
  } from "./chat-scroll";
  import { getDefaultPromptContent, shouldReplaceComposerDraft } from "./prompt-sync";
  import ChatEmptyState from "./ChatEmptyState.svelte";
  import ChatExchangeList from "./ChatExchangeList.svelte";
  import ChatComposer from "./composer/ChatComposer.svelte";

  interface Props {
    app: AppDetails | null;
    chatFlowItems: ChatFlowItem[];
    scopeHookFirings?: Map<string, HookFiring[]>;
    loading: boolean;
    canSend: boolean;
    canStageNext: boolean;
    queuedMessageCount?: number;
    hasActiveSession: boolean;
    messageType: SendableMessageType;
    savedPrompts: SavedPrompt[];
    // Structured output: UI control lives in ConfigTab; ChatPanel reads the config
    // for message submission and writes it when a prompt auto-selects a tool.
    structuredOutputConfig: StructuredOutputConfig;
    onStructuredOutputChange: (config: StructuredOutputConfig) => void;
    availableModelTools?: ModelToolOption[];
    selectedVariant?: string | undefined;
    showToolArgs?: boolean;
    expandAllCards?: boolean;
    richResultDisplay?: boolean;
    showStructuredOutput?: boolean;
    showSessionDetails?: boolean;
    threadResetRevision?: number;
    // Enrichment props
    currentPhaseMessage?: string | null;
    // Interrupt props
    interruptStyle?: InterruptStyle;
    pendingInterrupts?: InterruptData[];
    onSend: (
      message: string,
      messageType?: SendableMessageType,
      structuredOutput?: StructuredOutputConfig,
      attachments?: MessageAttachmentPayload[],
      batch?: BatchInvocationConfig,
    ) => void | Promise<void>;
    onStart: (
      message: string,
      options?: {
        variant?: string;
        messageType?: SendableMessageType;
        systemMessage?: string;
        structuredOutput?: StructuredOutputConfig;
        attachments?: MessageAttachmentPayload[];
        batch?: BatchInvocationConfig;
      },
    ) => void | Promise<void>;
    onCancel?: () => void;
    onMessageTypeChange: (type: SendableMessageType) => void;
    onSelectedVariantChange?: (variant: string | undefined) => void;
    onSavePrompt?: (content: string) => void;
    // Interrupt handlers
    onSubmitInterrupt?: (interruptId: string, value: string) => void;
    onCancelInterrupt?: (interruptId: string) => void;
  }

  let {
    app,
    chatFlowItems,
    scopeHookFirings,
    loading,
    canSend,
    canStageNext,
    queuedMessageCount = 0,
    hasActiveSession,
    messageType,
    savedPrompts = [],
    // Structured output (UI in ConfigTab; used here for submit + prompt auto-select)
    structuredOutputConfig,
    onStructuredOutputChange,
    availableModelTools = [],
    selectedVariant = $bindable<string | undefined>(undefined),
    showToolArgs = true,
    expandAllCards = false,
    richResultDisplay = true,
    showStructuredOutput = false,
    showSessionDetails = false,
    threadResetRevision = 0,
    // Enrichment props
    currentPhaseMessage = null,
    // Interrupt props
    interruptStyle = "inline",
    pendingInterrupts = [],
    onSend,
    onStart,
    onCancel,
    onMessageTypeChange,
    onSelectedVariantChange,
    onSavePrompt,
    // Interrupt handlers
    onSubmitInterrupt,
    onCancelInterrupt,
  }: Props = $props();

  let inputValue = $state("");
  let localSystemMessage = $state("");
  let showSystemInput = $state(false);
  let batchMode = $state(false);
  let batchRunsPerInput = $state(1);
  let batchMaxConcurrency = $state(3);
  let batchAsyncMode = $state(true);
  let batchRows = $state<BatchInvocationRow[]>([]);
  let wasBatchMode = $state(false);
  let chatContainer: HTMLDivElement;
  let showScrollToBottom = $state(false);
  const SCROLL_BOTTOM_THRESHOLD = 4;
  let pendingVariantPromptSync = $state<{ seed: string; promptSignature: string } | null>(null);

  let pendingAttachments = $state<PendingAttachment[]>([]);
  // Tracks whether a schedule is configured for the current app. ScheduleRunsView
  // tells us via onActiveChange so we can hide the chat empty state — when the
  // user is in cron mode, the welcome scaffolding would just be in the way.
  let scheduleActive = $state(false);

  // Composer mode toggle. "schedule" reveals cadence config + replaces the
  // Send button with start/update/pause/stop controls.
  let composerMode = $state<"chat" | "schedule">("chat");

  // Per-app schedule store (reference-counted, polls on its own). Held
  // here so the composer's submit handler can write config + prompt_text.
  type ScheduleHandle = ReturnType<typeof useSchedule>;

  let schedule = $state<ScheduleHandle | null>(null);
  let scheduleAppId = $state<string | null>(null);
  let seenThreadResetRevision = $state<number | null>(null);
  let scheduleResetRevision = $state(0);

  function ensureScheduleStore(): ScheduleHandle | null {
    const appId = app?.id ?? null;
    if (!appId) return null;
    if (schedule && scheduleAppId === appId) return schedule;
    if (schedule) schedule.dispose();
    scheduleAppId = appId;
    schedule = useSchedule(appId);
    return schedule;
  }

  function clearConfiguredSchedule(): void {
    scheduleActive = false;
    scheduleResetRevision += 1;
    const activeSchedule = schedule;
    schedule = null;
    if (activeSchedule) {
      void activeSchedule.remove().finally(() => activeSchedule.dispose());
    }
  }

  function resetLocalThreadState(): void {
    inputValue = "";
    localSystemMessage = "";
    showSystemInput = false;
    batchMode = false;
    batchRunsPerInput = 1;
    batchMaxConcurrency = 3;
    batchAsyncMode = true;
    batchRows = [];
    wasBatchMode = false;
    pendingAttachments = clearPendingAttachments();
    scheduleActive = false;
    composerMode = "chat";
    pendingVariantPromptSync = null;
  }

  $effect(() => {
    const newAppId = app?.id ?? null;
    if (newAppId === scheduleAppId) return;
    if (schedule) {
      schedule.dispose();
      schedule = null;
    }
    scheduleAppId = newAppId;
    if (newAppId) {
      schedule = useSchedule(newAppId);
    }
  });

  onDestroy(() => {
    if (schedule) schedule.dispose();
  });

  $effect(() => {
    const revision = threadResetRevision;
    if (seenThreadResetRevision === null) {
      seenThreadResetRevision = revision;
      return;
    }
    if (revision === seenThreadResetRevision) return;
    seenThreadResetRevision = revision;
    resetLocalThreadState();
    clearConfiguredSchedule();
  });

  function handleComposerModeChange(mode: "chat" | "schedule"): void {
    composerMode = mode;
    if (mode === "chat") {
      clearConfiguredSchedule();
    } else {
      ensureScheduleStore();
    }
  }

  // Tracks whether the textarea differs from the prompt the schedule was
  // last saved with. When dirty, the action bar's Update button highlights.
  const schedulePromptDirty = $derived.by(() => {
    if (!schedule?.summary) return false;
    const saved = schedule.summary.config.prompt_text ?? "";
    return inputValue.trim() !== saved.trim();
  });

  // Hydrate the textarea with the schedule's saved prompt when entering
  // schedule mode (so the user sees what's currently running). Skipped if
  // they've typed something the schedule doesn't yet know about.
  $effect(() => {
    if (composerMode !== "schedule") return;
    const saved = schedule?.summary?.config.prompt_text;
    if (typeof saved === "string" && saved.trim() && !inputValue.trim()) {
      inputValue = saved;
    }
  });

  async function handleScheduleStart(): Promise<void> {
    const activeSchedule = ensureScheduleStore();
    if (!activeSchedule) return;
    activeSchedule.setConfig({ ...activeSchedule.config, prompt_text: inputValue });
    await activeSchedule.start();
  }

  // Auto-scroll to bottom when new items arrive
  function updateScrollIndicator() {
    if (!chatContainer) return;
    showScrollToBottom = shouldShowScrollToBottom(chatContainer, SCROLL_BOTTOM_THRESHOLD);
  }

  function scrollToBottom() {
    if (!chatContainer) return;
    scrollContainerToBottom(chatContainer);
  }

  function handleFilesSelected(files: File[]): void {
    pendingAttachments = dedupeAndAppendFiles(pendingAttachments, files);
  }

  function removeAttachment(attachmentId: string): void {
    pendingAttachments = removePendingAttachment(pendingAttachments, attachmentId);
  }

  function clearAttachments(): void {
    pendingAttachments = clearPendingAttachments();
  }

  $effect(() => {
    if (chatFlowItems.length > 0 && chatContainer) {
      requestAnimationFrame(() => {
        jumpContainerToBottom(chatContainer);
        updateScrollIndicator();
      });
    }
  });

  $effect(() => {
    if (!canUseBatchMode() && batchMode) {
      batchMode = false;
    }
  });

  $effect(() => {
    if (batchMode && !wasBatchMode) {
      const seededRows = inputValue
        .split(/\r?\n/)
        .map((item) => item.trim())
        .filter(Boolean)
        .map((message) => ({
          id: crypto.randomUUID(),
          label: "",
          message,
        }));
      if (seededRows.length > 0) {
        batchRows = seededRows;
      }
      inputValue = "";
    }
    wasBatchMode = batchMode;
  });

  const runnableBatchRows = $derived(() =>
    batchRows
      .map((row) => ({
        ...row,
        label: row.label?.trim() || undefined,
        message: row.message.trim(),
        system_message: row.system_message?.trim() || undefined,
        targeted_tools: row.targeted_tools?.map((tool) => tool.trim()).filter(Boolean),
      }))
      .filter((row) => row.message),
  );
  const effectiveBatchRows = $derived(() =>
    runnableBatchRows().flatMap((row) =>
      Array.from({ length: batchRunsPerInput }, (_, runIndex) => ({
        ...row,
        id: `${row.id ?? row.message}:${runIndex}`,
        label:
          batchRunsPerInput > 1 && row.label
            ? `${row.label} ${runIndex + 1}`
            : batchRunsPerInput > 1
              ? `Run ${runIndex + 1}`
              : row.label,
      })),
    ),
  );
  const canUseBatchMode = $derived(() => !hasActiveSession);

  // Determine if the current input can be sent
  const canSubmitMessage = $derived(() => {
    if (app?.loadable === false) return false;
    if (batchMode && !hasActiveSession && effectiveBatchRows().length === 0) return false;
    if (!batchMode && !inputValue.trim() && pendingAttachments.length === 0) return false;
    if (loading && !(hasActiveSession && !canSend && canStageNext)) return false;
    return true;
  });

  const queueMode = $derived(() => hasActiveSession && !canSend && canStageNext);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    if (
      (!batchMode && !inputValue.trim() && pendingAttachments.length === 0) ||
      (batchMode && !hasActiveSession && effectiveBatchRows().length === 0) ||
      (loading && !queueMode())
    ) {
      return;
    }
    if (hasActiveSession && !canSend && !canStageNext) return;

    const outputConfig = structuredOutputConfig.enabled ? structuredOutputConfig : undefined;
    const activeBatchRows = batchMode && !hasActiveSession ? effectiveBatchRows() : [];
    const message =
      activeBatchRows.length > 0
        ? activeBatchRows
            .map((row, index) => `${index + 1}. ${row.label ? `${row.label}: ` : ""}${row.message}`)
            .join("\n")
        : inputValue.trim();
    const attachments = await buildAttachmentPayloads(pendingAttachments);
    const batchConfig: BatchInvocationConfig | undefined =
      activeBatchRows.length > 0
        ? {
            enabled: true,
            messages: activeBatchRows.map((row) => row.message),
            rows: activeBatchRows.map((row) => ({
              id: row.id,
              label: row.label,
              message: row.message,
              variant: row.variant,
              model: row.model,
              reasoning: row.reasoning,
              system_message: row.system_message,
              targeted_tools:
                row.targeted_tools && row.targeted_tools.length > 0
                  ? row.targeted_tools
                  : undefined,
              force_final_tool: row.force_final_tool,
              stream_response: row.stream_response,
            })),
            max_concurrency: batchMaxConcurrency,
            async_mode: batchAsyncMode,
          }
        : undefined;

    try {
      if (!hasActiveSession) {
        await onStart(message, {
          variant: selectedVariant,
          messageType,
          systemMessage: localSystemMessage.trim() || undefined,
          structuredOutput: outputConfig,
          attachments,
          batch: batchConfig,
        });
        localSystemMessage = ""; // Reset system message after starting
      } else if (canSend || canStageNext) {
        await onSend(message, messageType, outputConfig, attachments);
      }
      inputValue = "";
      clearAttachments();
    } catch (err) {
      console.error("Failed to submit message", err);
      inputValue = "";
      clearAttachments();
    }
  }

  function selectPrompt(
    content: string,
    structuredOutputTool?: string,
    promptMessageType?: string,
    promptVariant?: string,
  ) {
    inputValue = content;
    if (batchMode && !hasActiveSession) {
      batchRows = [
        {
          id: crypto.randomUUID(),
          label: "",
          message: content,
          variant: promptVariant || undefined,
        },
      ];
      inputValue = "";
    }
    // Auto-select structured output when prompt specifies one
    if (structuredOutputTool) {
      onStructuredOutputChange({
        enabled: true,
        selectedTool: structuredOutputTool,
      });
    } else {
      onStructuredOutputChange({
        enabled: false,
        selectedTool: undefined,
      });
    }
    // Auto-select message type when prompt specifies one
    if (promptMessageType === "human" || promptMessageType === "redacted") {
      onMessageTypeChange(promptMessageType);
    }
    // Auto-select variant when prompt specifies one, otherwise reset to default
    selectedVariant = promptVariant || undefined;
    onSelectedVariantChange?.(selectedVariant);
  }

  function handleSavePrompt() {
    if (inputValue.trim() && onSavePrompt) {
      onSavePrompt(inputValue.trim());
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (batchMode && !hasActiveSession && e.key === "Enter" && !(e.ctrlKey || e.metaKey)) {
      return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  const variants = $derived(app ? Object.entries(app.variants) : []);
  const prompts = $derived(app?.prompts || []);
  const promptSignature = $derived(
    prompts.map((prompt) => `${prompt.id}:${prompt.content}`).join("\u0001"),
  );
  const pendingAttachmentViews = $derived(
    pendingAttachments.map((attachment) => ({
      id: attachment.id,
      name: attachment.name,
      size: attachment.size,
    })),
  );

  const exchanges = $derived(() => buildExchanges(chatFlowItems));

  // Handle interrupt submission
  function handleInterruptSubmit(interruptId: string, value: string) {
    if (onSubmitInterrupt) {
      onSubmitInterrupt(interruptId, value);
    }
  }

  // Handle interrupt cancellation
  function handleInterruptCancel(interruptId: string) {
    if (onCancelInterrupt) {
      onCancelInterrupt(interruptId);
    }
  }

  // Check if there are pending interrupts that need overlay rendering (modal, drawer, floating)
  const hasOverlayInterrupts = $derived(
    pendingInterrupts.length > 0 && interruptStyle !== "inline",
  );

  // Check if there are any waiting interrupts (to hide thinking indicator)
  const hasWaitingInterrupts = $derived(
    pendingInterrupts.some((i) => i.status === "waiting") ||
      chatFlowItems.some(
        (item) => item.type === "interrupt_card" && item.data.status === "waiting",
      ),
  );

  $effect(() => {
    const pendingSync = pendingVariantPromptSync;
    const currentPromptSignature = promptSignature;
    if (
      !pendingSync ||
      hasActiveSession ||
      currentPromptSignature === pendingSync.promptSignature
    ) {
      return;
    }

    pendingVariantPromptSync = null;
    if (inputValue.trim() !== pendingSync.seed) {
      return;
    }

    const nextDefaultPrompt = getDefaultPromptContent(prompts);
    if (!nextDefaultPrompt) {
      return;
    }

    inputValue = nextDefaultPrompt;
  });

  function handleSelectedVariantChange(variant: string | undefined): void {
    pendingVariantPromptSync = shouldReplaceComposerDraft(inputValue, prompts)
      ? {
          seed: inputValue.trim(),
          promptSignature,
        }
      : null;
    selectedVariant = variant;
    onSelectedVariantChange?.(variant);
  }
</script>

<div class="flex h-full flex-col" role="region" aria-label="Chat">
  <!-- Chat Flow Area (scrollable) -->
  <div class="relative flex-1 min-h-0">
    <div
      bind:this={chatContainer}
      class="h-full overflow-y-auto p-4"
      onscroll={updateScrollIndicator}
      role="log"
      aria-label="Chat messages"
      aria-live="polite"
    >
      <div class="chat-content-lane">
        {#if app}
          <ScheduleRunsView
            appId={app.id}
            {chatFlowItems}
            resetRevision={threadResetRevision + scheduleResetRevision}
            onActiveChange={(active) => (scheduleActive = active)}
          />
        {/if}
        {#if chatFlowItems.length === 0 && !hasActiveSession && !scheduleActive}
          <ChatEmptyState {app} {prompts} onSelectPrompt={selectPrompt} />
        {:else if chatFlowItems.length > 0 || hasActiveSession}
          <ChatExchangeList
            exchanges={exchanges()}
            {loading}
            {hasWaitingInterrupts}
            {currentPhaseMessage}
            {interruptStyle}
            {showToolArgs}
            {expandAllCards}
            {richResultDisplay}
            {showStructuredOutput}
            {showSessionDetails}
            {hasActiveSession}
            chatFlowItemsLength={chatFlowItems.length}
            {scopeHookFirings}
            onSubmitInterrupt={handleInterruptSubmit}
            onCancelInterrupt={handleInterruptCancel}
          />
        {/if}
      </div>
    </div>

    {#if showScrollToBottom}
      <button
        type="button"
        onclick={scrollToBottom}
        class="absolute bottom-4 right-6 z-10 flex items-center justify-center w-10 h-10 rounded-full
               bg-[var(--color-secondary)] text-[var(--color-on-secondary)]
               shadow-lg shadow-black/30 hover:bg-[var(--color-accent-hover)]
               transition-all duration-200"
        aria-label="Scroll to bottom"
        title="Scroll to bottom"
      >
        <ChevronDown size={20} />
      </button>
    {/if}

    <!-- Non-inline interrupt container (modal, drawer, floating) -->
    {#if hasOverlayInterrupts}
      <InterruptContainer
        style={interruptStyle}
        interrupts={pendingInterrupts}
        onSubmit={handleInterruptSubmit}
        onCancel={handleInterruptCancel}
      />
    {/if}
  </div>

  <ChatComposer
    hasApp={!!app}
    {hasActiveSession}
    {canSend}
    {canStageNext}
    {loading}
    {queuedMessageCount}
    {messageType}
    discoveredPrompts={prompts}
    {savedPrompts}
    {variants}
    appTools={app?.tools ?? []}
    pendingAttachments={pendingAttachmentViews}
    {formatAttachmentSize}
    canSubmitMessage={canSubmitMessage()}
    queueMode={queueMode()}
    batchItemCount={effectiveBatchRows().length}
    bind:inputValue
    bind:selectedVariant
    bind:localSystemMessage
    bind:showSystemInput
    bind:batchMode
    bind:batchRunsPerInput
    bind:batchMaxConcurrency
    bind:batchAsyncMode
    bind:batchRows
    {composerMode}
    scheduleSummary={schedule?.summary ?? null}
    scheduleConfig={schedule?.config}
    scheduleBusy={schedule?.busy ?? false}
    {schedulePromptDirty}
    promptOptions={prompts.map((p) => ({ id: p.id, name: p.name }))}
    {structuredOutputConfig}
    {availableModelTools}
    {onStructuredOutputChange}
    onComposerModeChange={handleComposerModeChange}
    onScheduleConfigChange={(next) => schedule?.setConfig(next)}
    onScheduleStart={handleScheduleStart}
    onSchedulePause={() => schedule?.pause()}
    onScheduleResume={() => schedule?.resume()}
    onScheduleTrigger={() => schedule?.trigger()}
    onScheduleStop={() => schedule?.stop()}
    onScheduleRemove={() => schedule?.remove()}
    onSelectedVariantChange={handleSelectedVariantChange}
    onSubmit={handleSubmit}
    {onMessageTypeChange}
    onSavePrompt={inputValue.trim() ? handleSavePrompt : undefined}
    onSelectPrompt={selectPrompt}
    onFilesSelected={handleFilesSelected}
    onRemoveAttachment={removeAttachment}
    onClearAttachments={clearAttachments}
    onKeyDown={handleKeyDown}
    {onCancel}
  />
</div>

<style>
  .chat-content-lane {
    width: 100%;
    max-width: 62rem;
    margin-inline: auto;
    min-height: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
</style>
