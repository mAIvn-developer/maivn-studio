<script lang="ts">
  import MarkdownContent from "../markdown/MarkdownContent.svelte";
  import { formatToolValue, isToolValueTruncated } from "./tool-card-display";

  interface Props {
    args: Record<string, unknown>;
    expandedArgs: Set<string>;
    richResultDisplay?: boolean;
    onToggleArgExpanded: (key: string) => void;
  }

  let { args, expandedArgs, richResultDisplay = true, onToggleArgExpanded }: Props = $props();
</script>

<div class="px-3 py-2.5 border-b border-[var(--color-outline-variant)]">
  <div
    class="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] mb-1.5 font-medium"
  >
    Arguments
  </div>
  <div class="space-y-3">
    {#each Object.entries(args) as [key, value]}
      {@const isArgExpanded = expandedArgs.has(key)}
      {@const isTruncated = isToolValueTruncated(value)}
      {@const isStringValue = typeof value === "string"}
      <div class="text-xs">
        <div class="flex items-start gap-2">
          <span class="text-[var(--color-text-secondary)] font-mono shrink-0">{key}:</span>
          <div class="flex-1 min-w-0">
            {#if isStringValue && isArgExpanded && richResultDisplay}
              <div class="text-[var(--color-text)] max-h-96 overflow-y-auto">
                <MarkdownContent content={String(value)} />
              </div>
            {:else}
              <pre
                class="font-mono text-[var(--color-text)] whitespace-pre-wrap break-all"
                class:max-h-24={!isArgExpanded}
                class:overflow-hidden={!isArgExpanded}>{formatToolValue(
                  value,
                  !isArgExpanded,
                )}</pre>
            {/if}
            {#if isTruncated}
              <button
                type="button"
                class="text-[10px] text-[var(--color-primary)] hover:underline mt-1"
                onclick={() => onToggleArgExpanded(key)}
              >
                {isArgExpanded ? "Show less" : "Show full content"}
              </button>
            {/if}
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>
