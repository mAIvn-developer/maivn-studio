<script lang="ts">
  import type { HookFiring, PhaseChipData, ToolCard as ToolCardType } from "$lib/types";
  import HookFiringMarker from "../ui/HookFiringMarker.svelte";
  import { getAgentResponse, isAgentFinalOutput } from "./scope-group-agent-response";
  import {
    buildNestedAgentPhaseChipsMap,
    getActiveAgentCount,
    getAggregateStatus,
    getDisplayPhaseMessage,
    getDisplayTools,
    getScopeGroupCounts,
    getStatusTools,
    resolveDirectPhaseChip,
    resolveNestedAgentPhaseChips,
    type NestedAgent,
    type ScopeType,
  } from "./scope-group-helpers";
  import {
    getScopeGroupCurrentStatus,
    getScopeGroupExpandIconSizePx,
    getScopeGroupIconSize,
    getScopeGroupInnerIconSizePx,
  } from "./scope-group-status-ui";
  import ScopeGroupHeader from "./ScopeGroupHeader.svelte";
  import ScopeGroupNestedContent from "./ScopeGroupNestedContent.svelte";

  interface Props {
    scopeType: ScopeType;
    scopeName: string;
    scopeId?: string;
    tools: ToolCardType[];
    nestedAgents?: NestedAgent[]; // For swarm type, contains child agents
    phaseChips?: PhaseChipData[]; // Scoped enrichment phase chips
    hookFirings?: HookFiring[]; // Scoped before/after hook firings
    /**
     * Map of all scope hook firings keyed by ``"{type}:{id_or_name}"``. Kept
     * here as an out-of-band prop so a swarm card can resolve hook firings
     * for each of its nested agent cards too (the top level is handled by
     * ``ExchangeScopeGroupList``).
     */
    scopeHookFirings?: Map<string, HookFiring[]>;
    latestStatusMessage?: string | null;
    showArgs?: boolean;
    expandAllCards?: boolean;
    richResultDisplay?: boolean;
    isLive?: boolean;
    compact?: boolean;
    depth?: number;
  }

  let {
    scopeType,
    scopeName,
    scopeId = undefined,
    tools,
    nestedAgents = [],
    phaseChips = [],
    hookFirings = [],
    scopeHookFirings,
    latestStatusMessage = null,
    showArgs = true,
    expandAllCards = false,
    richResultDisplay = true,
    isLive = false,
    compact = false,
    depth = 0,
  }: Props = $props();
  const directPhaseChip = $derived(() =>
    resolveDirectPhaseChip(scopeType, scopeName, scopeId, phaseChips),
  );
  const nestedAgentPhaseChips = $derived(() =>
    buildNestedAgentPhaseChipsMap(scopeType, phaseChips),
  );

  function resolveNestedAgentChips(agent: NestedAgent): PhaseChipData[] {
    return resolveNestedAgentPhaseChips(nestedAgentPhaseChips(), agent);
  }

  let isExpanded = $state(true);

  // Auto-scroll agent response when still executing
  let agentResponseEl = $state<HTMLDivElement | undefined>();

  $effect(() => {
    const status = aggregateStatus();
    const response = agentResponse();
    if (status === "executing" && response && agentResponseEl) {
      requestAnimationFrame(() => {
        if (agentResponseEl) {
          agentResponseEl.scrollTop = agentResponseEl.scrollHeight;
        }
      });
    }
  });

  function toggleExpanded() {
    isExpanded = !isExpanded;
  }

  const displayTools = $derived(() => getDisplayTools(tools));

  const agentInvocation = $derived(() =>
    scopeType === "agent" ? (tools.find((t) => t.toolType === "agent") ?? null) : null,
  );
  const agentIsFinalOutput = $derived(() => isAgentFinalOutput(agentInvocation()));
  const agentResponse = $derived(() => getAgentResponse(agentInvocation()));

  const shouldShowAgentResponse = $derived(() => {
    if (scopeType !== "agent") return false;
    if (!agentResponse()) return false;
    const hasToolCalls = displayTools().length > 0;
    const isNested = depth > 0;
    return isNested || hasToolCalls;
  });

  const statusTools = $derived(() => getStatusTools(scopeType, tools, nestedAgents));
  const aggregateStatus = $derived(() => getAggregateStatus(scopeType, tools, nestedAgents));
  const displayPhaseMessage = $derived(() =>
    getDisplayPhaseMessage(directPhaseChip(), aggregateStatus(), scopeType, latestStatusMessage),
  );

  const currentStatus = $derived(getScopeGroupCurrentStatus(scopeType, aggregateStatus()));
  const counts = $derived(() => getScopeGroupCounts(statusTools()));
  const completedCount = $derived(counts().completedCount);
  const failedCount = $derived(counts().failedCount);
  const executingCount = $derived(counts().executingCount);
  const totalCount = $derived(counts().totalCount);
  const progress = $derived(counts().progress);

  const activeAgentCount = $derived(() => getActiveAgentCount(scopeType, nestedAgents));

  const iconSize = $derived(getScopeGroupIconSize(compact, scopeType));
  const innerIconSizePx = $derived(getScopeGroupInnerIconSizePx(compact, scopeType));
  const expandIconSizePx = $derived(getScopeGroupExpandIconSizePx(compact, scopeType));
</script>

<div
  class="scope-group overflow-hidden animate-in rounded-xl"
  class:compact
  class:executing={aggregateStatus() === "executing"}
  class:is-swarm={scopeType === "swarm"}
  class:nested={depth > 0}
  style="--status-color: {currentStatus.color}; --status-bg: {currentStatus.bg}"
>
  {#if hookFirings.length > 0}
    <HookFiringMarker firings={hookFirings} stage="before" />
  {/if}

  <ScopeGroupHeader
    {scopeType}
    {scopeName}
    {compact}
    nestedAgentsCount={nestedAgents.length}
    {executingCount}
    activeAgentCount={activeAgentCount()}
    displayPhaseMessage={displayPhaseMessage()}
    {failedCount}
    {completedCount}
    {totalCount}
    {progress}
    {currentStatus}
    aggregateStatus={aggregateStatus()}
    {innerIconSizePx}
    {expandIconSizePx}
    {iconSize}
    {isExpanded}
    onToggleExpanded={toggleExpanded}
  />

  <!-- Nested Content -->
  {#if isExpanded}
    <ScopeGroupNestedContent
      {scopeType}
      {nestedAgents}
      {resolveNestedAgentChips}
      {scopeHookFirings}
      {isLive}
      {showArgs}
      {expandAllCards}
      {richResultDisplay}
      {compact}
      {depth}
      shouldShowAgentResponse={shouldShowAgentResponse()}
      agentResponse={agentResponse()}
      agentIsFinalOutput={agentIsFinalOutput()}
      bind:bindAgentResponseEl={agentResponseEl}
      displayTools={displayTools()}
    />
  {/if}

  {#if hookFirings.length > 0}
    <HookFiringMarker firings={hookFirings} stage="after" />
  {/if}
</div>

<style>
  .scope-group {
    background-color: var(--color-bg-secondary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    transition: box-shadow 0.2s ease;
  }

  .scope-group:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  }

  .scope-group.is-swarm {
    border: 2px solid var(--status-color);
    border-color: color-mix(in srgb, var(--status-color) 20%, transparent);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .scope-group.is-swarm:hover {
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  }

  .scope-group.is-swarm.executing {
    animation: pulse-border 2s ease-in-out infinite;
  }

  @keyframes pulse-border {
    0%,
    100% {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    50% {
      box-shadow:
        0 2px 8px rgba(0, 0, 0, 0.1),
        0 0 0 3px var(--status-bg);
    }
  }

  .scope-group.nested {
    box-shadow: none;
    border: 1px solid var(--color-outline-variant);
  }

  .scope-group.nested:hover {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  }
</style>
