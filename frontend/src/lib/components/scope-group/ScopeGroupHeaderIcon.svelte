<script lang="ts">
  import { Check, CheckCircle, Loader2, Monitor, Users, X } from "lucide-svelte";
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
</script>

<div class="relative flex-shrink-0">
  <div
    class="avatar-container rounded-lg flex items-center justify-center transition-all duration-300 {iconSize}"
    class:rounded-xl={scopeType === "swarm"}
    style="background: {scopeType === 'swarm'
      ? `linear-gradient(135deg, ${currentStatus.bg}, ${currentStatus.color}15)`
      : currentStatus.bg}"
  >
    {#if aggregateStatus === "executing"}
      {#if scopeType === "swarm"}
        <div class="relative">
          <Users size={innerIconSizePx} style="color: {currentStatus.color}" />
          <div
            class="absolute -top-1 -right-1 w-2 h-2 rounded-full animate-pulse"
            style="background: {currentStatus.color}"
          ></div>
        </div>
      {:else}
        <Loader2 size={innerIconSizePx} class="animate-spin" style="color: {currentStatus.color}" />
      {/if}
    {:else if aggregateStatus === "completed"}
      {#if scopeType === "swarm"}
        <CheckCircle size={innerIconSizePx} style="color: {currentStatus.color}" />
      {:else}
        <Check size={innerIconSizePx} style="color: {currentStatus.color}" />
      {/if}
    {:else if aggregateStatus === "failed"}
      <X size={innerIconSizePx} style="color: {currentStatus.color}" />
    {:else if scopeType === "swarm"}
      <Users size={innerIconSizePx} style="color: var(--color-text-secondary)" />
    {:else}
      <Monitor size={innerIconSizePx} style="color: var(--color-text-secondary)" />
    {/if}
  </div>
</div>

<style>
  .animate-spin {
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
