<script lang="ts">
  import type { InterruptCardStatus, InterruptData } from "$lib/types";
  import { Loader2, CircleHelp, RefreshCw, Check, X, ChevronDown } from "lucide-svelte";
  import InterruptInput from "./InterruptInput.svelte";

  interface Props {
    interrupt: InterruptData;
    onSubmit: (interruptId: string, value: string) => void;
    onCancel: (interruptId: string) => void;
  }

  let { interrupt, onSubmit, onCancel }: Props = $props();

  // Track expanded state - auto-collapse when completed/cancelled
  let isExpanded = $state(true);

  // Frozen submitted value - captured when status becomes completed
  // This prevents the displayed value from changing if the interrupt is reused
  let frozenSubmittedValue = $state<string | undefined>(undefined);

  // Auto-collapse when status changes to completed or cancelled
  // Also freeze the submitted value at completion time
  $effect(() => {
    if (interrupt.status === "completed" || interrupt.status === "cancelled") {
      isExpanded = false;
      // Freeze the value only once (when first completed)
      if (frozenSubmittedValue === undefined && interrupt.submittedValue) {
        frozenSubmittedValue = interrupt.submittedValue;
      }
    }
  });

  // Whether the card is collapsible (only completed/cancelled can collapse)
  const isCollapsible = $derived(
    interrupt.status === "completed" || interrupt.status === "cancelled",
  );

  // Status configuration
  const statusConfig: Record<
    InterruptCardStatus,
    { color: string; bg: string; borderColor: string; icon: typeof CircleHelp; label: string }
  > = {
    waiting: {
      color: "var(--color-warning)",
      bg: "rgba(245, 158, 11, 0.1)",
      borderColor: "rgb(245, 158, 11)",
      icon: CircleHelp,
      label: "INPUT REQUIRED",
    },
    submitting: {
      color: "var(--color-secondary)",
      bg: "rgba(137, 208, 237, 0.1)",
      borderColor: "rgb(96, 165, 250)",
      icon: RefreshCw,
      label: "SUBMITTING",
    },
    completed: {
      color: "var(--color-success)",
      bg: "rgba(52, 211, 153, 0.1)",
      borderColor: "rgb(52, 211, 153)",
      icon: Check,
      label: "COMPLETED",
    },
    cancelled: {
      color: "var(--color-text-tertiary)",
      bg: "rgba(156, 163, 175, 0.1)",
      borderColor: "rgb(156, 163, 175)",
      icon: X,
      label: "CANCELLED",
    },
  };

  const status = $derived(statusConfig[interrupt.status]);

  // Get truncated display value for collapsed view
  // Uses frozen value if available (preserves historical input)
  const displayValue = $derived(() => {
    if (interrupt.status === "cancelled") return "Cancelled";
    // Use frozen value if available, otherwise fall back to current
    const val = frozenSubmittedValue ?? interrupt.submittedValue;
    if (!val) return "";
    // Mask password values
    if (interrupt.inputType === "password") return "********";
    // Truncate long values
    return val.length > 40 ? val.slice(0, 40) + "..." : val;
  });

  function handleSubmit(value: string) {
    onSubmit(interrupt.interruptId, value);
  }

  function handleCancel() {
    onCancel(interrupt.interruptId);
  }

  function toggleExpanded() {
    if (isCollapsible) {
      isExpanded = !isExpanded;
    }
  }
</script>

<!-- Snippet for shared header content -->
{#snippet headerContent()}
  <!-- Status indicator -->
  <div
    class="flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center"
    style="background: rgba(0,0,0,0.1)"
  >
    {#if interrupt.status === "submitting"}
      <Loader2 size={14} class="animate-spin" style="color: {status.color}" />
    {:else}
      {@const Icon = status.icon}
      <Icon size={14} style="color: {status.color}" />
    {/if}
  </div>

  <!-- Title / Collapsed info -->
  <div class="flex-1 min-w-0">
    {#if isCollapsible && !isExpanded}
      <!-- Collapsed view: show status, tool name, and submitted value inline -->
      <div class="flex items-center gap-2 flex-wrap">
        <span class="font-medium text-xs" style="color: {status.color}">{status.label}</span>
        <span
          class="text-[10px] font-semibold px-1.5 py-0.5 rounded"
          style="background: rgba(167, 139, 250, 0.15); color: #A78BFA"
        >
          {interrupt.toolName}
        </span>
        {#if displayValue()}
          <span class="text-xs text-[var(--color-text-secondary)] font-mono truncate max-w-[200px]">
            {displayValue()}
          </span>
        {/if}
      </div>
    {:else}
      <!-- Expanded view: standard header -->
      <div class="flex items-center gap-2 flex-wrap">
        <span class="font-medium text-sm text-[var(--color-text)]">{status.label}</span>
        <span
          class="text-[10px] font-semibold px-1.5 py-0.5 rounded"
          style="background: rgba(167, 139, 250, 0.15); color: #A78BFA"
        >
          {interrupt.toolName}
        </span>
      </div>
    {/if}
  </div>

  <!-- Expand/collapse chevron or timestamp -->
  {#if isCollapsible}
    <div class="flex items-center gap-2">
      <div class="text-[11px] text-[var(--color-text-tertiary)] tabular-nums font-mono">
        {new Date(interrupt.timestamp).toLocaleTimeString()}
      </div>
      <ChevronDown
        size={16}
        class="text-[var(--color-text-tertiary)] transition-transform duration-200 {isExpanded
          ? 'rotate-180'
          : ''}"
      />
    </div>
  {:else}
    <div class="text-[11px] text-[var(--color-text-tertiary)] tabular-nums font-mono">
      {new Date(interrupt.timestamp).toLocaleTimeString()}
    </div>
  {/if}
{/snippet}

<div
  class="interrupt-inline-card overflow-hidden transition-all duration-200 animate-in rounded-lg"
  class:collapsed={isCollapsible && !isExpanded}
  style="border-left: 3px solid {status.borderColor}"
>
  <!-- Header (button when collapsible, div otherwise) -->
  {#if isCollapsible}
    <button
      type="button"
      class="interrupt-header w-full flex items-center gap-3 px-3 py-2.5 text-left cursor-pointer hover:brightness-95 border-0"
      style="background: {status.bg}"
      onclick={toggleExpanded}
      aria-expanded={isExpanded}
    >
      {@render headerContent()}
    </button>
  {:else}
    <div
      class="interrupt-header flex items-center gap-3 px-3 py-2.5"
      style="background: {status.bg}"
    >
      {@render headerContent()}
    </div>
  {/if}

  <!-- Content (only visible when expanded or when waiting/submitting) -->
  {#if !isCollapsible || isExpanded}
    <div class="interrupt-content px-4 py-3 bg-[var(--color-bg-secondary)]">
      <InterruptInput {interrupt} onSubmit={handleSubmit} onCancel={handleCancel} />
    </div>
  {/if}
</div>

<style>
  .interrupt-inline-card {
    background-color: var(--color-bg-secondary);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    transition:
      box-shadow 0.2s ease,
      transform 0.2s ease;
  }

  .interrupt-inline-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .interrupt-inline-card.collapsed {
    box-shadow: none;
  }

  .interrupt-inline-card.collapsed:hover {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  }

  .interrupt-header {
    transition: background-color 0.15s ease;
  }

  .interrupt-content {
    animation: slideDown 0.2s ease-out;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  :global(.animate-spin) {
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
