<script lang="ts">
  import { Check, Copy, FileText } from "lucide-svelte";
  import KeyValueDisplay from "../KeyValueDisplay.svelte";

  interface Props {
    structuredOutput: unknown;
    copiedStructured: boolean;
    onCopyStructuredOutput: () => void | Promise<void>;
  }

  let { structuredOutput, copiedStructured, onCopyStructuredOutput }: Props = $props();
</script>

<div
  class="structured-output-section border-t border-[var(--color-outline-variant)]/50 bg-black/10"
>
  <div class="px-4 py-3">
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <FileText size={16} class="text-[var(--color-tertiary)]" strokeWidth={1.5} />
        <span class="text-xs font-medium text-[var(--color-tertiary)]">Structured Output</span>
      </div>

      <button
        type="button"
        onclick={onCopyStructuredOutput}
        class="p-1.5 rounded-md hover:bg-white/10 transition-colors"
        title="Copy structured output"
      >
        {#if copiedStructured}
          <Check size={16} class="text-[var(--color-success)]" strokeWidth={2} />
        {:else}
          <Copy size={16} class="text-[var(--color-text-secondary)]" strokeWidth={2} />
        {/if}
      </button>
    </div>
    <div class="bg-[var(--color-bg-tertiary)] rounded-lg p-3">
      <KeyValueDisplay data={structuredOutput} initialExpanded={true} />
    </div>
  </div>
</div>
