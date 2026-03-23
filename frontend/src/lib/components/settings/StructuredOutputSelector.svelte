<script lang="ts">
  import { TableProperties, ChevronDown, Check } from "lucide-svelte";
  import type { ModelToolOption, StructuredOutputConfig } from "$lib/types";

  interface Props {
    config: StructuredOutputConfig;
    availableTools?: ModelToolOption[];
    disabled?: boolean;
    onConfigChange: (config: StructuredOutputConfig) => void;
  }

  let { config, availableTools = [], disabled = false, onConfigChange }: Props = $props();

  let isExpanded = $state(true);
  let showSchemaEditor = $state(false);
  let customSchemaText = $state("");
  let schemaError = $state<string | null>(null);

  // Sync custom schema text when config changes
  $effect(() => {
    if (config.schema && !config.selectedTool) {
      customSchemaText = JSON.stringify(config.schema.schema, null, 2);
    }
  });

  function toggleEnabled(e: Event) {
    e.stopPropagation();
    if (config.enabled) {
      onConfigChange({
        enabled: false,
        selectedTool: undefined,
        schema: undefined,
      });
    } else {
      onConfigChange({
        ...config,
        enabled: true,
      });
    }
  }

  function selectTool(toolName: string | null) {
    if (toolName === null) {
      onConfigChange({
        ...config,
        selectedTool: undefined,
        schema: config.schema || {
          name: "custom_output",
          description: "Custom structured output",
          schema: { type: "object", properties: {} },
        },
      });
    } else {
      const tool = availableTools.find((t) => t.name === toolName);
      onConfigChange({
        ...config,
        selectedTool: toolName,
        schema: tool
          ? {
              name: tool.name,
              description: tool.description,
              schema: tool.schema || {},
            }
          : undefined,
      });
    }
  }

  function updateCustomSchema() {
    schemaError = null;
    try {
      const parsed = JSON.parse(customSchemaText);
      onConfigChange({
        ...config,
        selectedTool: undefined,
        schema: {
          name: "custom_output",
          description: "Custom structured output",
          schema: parsed,
        },
      });
    } catch {
      schemaError = "Invalid JSON schema";
    }
  }

  const isCustomMode = $derived(!config.selectedTool && config.enabled);
</script>

<div>
  <!-- Section header (clickable to collapse) -->
  <button
    class="w-full flex items-center gap-3 text-left transition-colors rounded-lg p-2
           hover:bg-[var(--color-bg-tertiary)]/50"
    onclick={() => (isExpanded = !isExpanded)}
  >
    <!-- Icon -->
    <div
      class="flex h-8 w-8 items-center justify-center rounded-lg shrink-0
             {config.enabled ? 'bg-[var(--color-tertiary)]/15' : 'bg-[var(--color-bg-tertiary)]'}"
    >
      <TableProperties
        size={16}
        class={config.enabled
          ? "text-[var(--color-tertiary)]"
          : "text-[var(--color-text-tertiary)]"}
      />
    </div>

    <div class="flex-1 min-w-0">
      <span class="font-medium text-sm text-[var(--color-text)]">Structured Output</span>
      <p class="text-xs text-[var(--color-text-tertiary)] mt-0.5">
        {config.enabled && config.selectedTool
          ? config.selectedTool
          : config.enabled
            ? "Custom schema"
            : "Tool model & schema"}
      </p>
    </div>

    <!-- Enable/disable toggle -->
    <div
      class="relative flex-shrink-0 w-8 h-[1.125rem] rounded-full transition-colors cursor-pointer
             {config.enabled
        ? 'bg-[var(--color-tertiary)]'
        : 'bg-[rgba(var(--color-outline-rgb,128,128,128),0.3)]'}"
      class:opacity-50={disabled}
      role="switch"
      tabindex="0"
      aria-checked={config.enabled}
      aria-label="Toggle structured output"
      onclick={toggleEnabled}
      onkeydown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleEnabled(e);
        }
      }}
    >
      <div
        class="absolute left-0.5 top-[1px] w-4 h-4 rounded-full bg-white transition-transform
               {config.enabled ? 'translate-x-[14px]' : ''}"
      ></div>
    </div>

    <!-- Expand indicator -->
    <ChevronDown
      size={16}
      class="text-[var(--color-text-tertiary)] transition-transform shrink-0 {isExpanded
        ? 'rotate-180'
        : ''}"
    />
  </button>

  {#if isExpanded && config.enabled}
    <div class="mt-2 space-y-3 p-2 rounded-lg bg-[var(--color-bg-tertiary)] animate-in">
      <!-- Tool selection -->
      {#if availableTools.length > 0}
        <div class="space-y-1.5">
          <span class="field-label">Use Tool as Model</span>
          <select
            class="w-full rounded-lg bg-[var(--color-bg)] border border-[var(--color-outline-variant)]
                   px-3 py-2 text-xs text-[var(--color-text)]
                   focus:outline-none focus:border-[var(--color-tertiary)]/50"
            value={config.selectedTool || ""}
            onchange={(e) => selectTool((e.target as HTMLSelectElement).value || null)}
            {disabled}
          >
            <option value="">Custom Schema...</option>
            {#each availableTools as tool}
              <option value={tool.name}>{tool.name}</option>
            {/each}
          </select>
        </div>
      {/if}

      <!-- Custom schema editor -->
      {#if isCustomMode || availableTools.length === 0}
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="field-label">JSON Schema</span>
            <button
              type="button"
              class="text-[10px] text-[var(--color-tertiary)] hover:underline"
              onclick={() => (showSchemaEditor = !showSchemaEditor)}
            >
              {showSchemaEditor ? "Collapse" : "Expand"}
            </button>
          </div>

          {#if showSchemaEditor}
            <textarea
              bind:value={customSchemaText}
              aria-label="JSON Schema editor"
              class="w-full h-32 rounded-lg bg-[var(--color-bg)] border border-[var(--color-outline-variant)]
                     px-3 py-2 text-xs font-mono text-[var(--color-text)]
                     focus:outline-none focus:border-[var(--color-tertiary)]/50 resize-none"
              placeholder={'{"type": "object", "properties": {...}}'}
              onblur={updateCustomSchema}
              {disabled}
            ></textarea>
            {#if schemaError}
              <p class="text-[10px] text-[var(--color-error)]">{schemaError}</p>
            {/if}
          {:else}
            <div
              class="rounded-lg bg-[var(--color-bg)] px-3 py-2 text-xs text-[var(--color-text-tertiary)]"
            >
              {config.schema?.name || "No schema defined"}
            </div>
          {/if}
        </div>
      {:else if config.selectedTool}
        <!-- Show selected tool info -->
        <div class="rounded-lg bg-[var(--color-bg)] p-2">
          <div class="flex items-center gap-2">
            <Check size={14} class="text-[var(--color-secondary)]" />
            <span class="text-xs font-medium text-[var(--color-text)]">{config.selectedTool}</span>
          </div>
          {#if config.schema?.description}
            <p class="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
              {config.schema.description}
            </p>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .field-label {
    display: block;
    font-size: 0.6875rem;
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  .animate-in {
    animation: slideIn 0.15s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
