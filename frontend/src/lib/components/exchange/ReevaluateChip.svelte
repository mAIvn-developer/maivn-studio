<script lang="ts">
  import type { PhaseChipData } from "$lib/types";
  import { RefreshCw } from "lucide-svelte";

  interface Props {
    phaseChip: PhaseChipData;
  }

  let { phaseChip }: Props = $props();

  const reevaluate = $derived(phaseChip.reevaluate);
  const isDependency = $derived(reevaluate?.source === "dependency");
  const trigger = $derived(reevaluate?.triggerTool ?? "");
  const target = $derived(reevaluate?.targetTool ?? "");
  const cycle = $derived(reevaluate?.cycle);

  const tooltip = $derived.by(() => {
    const parts: string[] = [];
    if (typeof cycle === "number") parts.push(`cycle ${cycle}`);
    if (isDependency && trigger && target) {
      parts.push(`@depends_on_reevaluate: ${trigger} -> ${target}`);
    } else if (isDependency && trigger) {
      parts.push(`triggered by ${trigger}`);
    } else {
      parts.push("LLM-planned");
    }
    return parts.join(" - ");
  });
</script>

<div class="reeval-row" title={tooltip}>
  <RefreshCw size={11} class="reeval-icon" />
  <span>Reevaluate</span>
</div>

<style>
  .reeval-row {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.125rem 0.25rem;
    font-size: 0.7rem;
    color: var(--color-secondary);
    line-height: 1;
  }
  :global(.reeval-icon) {
    flex-shrink: 0;
    opacity: 0.85;
  }
</style>
