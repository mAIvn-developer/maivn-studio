<script lang="ts">
  import type {
    AgentInfo,
    ChatFlowFilters,
    EventSummary,
    ExtractedInsightSummary,
    ExtractedSkillSummary,
    InterruptStyle,
    InvocationConfig,
    MemoryConfig,
    ModelToolOption,
    PrivateDataField,
    RetrievedMemoryContext,
    StructuredOutputConfig,
    SwarmInfo,
    UIEvent,
  } from "$lib/types";
  import { BrainCircuit, Clock, Search, Settings } from "lucide-svelte";
  import Badge from "../ui/Badge.svelte";
  import ConfigTab from "./ConfigTab.svelte";
  import InspectTab from "./InspectTab.svelte";
  import MemoryTab from "./MemoryTab.svelte";
  import ScheduleTab from "./ScheduleTab.svelte";

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

  type InspectorTab = "config" | "inspect" | "memory" | "schedule";

  interface Props {
    events: UIEvent[];
    filters: ChatFlowFilters;
    eventSummary: EventSummary;
    accumulatedStats?: AccumulatedStats;
    privateDataSchema?: PrivateDataField[];
    privateData?: Record<string, unknown>;
    privateDataDefaults?: Record<string, unknown>;
    hasActiveSession?: boolean;
    agents?: AgentInfo[];
    swarms?: SwarmInfo[];
    appId?: string;
    invocationConfig?: InvocationConfig;
    availableTools?: string[];
    structuredOutputConfig?: StructuredOutputConfig;
    availableModelTools?: ModelToolOption[];
    interruptStyle?: InterruptStyle;
    extractedSkills?: ExtractedSkillSummary[];
    extractedInsights?: ExtractedInsightSummary[];
    retrievedMemoryContext?: RetrievedMemoryContext | null;
    memoryConfig?: MemoryConfig;
    onFilterChange: (filters: Partial<ChatFlowFilters>) => void;
    onPrivateDataChange?: (data: Record<string, unknown>) => void;
    onAppRefresh?: () => void;
    onInvocationChange?: (config: InvocationConfig) => void;
    onStructuredOutputChange?: (config: StructuredOutputConfig) => void;
    onInterruptStyleChange?: (style: InterruptStyle) => void;
    onMemoryConfigChange?: (config: MemoryConfig) => void;
  }

  let {
    events,
    filters,
    eventSummary,
    accumulatedStats,
    privateDataSchema = [],
    privateData = {},
    privateDataDefaults = {},
    hasActiveSession = false,
    agents = [],
    swarms = [],
    appId = "",
    invocationConfig,
    availableTools = [],
    structuredOutputConfig,
    interruptStyle = "inline",
    extractedSkills = [],
    extractedInsights = [],
    retrievedMemoryContext = null,
    memoryConfig,
    onFilterChange,
    onPrivateDataChange,
    onAppRefresh,
    onInvocationChange,
    onInterruptStyleChange,
    onMemoryConfigChange,
  }: Props = $props();

  // MARK: Tab State

  let activeTab = $state<InspectorTab>("config");
  let previousHasActiveSession = $state(false);
  let previousMemoryItemCount = $state(0);

  // Count active filters for badge on Inspect tab
  let activeFilterCount = $derived(
    (filters.itemType !== "all" ? 1 : 0) +
      (filters.toolStatus !== "all" ? 1 : 0) +
      (filters.expandAllCards ? 1 : 0) +
      (filters.showToolArgs ? 1 : 0) +
      (filters.richResultDisplay ? 1 : 0) +
      (filters.showStructuredOutput ? 1 : 0) +
      (filters.showSessionDetails ? 1 : 0),
  );

  let memoryItemCount = $derived(
    extractedSkills.length +
      extractedInsights.length +
      (retrievedMemoryContext?.skills?.length ?? 0) +
      (retrievedMemoryContext?.insights?.length ?? 0),
  );

  // Smart auto-switching: when session starts, switch to inspect tab
  $effect(() => {
    if (hasActiveSession && !previousHasActiveSession) {
      activeTab = "inspect";
    }
    previousHasActiveSession = hasActiveSession;
  });

  // Auto-switch to memory tab when first memory data arrives
  $effect(() => {
    const hasMemoryData = memoryItemCount > 0 || retrievedMemoryContext !== null;
    if (hasActiveSession && hasMemoryData && previousMemoryItemCount === 0) {
      activeTab = "memory";
    }
    previousMemoryItemCount = memoryItemCount;
  });

  // MARK: Tab Configuration

  const tabs: { id: InspectorTab; label: string; icon: typeof Settings }[] = [
    { id: "config", label: "Config", icon: Settings },
    { id: "inspect", label: "Inspect", icon: Search },
    { id: "memory", label: "Recall", icon: BrainCircuit },
    { id: "schedule", label: "Schedule", icon: Clock },
  ];
</script>

<div class="h-full flex flex-col overflow-hidden">
  <!-- Tab Bar -->
  <div class="shrink-0 border-b border-[var(--color-outline-variant)]">
    <div class="flex">
      {#each tabs as tab}
        <button
          class="tab-button flex-1 min-w-0 flex items-center justify-center gap-1 px-2 py-2.5
                 text-xs font-medium transition-colors relative"
          class:tab-active={activeTab === tab.id}
          class:tab-inactive={activeTab !== tab.id}
          onclick={() => (activeTab = tab.id)}
        >
          <tab.icon size={13} strokeWidth={2} class="shrink-0" />
          <span class="truncate">{tab.label}</span>
          {#if tab.id === "inspect" && (activeFilterCount > 0 || events.length > 0)}
            <Badge variant="tertiary" pill>
              {activeFilterCount > 0 ? activeFilterCount : events.length}
            </Badge>
          {/if}
          {#if tab.id === "memory" && memoryItemCount > 0}
            <Badge variant="secondary" pill>
              {memoryItemCount}
            </Badge>
          {/if}
        </button>
      {/each}
    </div>
  </div>

  <!-- Tab Content -->
  <div class="flex-1 min-h-0 overflow-hidden">
    {#if activeTab === "config"}
      <ConfigTab
        {privateDataSchema}
        {privateData}
        {privateDataDefaults}
        {hasActiveSession}
        {agents}
        {swarms}
        {appId}
        {invocationConfig}
        {availableTools}
        {structuredOutputConfig}
        {interruptStyle}
        {memoryConfig}
        {onPrivateDataChange}
        {onAppRefresh}
        {onInvocationChange}
        {onInterruptStyleChange}
        {onMemoryConfigChange}
      />
    {:else if activeTab === "inspect"}
      <InspectTab {eventSummary} {accumulatedStats} {filters} {onFilterChange} {events} />
    {:else if activeTab === "memory"}
      <MemoryTab {extractedSkills} {extractedInsights} {retrievedMemoryContext} />
    {:else if activeTab === "schedule"}
      <ScheduleTab {appId} />
    {/if}
  </div>
</div>

<style>
  .tab-button {
    border-bottom: 2px solid transparent;
    background: none;
    cursor: pointer;
  }

  .tab-active {
    color: var(--color-secondary);
    border-bottom-color: var(--color-secondary);
    background-color: var(--color-bg-secondary);
  }

  .tab-inactive {
    color: var(--color-text-tertiary);
  }

  .tab-inactive:hover {
    color: var(--color-text-secondary);
    background-color: var(--color-bg-secondary);
  }
</style>
