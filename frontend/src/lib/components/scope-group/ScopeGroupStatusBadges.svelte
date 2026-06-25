<script lang="ts">
  import type { ScopeType } from "./scope-group-helpers";
  import type { ScopeGroupStatusColors } from "./scope-group-status-ui";

  interface Props {
    scopeType: ScopeType;
    nestedAgentsCount?: number;
    executingCount?: number;
    activeAgentCount?: number;
    displayPhaseMessage?: string | null;
    failedCount?: number;
    currentStatus: ScopeGroupStatusColors;
    aggregateStatus: "pending" | "executing" | "failed" | "completed";
  }

  let {
    scopeType,
    nestedAgentsCount = 0,
    executingCount = 0,
    activeAgentCount = 0,
    displayPhaseMessage = null,
    failedCount = 0,
    currentStatus,
    aggregateStatus,
  }: Props = $props();

  const scopeLabel = $derived(
    scopeType === "swarm" ? "Swarm" : scopeType === "system" ? "Tools" : "Agent",
  );
</script>

<span
  class="text-[10px] px-1.5 py-0.5 rounded font-medium"
  class:rounded-full={scopeType === "swarm"}
  class:px-2={scopeType === "swarm"}
  class:uppercase={scopeType === "swarm"}
  class:tracking-wide={scopeType === "swarm"}
  class:font-bold={scopeType === "swarm"}
  style="background: {scopeType === 'swarm'
    ? 'var(--color-primary)'
    : 'var(--color-secondary)'}20; color: {scopeType === 'swarm'
    ? 'var(--color-primary)'
    : 'var(--color-secondary)'}"
>
  {scopeLabel}
</span>

{#if scopeType === "swarm" && nestedAgentsCount > 0}
  <span
    class="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-secondary)]/15 text-[var(--color-secondary)]"
  >
    {nestedAgentsCount} agent{nestedAgentsCount !== 1 ? "s" : ""}
  </span>
{/if}

{#if executingCount > 0}
  <span
    class="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded"
    style="background: {currentStatus.bg}; color: {currentStatus.color}"
  >
    <span class="w-1.5 h-1.5 rounded-full animate-pulse" style="background: {currentStatus.color}"
    ></span>
    {#if scopeType === "swarm"}
      {activeAgentCount} active
    {:else}
      {executingCount} running
    {/if}
  </span>
{/if}

{#if displayPhaseMessage}
  <span
    class="inline-flex max-w-full items-center gap-1 rounded
           bg-[var(--color-secondary)]/12 px-1.5 py-0.5 text-[10px]
           text-[var(--color-secondary)]"
    title={displayPhaseMessage ?? undefined}
  >
    <span
      class="h-1.5 w-1.5 rounded-full bg-[var(--color-secondary)]"
      class:animate-pulse={aggregateStatus === "executing"}
    ></span>
    <span class="max-w-[22ch] truncate">{displayPhaseMessage}</span>
  </span>
{/if}

{#if failedCount > 0}
  <span
    class="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded"
    style="background: rgba(255, 180, 171, 0.15); color: var(--color-error)"
  >
    {failedCount} failed
  </span>
{/if}
