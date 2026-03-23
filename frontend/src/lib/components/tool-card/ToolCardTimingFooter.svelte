<script lang="ts">
  import { Check, Clock } from "lucide-svelte";

  interface Props {
    startedAt: string;
    completedAt?: string | null;
  }

  let { startedAt, completedAt = null }: Props = $props();
</script>

<div
  class="px-3 py-1.5 bg-black/5 flex gap-3 text-[10px] text-[var(--color-text-tertiary)] items-center"
>
  <span class="flex items-center gap-1">
    <Clock size={10} strokeWidth={2} />
    {new Date(startedAt).toLocaleTimeString()}
  </span>
  {#if completedAt}
    <span class="flex items-center gap-1">
      <Check size={10} strokeWidth={2} />
      {new Date(completedAt).toLocaleTimeString()}
    </span>
  {/if}
</div>
