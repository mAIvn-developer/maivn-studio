<script lang="ts">
  import type { PhaseChipData } from "$lib/types";
  import MemoryActivityPanel from "./MemoryActivityPanel.svelte";

  interface Props {
    latestRootPhaseChip: PhaseChipData | null;
    memoryPhaseChips: PhaseChipData[];
    isLive?: boolean;
  }

  let { latestRootPhaseChip, memoryPhaseChips, isLive = false }: Props = $props();
</script>

{#if latestRootPhaseChip && !isLive}
  <div
    class="mb-2 inline-flex items-center gap-1.5 rounded-md
              bg-[var(--color-secondary)]/10 px-2.5 py-1 text-xs
              text-[var(--color-secondary)]"
  >
    <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-secondary)]"></span>
    <span>{latestRootPhaseChip.message}</span>
  </div>
{/if}

{#each memoryPhaseChips as chip (chip.phase)}
  <div class="mb-2">
    <MemoryActivityPanel phaseChip={chip} {isLive} />
  </div>
{/each}
