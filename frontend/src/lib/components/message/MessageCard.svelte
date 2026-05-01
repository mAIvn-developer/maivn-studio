<script lang="ts">
  import type { ChatFlowOrigin, Message } from "$lib/types";
  import { CalendarClock, Clock } from "lucide-svelte";
  import {
    highlightPrivateData,
    containsPrivateDataPlaceholders,
  } from "../markdown/markdown-parser";
  import MarkdownContent from "../markdown/MarkdownContent.svelte";
  import { copyMessageCardContent, copyMessageCardStructuredOutput } from "./message-card-copy";
  import MessageCardActionControls from "./MessageCardActionControls.svelte";
  import MessageCardSessionDetails from "./MessageCardSessionDetails.svelte";
  import MessageCardStructuredOutput from "./MessageCardStructuredOutput.svelte";

  interface Props {
    message: Message;
    structuredOutput?: unknown;
    autoShowStructuredOutput?: boolean;
    autoShowSessionDetails?: boolean;
    /** Origin of the message — defaults to user-typed. "schedule" applies a cron badge + border. */
    origin?: ChatFlowOrigin;
    /** Optional fire ID from the schedule that triggered this run. */
    scheduleFireId?: string;
  }

  let {
    message,
    structuredOutput,
    autoShowStructuredOutput = false,
    autoShowSessionDetails = false,
    origin = "user",
    scheduleFireId,
  }: Props = $props();

  const isFromSchedule = $derived(origin === "schedule");

  let showRawContent = $state(false);
  let showStructuredOutput = $state(false);
  let copied = $state(false);
  let copiedStructured = $state(false);

  const isUser = $derived(message.role === "user");
  const isAssistant = $derived(message.role === "assistant");
  const isStatus = $derived(message.messageType === "status");

  const hasStructuredContent = $derived(() => {
    if (!isAssistant) return false;
    return message.content.length > 500 || message.content.includes("```");
  });

  const hasStructuredOutput = $derived(structuredOutput !== undefined && structuredOutput !== null);

  // Check if this message has session details (stats from SDK invocation)
  const hasSessionDetails = $derived(
    message.sessionDetails?.duration_ms !== undefined ||
      message.sessionDetails?.token_usage !== undefined,
  );

  let showSessionDetails = $state(false);

  $effect(() => {
    if (autoShowStructuredOutput && hasStructuredOutput) {
      showStructuredOutput = true;
    }
  });

  $effect(() => {
    if (autoShowSessionDetails && hasSessionDetails) {
      showSessionDetails = true;
    }
  });

  const hasFooterActions = $derived(
    () => isAssistant && (hasStructuredContent() || hasStructuredOutput || hasSessionDetails),
  );

  // Format duration as seconds with 1 decimal
  function formatDuration(ms: number): string {
    return (ms / 1000).toFixed(1) + "s";
  }

  // Format token count with commas
  function formatTokens(count: number): string {
    return count.toLocaleString();
  }

  async function copyContent() {
    const success = await copyMessageCardContent(message.content);
    if (success) {
      copied = true;
      setTimeout(() => (copied = false), 2000);
    }
  }

  async function copyStructuredOutput() {
    if (!hasStructuredOutput) return;
    const success = await copyMessageCardStructuredOutput(structuredOutput);
    if (success) {
      copiedStructured = true;
      setTimeout(() => (copiedStructured = false), 2000);
    }
  }
</script>

<div class="flex animate-in" class:justify-end={isUser}>
  <div
    class="message-card group relative max-w-[85%] rounded-2xl overflow-hidden transition-all duration-200"
    class:user-message={isUser}
    class:assistant-message={isAssistant}
    class:status-message={isStatus}
    class:scheduled={isFromSchedule}
    title={isFromSchedule && scheduleFireId
      ? `Triggered by schedule (fire ${scheduleFireId})`
      : isFromSchedule
        ? "Triggered by schedule"
        : undefined}
  >
    {#if isFromSchedule}
      <span class="schedule-ribbon">
        <CalendarClock size={11} />
        Scheduled
      </span>
    {/if}
    <!-- Subtle gradient overlay for depth -->
    <div
      class="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent pointer-events-none"
    ></div>

    <!-- Header -->
    <div
      class="relative flex items-center justify-between px-4 py-2.5 border-b header-border"
      class:user-header={isUser}
      class:assistant-header={isAssistant}
      class:status-header={isStatus}
    >
      <div class="flex items-center gap-2.5">
        <!-- Avatar with brand colors -->
        <div
          class="avatar flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold shadow-inner"
          class:user-avatar={isUser}
          class:assistant-avatar={isAssistant}
          class:status-avatar={isStatus}
        >
          {isUser ? "U" : "AI"}
        </div>
        <span class="text-sm font-medium">
          {isUser ? "You" : "Assistant"}
        </span>

        <!-- Message type badge for non-human user messages -->
        {#if message.messageType !== "human" && isUser}
          <span
            class="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide
                   {message.messageType === 'redacted'
              ? 'bg-[var(--color-warning)]/20 text-[var(--color-warning)]'
              : ''}
                   {message.messageType === 'system'
              ? 'bg-[var(--color-secondary)]/20 text-[var(--color-secondary)]'
              : ''}"
          >
            {message.messageType}
          </span>
        {/if}

        {#if isUser && message.metadata?.queuedForNextTurn}
          <span
            class="inline-flex items-center gap-1 rounded-full bg-[var(--color-secondary)]/15
                   px-2 py-0.5 text-[10px] font-semibold text-[var(--color-secondary)]"
          >
            <Clock size={10} strokeWidth={2} />
            Queued for next turn
          </span>
        {/if}

        {#if isStatus}
          <span
            class="inline-flex items-center gap-1 rounded-full border border-[var(--color-outline-variant)]/70
                   bg-[var(--color-surface-variant)]/45 px-2 py-0.5 text-[10px] font-semibold uppercase
                   tracking-wide text-[var(--color-text-secondary)]"
          >
            Status Update
          </span>
        {/if}
      </div>

      <div class="flex items-center gap-2">
        <MessageCardActionControls
          {copied}
          hasStructuredContent={hasStructuredContent()}
          {hasStructuredOutput}
          {hasSessionDetails}
          {isAssistant}
          {showRawContent}
          {showStructuredOutput}
          {showSessionDetails}
          onCopyContent={copyContent}
          onToggleRawContent={() => (showRawContent = !showRawContent)}
          onToggleStructuredOutput={() => (showStructuredOutput = !showStructuredOutput)}
          onToggleSessionDetails={() => (showSessionDetails = !showSessionDetails)}
        />

        <span class="text-[10px] text-[var(--color-text-tertiary)] tabular-nums">
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>

    <!-- Content -->
    <div class="relative px-4 py-3">
      {#if isAssistant}
        {#if showRawContent}
          <pre
            class="whitespace-pre-wrap text-sm font-mono overflow-x-auto text-[var(--color-text-secondary)]">{message.content}</pre>
        {:else}
          <MarkdownContent content={message.content} />
        {/if}
      {:else if containsPrivateDataPlaceholders(message.content)}
        <!-- eslint-disable svelte/no-at-html-tags -->
        <div class="whitespace-pre-wrap text-[var(--color-text-secondary)]">
          {@html highlightPrivateData(message.content)}
        </div>
        <!-- eslint-enable svelte/no-at-html-tags -->
      {:else}
        <div class="whitespace-pre-wrap text-[var(--color-text-secondary)]">
          {message.content}
        </div>
      {/if}
    </div>

    <!-- Footer actions (duplicate of header toggles for long messages) -->
    {#if hasFooterActions()}
      <div
        class="flex items-center justify-end gap-2 px-4 py-2 border-t border-[var(--color-outline-variant)]/40 bg-black/5"
      >
        <div class="flex items-center gap-2">
          <MessageCardActionControls
            {copied}
            hasStructuredContent={hasStructuredContent()}
            {hasStructuredOutput}
            {hasSessionDetails}
            {isAssistant}
            {showRawContent}
            {showStructuredOutput}
            {showSessionDetails}
            onCopyContent={copyContent}
            onToggleRawContent={() => (showRawContent = !showRawContent)}
            onToggleStructuredOutput={() => (showStructuredOutput = !showStructuredOutput)}
            onToggleSessionDetails={() => (showSessionDetails = !showSessionDetails)}
          />
        </div>
      </div>
    {/if}

    <!-- Structured Output Section (collapsible) -->
    {#if isAssistant && hasStructuredOutput && showStructuredOutput}
      <MessageCardStructuredOutput
        {structuredOutput}
        {copiedStructured}
        onCopyStructuredOutput={copyStructuredOutput}
      />
    {/if}

    <!-- Session Details Section (collapsible) - stats from SDK invocation -->
    {#if isAssistant && hasSessionDetails && showSessionDetails}
      <MessageCardSessionDetails {message} {formatDuration} {formatTokens} />
    {/if}
  </div>
</div>

<style>
  .message-card {
    background-color: var(--color-bg-secondary);
    border: 1px solid var(--color-outline-variant);
  }

  /* User messages - more subtle/dull styling */
  .user-message {
    background-color: var(--color-bg-tertiary);
    border-color: var(--color-outline-variant);
  }

  /* AI/Assistant messages - muted tertiary accent */
  .assistant-message {
    background: linear-gradient(
      135deg,
      color-mix(in srgb, var(--color-tertiary-container) 80%, var(--color-bg-secondary)) 0%,
      color-mix(in srgb, var(--color-secondary) 20%, var(--color-bg-secondary)) 100%
    );
    border-color: color-mix(in srgb, var(--color-secondary) 30%, transparent);
  }

  .status-message {
    background: linear-gradient(
      135deg,
      color-mix(in srgb, var(--color-surface-variant) 72%, var(--color-bg-secondary)) 0%,
      color-mix(in srgb, var(--color-secondary) 10%, var(--color-bg-secondary)) 100%
    );
    border-color: color-mix(in srgb, var(--color-secondary) 16%, var(--color-outline-variant));
  }

  .user-header {
    border-color: var(--color-outline-variant);
  }

  .assistant-header {
    border-color: color-mix(in srgb, var(--color-secondary) 18%, transparent);
  }

  .status-header {
    border-color: color-mix(in srgb, var(--color-outline-variant) 78%, transparent);
  }

  .user-avatar {
    background-color: color-mix(in srgb, var(--color-primary) 15%, transparent);
    color: var(--color-text-secondary);
  }

  .assistant-avatar {
    background-color: color-mix(in srgb, var(--color-secondary) 25%, transparent);
    color: var(--color-secondary);
  }

  .status-avatar {
    background-color: color-mix(in srgb, var(--color-surface-variant) 88%, transparent);
    color: var(--color-text-secondary);
  }

  /* Cron-triggered card treatment. Uses tertiary (the warm pink/lavender) so
     scheduled runs read as "different from a user-typed turn" without
     fighting the cyan secondary that drives most accents. */
  .message-card.scheduled {
    border: 1px solid color-mix(in srgb, var(--color-tertiary) 45%, var(--color-outline-variant));
    box-shadow:
      0 0 0 1px color-mix(in srgb, var(--color-tertiary) 18%, transparent),
      var(--shadow-glow-tertiary);
    padding-top: 1.4rem;
  }

  .schedule-ribbon {
    position: absolute;
    top: 0.45rem;
    left: 0.55rem;
    z-index: 2;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.1rem 0.45rem;
    border-radius: var(--radius-full);
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-on-tertiary);
    background: var(--color-tertiary);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
  }
</style>
