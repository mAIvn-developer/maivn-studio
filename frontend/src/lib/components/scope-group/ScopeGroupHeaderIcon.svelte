<script lang="ts">
  import { Bot, Check, Loader2, Network, Wrench, X } from "lucide-svelte";
  import type { ScopeType } from "./scope-group-helpers";
  import type { ScopeGroupStatusColors } from "./scope-group-status-ui";

  interface Props {
    scopeType: ScopeType;
    aggregateStatus: "pending" | "executing" | "failed" | "completed";
    currentStatus: ScopeGroupStatusColors;
    innerIconSizePx: number;
    iconSize: string;
  }

  let { scopeType, aggregateStatus, currentStatus, innerIconSizePx, iconSize }: Props = $props();

  const badgeSize = $derived(Math.max(10, Math.round(innerIconSizePx * 0.55)));
</script>

<div class="relative flex-shrink-0">
  <div
    class="avatar-container rounded-lg flex items-center justify-center transition-all duration-300 {iconSize}"
    class:rounded-xl={scopeType === "swarm"}
    class:is-executing={aggregateStatus === "executing"}
    style="background: {scopeType === 'swarm'
      ? `linear-gradient(135deg, ${currentStatus.bg}, ${currentStatus.color}15)`
      : `linear-gradient(135deg, ${currentStatus.bg}, ${currentStatus.color}10)`};
           border: 1px solid {currentStatus.color}33;
           --status-color: {currentStatus.color};"
  >
    <!-- MARK: Base Identity Icon -->
    {#if scopeType === "swarm"}
      <Network size={innerIconSizePx} style="color: {currentStatus.color}" />
    {:else if scopeType === "system"}
      <Wrench size={innerIconSizePx} style="color: {currentStatus.color}" />
    {:else}
      <Bot size={innerIconSizePx} style="color: {currentStatus.color}" />
    {/if}

    <!-- MARK: Status Badge Overlay -->
    {#if aggregateStatus === "executing"}
      <span
        class="status-badge status-badge-executing"
        style="color: {currentStatus.color}; background: {currentStatus.bg}"
      >
        <Loader2 size={badgeSize} class="animate-spin" />
      </span>
    {:else if aggregateStatus === "completed"}
      <span class="status-badge status-badge-success">
        <Check size={badgeSize} />
      </span>
    {:else if aggregateStatus === "failed"}
      <span class="status-badge status-badge-error">
        <X size={badgeSize} />
      </span>
    {/if}
  </div>
</div>

<style>
  .avatar-container {
    position: relative;
  }

  .avatar-container.is-executing {
    animation: status-pulse 1.8s ease-in-out infinite;
  }

  @keyframes status-pulse {
    0%,
    100% {
      box-shadow: 0 0 0 0 color-mix(in srgb, var(--status-color) 30%, transparent);
    }
    50% {
      box-shadow: 0 0 0 4px color-mix(in srgb, var(--status-color) 8%, transparent);
    }
  }

  .status-badge {
    position: absolute;
    right: -4px;
    bottom: -4px;
    width: 1rem;
    height: 1rem;
    border-radius: 9999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1.5px solid var(--color-bg-secondary);
    pointer-events: none;
  }

  .status-badge-success {
    background: var(--color-success);
    color: var(--color-on-success, #001a10);
  }

  .status-badge-error {
    background: var(--color-error);
    color: var(--color-on-error, #2b0006);
  }

  .animate-spin {
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
