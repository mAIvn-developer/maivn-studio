<script lang="ts">
  import type { InterruptStyle } from "$lib/types";
  import ExchangeContainer from "../exchange/ExchangeContainer.svelte";
  import MessageCard from "../message/MessageCard.svelte";
  import type { Exchange } from "./chat-exchanges";
  import ChatFilteredEmptyState from "./ChatFilteredEmptyState.svelte";
  import ChatProcessingIndicator from "./ChatProcessingIndicator.svelte";

  interface Props {
    exchanges: Exchange[];
    loading: boolean;
    hasWaitingInterrupts: boolean;
    currentPhaseMessage?: string | null;
    interruptStyle?: InterruptStyle;
    showToolArgs?: boolean;
    expandAllCards?: boolean;
    richResultDisplay?: boolean;
    showStructuredOutput?: boolean;
    showSessionDetails?: boolean;
    hasActiveSession: boolean;
    chatFlowItemsLength: number;
    onSubmitInterrupt?: (interruptId: string, value: string) => void;
    onCancelInterrupt?: (interruptId: string) => void;
  }

  let {
    exchanges,
    loading,
    hasWaitingInterrupts,
    currentPhaseMessage = null,
    interruptStyle = "inline",
    showToolArgs = true,
    expandAllCards = false,
    richResultDisplay = true,
    showStructuredOutput = false,
    showSessionDetails = false,
    hasActiveSession,
    chatFlowItemsLength,
    onSubmitInterrupt,
    onCancelInterrupt,
  }: Props = $props();
</script>

{#each exchanges as exchange, i (i)}
  {#if exchange.humanMessage.content}
    <ExchangeContainer
      humanMessage={exchange.humanMessage}
      toolCards={exchange.toolCards}
      phaseChips={exchange.phaseChips}
      statusMessages={exchange.statusMessages}
      interruptCards={interruptStyle === "inline" || interruptStyle === "hybrid"
        ? exchange.interruptCards
        : []}
      aiMessage={exchange.aiMessage}
      isLive={loading && i === exchanges.length - 1 && !exchange.aiMessage}
      {showToolArgs}
      {expandAllCards}
      {richResultDisplay}
      {showStructuredOutput}
      {showSessionDetails}
      {onSubmitInterrupt}
      {onCancelInterrupt}
    />
  {:else if exchange.aiMessage}
    <MessageCard
      message={exchange.aiMessage}
      autoShowStructuredOutput={showStructuredOutput}
      autoShowSessionDetails={showSessionDetails}
    />
  {/if}
{/each}

{#if loading && !hasWaitingInterrupts}
  <ChatProcessingIndicator {currentPhaseMessage} />
{/if}

{#if chatFlowItemsLength === 0 && hasActiveSession}
  <ChatFilteredEmptyState />
{/if}
