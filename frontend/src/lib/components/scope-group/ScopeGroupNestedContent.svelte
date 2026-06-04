<script lang="ts">
  import type { HookFiring, PhaseChipData, ToolCard as ToolCardType } from "$lib/types";
  import MarkdownContent from "../markdown/MarkdownContent.svelte";
  import ToolCard from "../tool-card/ToolCard.svelte";
  import ReevaluateChip from "../exchange/ReevaluateChip.svelte";
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
    /**
     * Reevaluate enrichment chips for this scope. The component interleaves
     * them with ``displayTools`` based on timestamp so each chip renders at
     * the position where the reevaluate cycle actually fired (i.e. between
     * the tools that completed before and after it).
     */
    reevaluatePhaseChips?: PhaseChipData[];
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
    reevaluatePhaseChips = [],
  }: Props = $props();

  type ToolItem = { kind: "tool"; tool: ToolCardType; key: string };
  type ChipItem = { kind: "chip"; chip: PhaseChipData; key: string };
  type TimelineItem = ToolItem | ChipItem;

  /**
   * Build the displayed timeline by anchoring reevaluate chips to the tool
   * they semantically follow:
   *
   * - Dependency-attributed chips (``source="dependency"``) gate a downstream
   *   tool; they're placed AFTER the chip's ``target_tool`` (the tool the
   *   dependent was waiting on), so the chip sits between target and
   *   dependent. If the target isn't present, fall back to the LLM-planned
   *   rule.
   * - LLM-planned chips (``source="llm"``) don't have a target; we place
   *   them after the Nth tool, where N is the chip's ``collected_count``
   *   capped to the number of tools available. This puts cycle 1 after the
   *   first batch, cycle 2 after the next batch, etc.
   * - Chips with no positioning hint at all fall through to the end.
   *
   * The chip-by-timestamp ordering used to land both chips at the end of
   * the list because every chip event flows through the SDK pipeline after
   * the tool-complete events — anchoring by name/count puts them where the
   * boundary actually sits in execution.
   */
  /**
   * Collapse chips that would land in the same gap to a single marker so the
   * UI doesn't render two stacked Reevaluate lines for the same conceptual
   * boundary. When both an LLM-planned and a dependency-attributed chip
   * target the same gap, prefer the dependency variant (it carries
   * attribution).
   */
  function pickCanonicalChipPerGap(
    chips: PhaseChipData[],
    indexByName: (name: string | undefined) => number,
    toolCount: number,
  ): { chip: PhaseChipData; insertAfter: number }[] {
    const byGap = new Map<number, { chip: PhaseChipData; insertAfter: number }>();
    chips.forEach((chip, idx) => {
      let insertAfter = -1;
      const targetTool = chip.reevaluate?.targetTool;
      if (chip.reevaluate?.source === "dependency" && targetTool) {
        insertAfter = indexByName(targetTool);
      }
      if (insertAfter === -1) {
        const cycle = chip.reevaluate?.cycle;
        if (typeof cycle === "number" && cycle > 0) {
          insertAfter = Math.min(cycle, toolCount) - 1;
        }
      }
      if (insertAfter === -1) {
        insertAfter = toolCount + idx;
      }
      const existing = byGap.get(insertAfter);
      if (
        !existing ||
        (existing.chip.reevaluate?.source !== "dependency" &&
          chip.reevaluate?.source === "dependency")
      ) {
        byGap.set(insertAfter, { chip, insertAfter });
      }
    });
    return Array.from(byGap.values()).sort((a, b) => a.insertAfter - b.insertAfter);
  }

  const timeline = $derived.by<TimelineItem[]>(() => {
    const items: TimelineItem[] = displayTools.map((tool) => ({
      kind: "tool",
      tool,
      key: `tool:${tool.toolId}`,
    }));

    function indexOfToolByName(name: string | undefined): number {
      if (!name) return -1;
      return items.findIndex((item) => item.kind === "tool" && item.tool.toolName === name);
    }

    const toolCount = items.length;
    const canonicalChips = pickCanonicalChipPerGap(
      reevaluatePhaseChips,
      indexOfToolByName,
      toolCount,
    );

    // Walk in reverse so each splice doesn't shift the indices of pending
    // chips still to be inserted at earlier positions.
    for (let i = canonicalChips.length - 1; i >= 0; i--) {
      const { chip, insertAfter } = canonicalChips[i];
      const chipItem: ChipItem = {
        kind: "chip",
        chip,
        key: `reeval:${chip.reevaluate?.cycle ?? insertAfter}:${chip.timestamp}`,
      };
      if (insertAfter >= toolCount) {
        items.push(chipItem);
      } else {
        items.splice(insertAfter + 1, 0, chipItem);
      }
    }

    return items;
  });

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

  {#each timeline as item (item.key)}
    {#if item.kind === "tool"}
      <ToolCard
        card={item.tool}
        {showArgs}
        expanded={expandAllCards}
        {richResultDisplay}
        nested
        depth={depth + 1}
      />
    {:else}
      <ReevaluateChip phaseChip={item.chip} />
    {/if}
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
