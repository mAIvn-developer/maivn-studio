<script lang="ts">
  import type {
    BatchResult,
    HookFiring,
    InterruptData,
    Message,
    PhaseChipData,
    ToolCard as ToolCardType,
  } from "$lib/types";
  import MessageCard from "../message/MessageCard.svelte";
  import {
    buildScopeGroups,
    getMemoryPhaseChipsByPhase,
    getLatestRootPhaseChip,
    resolveScopePhaseChips,
  } from "./exchange-scope-groups";
  import {
    getFinalStructuredResult,
    getStructuredOutputPayload,
    hasAiTextResponse,
  } from "./exchange-structured-output";
  import ExchangeInlineInterrupts from "./ExchangeInlineInterrupts.svelte";
  import ExchangeBatchResultCard from "./ExchangeBatchResultCard.svelte";
  import ExchangePhasePreamble from "./ExchangePhasePreamble.svelte";
  import ExchangeScopeGroupList from "./ExchangeScopeGroupList.svelte";
  import ExchangeStatusMessages from "./ExchangeStatusMessages.svelte";
  import ExchangeStructuredOutputCard from "./ExchangeStructuredOutputCard.svelte";

  interface Props {
    humanMessage: Message;
    toolCards: ToolCardType[];
    phaseChips?: PhaseChipData[];
    scopeHookFirings?: Map<string, HookFiring[]>;
    statusMessages?: Message[];
    interruptCards?: InterruptData[];
    batchResults?: BatchResult[];
    aiMessage: Message | null;
    isLive?: boolean;
    showToolArgs?: boolean;
    expandAllCards?: boolean;
    richResultDisplay?: boolean;
    showStructuredOutput?: boolean;
    showSessionDetails?: boolean;
    /** Origin of the exchange — "schedule" applies the cron badge + tertiary border on its cards. */
    origin?: import("$lib/types").ChatFlowOrigin;
    /** Optional fire ID from the schedule. */
    scheduleFireId?: string;
    onSubmitInterrupt?: (interruptId: string, value: string) => void;
    onCancelInterrupt?: (interruptId: string) => void;
  }

  let {
    humanMessage,
    toolCards,
    phaseChips = [],
    scopeHookFirings,
    statusMessages = [],
    interruptCards = [],
    batchResults = [],
    aiMessage,
    isLive = false,
    showToolArgs = true,
    expandAllCards = false,
    richResultDisplay = true,
    showStructuredOutput = false,
    showSessionDetails = false,
    origin = "user",
    scheduleFireId,
    onSubmitInterrupt,
    onCancelInterrupt,
  }: Props = $props();

  const latestRootPhaseChip = $derived(() => getLatestRootPhaseChip(phaseChips));
  const memoryPhaseChips = $derived(() => getMemoryPhaseChipsByPhase(phaseChips));
  const scopeGroups = $derived(() => buildScopeGroups(toolCards));
  const latestStatusMessage = $derived(() => {
    const latest = statusMessages.at(-1);
    return typeof latest?.content === "string" && latest.content.trim().length > 0
      ? latest.content.trim()
      : null;
  });

  // Get tools that have results for the result section
  const toolsWithResults = $derived(
    toolCards.filter((t) => t.result !== undefined || t.error !== undefined || t.streamContent),
  );

  // Check if this message has session details (stats from SDK invocation)
  const hasSessionDetails = $derived(
    aiMessage?.sessionDetails?.duration_ms !== undefined ||
      aiMessage?.sessionDetails?.token_usage !== undefined,
  );

  const hasAiText = $derived(() => hasAiTextResponse(aiMessage));
  const finalResult = $derived(() => getFinalStructuredResult(aiMessage, toolCards));
  const structuredOutputPayload = $derived(() =>
    getStructuredOutputPayload(finalResult(), toolsWithResults),
  );
</script>

<div class="exchange-container space-y-3">
  <!-- Human Message -->
  <MessageCard message={humanMessage} {origin} {scheduleFireId} />

  <!-- Phase Chips + Tool/Agent Cards -->
  {#if phaseChips.length > 0 || toolCards.length > 0}
    <div class="agent-execution-section max-w-[85%]">
      <ExchangePhasePreamble
        latestRootPhaseChip={latestRootPhaseChip()}
        memoryPhaseChips={memoryPhaseChips()}
        {isLive}
      />

      <ExchangeScopeGroupList
        scopeGroups={scopeGroups()}
        {phaseChips}
        {scopeHookFirings}
        latestStatusMessage={latestStatusMessage()}
        {isLive}
        {showToolArgs}
        {expandAllCards}
        {richResultDisplay}
        {resolveScopePhaseChips}
      />
    </div>
  {/if}

  <ExchangeStatusMessages {statusMessages} />

  <ExchangeInlineInterrupts {interruptCards} {onSubmitInterrupt} {onCancelInterrupt} />

  {#each batchResults as batch (batch.batchId)}
    <ExchangeBatchResultCard {batch} {richResultDisplay} {showSessionDetails} />
  {/each}

  <!-- AI Message (separate card) -->
  {#if aiMessage}
    <div class="ai-response-section">
      {#if hasAiText()}
        <!-- AI has text response - show message card -->
        <MessageCard
          message={aiMessage}
          {origin}
          {scheduleFireId}
          structuredOutput={finalResult()}
          autoShowStructuredOutput={showStructuredOutput}
          autoShowSessionDetails={showSessionDetails}
        />
      {:else}
        <ExchangeStructuredOutputCard
          {aiMessage}
          structuredOutputPayload={structuredOutputPayload()}
          {hasSessionDetails}
          autoShowSessionDetails={showSessionDetails}
        />
      {/if}
    </div>
  {/if}
</div>

<style>
  .exchange-container {
    animation: slideIn 0.2s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* Agent execution section - centered to match message cards */
  .agent-execution-section {
    /* Center align like message cards */
    margin-left: auto;
    margin-right: auto;
    padding-left: 0;
    padding-right: 0;
  }
</style>
