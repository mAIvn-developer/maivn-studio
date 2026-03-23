<script lang="ts">
  import type { ToolCard } from "$lib/types";
  import { Check, ChevronDown, Clock, LoaderCircle, User, X } from "lucide-svelte";
  import type { ToolStatusDisplayConfig, ToolTypeDisplayConfig } from "./tool-card-display";

  interface Props {
    card: ToolCard;
    isExpanded: boolean;
    compact?: boolean;
    showArgs?: boolean;
    compactArgsPreview?: string | null;
    duration?: string | null;
    typeConfig: ToolTypeDisplayConfig;
    status: ToolStatusDisplayConfig;
    onToggleExpanded: () => void;
  }

  let {
    card,
    isExpanded,
    compact = false,
    showArgs = true,
    compactArgsPreview = null,
    duration = null,
    typeConfig,
    status,
    onToggleExpanded,
  }: Props = $props();
</script>

<button
  class="tool-header flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors"
  class:compact
  onclick={onToggleExpanded}
>
  <div
    class="flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center"
    style="background: {status.bg}"
  >
    {#if card.status === "executing"}
      <LoaderCircle size={14} class="animate-spin" style="color: {status.color}" strokeWidth={2} />
    {:else if card.status === "pending"}
      <Clock size={14} style="color: {status.color}" strokeWidth={2} />
    {:else if card.status === "completed"}
      <Check size={14} style="color: {status.color}" strokeWidth={2} />
    {:else if card.status === "failed"}
      <X size={14} style="color: {status.color}" strokeWidth={2} />
    {/if}
  </div>

  <div class="flex-1 min-w-0">
    <div class="flex items-center gap-2 flex-wrap">
      <span class="font-medium text-sm truncate text-[var(--color-text)]">{card.toolName}</span>

      <span
        class="text-[10px] font-semibold px-1.5 py-0.5 rounded"
        style="background: {typeConfig.bg}; color: {typeConfig.color}"
      >
        {typeConfig.label}
      </span>

      {#if card.agentName}
        <span
          class="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]"
        >
          <User size={10} strokeWidth={2} />
          {card.agentName}
        </span>
      {/if}
    </div>

    {#if !isExpanded && showArgs && compactArgsPreview}
      <div class="text-[11px] text-[var(--color-text-tertiary)] mt-0.5 truncate font-mono">
        {compactArgsPreview}
      </div>
    {/if}
  </div>

  <div class="flex items-center gap-2 flex-shrink-0">
    {#if duration}
      <span class="text-[11px] text-[var(--color-text-tertiary)] tabular-nums font-mono">
        {duration}
      </span>
    {/if}

    {#if card.status === "executing"}
      <div class="w-12 h-1 rounded-full bg-[var(--color-bg-tertiary)] overflow-hidden">
        <div class="h-full rounded-full animate-progress" style="background: {status.color}"></div>
      </div>
    {/if}

    <ChevronDown
      size={14}
      class="text-[var(--color-text-tertiary)] transition-transform duration-200 {isExpanded
        ? 'rotate-180'
        : ''}"
      strokeWidth={2}
    />
  </div>
</button>

<style>
  .tool-header:hover {
    background-color: var(--color-bg-tertiary);
  }

  .tool-header.compact {
    padding: 0.375rem 0.625rem;
  }

  :global(.animate-spin) {
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes progress {
    0% {
      width: 0%;
      margin-left: 0;
    }
    50% {
      width: 60%;
      margin-left: 20%;
    }
    100% {
      width: 0%;
      margin-left: 100%;
    }
  }

  .animate-progress {
    animation: progress 2s ease-in-out infinite;
  }
</style>
