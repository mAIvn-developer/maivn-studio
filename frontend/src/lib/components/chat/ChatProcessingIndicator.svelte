<script lang="ts">
  import { Monitor } from "lucide-svelte";

  interface Props {
    currentPhaseMessage?: string | null;
  }

  let { currentPhaseMessage = null }: Props = $props();
</script>

<div class="flex animate-in" role="status" aria-label="Processing">
  <div
    class="rounded-xl bg-[var(--color-bg-secondary)]
         px-4 py-3 border border-[var(--color-tertiary)]/20"
  >
    <div class="flex items-center gap-3">
      <div
        class="w-7 h-7 rounded-lg bg-[var(--color-tertiary)]/15
             flex items-center justify-center"
      >
        <Monitor size={16} class="text-[var(--color-tertiary)] animate-pulse" />
      </div>
      <span class="text-sm text-[var(--color-text-secondary)]"
        >{currentPhaseMessage ?? "Processing"}</span
      >
      <div class="flex gap-0.5">
        {#each [0, 1, 2] as i}
          <div
            class="h-1 w-1 rounded-full bg-[var(--color-tertiary)]"
            style="animation: bounce 1.4s infinite ease-in-out; animation-delay: {i * 0.2}s"
          ></div>
        {/each}
      </div>
    </div>
  </div>
</div>
