<script lang="ts">
  import type { ToolCard } from "$lib/types";
  import {
    getCompactArgsPreview,
    getToolDuration,
    getToolStatusDisplayConfig,
    getToolTypeDisplayConfig,
  } from "./tool-card-display";
  import HookFiringMarker from "../ui/HookFiringMarker.svelte";
  import ToolCardArguments from "./ToolCardArguments.svelte";
  import ToolCardError from "./ToolCardError.svelte";
  import ToolCardHeader from "./ToolCardHeader.svelte";
  import ToolCardResult from "./ToolCardResult.svelte";
  import ToolCardStreamingContent from "./ToolCardStreamingContent.svelte";
  import ToolCardTimingFooter from "./ToolCardTimingFooter.svelte";

  interface Props {
    card: ToolCard;
    expanded?: boolean;
    showArgs?: boolean;
    nested?: boolean;
    depth?: number;
    compact?: boolean;
    richResultDisplay?: boolean;
  }

  let {
    card,
    expanded = false,
    showArgs = true,
    nested = false,
    depth = 0,
    compact = false,
    richResultDisplay = true,
  }: Props = $props();

  // Auto-scroll streaming content
  let streamContentEl = $state<HTMLDivElement | undefined>();

  $effect(() => {
    if (card.isStreaming && card.streamContent && streamContentEl) {
      requestAnimationFrame(() => {
        if (streamContentEl) {
          streamContentEl.scrollTop = streamContentEl.scrollHeight;
        }
      });
    }
  });

  // Local expanded state
  let localExpanded = $state(false);
  let userToggled = $state(false);
  const isExpanded = $derived(userToggled ? localExpanded : expanded);

  // Track which argument values are expanded to show full content
  let expandedArgs = $state<Set<string>>(new Set());

  function toggleExpanded() {
    userToggled = true;
    localExpanded = !localExpanded;
  }

  function toggleArgExpanded(key: string) {
    if (expandedArgs.has(key)) {
      expandedArgs = new Set([...expandedArgs].filter((k) => k !== key));
    } else {
      expandedArgs = new Set([...expandedArgs, key]);
    }
  }

  // For system tools like 'think', use streamContent as result when result is null/undefined
  const effectiveResult = $derived(() => {
    if (card.result !== null && card.result !== undefined) {
      return card.result;
    }
    // For system tools, fall back to streamContent
    if (card.isSystemTool && card.streamContent) {
      return card.streamContent;
    }
    return null;
  });

  const typeConfig = $derived(getToolTypeDisplayConfig(card.toolType));
  const status = $derived(getToolStatusDisplayConfig(card.status));
  const compactArgsPreview = $derived(
    showArgs && Object.keys(card.args).length > 0 ? getCompactArgsPreview(card.args) : null,
  );
  const duration = $derived(getToolDuration(card));
</script>

<div
  class="tool-card overflow-hidden transition-all duration-200 animate-in rounded-lg"
  class:nested
  class:compact
  style="--type-color: {typeConfig.color}; --status-color: {status.color}; margin-left: {depth *
    12}px"
>
  {#if card.hookFirings && card.hookFirings.length > 0}
    <HookFiringMarker firings={card.hookFirings} stage="before" />
  {/if}

  <ToolCardHeader
    {card}
    {isExpanded}
    {compact}
    {showArgs}
    {typeConfig}
    {status}
    {compactArgsPreview}
    {duration}
    onToggleExpanded={toggleExpanded}
  />

  {#if card.isStreaming && card.streamContent}
    <ToolCardStreamingContent bind:streamContentEl streamContent={card.streamContent} />
  {/if}

  <!-- Expanded Content -->
  {#if isExpanded}
    <div class="expanded-content border-t border-[var(--color-outline-variant)]">
      {#if showArgs && Object.keys(card.args).length > 0}
        <ToolCardArguments
          args={card.args}
          {expandedArgs}
          {richResultDisplay}
          onToggleArgExpanded={toggleArgExpanded}
        />
      {/if}

      <!-- Result -->
      {#if card.status === "completed" && effectiveResult() !== null}
        {@const result = effectiveResult()}
        <ToolCardResult {result} {richResultDisplay} {status} />
      {/if}

      <!-- Error -->
      {#if card.status === "failed" && card.error}
        <ToolCardError error={card.error} {status} />
      {/if}

      <ToolCardTimingFooter startedAt={card.startedAt} completedAt={card.completedAt} />
    </div>
  {/if}

  {#if card.hookFirings && card.hookFirings.length > 0}
    <HookFiringMarker firings={card.hookFirings} stage="after" />
  {/if}
</div>

<style>
  .tool-card {
    background-color: var(--color-bg-secondary);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    transition:
      box-shadow 0.2s ease,
      transform 0.2s ease;
  }

  .tool-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .tool-card.nested {
    background-color: var(--color-bg-tertiary);
    box-shadow: none;
  }

  .tool-card.nested:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }
</style>
