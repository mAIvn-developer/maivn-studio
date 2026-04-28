<script lang="ts">
  import type { BatchResultItem } from "$lib/types";
  import { AlertCircle, CheckCircle2, Circle, LoaderCircle, XCircle } from "lucide-svelte";
  import MarkdownContent from "../markdown/MarkdownContent.svelte";
  import BatchStructuredDiff from "./BatchStructuredDiff.svelte";
  import type { StructuredDiffColumn } from "./batch-structured-diff";

  interface Props {
    items: BatchResultItem[];
    richResultDisplay?: boolean;
  }

  let { items, richResultDisplay = true }: Props = $props();

  const sortedItems = $derived(
    items.filter(Boolean).toSorted((left, right) => left.index - right.index),
  );
  const diffColumns = $derived<StructuredDiffColumn[]>(
    sortedItems
      .filter((item) => item.result !== undefined && item.result !== null)
      .map((item) => ({
        id: String(item.index),
        label: `#${item.index + 1}`,
        value: item.result,
      })),
  );

  function itemResponse(item: BatchResultItem): string {
    return item.response || item.responses?.find((response) => response.trim()) || "";
  }

  function itemStatusLabel(item: BatchResultItem): string {
    if (item.status === "completed") return "Completed";
    if (item.status === "failed") return "Failed";
    return "Pending";
  }

  function itemTitle(item: BatchResultItem): string {
    return item.label || item.input || "Batch input";
  }
</script>

<div class="compare-view">
  <header class="compare-header">
    <div>
      <h3>Compare Batch Items</h3>
      <span>{sortedItems.length} selected</span>
    </div>
  </header>

  {#if sortedItems.length < 2}
    <div class="compare-empty">
      <AlertCircle size={16} />
      <span>Select at least two batch items to compare.</span>
    </div>
  {:else}
    <div class="response-grid" style={`--compare-count: ${Math.min(sortedItems.length, 3)}`}>
      {#each sortedItems as item (item.index)}
        <article class="response-pane" class:failed={item.status === "failed"}>
          <header class="response-header">
            <div class="status-line">
              <span class="item-status" class:failed={item.status === "failed"}>
                {#if item.status === "completed"}
                  <CheckCircle2 size={14} />
                {:else if item.status === "failed"}
                  <XCircle size={14} />
                {:else if item.status === "pending"}
                  <LoaderCircle size={14} class="spin" />
                {:else}
                  <Circle size={14} />
                {/if}
              </span>
              <span class="item-index">#{item.index + 1}</span>
              <span class="status-copy">{itemStatusLabel(item)}</span>
            </div>
            <h4>{itemTitle(item)}</h4>
            {#if item.label && item.input}
              <p>{item.input}</p>
            {/if}
          </header>

          <div class="response-body">
            {#if item.error}
              <div class="item-error">{item.error}</div>
            {:else if itemResponse(item)}
              <MarkdownContent content={itemResponse(item)} />
            {:else}
              <p class="pending-copy">Waiting for this batch item to finish.</p>
            {/if}
          </div>
        </article>
      {/each}
    </div>

    {#if richResultDisplay}
      <BatchStructuredDiff columns={diffColumns} />
    {/if}
  {/if}
</div>

<style>
  .compare-view {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }

  .compare-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .compare-header h3 {
    margin: 0;
    font-size: 0.8125rem;
    line-height: 1.2;
    font-weight: 700;
    color: var(--color-text);
  }

  .compare-header span {
    display: block;
    margin-top: 0.125rem;
    font-size: 0.6875rem;
    color: var(--color-text-tertiary);
  }

  .compare-empty {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    padding: 0.75rem 0.875rem;
    color: var(--color-text-tertiary);
    font-size: 0.75rem;
    background: color-mix(in srgb, var(--color-bg-tertiary) 42%, transparent);
  }

  .response-grid {
    display: grid;
    grid-template-columns: repeat(var(--compare-count), minmax(14rem, 1fr));
    gap: 0.75rem;
    overflow-x: auto;
    padding-bottom: 0.125rem;
  }

  .response-pane {
    min-width: 14rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-bg-tertiary) 50%, transparent);
    overflow: hidden;
  }

  .response-pane.failed {
    border-color: color-mix(in srgb, var(--color-error) 35%, var(--color-outline-variant));
  }

  .response-header {
    padding: 0.625rem 0.75rem;
    border-bottom: 1px solid var(--color-outline-variant);
    background: color-mix(in srgb, var(--color-bg-secondary) 70%, transparent);
  }

  .status-line {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    margin-bottom: 0.35rem;
    min-width: 0;
  }

  .item-status {
    display: inline-flex;
    color: var(--color-tertiary);
  }

  .item-status.failed,
  .item-error {
    color: var(--color-error);
  }

  .item-index {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.6875rem;
    color: var(--color-text-tertiary);
  }

  .status-copy {
    font-size: 0.6875rem;
    color: var(--color-text-tertiary);
  }

  .response-header h4 {
    margin: 0;
    max-width: 100%;
    overflow-wrap: anywhere;
    font-size: 0.75rem;
    line-height: 1.35;
    font-weight: 700;
    color: var(--color-text);
  }

  .response-header p {
    margin: 0.25rem 0 0;
    max-width: 100%;
    overflow-wrap: anywhere;
    font-size: 0.6875rem;
    line-height: 1.35;
    color: var(--color-text-tertiary);
  }

  .response-body {
    padding: 0.75rem;
    font-size: 0.8125rem;
    line-height: 1.55;
    color: var(--color-text-secondary);
  }

  .pending-copy {
    margin: 0;
    color: var(--color-text-tertiary);
  }

  :global(.spin) {
    animation: spin 0.9s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 760px) {
    .response-grid {
      grid-template-columns: 1fr;
      overflow-x: visible;
    }

    .response-pane {
      min-width: 0;
    }
  }
</style>
