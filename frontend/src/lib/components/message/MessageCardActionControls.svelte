<script lang="ts">
  import { ChartBar, Check, Copy, FileText } from "lucide-svelte";

  interface Props {
    copied: boolean;
    copiedStructured?: boolean;
    hasStructuredContent?: boolean;
    hasStructuredOutput?: boolean;
    hasSessionDetails?: boolean;
    isAssistant?: boolean;
    showRawContent?: boolean;
    showStructuredOutput?: boolean;
    showSessionDetails?: boolean;
    showCopyLabel?: boolean;
    onCopyContent: () => void | Promise<void>;
    onToggleRawContent: () => void;
    onToggleStructuredOutput: () => void;
    onToggleSessionDetails: () => void;
  }

  let {
    copied,
    copiedStructured = false,
    hasStructuredContent = false,
    hasStructuredOutput = false,
    hasSessionDetails = false,
    isAssistant = false,
    showRawContent = false,
    showStructuredOutput = false,
    showSessionDetails = false,
    showCopyLabel = false,
    onCopyContent,
    onToggleRawContent,
    onToggleStructuredOutput,
    onToggleSessionDetails,
  }: Props = $props();
</script>

<button
  type="button"
  onclick={onCopyContent}
  class="p-1.5 rounded-md hover:bg-white/10 transition-colors"
  title="Copy message"
>
  {#if copied}
    <Check size={16} class="text-[var(--color-success)]" strokeWidth={2} />
  {:else}
    <Copy size={16} class="text-[var(--color-text-secondary)]" strokeWidth={2} />
  {/if}
</button>

{#if showCopyLabel}
  <span class="sr-only">Copy message</span>
{/if}

{#if isAssistant && hasStructuredContent}
  <button
    type="button"
    onclick={onToggleRawContent}
    class="px-2 py-1 rounded-md hover:bg-white/10 transition-colors text-xs text-[var(--color-text-secondary)]"
  >
    {showRawContent ? "Rich" : "Raw"}
  </button>
{/if}

{#if isAssistant && hasStructuredOutput}
  <button
    type="button"
    onclick={onToggleStructuredOutput}
    class="p-1.5 rounded-md transition-colors
           {showStructuredOutput
      ? 'bg-[var(--color-tertiary)]/20 text-[var(--color-tertiary)]'
      : 'hover:bg-white/10 text-[var(--color-text-secondary)]'}"
    title="Toggle structured output"
  >
    {#if copiedStructured}
      <Check size={16} class="text-[var(--color-success)]" strokeWidth={2} />
    {:else}
      <FileText size={16} strokeWidth={1.5} />
    {/if}
  </button>
{/if}

{#if isAssistant && hasSessionDetails}
  <button
    type="button"
    onclick={onToggleSessionDetails}
    class="p-1.5 rounded-md transition-colors
           {showSessionDetails
      ? 'bg-[var(--color-primary)]/20 text-[var(--color-primary)]'
      : 'hover:bg-white/10 text-[var(--color-text-secondary)]'}"
    title="Toggle session details"
  >
    <ChartBar size={16} strokeWidth={1.5} />
  </button>
{/if}
