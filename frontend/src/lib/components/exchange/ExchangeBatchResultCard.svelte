<script lang="ts">
  import type { BatchResult, BatchResultItem } from "$lib/types";
  import {
    CheckCircle2,
    ChevronLeft,
    ChevronRight,
    Circle,
    Columns3,
    Clock3,
    Layers3,
    LoaderCircle,
    XCircle,
  } from "lucide-svelte";
  import MarkdownContent from "../markdown/MarkdownContent.svelte";
  import { copyMessageCardStructuredOutput } from "../message/message-card-copy";
  import MessageCardStructuredOutput from "../message/MessageCardStructuredOutput.svelte";
  import BatchCompareView from "./BatchCompareView.svelte";

  type BatchViewMode = "single" | "compare";

  interface Props {
    batch: BatchResult;
    richResultDisplay?: boolean;
    showSessionDetails?: boolean;
  }

  let { batch, richResultDisplay = true, showSessionDetails = false }: Props = $props();
  let activeIndex = $state(0);
  let viewMode = $state<BatchViewMode>("single");
  let compareIndexes = $state<number[]>([]);
  let copiedStructuredIndex = $state<number | null>(null);
  let copiedStructuredTimeout: ReturnType<typeof setTimeout> | undefined;

  const completedCount = $derived(batch.items.filter((item) => item.status === "completed").length);
  const failedCount = $derived(batch.items.filter((item) => item.status === "failed").length);
  const pendingCount = $derived(batch.items.filter((item) => item.status === "pending").length);
  const sortedItems = $derived(
    batch.items.filter(Boolean).toSorted((left, right) => left.index - right.index),
  );
  const activeItem = $derived(
    sortedItems.find((item) => item.index === activeIndex) ?? sortedItems[0] ?? null,
  );
  const activeResponse = $derived(activeItem ? itemResponse(activeItem) : "");
  const selectedCompareItems = $derived(
    sortedItems.filter((item) => compareIndexes.includes(item.index)),
  );
  const activePosition = $derived(
    Math.max(
      0,
      sortedItems.findIndex((item) => item.index === activeItem?.index),
    ),
  );
  const canGoPrev = $derived(activePosition > 0);
  const canGoNext = $derived(activePosition < sortedItems.length - 1);

  $effect(() => {
    if (sortedItems.length === 0) {
      activeIndex = 0;
      return;
    }
    if (!sortedItems.some((item) => item.index === activeIndex)) {
      activeIndex = sortedItems[0].index;
    }
  });

  $effect(() => {
    const availableIndexes = new Set(sortedItems.map((item) => item.index));
    const nextIndexes = compareIndexes.filter((index) => availableIndexes.has(index));
    if (!sameIndexes(compareIndexes, nextIndexes)) {
      compareIndexes = nextIndexes;
    }
  });

  function formatDuration(ms?: number): string | null {
    if (typeof ms !== "number" || !Number.isFinite(ms)) return null;
    if (ms < 1000) return `${ms} ms`;
    return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`;
  }

  function itemResponse(item: BatchResultItem): string {
    return item.response || item.responses?.find((response) => response.trim()) || "";
  }

  function itemTitle(item: BatchResultItem): string {
    return item.label || item.input || "Batch input";
  }

  function sameIndexes(left: number[], right: number[]): boolean {
    return left.length === right.length && left.every((value, index) => value === right[index]);
  }

  function setViewMode(nextMode: BatchViewMode): void {
    if (nextMode === "compare") {
      ensureCompareSelection();
    }
    viewMode = nextMode;
  }

  function ensureCompareSelection(): void {
    if (compareIndexes.length >= 2 || sortedItems.length < 2) {
      return;
    }

    const seeded = [activeItem?.index, ...sortedItems.map((item) => item.index)].filter(
      (index, position, indexes): index is number =>
        typeof index === "number" && indexes.indexOf(index) === position,
    );
    compareIndexes = seeded.slice(0, 2);
  }

  function selectItem(index: number): void {
    activeIndex = index;
  }

  function toggleCompareIndex(index: number): void {
    compareIndexes = compareIndexes.includes(index)
      ? compareIndexes.filter((itemIndex) => itemIndex !== index)
      : [...compareIndexes, index].toSorted((left, right) => left - right);
  }

  function stepSelection(delta: -1 | 1): void {
    const next = sortedItems[activePosition + delta];
    if (next) {
      activeIndex = next.index;
    }
  }

  async function copyActiveStructuredOutput(): Promise<void> {
    if (!activeItem || activeItem.result === undefined || activeItem.result === null) {
      return;
    }

    const success = await copyMessageCardStructuredOutput(activeItem.result);
    if (!success) {
      return;
    }

    copiedStructuredIndex = activeItem.index;
    if (copiedStructuredTimeout) {
      clearTimeout(copiedStructuredTimeout);
    }
    copiedStructuredTimeout = setTimeout(() => {
      copiedStructuredIndex = null;
    }, 2000);
  }
</script>

<section class="batch-card" aria-label="Batch execution result">
  <header class="batch-header">
    <div class="batch-title-group">
      <div class="batch-icon-shell" class:failed={batch.status === "failed"}>
        {#if batch.status === "running"}
          <LoaderCircle size={16} class="spin" />
        {:else if batch.status === "failed"}
          <XCircle size={16} />
        {:else}
          <Layers3 size={16} />
        {/if}
      </div>
      <div class="batch-title-copy">
        <div class="batch-title-row">
          <span class="batch-title">{batch.mode === "abatch" ? "Async batch" : "Batch"}</span>
          <span class="batch-status" class:failed={batch.status === "failed"}>{batch.status}</span>
        </div>
        <div class="batch-meta">
          <span>{completedCount}/{batch.itemCount} complete</span>
          {#if failedCount > 0}
            <span>{failedCount} failed</span>
          {/if}
          {#if pendingCount > 0}
            <span>{pendingCount} pending</span>
          {/if}
          {#if batch.maxConcurrency}
            <span>Concurrency {batch.maxConcurrency}</span>
          {/if}
          {#if formatDuration(batch.duration_ms)}
            <span>{formatDuration(batch.duration_ms)}</span>
          {/if}
        </div>
      </div>
    </div>
  </header>

  {#if batch.error}
    <div class="batch-error">{batch.error}</div>
  {/if}

  <div class="batch-viewer">
    <div class="batch-switcher" role="tablist" aria-label="Batch inputs">
      <div class="batch-switcher-toolbar">
        <span>Items</span>
        <span>{selectedCompareItems.length} selected</span>
      </div>
      {#each sortedItems as item (item.index)}
        <div class="batch-tab-row">
          <label class="compare-check" title="Select for compare">
            <input
              type="checkbox"
              aria-label={`Select batch item ${item.index + 1} for compare`}
              checked={compareIndexes.includes(item.index)}
              onchange={() => toggleCompareIndex(item.index)}
            />
          </label>
          <button
            type="button"
            class="batch-tab"
            class:active={activeItem?.index === item.index}
            class:failed={item.status === "failed"}
            role="tab"
            aria-selected={activeItem?.index === item.index}
            onclick={() => selectItem(item.index)}
          >
            <span class="item-status" class:failed={item.status === "failed"}>
              {#if item.status === "completed"}
                <CheckCircle2 size={14} />
              {:else if item.status === "failed"}
                <XCircle size={14} />
              {:else if batch.status === "running"}
                <LoaderCircle size={14} class="spin" />
              {:else}
                <Circle size={14} />
              {/if}
            </span>
            <span class="item-index">#{item.index + 1}</span>
            <span class="item-input">{itemTitle(item)}</span>
          </button>
        </div>
      {/each}
    </div>

    <article class="batch-detail" aria-live={batch.status === "running" ? "polite" : "off"}>
      <div class="batch-detail-toolbar">
        <div class="view-toggle" aria-label="Batch result view mode">
          <button
            type="button"
            class:active={viewMode === "single"}
            onclick={() => setViewMode("single")}
          >
            Single
          </button>
          <button
            type="button"
            class:active={viewMode === "compare"}
            onclick={() => setViewMode("compare")}
          >
            <Columns3 size={13} />
            Compare
          </button>
        </div>
      </div>

      {#if viewMode === "compare"}
        <BatchCompareView items={selectedCompareItems} {richResultDisplay} />
      {:else if activeItem}
        <header class="detail-header">
          <div class="detail-title-group">
            <span class="item-status detail-status" class:failed={activeItem.status === "failed"}>
              {#if activeItem.status === "completed"}
                <CheckCircle2 size={15} />
              {:else if activeItem.status === "failed"}
                <XCircle size={15} />
              {:else if batch.status === "running"}
                <LoaderCircle size={15} class="spin" />
              {:else}
                <Circle size={15} />
              {/if}
            </span>
            <div class="detail-title-copy">
              <span class="detail-index">Batch {activePosition + 1} of {sortedItems.length}</span>
              <h3>{itemTitle(activeItem)}</h3>
              {#if activeItem.label && activeItem.input}
                <p>{activeItem.input}</p>
              {/if}
              {#if activeItem.variant || activeItem.model || activeItem.reasoning}
                <div class="detail-chips">
                  {#if activeItem.variant}
                    <span>{activeItem.variant}</span>
                  {/if}
                  {#if activeItem.model}
                    <span>{activeItem.model}</span>
                  {/if}
                  {#if activeItem.reasoning}
                    <span>{activeItem.reasoning}</span>
                  {/if}
                </div>
              {/if}
            </div>
          </div>

          <div class="detail-nav">
            <button
              type="button"
              aria-label="Previous batch input"
              title="Previous"
              disabled={!canGoPrev}
              onclick={() => stepSelection(-1)}
            >
              <ChevronLeft size={16} />
            </button>
            <button
              type="button"
              aria-label="Next batch input"
              title="Next"
              disabled={!canGoNext}
              onclick={() => stepSelection(1)}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </header>

        <div class="item-body">
          {#if activeItem.error}
            <div class="item-error">{activeItem.error}</div>
          {:else if activeResponse}
            <div class="item-response">
              <MarkdownContent content={activeResponse} />
            </div>
          {:else}
            <p class="pending-copy">Waiting for this batch input to finish.</p>
          {/if}

          {#if richResultDisplay && activeItem.result !== undefined && activeItem.result !== null}
            <div class="item-structured-result">
              <MessageCardStructuredOutput
                structuredOutput={activeItem.result}
                copiedStructured={copiedStructuredIndex === activeItem.index}
                onCopyStructuredOutput={copyActiveStructuredOutput}
              />
            </div>
          {/if}

          {#if showSessionDetails && activeItem.token_usage}
            <div class="item-stats">
              <Clock3 size={12} />
              <span>{activeItem.token_usage.total_tokens} tokens</span>
            </div>
          {/if}
        </div>
      {/if}
    </article>
  </div>
</section>

<style>
  .batch-card {
    width: min(90%, 64rem);
    margin-inline: auto;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-bg-secondary) 86%, transparent);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }

  .batch-header {
    padding: 0.875rem 1rem;
    border-bottom: 1px solid var(--color-outline-variant);
  }

  .batch-title-group {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    min-width: 0;
  }

  .batch-icon-shell {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.875rem;
    height: 1.875rem;
    border-radius: var(--radius-md);
    color: var(--color-tertiary);
    background: color-mix(in srgb, var(--color-tertiary) 16%, transparent);
    flex: 0 0 auto;
  }

  .batch-icon-shell.failed {
    color: var(--color-error);
    background: color-mix(in srgb, var(--color-error) 15%, transparent);
  }

  .batch-title-copy {
    min-width: 0;
    flex: 1;
  }

  .batch-title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
  }

  .batch-title {
    font-size: 0.875rem;
    font-weight: 700;
    color: var(--color-text);
  }

  .batch-status {
    border: 1px solid color-mix(in srgb, var(--color-tertiary) 42%, transparent);
    border-radius: var(--radius-full);
    padding: 0.1rem 0.45rem;
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--color-tertiary);
    background: color-mix(in srgb, var(--color-tertiary) 10%, transparent);
  }

  .batch-status.failed {
    border-color: color-mix(in srgb, var(--color-error) 42%, transparent);
    color: var(--color-error);
    background: color-mix(in srgb, var(--color-error) 10%, transparent);
  }

  .batch-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem 0.75rem;
    margin-top: 0.25rem;
    font-size: 0.6875rem;
    color: var(--color-text-tertiary);
  }

  .batch-error,
  .item-error {
    color: var(--color-error);
    font-size: 0.75rem;
    line-height: 1.4;
  }

  .batch-error {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--color-outline-variant);
    background: color-mix(in srgb, var(--color-error) 8%, transparent);
  }

  .batch-viewer {
    display: grid;
    grid-template-columns: minmax(12rem, 16rem) minmax(0, 1fr);
    min-height: 14rem;
  }

  .batch-switcher {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    max-height: 32rem;
    overflow: auto;
    border-right: 1px solid var(--color-outline-variant);
    padding: 0.625rem;
    background: color-mix(in srgb, var(--color-bg) 28%, transparent);
  }

  .batch-switcher-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.125rem 0.25rem 0.375rem;
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--color-text-tertiary);
  }

  .batch-tab-row {
    display: grid;
    grid-template-columns: 1rem minmax(0, 1fr);
    gap: 0.35rem;
    align-items: center;
  }

  .compare-check {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1rem;
    min-height: 1rem;
  }

  .compare-check input {
    width: 0.875rem;
    height: 0.875rem;
    accent-color: var(--color-tertiary);
  }

  .batch-tab {
    display: grid;
    grid-template-columns: 1rem 2.25rem minmax(0, 1fr);
    gap: 0.45rem;
    align-items: center;
    width: 100%;
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    padding: 0.5rem;
    background: transparent;
    color: var(--color-text-secondary);
    text-align: left;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast);
  }

  .batch-tab:hover {
    background: color-mix(in srgb, var(--color-surface-variant) 26%, transparent);
  }

  .batch-tab.active {
    border-color: color-mix(in srgb, var(--color-tertiary) 44%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-tertiary) 12%, transparent);
    color: var(--color-text);
  }

  .batch-tab.failed.active {
    border-color: color-mix(in srgb, var(--color-error) 44%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-error) 10%, transparent);
  }

  .batch-detail {
    min-width: 0;
    padding: 0.875rem 1rem 1rem;
  }

  .batch-detail-toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.75rem;
  }

  .view-toggle {
    display: inline-flex;
    gap: 0.125rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    padding: 0.125rem;
    background: color-mix(in srgb, var(--color-bg-tertiary) 55%, transparent);
  }

  .view-toggle button {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border: 0;
    border-radius: calc(var(--radius-md) - 2px);
    padding: 0.35rem 0.55rem;
    background: transparent;
    color: var(--color-text-tertiary);
    font-size: 0.6875rem;
    font-weight: 700;
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast);
  }

  .view-toggle button:hover {
    color: var(--color-text-secondary);
  }

  .view-toggle button.active {
    background: color-mix(in srgb, var(--color-tertiary) 18%, transparent);
    color: var(--color-tertiary);
  }

  .detail-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .detail-title-group {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    min-width: 0;
  }

  .detail-title-copy {
    min-width: 0;
  }

  .detail-index {
    display: block;
    margin-bottom: 0.125rem;
    font-size: 0.625rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: var(--color-text-tertiary);
  }

  .detail-title-copy h3 {
    margin: 0;
    max-width: 100%;
    overflow-wrap: anywhere;
    font-size: 0.8125rem;
    line-height: 1.35;
    font-weight: 700;
    color: var(--color-text);
  }

  .detail-title-copy p {
    margin: 0.2rem 0 0;
    max-width: 100%;
    overflow-wrap: anywhere;
    font-size: 0.75rem;
    line-height: 1.35;
    color: var(--color-text-tertiary);
  }

  .detail-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    margin-top: 0.35rem;
  }

  .detail-chips span {
    border-radius: var(--radius-full);
    padding: 0.1rem 0.4rem;
    font-size: 0.625rem;
    font-weight: 700;
    color: var(--color-text-tertiary);
    background: color-mix(in srgb, var(--color-bg-tertiary) 70%, transparent);
  }

  .detail-nav {
    display: inline-flex;
    gap: 0.25rem;
    flex: 0 0 auto;
  }

  .detail-nav button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.875rem;
    height: 1.875rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-tertiary) 55%, transparent);
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      opacity var(--transition-fast);
  }

  .detail-nav button:hover:not(:disabled) {
    border-color: color-mix(in srgb, var(--color-tertiary) 44%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-tertiary) 12%, transparent);
  }

  .detail-nav button:disabled {
    cursor: not-allowed;
    opacity: 0.42;
  }

  .item-status {
    display: inline-flex;
    align-items: center;
    color: var(--color-tertiary);
  }

  .item-status.failed {
    color: var(--color-error);
  }

  .detail-status {
    margin-top: 0.0625rem;
  }

  .item-index {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.6875rem;
    color: var(--color-text-tertiary);
  }

  .item-input {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .item-body {
    font-size: 0.8125rem;
    line-height: 1.55;
    color: var(--color-text-secondary);
  }

  .item-body p {
    margin: 0;
    white-space: pre-wrap;
  }

  .pending-copy {
    color: var(--color-text-tertiary);
  }

  .item-structured-result {
    margin-top: 0.75rem;
    overflow: hidden;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
  }

  .item-stats {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    margin-top: 0.5rem;
    font-size: 0.6875rem;
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

  @media (max-width: 640px) {
    .batch-card {
      width: 100%;
    }

    .batch-viewer {
      grid-template-columns: 1fr;
    }

    .batch-switcher {
      flex-direction: row;
      border-right: 0;
      border-bottom: 1px solid var(--color-outline-variant);
      overflow-x: auto;
    }

    .batch-tab {
      min-width: 12rem;
    }

    .batch-tab-row {
      grid-template-columns: 1rem 12rem;
      flex: 0 0 auto;
    }
  }
</style>
