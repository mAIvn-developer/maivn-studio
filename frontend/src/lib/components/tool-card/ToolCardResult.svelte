<script lang="ts">
  import KeyValueDisplay from "../KeyValueDisplay.svelte";
  import {
    highlightPrivateData,
    containsPrivateDataPlaceholders,
  } from "../markdown/markdown-parser";
  import MarkdownContent from "../markdown/MarkdownContent.svelte";
  import type { ToolStatusDisplayConfig } from "./tool-card-display";
  import { formatToolValue } from "./tool-card-display";

  interface Props {
    result: unknown;
    richResultDisplay?: boolean;
    status: ToolStatusDisplayConfig;
  }

  let { result, richResultDisplay = true, status }: Props = $props();
</script>

<div class="px-3 py-2.5" style="background: {status.bg}">
  <div
    class="text-[10px] uppercase tracking-wider mb-1.5 font-medium"
    style="color: {status.color}"
  >
    Result
  </div>
  {#if richResultDisplay && typeof result === "object" && result !== null}
    <div class="max-h-48 overflow-y-auto">
      <KeyValueDisplay data={result} initialExpanded={true} maxDepth={3} />
    </div>
  {:else if richResultDisplay && typeof result === "string"}
    <div class="max-h-80 overflow-y-auto text-[var(--color-text-secondary)]">
      <MarkdownContent content={result} />
    </div>
  {:else}
    {@const formatted = formatToolValue(result, false)}
    {#if containsPrivateDataPlaceholders(formatted)}
      <!-- eslint-disable svelte/no-at-html-tags -->
      <pre
        class="text-xs font-mono text-[var(--color-text-secondary)] whitespace-pre-wrap break-all max-h-60 overflow-y-auto">{@html highlightPrivateData(
          formatted,
        )}</pre>
      <!-- eslint-enable svelte/no-at-html-tags -->
    {:else}
      <pre
        class="text-xs font-mono text-[var(--color-text-secondary)] whitespace-pre-wrap break-all max-h-60 overflow-y-auto">{formatted}</pre>
    {/if}
  {/if}
</div>
