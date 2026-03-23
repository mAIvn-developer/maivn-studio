<script lang="ts">
  import { MessageSquare, Wrench, Users, Clock, Hash, ChevronDown } from "lucide-svelte";
  import SegmentedControl from "../ui/SegmentedControl.svelte";
  import Checkbox from "../ui/Checkbox.svelte";
  import { formatDuration, formatTokens, formatTimeWithSeconds } from "$lib/utils/format";
  import type {
    ChatFlowFilter,
    ChatFlowFilters,
    EventSummary,
    ToolStatusFilter,
    UIEvent,
  } from "$lib/types";

  // AccumulatedStats tracks aggregated stats across all SDK invocations (sessions) in the thread
  interface AccumulatedStats {
    totalDurationMs: number;
    totalTokens: number;
    inputTokens: number;
    outputTokens: number;
    reasoningTokens: number;
    cacheReadTokens: number;
    cacheCreationTokens: number;
    sessionCount: number;
  }

  interface Props {
    eventSummary: EventSummary;
    accumulatedStats?: AccumulatedStats;
    filters: ChatFlowFilters;
    events?: UIEvent[];
    onFilterChange: (filters: Partial<ChatFlowFilters>) => void;
  }

  let { eventSummary, accumulatedStats, filters, events = [], onFilterChange }: Props = $props();

  let eventsExpanded = $state(false);

  // Show most recent events first, limited to last 50
  let recentEvents = $derived(events.slice(-50).toReversed());

  // MARK: Filter Options

  const itemTypeOptions: { value: ChatFlowFilter; label: string }[] = [
    { value: "all", label: "All" },
    { value: "messages", label: "Messages" },
    { value: "tools", label: "Tools" },
  ];

  const toolStatusOptions: { value: ToolStatusFilter; label: string; color?: string }[] = [
    { value: "all", label: "All" },
    { value: "pending", label: "Pending", color: "var(--color-warning)" },
    { value: "executing", label: "Running", color: "var(--color-tertiary)" },
    { value: "completed", label: "Done", color: "var(--color-tertiary)" },
    { value: "failed", label: "Failed", color: "var(--color-error)" },
  ];

  // MARK: Event Styling

  function getEventColor(type: string): string {
    if (type.includes("error") || type.includes("fail")) return "var(--color-error)";
    if (type.includes("complete") || type.includes("success")) return "var(--color-tertiary)";
    if (type.includes("start") || type.includes("executing")) return "var(--color-secondary)";
    if (type.includes("pending") || type.includes("queue")) return "var(--color-warning)";
    return "var(--color-text-tertiary)";
  }
</script>

<div class="h-full overflow-y-auto overflow-x-hidden">
  <!-- Summary Stats -->
  <div class="border-b border-[var(--color-outline-variant)] p-4">
    <h4 class="text-overline text-[var(--color-text-tertiary)] mb-3">Summary</h4>

    <!-- Stats cards with Lucide icons -->
    <div class="grid grid-cols-2 gap-2">
      <div class="stat-card">
        <div class="stat-icon bg-[var(--color-primary)]/15">
          <MessageSquare size={16} class="text-[var(--color-primary)]" />
        </div>
        <div>
          <span class="text-lg font-semibold text-[var(--color-text)]">
            {eventSummary.totalMessages}
          </span>
          <span class="text-xs text-[var(--color-text-tertiary)] block">Messages</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-[var(--color-tertiary)]/15">
          <Wrench size={16} class="text-[var(--color-tertiary)]" />
        </div>
        <div>
          <span class="text-lg font-semibold text-[var(--color-text)]">
            {eventSummary.totalTools}
          </span>
          <span class="text-xs text-[var(--color-text-tertiary)] block">Tools</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bg-[var(--color-secondary)]/15">
          <Users size={16} class="text-[var(--color-secondary)]" />
        </div>
        <div>
          <span class="text-lg font-semibold text-[var(--color-text)]">
            {eventSummary.totalAgents}
          </span>
          <span class="text-xs text-[var(--color-text-tertiary)] block">Agents</span>
        </div>
      </div>
    </div>

    <!-- Tool/Agent status breakdown -->
    {#if eventSummary.totalTools > 0 || eventSummary.totalAgents > 0}
      <div class="mt-4 space-y-4">
        {#if eventSummary.totalTools > 0}
          <div>
            <div class="text-[10px] uppercase tracking-wide text-[var(--color-text-tertiary)]">
              Tools
            </div>
            <div class="mt-2 space-y-2">
              {#if eventSummary.pendingTools > 0}
                <div class="status-row">
                  <div class="w-2 h-2 rounded-full bg-[var(--color-warning)]"></div>
                  <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Pending</span>
                  <span class="text-xs font-medium" style="color: var(--color-warning)">
                    {eventSummary.pendingTools}
                  </span>
                </div>
              {/if}
              {#if eventSummary.executingTools > 0}
                <div class="status-row">
                  <div class="w-2 h-2 rounded-full bg-[var(--color-tertiary)] animate-pulse"></div>
                  <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Running</span>
                  <span class="text-xs font-medium text-[var(--color-tertiary)]">
                    {eventSummary.executingTools}
                  </span>
                </div>
              {/if}
              {#if eventSummary.completedTools > 0}
                <div class="status-row">
                  <div class="w-2 h-2 rounded-full bg-[var(--color-tertiary)]"></div>
                  <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Completed</span>
                  <span class="text-xs font-medium text-[var(--color-tertiary)]">
                    {eventSummary.completedTools}
                  </span>
                </div>
              {/if}
              {#if eventSummary.failedTools > 0}
                <div class="status-row">
                  <div class="w-2 h-2 rounded-full bg-[var(--color-error)]"></div>
                  <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Failed</span>
                  <span class="text-xs font-medium text-[var(--color-error)]">
                    {eventSummary.failedTools}
                  </span>
                </div>
              {/if}
            </div>
          </div>
        {/if}

        {#if eventSummary.totalAgents > 0}
          <div>
            <div class="text-[10px] uppercase tracking-wide text-[var(--color-text-tertiary)]">
              Agents
            </div>
            <div class="mt-2 space-y-2">
              {#if eventSummary.pendingAgents > 0}
                <div class="status-row">
                  <div class="w-2 h-2 rounded-full bg-[var(--color-warning)]"></div>
                  <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Pending</span>
                  <span class="text-xs font-medium" style="color: var(--color-warning)">
                    {eventSummary.pendingAgents}
                  </span>
                </div>
              {/if}
              {#if eventSummary.executingAgents > 0}
                <div class="status-row">
                  <div class="w-2 h-2 rounded-full bg-[var(--color-secondary)] animate-pulse"></div>
                  <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Running</span>
                  <span class="text-xs font-medium text-[var(--color-secondary)]">
                    {eventSummary.executingAgents}
                  </span>
                </div>
              {/if}
              {#if eventSummary.completedAgents > 0}
                <div class="status-row">
                  <div class="w-2 h-2 rounded-full bg-[var(--color-secondary)]"></div>
                  <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Completed</span>
                  <span class="text-xs font-medium text-[var(--color-secondary)]">
                    {eventSummary.completedAgents}
                  </span>
                </div>
              {/if}
              {#if eventSummary.failedAgents > 0}
                <div class="status-row">
                  <div class="w-2 h-2 rounded-full bg-[var(--color-error)]"></div>
                  <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Failed</span>
                  <span class="text-xs font-medium text-[var(--color-error)]">
                    {eventSummary.failedAgents}
                  </span>
                </div>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Thread Stats (accumulated across sessions) -->
  {#if accumulatedStats && accumulatedStats.sessionCount > 0}
    <div class="border-b border-[var(--color-outline-variant)] p-4">
      <h4 class="text-overline text-[var(--color-text-tertiary)] mb-3">Thread Stats</h4>

      <div class="grid grid-cols-2 gap-2 mb-3">
        <!-- Total Duration -->
        <div class="stat-card">
          <div class="stat-icon bg-[var(--color-tertiary)]/15">
            <Clock size={16} class="text-[var(--color-tertiary)]" />
          </div>
          <div>
            <span class="text-lg font-semibold text-[var(--color-text)] tabular-nums">
              {formatDuration(accumulatedStats.totalDurationMs)}
            </span>
            <span class="text-xs text-[var(--color-text-tertiary)] block">Duration</span>
          </div>
        </div>

        <!-- Total Tokens -->
        <div class="stat-card">
          <div class="stat-icon bg-[var(--color-primary)]/15">
            <Hash size={16} class="text-[var(--color-primary)]" />
          </div>
          <div>
            <span class="text-lg font-semibold text-[var(--color-text)] tabular-nums">
              {formatTokens(accumulatedStats.totalTokens)}
            </span>
            <span class="text-xs text-[var(--color-text-tertiary)] block">Tokens</span>
          </div>
        </div>
      </div>

      <!-- Token breakdown -->
      {#if accumulatedStats.totalTokens > 0}
        <div class="space-y-2">
          <div class="status-row">
            <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Input</span>
            <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
              {formatTokens(accumulatedStats.inputTokens)}
            </span>
          </div>
          <div class="status-row">
            <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Output</span>
            <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
              {formatTokens(accumulatedStats.outputTokens)}
            </span>
          </div>
          {#if accumulatedStats.reasoningTokens > 0}
            <div class="status-row">
              <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Reasoning</span>
              <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
                {formatTokens(accumulatedStats.reasoningTokens)}
              </span>
            </div>
          {/if}
          {#if accumulatedStats.cacheReadTokens > 0}
            <div class="status-row">
              <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Cache Read</span>
              <span class="text-xs font-medium text-[var(--color-success)] tabular-nums">
                {formatTokens(accumulatedStats.cacheReadTokens)}
              </span>
            </div>
          {/if}
          {#if accumulatedStats.cacheCreationTokens > 0}
            <div class="status-row">
              <span class="flex-1 text-xs text-[var(--color-text-secondary)]">Cache Write</span>
              <span class="text-xs font-medium text-[var(--color-text)] tabular-nums">
                {formatTokens(accumulatedStats.cacheCreationTokens)}
              </span>
            </div>
          {/if}
        </div>
      {/if}

      <!-- Session count -->
      <div class="mt-3 text-center">
        <span class="text-[10px] text-[var(--color-text-tertiary)] uppercase">
          {accumulatedStats.sessionCount} session{accumulatedStats.sessionCount !== 1 ? "s" : ""}
        </span>
      </div>
    </div>
  {/if}

  <!-- Filter by Item Type -->
  <div class="border-b border-[var(--color-outline-variant)] p-4">
    <h4 class="text-overline text-[var(--color-text-tertiary)] mb-3">Show</h4>
    <SegmentedControl
      options={itemTypeOptions}
      value={filters.itemType}
      onchange={(value) => onFilterChange({ itemType: value })}
    />
  </div>

  <!-- Filter by Tool Status -->
  <div class="border-b border-[var(--color-outline-variant)] p-4">
    <h4 class="text-overline text-[var(--color-text-tertiary)] mb-3">Tool Status</h4>
    <SegmentedControl
      options={toolStatusOptions}
      value={filters.toolStatus}
      onchange={(value) => onFilterChange({ toolStatus: value })}
    />
  </div>

  <!-- Display Options -->
  <div class="border-b border-[var(--color-outline-variant)] p-4">
    <h4 class="text-overline text-[var(--color-text-tertiary)] mb-3">Display Options</h4>
    <div class="space-y-3">
      <Checkbox
        checked={filters.expandAllCards}
        label="Expand all tool cards"
        onchange={() => onFilterChange({ expandAllCards: !filters.expandAllCards })}
      />
      <Checkbox
        checked={filters.showToolArgs}
        label="Show tool arguments"
        onchange={() => onFilterChange({ showToolArgs: !filters.showToolArgs })}
      />
      <Checkbox
        checked={filters.richResultDisplay}
        label="Rich result display"
        onchange={() => onFilterChange({ richResultDisplay: !filters.richResultDisplay })}
      />
      <Checkbox
        checked={filters.showStructuredOutput}
        label="Always show structured output"
        onchange={() => onFilterChange({ showStructuredOutput: !filters.showStructuredOutput })}
      />
      <Checkbox
        checked={filters.showSessionDetails}
        label="Always show session details"
        onchange={() => onFilterChange({ showSessionDetails: !filters.showSessionDetails })}
      />
    </div>
  </div>

  <!-- Event Log (collapsible) -->
  <div class="p-4">
    <button
      type="button"
      class="events-toggle"
      aria-expanded={eventsExpanded}
      onclick={() => (eventsExpanded = !eventsExpanded)}
    >
      <h4 class="text-overline text-[var(--color-text-tertiary)]">Event Log</h4>
      <div class="flex items-center gap-1.5">
        {#if events.length > 0}
          <span class="text-[10px] text-[var(--color-text-tertiary)] tabular-nums">
            {events.length}
          </span>
        {/if}
        <ChevronDown
          size={14}
          class="text-[var(--color-text-tertiary)] transition-transform {eventsExpanded
            ? 'rotate-180'
            : ''}"
        />
      </div>
    </button>

    {#if eventsExpanded}
      <div class="event-list animate-in">
        {#if recentEvents.length > 0}
          {#each recentEvents as event (event.id)}
            <div class="event-row">
              <div class="flex items-center gap-2 min-w-0">
                <div class="event-dot" style="background-color: {getEventColor(event.type)}"></div>
                <span class="event-type">{event.type}</span>
              </div>
              <span class="event-time">
                {formatTimeWithSeconds(event.timestamp)}
              </span>
            </div>
          {/each}
        {:else}
          <p class="text-xs text-[var(--color-text-tertiary)] py-2">
            No events yet. Events appear as the session runs.
          </p>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .stat-card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    border-radius: var(--radius-lg);
    background-color: var(--color-bg-tertiary);
  }

  .stat-icon {
    width: 2rem;
    height: 2rem;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .status-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-md);
    background-color: var(--color-bg-tertiary);
  }

  .events-toggle {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    margin-bottom: 0.25rem;
  }

  .event-list {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    margin-top: 0.5rem;
  }

  .event-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.375rem 0.5rem;
    border-radius: var(--radius-sm);
    transition: background-color var(--transition-fast);
  }

  .event-row:hover {
    background: var(--color-bg-tertiary);
  }

  .event-dot {
    width: 0.375rem;
    height: 0.375rem;
    border-radius: var(--radius-full);
    flex-shrink: 0;
  }

  .event-type {
    font-size: 0.6875rem;
    font-weight: 500;
    color: var(--color-text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .event-time {
    font-size: 0.625rem;
    color: var(--color-text-tertiary);
    font-variant-numeric: tabular-nums;
    flex-shrink: 0;
  }
</style>
