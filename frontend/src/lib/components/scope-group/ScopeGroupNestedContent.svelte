<script lang="ts">
  import type { HookFiring, PhaseChipData, ToolCard as ToolCardType } from "$lib/types";
  import MarkdownContent from "../markdown/MarkdownContent.svelte";
  import ToolCard from "../tool-card/ToolCard.svelte";
  import type { NestedAgent, ScopeType } from "./scope-group-helpers";
  import Self from "./ScopeGroupCard.svelte";

  interface Props {
    scopeType: ScopeType;
    nestedAgents: NestedAgent[];
    resolveNestedAgentChips: (agent: NestedAgent) => PhaseChipData[];
    /**
     * Map of all scope hook firings. Used to resolve nested agent cards'
     * own firings (the SDK emits them with target_type="agent" / target_id
     * = agent.id; the frontend stores under both ``agent:<id>`` and
     * ``agent:<name>`` for fallback). Passed through unchanged so deeper
     * nested ScopeGroupCards can recurse if needed.
     */
    scopeHookFirings?: Map<string, HookFiring[]>;
    isLive?: boolean;
    showArgs?: boolean;
    expandAllCards?: boolean;
    richResultDisplay?: boolean;
    compact?: boolean;
    depth?: number;
    shouldShowAgentResponse: boolean;
    agentResponse: string | null;
    agentIsFinalOutput: boolean;
    bindAgentResponseEl?: HTMLDivElement | undefined;
    displayTools: ToolCardType[];
  }

  let {
    scopeType,
    nestedAgents,
    resolveNestedAgentChips,
    scopeHookFirings,
    isLive = false,
    showArgs = true,
    expandAllCards = false,
    richResultDisplay = true,
    compact = false,
    depth = 0,
    shouldShowAgentResponse,
    agentResponse,
    agentIsFinalOutput,
    bindAgentResponseEl = $bindable(undefined),
    displayTools,
  }: Props = $props();

  function resolveNestedAgentFirings(agent: NestedAgent): HookFiring[] {
    if (!scopeHookFirings) return [];
    const byId = agent.agentId ? scopeHookFirings.get(`agent:${agent.agentId}`) : undefined;
    const byName = scopeHookFirings.get(`agent:${agent.agentName}`);
    // ``hook-events.ts`` stores the same firing object under both ``agent:<id>``
    // and ``agent:<name>``, so ``byId`` and ``byName`` are either the same
    // array or one is undefined — no merge / dedup needed here.
    return byId ?? byName ?? [];
  }
</script>

<div
  class="nested-content space-y-1.5"
  class:p-3={scopeType === "swarm"}
  class:p-2={scopeType === "agent"}
  style="background: {scopeType === 'swarm'
    ? 'color-mix(in srgb, var(--color-bg) 50%, transparent)'
    : 'rgba(0, 0, 0, 0.05)'}"
>
  {#if scopeType === "swarm" && nestedAgents.length > 0}
    {#each nestedAgents as agent (agent.invocationId)}
      <Self
        scopeType="agent"
        scopeName={agent.agentName}
        scopeId={agent.agentId}
        tools={agent.tools}
        phaseChips={resolveNestedAgentChips(agent)}
        hookFirings={resolveNestedAgentFirings(agent)}
        {scopeHookFirings}
        {isLive}
        {showArgs}
        {expandAllCards}
        {richResultDisplay}
        compact
        depth={depth + 1}
      />
    {/each}
  {/if}

  {#if shouldShowAgentResponse}
    <div
      class="rounded-lg border border-[var(--color-outline-variant)]/60 bg-[var(--color-bg-secondary)]/60"
      class:p-2={compact}
      class:p-3={!compact}
    >
      <div
        class="flex items-center justify-between text-[10px] uppercase tracking-wide text-[var(--color-text-tertiary)]"
      >
        <span>Agent Response</span>
        {#if agentIsFinalOutput}
          <span class="text-[10px] text-[var(--color-secondary)]">Final Output</span>
        {/if}
      </div>
      <div
        bind:this={bindAgentResponseEl}
        class="mt-2 text-[var(--color-text)] leading-relaxed max-h-96 overflow-y-auto"
        class:text-xs={compact}
        class:text-sm={!compact}
      >
        <MarkdownContent content={agentResponse ?? ""} />
      </div>
    </div>
  {/if}

  {#each displayTools as tool (tool.toolId)}
    <ToolCard
      card={tool}
      {showArgs}
      expanded={expandAllCards}
      {richResultDisplay}
      nested
      depth={depth + 1}
    />
  {/each}
</div>

<style>
  .nested-content {
    animation: expandIn 0.2s ease-out;
  }

  @keyframes expandIn {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
