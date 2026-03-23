<script lang="ts">
  import type { ScopeType } from "./scope-group-helpers";
  import type { ScopeGroupStatusColors } from "./scope-group-status-ui";

  interface Props {
    scopeType: ScopeType;
    compact?: boolean;
    progress?: number;
    completedCount?: number;
    totalCount?: number;
    currentStatus: ScopeGroupStatusColors;
  }

  let {
    scopeType,
    compact = false,
    progress = 0,
    completedCount = 0,
    totalCount = 0,
    currentStatus,
  }: Props = $props();
</script>

<div class="mt-1.5 flex items-center gap-2">
  <div
    class="flex-1 rounded-full bg-[var(--color-bg-tertiary)] overflow-hidden"
    class:h-1.5={scopeType === "swarm" && !compact}
    class:h-1={scopeType === "agent" || compact}
  >
    <div
      class="h-full rounded-full transition-all duration-500 ease-out"
      style="width: {progress}%; background: {scopeType === 'swarm'
        ? `linear-gradient(90deg, ${currentStatus.color}, var(--color-secondary))`
        : currentStatus.color}"
    ></div>
  </div>
  <span class="text-[10px] text-[var(--color-text-tertiary)] tabular-nums font-medium">
    {completedCount}/{totalCount}
  </span>
</div>
