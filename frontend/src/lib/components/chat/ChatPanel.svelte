<script lang="ts">
  import type {
    ChatFlowItem,
    DemoDetails,
    InterruptData,
    InterruptStyle,
    MessageAttachmentPayload,
    SavedPrompt,
    SendableMessageType,
    StructuredOutputConfig,
  } from "$lib/types";
  import { ChevronDown } from "lucide-svelte";
  import InterruptContainer from "../interrupts/InterruptContainer.svelte";
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
  import ChatEmptyState from "./ChatEmptyState.svelte";
  import ChatExchangeList from "./ChatExchangeList.svelte";
  import ChatComposer from "./composer/ChatComposer.svelte";

  interface Props {
    demo: DemoDetails | null;
    chatFlowItems: ChatFlowItem[];
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
    showToolArgs?: boolean;
    expandAllCards?: boolean;
    richResultDisplay?: boolean;
    showStructuredOutput?: boolean;
    showSessionDetails?: boolean;
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
    ) => void | Promise<void>;
    onStart: (
      message: string,
      options?: {
        variant?: string;
        messageType?: SendableMessageType;
        systemMessage?: string;
        structuredOutput?: StructuredOutputConfig;
        attachments?: MessageAttachmentPayload[];
      },
    ) => void | Promise<void>;
    onCancel?: () => void;
    onMessageTypeChange: (type: SendableMessageType) => void;
    onSavePrompt?: (content: string) => void;
    // Interrupt handlers
    onSubmitInterrupt?: (interruptId: string, value: string) => void;
    onCancelInterrupt?: (interruptId: string) => void;
  }

  let {
    demo,
    chatFlowItems,
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
    showToolArgs = true,
    expandAllCards = false,
    richResultDisplay = true,
    showStructuredOutput = false,
    showSessionDetails = false,
    // Enrichment props
    currentPhaseMessage = null,
    // Interrupt props
    interruptStyle = "inline",
    pendingInterrupts = [],
    onSend,
    onStart,
    onCancel,
    onMessageTypeChange,
    onSavePrompt,
    // Interrupt handlers
    onSubmitInterrupt,
    onCancelInterrupt,
  }: Props = $props();

  let inputValue = $state("");
  let selectedVariant = $state<string | undefined>(undefined);
  let localSystemMessage = $state("");
  let showSystemInput = $state(false);
  let chatContainer: HTMLDivElement;
  let showScrollToBottom = $state(false);
  const SCROLL_BOTTOM_THRESHOLD = 4;

  let pendingAttachments = $state<PendingAttachment[]>([]);

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

  // Determine if the current input can be sent
  const canSubmitMessage = $derived(() => {
    if (!inputValue.trim() && pendingAttachments.length === 0) return false;
    if (loading && !(hasActiveSession && !canSend && canStageNext)) return false;
    return true;
  });

  const queueMode = $derived(() => hasActiveSession && !canSend && canStageNext);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    if ((!inputValue.trim() && pendingAttachments.length === 0) || (loading && !queueMode())) {
      return;
    }
    if (hasActiveSession && !canSend && !canStageNext) return;

    const outputConfig = structuredOutputConfig.enabled ? structuredOutputConfig : undefined;
    const message = inputValue.trim();
    const attachments = await buildAttachmentPayloads(pendingAttachments);

    try {
      if (!hasActiveSession) {
        await onStart(message, {
          variant: selectedVariant,
          messageType,
          systemMessage: localSystemMessage.trim() || undefined,
          structuredOutput: outputConfig,
          attachments,
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
  }

  function handleSavePrompt() {
    if (inputValue.trim() && onSavePrompt) {
      onSavePrompt(inputValue.trim());
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  const variants = $derived(demo ? Object.entries(demo.variants) : []);
  const prompts = $derived(demo?.prompts || []);
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
        (item) =>
          item.type === "interrupt_card" && (item.data as InterruptData).status === "waiting",
      ),
  );
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
        {#if chatFlowItems.length === 0 && !hasActiveSession}
          <ChatEmptyState {demo} {prompts} onSelectPrompt={selectPrompt} />
        {:else}
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
               bg-[var(--color-tertiary)] text-[var(--color-on-tertiary)]
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
    hasDemo={!!demo}
    {hasActiveSession}
    {canSend}
    {canStageNext}
    {loading}
    {queuedMessageCount}
    {messageType}
    discoveredPrompts={prompts}
    {savedPrompts}
    {variants}
    pendingAttachments={pendingAttachmentViews}
    {formatAttachmentSize}
    canSubmitMessage={canSubmitMessage()}
    queueMode={queueMode()}
    bind:inputValue
    bind:selectedVariant
    bind:localSystemMessage
    bind:showSystemInput
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
