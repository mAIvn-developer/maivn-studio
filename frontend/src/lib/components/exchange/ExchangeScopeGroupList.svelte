<script lang="ts">
  import type { PhaseChipData } from "$lib/types";
  import ScopeGroupCard from "../scope-group/ScopeGroupCard.svelte";
  import type { ScopeGroup } from "./exchange-scope-groups";

  interface Props {
    scopeGroups: ScopeGroup[];
    phaseChips: PhaseChipData[];
    latestStatusMessage?: string | null;
    isLive?: boolean;
    showToolArgs?: boolean;
    expandAllCards?: boolean;
    richResultDisplay?: boolean;
    resolveScopePhaseChips: (group: ScopeGroup, phaseChips: PhaseChipData[]) => PhaseChipData[];
  }

  let {
    scopeGroups,
    phaseChips,
    latestStatusMessage = null,
    isLive = false,
    showToolArgs = true,
    expandAllCards = false,
    richResultDisplay = true,
    resolveScopePhaseChips,
  }: Props = $props();
</script>

{#if scopeGroups.length > 0}
  <div class="events-group space-y-2">
    {#each scopeGroups as group (group.invocationId ?? `${group.type}:${group.id ?? group.name}`)}
      <ScopeGroupCard
        scopeType={group.type}
        scopeName={group.name}
        scopeId={group.id}
        tools={group.tools}
        nestedAgents={group.nestedAgents}
        phaseChips={resolveScopePhaseChips(group, phaseChips)}
        {latestStatusMessage}
        {isLive}
        showArgs={showToolArgs}
        {expandAllCards}
        {richResultDisplay}
      />
    {/each}
  </div>
{/if}

<style>
  .events-group {
    position: relative;
  }
</style>
