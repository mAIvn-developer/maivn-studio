<script lang="ts">
  import type {
    AgentInfo,
    InterruptStyle,
    InvocationConfig,
    MemoryConfig,
    ModelToolOption,
    PrivateDataField,
    StructuredOutputConfig,
    SwarmInfo,
  } from "$lib/types";
  import AgentSettings from "../settings/AgentSettings.svelte";
  import InterruptStyleSelector from "../settings/InterruptStyleSelector.svelte";
  import InvocationSettings from "../settings/InvocationSettings.svelte";
  import MemorySettings from "../settings/MemorySettings.svelte";
  import PrivateDataConfig from "../settings/PrivateDataConfig.svelte";
  import StructuredOutputSelector from "../settings/StructuredOutputSelector.svelte";
  import SwarmSettings from "../settings/SwarmSettings.svelte";
  import CollapsibleConfigSection from "./CollapsibleConfigSection.svelte";

  interface Props {
    privateDataSchema?: PrivateDataField[];
    privateData?: Record<string, unknown>;
    privateDataDefaults?: Record<string, unknown>;
    hasActiveSession?: boolean;
    agents?: AgentInfo[];
    swarms?: SwarmInfo[];
    demoId?: string;
    invocationConfig?: InvocationConfig;
    availableTools?: string[];
    structuredOutputConfig?: StructuredOutputConfig;
    availableModelTools?: ModelToolOption[];
    interruptStyle?: InterruptStyle;
    memoryConfig?: MemoryConfig;
    onPrivateDataChange?: (data: Record<string, unknown>) => void;
    onDemoRefresh?: () => void;
    onInvocationChange?: (config: InvocationConfig) => void;
    onStructuredOutputChange?: (config: StructuredOutputConfig) => void;
    onInterruptStyleChange?: (style: InterruptStyle) => void;
    onMemoryConfigChange?: (config: MemoryConfig) => void;
  }

  let {
    privateDataSchema = [],
    privateData = {},
    privateDataDefaults = {},
    hasActiveSession = false,
    agents = [],
    swarms = [],
    demoId = "",
    invocationConfig,
    availableTools = [],
    structuredOutputConfig,
    availableModelTools = [],
    interruptStyle = "inline",
    memoryConfig,
    onPrivateDataChange,
    onDemoRefresh,
    onInvocationChange,
    onStructuredOutputChange,
    onInterruptStyleChange,
    onMemoryConfigChange,
  }: Props = $props();

  type SectionKey =
    | "privateData"
    | "structuredOutput"
    | "interruptStyle"
    | "agents"
    | "swarms"
    | "invocation"
    | "memory";

  let sectionOpen = $state<Record<SectionKey, boolean>>({
    privateData: true,
    structuredOutput: true,
    interruptStyle: true,
    agents: true,
    swarms: true,
    invocation: true,
    memory: true,
  });

  function toggleSection(section: SectionKey) {
    sectionOpen = {
      ...sectionOpen,
      [section]: !sectionOpen[section],
    };
  }
</script>

<div class="h-full overflow-y-auto overflow-x-hidden">
  <!-- Private Data Configuration -->
  {#if privateDataSchema.length > 0}
    <CollapsibleConfigSection
      title="Private Data"
      subtitle={`${privateDataSchema.length} field(s)`}
      open={sectionOpen.privateData}
      onToggle={() => toggleSection("privateData")}
    >
      <PrivateDataConfig
        schema={privateDataSchema}
        values={privateData}
        fallbackValues={privateDataDefaults}
        onchange={onPrivateDataChange}
        disabled={hasActiveSession}
      />
    </CollapsibleConfigSection>
  {/if}

  <!-- Structured Output -->
  {#if demoId && structuredOutputConfig && onStructuredOutputChange}
    <CollapsibleConfigSection
      title="Structured Output"
      subtitle="Tool model and schema"
      open={sectionOpen.structuredOutput}
      onToggle={() => toggleSection("structuredOutput")}
    >
      <StructuredOutputSelector
        config={structuredOutputConfig}
        availableTools={availableModelTools}
        disabled={hasActiveSession}
        onConfigChange={onStructuredOutputChange}
      />
    </CollapsibleConfigSection>
  {/if}

  <!-- Interrupt Style -->
  {#if demoId && onInterruptStyleChange}
    <CollapsibleConfigSection
      title="Interrupt Style"
      subtitle="Inline, modal, drawer, floating"
      open={sectionOpen.interruptStyle}
      onToggle={() => toggleSection("interruptStyle")}
    >
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-[var(--color-text)]">Style</span>
        <InterruptStyleSelector value={interruptStyle} onChange={onInterruptStyleChange} />
      </div>
    </CollapsibleConfigSection>
  {/if}

  <!-- Agent Settings -->
  {#if agents.length > 0 && demoId}
    <CollapsibleConfigSection
      title="Agents"
      subtitle={`${agents.length} configured`}
      open={sectionOpen.agents}
      onToggle={() => toggleSection("agents")}
    >
      <AgentSettings {agents} {demoId} disabled={hasActiveSession} onAgentUpdated={onDemoRefresh} />
    </CollapsibleConfigSection>
  {/if}

  <!-- Swarm Settings -->
  {#if swarms.length > 0 && demoId}
    <CollapsibleConfigSection
      title="Swarms"
      subtitle={`${swarms.length} configured`}
      open={sectionOpen.swarms}
      onToggle={() => toggleSection("swarms")}
    >
      <SwarmSettings {swarms} {demoId} disabled={hasActiveSession} onSwarmUpdated={onDemoRefresh} />
    </CollapsibleConfigSection>
  {/if}

  <!-- Invocation Settings -->
  {#if invocationConfig && onInvocationChange && demoId}
    <CollapsibleConfigSection
      title="Invocation"
      subtitle="Model, reasoning, tool targeting"
      open={sectionOpen.invocation}
      onToggle={() => toggleSection("invocation")}
    >
      <InvocationSettings
        config={invocationConfig}
        {availableTools}
        disabled={hasActiveSession}
        structuredOutputEnabled={structuredOutputConfig?.enabled ?? false}
        onChange={onInvocationChange}
      />
    </CollapsibleConfigSection>
  {/if}

  <!-- Memory Settings -->
  {#if demoId && memoryConfig && onMemoryConfigChange}
    <CollapsibleConfigSection
      title="Memory"
      subtitle={memoryConfig.enabled ? "Enabled" : "Disabled"}
      open={sectionOpen.memory}
      onToggle={() => toggleSection("memory")}
    >
      <MemorySettings
        config={memoryConfig}
        disabled={hasActiveSession}
        onChange={onMemoryConfigChange}
      />
    </CollapsibleConfigSection>
  {/if}

  <!-- Empty state when no config options available -->
  {#if privateDataSchema.length === 0 && agents.length === 0 && swarms.length === 0 && !invocationConfig && !demoId}
    <div class="flex flex-col items-center justify-center p-8 text-center">
      <p class="text-sm text-[var(--color-text-tertiary)]">No configuration options available.</p>
      <p class="text-xs text-[var(--color-text-tertiary)] mt-1">
        Select a demo to see its settings.
      </p>
    </div>
  {/if}
</div>
