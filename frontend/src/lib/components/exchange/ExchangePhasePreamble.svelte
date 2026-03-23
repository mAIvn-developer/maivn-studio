<script lang="ts">
  import type { PhaseChipData } from "$lib/types";
  import MemoryActivityPanel from "./MemoryActivityPanel.svelte";

  interface Props {
    latestRootPhaseChip: PhaseChipData | null;
    latestMemoryPhaseChip: PhaseChipData | null;
    isLive?: boolean;
  }

  let { latestRootPhaseChip, latestMemoryPhaseChip, isLive = false }: Props = $props();
</script>

{#if latestRootPhaseChip && !isLive}
  <div
    class="mb-2 inline-flex items-center gap-1.5 rounded-md
              bg-[var(--color-tertiary)]/10 px-2.5 py-1 text-xs
              text-[var(--color-tertiary)]"
  >
    <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-tertiary)]"></span>
    <span>{latestRootPhaseChip.message}</span>
  </div>
{/if}

{#if latestMemoryPhaseChip}
  <div class="mb-2">
    <MemoryActivityPanel phaseChip={latestMemoryPhaseChip} {isLive} />
  </div>
{/if}
