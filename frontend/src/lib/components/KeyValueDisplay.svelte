<script lang="ts">
  import { ChevronRight } from "lucide-svelte";
  // Self-import for recursive rendering
  import KeyValueDisplay from "./KeyValueDisplay.svelte";
  import {
    highlightPrivateData,
    containsPrivateDataPlaceholders,
  } from "./markdown/markdown-parser";

  interface Props {
    data: unknown;
    depth?: number;
    maxDepth?: number;
    initialExpanded?: boolean;
    label?: string;
  }

  let { data, depth = 0, maxDepth = 12, initialExpanded = true, label }: Props = $props();

  // Max characters before a primitive string value is truncated in the full view.
  const STRING_TRUNCATE_LENGTH = 200;
  // Max characters per string item inside the collapsed-array preview.
  const PREVIEW_STRING_LENGTH = 20;

  // Compute initial expanded state based on props
  let expanded = $state(false);

  $effect(() => {
    expanded = initialExpanded && depth < 2;
  });

  function toggleExpanded() {
    expanded = !expanded;
  }

  // Determine the type of data for rendering
  type DataType = "null" | "undefined" | "string" | "number" | "boolean" | "array" | "object";

  function getDataType(value: unknown): DataType {
    if (value === null) return "null";
    if (value === undefined) return "undefined";
    if (Array.isArray(value)) return "array";
    return typeof value as DataType;
  }

  const dataType = $derived(getDataType(data));
  const isExpandable = $derived(dataType === "object" || dataType === "array");

  // Get entries for objects/arrays
  const entries = $derived(() => {
    if (dataType === "array") {
      return (data as unknown[]).map((value, index) => ({
        key: String(index),
        value,
        isIndex: true,
      }));
    }
    if (dataType === "object" && data !== null) {
      return Object.entries(data as Record<string, unknown>).map(([key, value]) => ({
        key,
        value,
        isIndex: false,
      }));
    }
    return [];
  });

  const entryCount = $derived(entries().length);

  // Format primitive values for display
  function formatPrimitive(value: unknown): string {
    if (value === null) return "null";
    if (value === undefined) return "undefined";
    if (typeof value === "string") {
      // Truncate long strings
      if (value.length > STRING_TRUNCATE_LENGTH) {
        return `"${value.slice(0, STRING_TRUNCATE_LENGTH)}..."`;
      }
      return `"${value}"`;
    }
    if (typeof value === "boolean") return value ? "true" : "false";
    if (typeof value === "number") return String(value);
    return String(value);
  }

  // Get a preview for collapsed expandable items
  function getPreview(): string {
    if (dataType === "array") {
      const arr = data as unknown[];
      if (arr.length === 0) return "[]";
      if (arr.length <= 3) {
        const preview = arr
          .map((v) => {
            const t = getDataType(v);
            if (t === "object") return "{...}";
            if (t === "array") return "[...]";
            if (t === "string") {
              const s = v as string;
              return s.length > PREVIEW_STRING_LENGTH
                ? `"${s.slice(0, PREVIEW_STRING_LENGTH)}..."`
                : `"${s}"`;
            }
            return String(v);
          })
          .join(", ");
        return `[${preview}]`;
      }
      return `[${arr.length} items]`;
    }
    if (dataType === "object" && data !== null) {
      const obj = data as Record<string, unknown>;
      const keys = Object.keys(obj);
      if (keys.length === 0) return "{}";
      if (keys.length <= 3) {
        return `{${keys.join(", ")}}`;
      }
      return `{${keys.length} keys}`;
    }
    return "";
  }

  // Type-based styling
  const typeColors: Record<DataType, string> = {
    null: "text-[var(--color-text-tertiary)]",
    undefined: "text-[var(--color-text-tertiary)]",
    string: "text-[var(--color-success)]",
    number: "text-[var(--color-primary)]",
    boolean: "text-[var(--color-warning)]",
    array: "text-[var(--color-secondary)]",
    object: "text-[var(--color-secondary)]",
  };
</script>

{#if depth >= maxDepth}
  <!-- Max depth reached - show collapsed preview with label -->
  <div class="flex items-baseline gap-2 text-sm">
    {#if label}
      <span class="text-[var(--color-text-secondary)] font-medium shrink-0">{label}</span>
      <span class="text-[var(--color-text-tertiary)]">:</span>
    {/if}
    <span class="text-xs text-[var(--color-text-tertiary)] font-mono">
      {getPreview() || formatPrimitive(data)}
    </span>
  </div>
{:else if isExpandable}
  <!-- Expandable object or array -->
  <div class="kv-expandable" style="--depth: {depth}">
    <button
      type="button"
      class="kv-header flex items-center gap-1.5 text-left w-full py-0.5
             hover:bg-[var(--color-bg-tertiary)]/50 rounded transition-colors"
      onclick={toggleExpanded}
    >
      <!-- Expand/collapse chevron -->
      <ChevronRight
        size={14}
        class="text-[var(--color-text-tertiary)] transition-transform duration-150 shrink-0 {expanded
          ? 'rotate-90'
          : ''}"
      />

      <!-- Label (key name) if provided -->
      {#if label}
        <span class="text-[var(--color-text-secondary)] font-medium text-sm shrink-0">{label}</span>
        <span class="text-[var(--color-text-tertiary)]">:</span>
      {/if}

      <!-- Type badge -->
      <span
        class="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0
               {dataType === 'array'
          ? 'bg-[var(--color-secondary)]/15 text-[var(--color-secondary)]'
          : 'bg-[var(--color-primary)]/15 text-[var(--color-primary)]'}"
      >
        {dataType === "array" ? `Array(${entryCount})` : `Object(${entryCount})`}
      </span>

      <!-- Preview when collapsed -->
      {#if !expanded}
        <span class="text-xs text-[var(--color-text-tertiary)] font-mono truncate">
          {getPreview()}
        </span>
      {/if}
    </button>

    <!-- Expanded content -->
    {#if expanded}
      <div class="kv-content ml-4 pl-3 border-l border-[var(--color-outline-variant)]/50">
        {#each entries() as entry (entry.key)}
          <div class="kv-entry py-0.5">
            {#if getDataType(entry.value) === "object" || getDataType(entry.value) === "array"}
              <!-- Nested expandable -->
              <KeyValueDisplay
                data={entry.value}
                depth={depth + 1}
                {maxDepth}
                initialExpanded={depth < 1}
                label={entry.isIndex ? `[${entry.key}]` : entry.key}
              />
            {:else}
              <!-- Primitive value -->
              <div class="flex items-baseline gap-2 text-sm">
                <span class="text-[var(--color-text-secondary)] font-medium shrink-0">
                  {entry.isIndex ? `[${entry.key}]` : entry.key}
                </span>
                <span class="text-[var(--color-text-tertiary)]">:</span>
                {#if containsPrivateDataPlaceholders(formatPrimitive(entry.value))}
                  <!-- eslint-disable svelte/no-at-html-tags -->
                  <span class="font-mono break-all"
                    >{@html highlightPrivateData(formatPrimitive(entry.value))}</span
                  >
                  <!-- eslint-enable svelte/no-at-html-tags -->
                {:else}
                  <span class="font-mono break-all {typeColors[getDataType(entry.value)]}"
                    >{formatPrimitive(entry.value)}</span
                  >
                {/if}
              </div>
            {/if}
          </div>
        {/each}

        {#if entryCount === 0}
          <span class="text-xs text-[var(--color-text-tertiary)] italic">
            {dataType === "array" ? "empty array" : "empty object"}
          </span>
        {/if}
      </div>
    {/if}
  </div>
{:else}
  <!-- Primitive value at root -->
  <div class="flex items-baseline gap-2 text-sm">
    {#if label}
      <span class="text-[var(--color-text-secondary)] font-medium shrink-0">{label}</span>
      <span class="text-[var(--color-text-tertiary)]">:</span>
    {/if}
    <span class="font-mono break-all {typeColors[dataType]}">
      {formatPrimitive(data)}
    </span>
  </div>
{/if}

<style>
  .kv-expandable {
    font-size: 0.875rem;
  }

  .kv-content {
    animation: kv-expand 0.15s ease-out;
  }

  @keyframes kv-expand {
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
