<script lang="ts">
  import { ChevronDown } from "lucide-svelte";
  import type { ScopeType } from "./scope-group-helpers";
  import type { ScopeGroupStatusColors } from "./scope-group-status-ui";
  import ScopeGroupHeaderIcon from "./ScopeGroupHeaderIcon.svelte";
  import ScopeGroupProgressRow from "./ScopeGroupProgressRow.svelte";
  import ScopeGroupStatusBadges from "./ScopeGroupStatusBadges.svelte";
  import ScopeGroupTitle from "./ScopeGroupTitle.svelte";

  interface Props {
    scopeType: ScopeType;
    scopeName: string;
    compact?: boolean;
    nestedAgentsCount?: number;
    executingCount?: number;
    activeAgentCount?: number;
    displayPhaseMessage?: string | null;
    failedCount?: number;
    completedCount?: number;
    totalCount?: number;
    progress?: number;
    currentStatus: ScopeGroupStatusColors;
    aggregateStatus: "pending" | "executing" | "failed" | "completed";
    innerIconSizePx: number;
    expandIconSizePx: number;
    iconSize: string;
    isExpanded: boolean;
    onToggleExpanded: () => void;
  }

  let {
    scopeType,
    scopeName,
    compact = false,
    nestedAgentsCount = 0,
    executingCount = 0,
    activeAgentCount = 0,
    displayPhaseMessage = null,
    failedCount = 0,
    completedCount = 0,
    totalCount = 0,
    progress = 0,
    currentStatus,
    aggregateStatus,
    innerIconSizePx,
    expandIconSizePx,
    iconSize,
    isExpanded,
    onToggleExpanded,
  }: Props = $props();
</script>

<button
  class="w-full flex items-center gap-3 text-left transition-colors"
  class:px-4={!compact}
  class:py-3={!compact}
  class:px-3={compact}
  class:py-2={compact}
  class:bg-gradient-to-r={scopeType === "swarm"}
  class:from-[var(--color-bg-secondary)]={scopeType === "swarm"}
  class:to-[var(--color-bg-tertiary)]={scopeType === "swarm"}
  class:bg-[var(--color-bg-secondary)]={scopeType !== "swarm"}
  class:hover:bg-[var(--color-bg-tertiary)]={true}
  onclick={onToggleExpanded}
>
  <ScopeGroupHeaderIcon
    {scopeType}
    {aggregateStatus}
    {currentStatus}
    {innerIconSizePx}
    {iconSize}
  />

  <div class="flex-1 min-w-0">
    <div class="flex items-center gap-2 flex-wrap">
      <ScopeGroupTitle {scopeType} {scopeName} {compact} />

      <ScopeGroupStatusBadges
        {scopeType}
        {nestedAgentsCount}
        {executingCount}
        {activeAgentCount}
        {displayPhaseMessage}
        {failedCount}
        {currentStatus}
        {aggregateStatus}
      />
    </div>

    <ScopeGroupProgressRow
      {scopeType}
      {compact}
      {progress}
      {completedCount}
      {totalCount}
      {currentStatus}
    />
  </div>

  <ChevronDown
    size={expandIconSizePx}
    class="text-[var(--color-text-tertiary)] transition-transform duration-200 flex-shrink-0 {isExpanded
      ? 'rotate-180'
      : ''}"
  />
</button>
