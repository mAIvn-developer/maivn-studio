<script lang="ts">
  import type { PhaseChipData } from "$lib/types";
  import { BrainCircuit, ChevronDown, Shield } from "lucide-svelte";
  import KeyValueDisplay from "../KeyValueDisplay.svelte";

  interface Props {
    phaseChip: PhaseChipData;
    isLive?: boolean;
  }

  let { phaseChip, isLive = false }: Props = $props();
  let expanded = $state(false);

  const memoryDetails = $derived(phaseChip.memory);
  const redactionDetails = $derived(phaseChip.redaction);
  const isRedactionActivity = $derived(redactionDetails !== undefined);

  function toggleExpanded() {
    expanded = !expanded;
  }

  function formatBadgeValue(value: string | number): string {
    if (typeof value === "number") {
      return value.toLocaleString();
    }
    return value;
  }

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }

  // Compact inline summary for the collapsed header (e.g., "retrieve - 2 hits - 3492ms")
  const inlineSummary = $derived.by(() => {
    const redaction = redactionDetails;
    if (redaction) {
      const parts: string[] = [];
      if (redaction.insertedKeys?.length) parts.push(`${redaction.insertedKeys.length} keys`);
      if (redaction.redactedMessageCount !== undefined) {
        parts.push(`${redaction.redactedMessageCount} messages`);
      }
      if (redaction.redactedValueCount !== undefined) {
        parts.push(`${redaction.redactedValueCount} values`);
      }
      return parts.join(" \u00b7 ");
    }

    const details = memoryDetails;
    if (!details) return "";
    const parts: string[] = [];
    if (details.mode) parts.push(details.mode);
    if (details.hitCount !== undefined) parts.push(`${details.hitCount} hits`);
    if (details.skillCount !== undefined) parts.push(`${details.skillCount} skills`);
    if (details.insightCount !== undefined) parts.push(`${details.insightCount} insights`);
    if (details.resourceCount !== undefined) parts.push(`${details.resourceCount} resources`);
    if (details.latencyMs !== undefined) parts.push(`${details.latencyMs}ms`);
    return parts.join(" \u00b7 ");
  });

  const detailEntries = $derived.by(() => {
    const redaction = redactionDetails;
    if (redaction) {
      const entries: Array<{ label: string; value: string | number }> = [];
      if (redaction.redactedMessageCount !== undefined) {
        entries.push({ label: "Messages", value: redaction.redactedMessageCount });
      }
      if (redaction.redactedValueCount !== undefined) {
        entries.push({ label: "Values", value: redaction.redactedValueCount });
      }
      if (redaction.insertedKeys?.length) {
        entries.push({ label: "Inserted Keys", value: redaction.insertedKeys.length });
      }
      if (redaction.matchedKnownPiiValues?.length) {
        entries.push({ label: "Matched Known PII", value: redaction.matchedKnownPiiValues.length });
      }
      if (redaction.unmatchedKnownPiiValues?.length) {
        entries.push({
          label: "Unmatched Known PII",
          value: redaction.unmatchedKnownPiiValues.length,
        });
      }
      return entries;
    }

    const details = memoryDetails;
    if (!details) return [];

    const entries: Array<{ label: string; value: string | number }> = [];
    if (details.mode) entries.push({ label: "Mode", value: details.mode });
    if (details.memoryLevel) entries.push({ label: "Level", value: details.memoryLevel });
    if (details.policyMode) entries.push({ label: "Policy", value: details.policyMode });
    if (details.hitCount !== undefined) entries.push({ label: "Hits", value: details.hitCount });
    if (details.vectorHits !== undefined) {
      entries.push({ label: "Vector Hits", value: details.vectorHits });
    }
    if (details.keywordHits !== undefined) {
      entries.push({ label: "Keyword Hits", value: details.keywordHits });
    }
    if (details.graphHits !== undefined) {
      entries.push({ label: "Graph Hits", value: details.graphHits });
    }
    if (details.skillCount !== undefined) {
      entries.push({ label: "Skills", value: details.skillCount });
    }
    if (details.insightCount !== undefined) {
      entries.push({ label: "Insights", value: details.insightCount });
    }
    if (details.resourceCount !== undefined) {
      entries.push({ label: "Resources", value: details.resourceCount });
    }
    if (details.vectorRows !== undefined) {
      entries.push({ label: "Vector Rows", value: details.vectorRows });
    }
    if (details.graphEdges !== undefined) {
      entries.push({ label: "Graph Edges", value: details.graphEdges });
    }
    if (details.traceEventCount !== undefined) {
      entries.push({ label: "Trace Events", value: details.traceEventCount });
    }
    if (details.latencyMs !== undefined) {
      entries.push({ label: "Latency", value: `${details.latencyMs} ms` });
    }
    if (details.registeredCount !== undefined) {
      entries.push({ label: "Registered", value: details.registeredCount });
    }
    if (details.reusedCount !== undefined) {
      entries.push({ label: "Reused", value: details.reusedCount });
    }
    if (details.skippedCount !== undefined) {
      entries.push({ label: "Skipped", value: details.skippedCount });
    }
    if (details.totalBytes !== undefined) {
      entries.push({ label: "Total Bytes", value: formatBytes(details.totalBytes) });
    }
    if (details.dedupReusedCount !== undefined) {
      entries.push({ label: "Dedup Reused", value: details.dedupReusedCount });
    }
    if (details.versionSupersededCount !== undefined) {
      entries.push({ label: "Superseded", value: details.versionSupersededCount });
    }
    if (details.discoveryCount !== undefined) {
      entries.push({ label: "Discovery", value: details.discoveryCount });
    }
    if (details.selectedCount !== undefined) {
      entries.push({ label: "Selected", value: details.selectedCount });
    }
    if (details.chunkCount !== undefined) {
      entries.push({ label: "Chunks", value: details.chunkCount });
    }
    if (details.requestedMaxResources !== undefined) {
      entries.push({ label: "Requested Max", value: details.requestedMaxResources });
    }
    if (details.requiredTagCount !== undefined) {
      entries.push({ label: "Required Tags", value: details.requiredTagCount });
    }
    if (details.fullExtraction !== undefined) {
      entries.push({ label: "Full Extraction", value: details.fullExtraction ? "Yes" : "No" });
    }
    if (details.requestedResourceId) {
      entries.push({ label: "Requested Resource", value: details.requestedResourceId });
    }
    return entries;
  });

  const discoveredResourceIds = $derived(memoryDetails?.resourceIds ?? []);
  const supersededResourceIds = $derived(memoryDetails?.supersededResourceIds ?? []);
  const insertedKeys = $derived(redactionDetails?.insertedKeys ?? []);
  const matchedKnownPiiValues = $derived(redactionDetails?.matchedKnownPiiValues ?? []);
  const unmatchedKnownPiiValues = $derived(redactionDetails?.unmatchedKnownPiiValues ?? []);
  const addedPrivateData = $derived(redactionDetails?.addedPrivateData);
  const mergedPrivateData = $derived(redactionDetails?.mergedPrivateData);
</script>

<section
  class="memory-activity-panel rounded-lg border {isRedactionActivity
    ? 'border-[var(--color-warning)]/20 bg-[var(--color-warning)]/8'
    : 'border-[var(--color-tertiary)]/20 bg-[var(--color-tertiary)]/8'}"
>
  <button
    type="button"
    class="w-full px-2.5 py-1.5 flex items-center gap-2 text-left"
    onclick={toggleExpanded}
    aria-expanded={expanded}
  >
    <div
      class="w-5 h-5 rounded-md flex items-center justify-center shrink-0 {isRedactionActivity
        ? 'bg-[var(--color-warning)]/18'
        : 'bg-[var(--color-tertiary)]/18'}"
    >
      {#if isRedactionActivity}
        <Shield size={12} class="text-[var(--color-warning)]" />
      {:else}
        <BrainCircuit size={12} class="text-[var(--color-tertiary)]" />
      {/if}
    </div>
    <div class="min-w-0 flex-1">
      {#if expanded}
        <div
          class="text-[10px] font-semibold uppercase tracking-wide {isRedactionActivity
            ? 'text-[var(--color-warning)]'
            : 'text-[var(--color-tertiary)]'}"
        >
          {isRedactionActivity ? "Redaction Activity" : "Memory Activity"}
        </div>
        <div class="text-xs text-[var(--color-text-secondary)] truncate">{phaseChip.message}</div>
      {:else}
        <div class="text-[11px] text-[var(--color-text-secondary)] truncate">
          {inlineSummary || phaseChip.message}
        </div>
      {/if}
    </div>
    <div class="flex items-center gap-1.5 shrink-0">
      {#if isLive}
        <span
          class="inline-flex items-center gap-1 text-[9px] {isRedactionActivity
            ? 'text-[var(--color-warning)]'
            : 'text-[var(--color-tertiary)]'}"
        >
          <span
            class="h-1.5 w-1.5 rounded-full animate-pulse {isRedactionActivity
              ? 'bg-[var(--color-warning)]'
              : 'bg-[var(--color-tertiary)]'}"
          ></span>
          Live
        </span>
      {/if}
      <ChevronDown
        size={14}
        class="text-[var(--color-text-tertiary)] transition-transform duration-200 {expanded
          ? 'rotate-180'
          : ''}"
      />
    </div>
  </button>

  {#if expanded}
    <div class="px-2.5 pb-2">
      {#if detailEntries.length > 0}
        <div class="grid grid-cols-3 gap-1.5">
          {#each detailEntries as entry (entry.label)}
            <div
              class="rounded-md border border-[var(--color-outline-variant)]/60 bg-[var(--color-bg-secondary)] px-2 py-1.5"
            >
              <div class="text-[9px] uppercase tracking-wide text-[var(--color-text-tertiary)]">
                {entry.label}
              </div>
              <div class="text-[11px] font-medium text-[var(--color-text)] mt-0.5 truncate">
                {formatBadgeValue(entry.value)}
              </div>
            </div>
          {/each}
        </div>
      {/if}

      {#if insertedKeys.length > 0 || matchedKnownPiiValues.length > 0 || unmatchedKnownPiiValues.length > 0}
        <div class="mt-2 space-y-1.5">
          {#if insertedKeys.length > 0}
            <div>
              <div
                class="text-[9px] uppercase tracking-wide text-[var(--color-text-tertiary)] mb-0.5"
              >
                Inserted Keys
              </div>
              <div class="flex flex-wrap gap-1">
                {#each insertedKeys as insertedKey (insertedKey)}
                  <code
                    class="rounded-md border border-[var(--color-outline-variant)]/70 bg-[var(--color-bg-secondary)] px-1.5 py-0.5 text-[9px] text-[var(--color-text-secondary)]"
                  >
                    {insertedKey}
                  </code>
                {/each}
              </div>
            </div>
          {/if}

          {#if matchedKnownPiiValues.length > 0}
            <div>
              <div
                class="text-[9px] uppercase tracking-wide text-[var(--color-text-tertiary)] mb-0.5"
              >
                Matched Known PII
              </div>
              <div class="flex flex-wrap gap-1">
                {#each matchedKnownPiiValues as value (value)}
                  <code
                    class="rounded-md border border-[var(--color-outline-variant)]/70 bg-[var(--color-bg-secondary)] px-1.5 py-0.5 text-[9px] text-[var(--color-text-secondary)]"
                  >
                    {value}
                  </code>
                {/each}
              </div>
            </div>
          {/if}

          {#if unmatchedKnownPiiValues.length > 0}
            <div>
              <div
                class="text-[9px] uppercase tracking-wide text-[var(--color-text-tertiary)] mb-0.5"
              >
                Unmatched Known PII
              </div>
              <div class="flex flex-wrap gap-1">
                {#each unmatchedKnownPiiValues as value (value)}
                  <code
                    class="rounded-md border border-[var(--color-outline-variant)]/70 bg-[var(--color-bg-secondary)] px-1.5 py-0.5 text-[9px] text-[var(--color-text-secondary)]"
                  >
                    {value}
                  </code>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      {/if}

      {#if discoveredResourceIds.length > 0 || supersededResourceIds.length > 0}
        <div class="mt-2 space-y-1.5">
          {#if discoveredResourceIds.length > 0}
            <div>
              <div
                class="text-[9px] uppercase tracking-wide text-[var(--color-text-tertiary)] mb-0.5"
              >
                Resource IDs
              </div>
              <div class="flex flex-wrap gap-1">
                {#each discoveredResourceIds as resourceId (resourceId)}
                  <code
                    class="rounded-md border border-[var(--color-outline-variant)]/70 bg-[var(--color-bg-secondary)]
                         px-1.5 py-0.5 text-[9px] text-[var(--color-text-secondary)]"
                  >
                    {resourceId}
                  </code>
                {/each}
              </div>
            </div>
          {/if}

          {#if supersededResourceIds.length > 0}
            <div>
              <div
                class="text-[9px] uppercase tracking-wide text-[var(--color-text-tertiary)] mb-0.5"
              >
                Superseded IDs
              </div>
              <div class="flex flex-wrap gap-1">
                {#each supersededResourceIds as resourceId (resourceId)}
                  <code
                    class="rounded-md border border-[var(--color-outline-variant)]/70 bg-[var(--color-bg-secondary)]
                         px-1.5 py-0.5 text-[9px] text-[var(--color-text-secondary)]"
                  >
                    {resourceId}
                  </code>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      {/if}

      {#if addedPrivateData}
        <div class="mt-2">
          <div class="text-[9px] uppercase tracking-wide text-[var(--color-text-tertiary)] mb-0.5">
            Added Private Data
          </div>
          <div
            class="rounded-md border border-[var(--color-outline-variant)]/60 bg-[var(--color-bg-secondary)] px-2 py-1.5"
          >
            <KeyValueDisplay data={addedPrivateData} initialExpanded={false} maxDepth={6} />
          </div>
        </div>
      {/if}

      {#if mergedPrivateData}
        <div class="mt-2">
          <div class="text-[9px] uppercase tracking-wide text-[var(--color-text-tertiary)] mb-0.5">
            Merged Private Data
          </div>
          <div
            class="rounded-md border border-[var(--color-outline-variant)]/60 bg-[var(--color-bg-secondary)] px-2 py-1.5"
          >
            <KeyValueDisplay data={mergedPrivateData} initialExpanded={false} maxDepth={6} />
          </div>
        </div>
      {/if}

      {#if detailEntries.length === 0 && discoveredResourceIds.length === 0 && supersededResourceIds.length === 0 && insertedKeys.length === 0 && matchedKnownPiiValues.length === 0 && unmatchedKnownPiiValues.length === 0 && !addedPrivateData && !mergedPrivateData}
        <div class="text-xs text-[var(--color-text-tertiary)] mt-2">
          {isRedactionActivity
            ? "No redaction metrics available yet."
            : "No memory metrics available yet."}
        </div>
      {/if}
    </div>
  {/if}
</section>
