<script lang="ts">
  import type { HookFiring, PhaseChipData } from "$lib/types";
  import ScopeGroupCard from "../scope-group/ScopeGroupCard.svelte";
  import type { ScopeGroup } from "./exchange-scope-groups";

  interface Props {
    scopeGroups: ScopeGroup[];
    phaseChips: PhaseChipData[];
    scopeHookFirings?: Map<string, HookFiring[]>;
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
    scopeHookFirings,
    latestStatusMessage = null,
    isLive = false,
    showToolArgs = true,
    expandAllCards = false,
    richResultDisplay = true,
    resolveScopePhaseChips,
  }: Props = $props();

  function resolveScopeHookFirings(group: ScopeGroup): HookFiring[] {
    if (!scopeHookFirings) return [];
    const byId = group.id ? scopeHookFirings.get(`${group.type}:${group.id}`) : undefined;
    const byName = scopeHookFirings.get(`${group.type}:${group.name}`);
    if (byId && byName) {
      const seen = new Set<HookFiring>();
      const merged: HookFiring[] = [];
      for (const f of [...byId, ...byName]) {
        if (!seen.has(f)) {
          seen.add(f);
          merged.push(f);
        }
      }
      return merged;
    }
    return byId ?? byName ?? [];
  }
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
        hookFirings={resolveScopeHookFirings(group)}
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
