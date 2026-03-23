<script lang="ts">
  import type { Demo } from "$lib/types";
  import { ChevronDown, Frown, Search, X } from "lucide-svelte";

  interface Props {
    demos: Record<string, Demo[]>;
    selectedId?: string;
    onSelect: (demo: Demo) => void;
    onScanRepo?: () => void;
  }

  let { demos, selectedId, onSelect, onScanRepo }: Props = $props();

  function getSourceLabel(demo: Demo): string {
    return demo.source === "discovered" ? "Auto" : "Config";
  }

  function getSourceTitle(demo: Demo): string {
    return demo.source === "discovered"
      ? "Auto-discovered from configured discovery paths"
      : "Defined in maivn_studio.json";
  }

  let searchQuery = $state("");
  let searchInput: HTMLInputElement;

  // Category collapse state - all expanded by default
  let collapsedCategories = $state<Set<string>>(new Set());

  function toggleCategory(category: string) {
    const next = new Set(collapsedCategories);
    if (next.has(category)) {
      next.delete(category);
    } else {
      next.add(category);
    }
    collapsedCategories = next;
  }

  // Determine if a demo uses swarm or agent (based on naming conventions in tags)
  function getExecutorType(demo: Demo): "swarm" | "agent" | null {
    const tagString = demo.tags.join(" ").toLowerCase();
    if (tagString.includes("swarm")) return "swarm";
    if (tagString.includes("agent")) return "agent";
    return null;
  }

  // Filter demos by search query
  const filteredDemos = $derived.by(() => {
    if (!searchQuery.trim()) return demos;

    const query = searchQuery.toLowerCase();
    const result: Record<string, Demo[]> = {};

    for (const [category, categoryDemos] of Object.entries(demos)) {
      const filtered = categoryDemos.filter(
        (demo) =>
          demo.name.toLowerCase().includes(query) ||
          demo.description?.toLowerCase().includes(query) ||
          demo.tags.some((tag) => tag.toLowerCase().includes(query)),
      );
      if (filtered.length > 0) {
        result[category] = filtered;
      }
    }

    return result;
  });

  // Total app count
  const totalCount = $derived(Object.values(demos).reduce((sum, arr) => sum + arr.length, 0));

  // Filtered count
  const filteredCount = $derived(
    Object.values(filteredDemos).reduce((sum, arr) => sum + arr.length, 0),
  );

  function clearSearch() {
    searchQuery = "";
    searchInput?.focus();
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      clearSearch();
    }
  }
</script>

<div class="flex h-full flex-col">
  <div
    class="shrink-0 border-b border-[var(--color-outline-variant)] bg-[linear-gradient(180deg,rgba(30,31,37,0.96),rgba(30,31,37,0.82))] p-3 backdrop-blur-md"
  >
    <div class="mb-2 flex items-center justify-between gap-2">
      <div>
        <div
          class="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-tertiary)]"
        >
          Demo Catalog
        </div>
        <div class="mt-1 text-sm font-medium text-[var(--color-text)]">
          Browse experiments and agents
        </div>
      </div>
      {#if onScanRepo}
        <button
          class="rounded-xl border border-[var(--color-tertiary)]/20 px-3 py-1.5 text-[11px] font-medium
                 bg-[var(--color-tertiary)]/12 text-[var(--color-tertiary)] shadow-[var(--shadow-sm)]
                 hover:bg-[var(--color-tertiary)]/20 transition-colors"
          onclick={onScanRepo}
        >
          Scan Repo
        </button>
      {/if}
    </div>

    <!-- Search Input -->
    <div class="relative">
      <Search
        size={16}
        class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]"
      />
      <input
        bind:this={searchInput}
        bind:value={searchQuery}
        type="text"
        placeholder="Search demos, tags, categories..."
        class="w-full rounded-xl border border-[var(--color-outline-variant)] bg-[var(--color-bg-secondary)]/88 py-2.5 pl-10 pr-8 text-sm
               placeholder-[var(--color-text-tertiary)] text-[var(--color-text)]
               focus:outline-none focus:border-[var(--color-tertiary)]/50
               focus:shadow-[var(--shadow-glow-tertiary)]
               transition-all duration-200"
        onkeydown={handleKeyDown}
      />
      {#if searchQuery}
        <button
          class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md
                 hover:bg-[var(--color-bg-tertiary)] transition-colors"
          onclick={clearSearch}
          title="Clear search"
        >
          <X size={16} class="text-[var(--color-text-tertiary)]" />
        </button>
      {/if}
    </div>

    <div
      class="mt-3 flex items-center justify-between gap-3 text-xs text-[var(--color-text-tertiary)]"
    >
      <span
        class="inline-flex items-center gap-2 rounded-full border border-[var(--color-outline-variant)] bg-[var(--color-bg-secondary)]/80 px-2.5 py-1"
      >
        {#if searchQuery}
          {filteredCount} of {totalCount} apps
        {:else}
          {totalCount} apps
        {/if}
      </span>
      <span class="hidden text-[11px] sm:inline"
        >Press <kbd
          class="rounded-md border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)] px-1.5 py-0.5"
          >Esc</kbd
        > to clear search</span
      >
      {#if searchQuery && filteredCount === 0}
        <button class="text-[var(--color-tertiary)] hover:underline" onclick={clearSearch}>
          Clear search
        </button>
      {/if}
    </div>
  </div>

  <!-- Demo List (scrollable) -->
  <div class="flex-1 min-h-0 overflow-y-auto">
    {#if Object.keys(filteredDemos).length === 0}
      <!-- Empty State -->
      <div class="flex h-full flex-col items-center justify-center p-6 text-center">
        <div
          class="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]"
        >
          <Frown size={24} class="text-[var(--color-text-tertiary)]" strokeWidth={1.5} />
        </div>
        <p class="text-sm font-medium text-[var(--color-text-secondary)]">No demos found</p>
        <p class="mt-1 text-xs text-[var(--color-text-tertiary)]">
          Try a different search term or rescan the repo.
        </p>
        <button
          class="mt-4 rounded-xl border border-[var(--color-tertiary)]/20 px-3 py-1.5 text-xs
                 bg-[var(--color-tertiary)]/12 text-[var(--color-tertiary)]
                 hover:bg-[var(--color-tertiary)]/20 transition-colors"
          onclick={clearSearch}
        >
          Clear search
        </button>
      </div>
    {:else}
      {#each Object.entries(filteredDemos) as [category, categoryDemos]}
        <div class="category-group">
          <button
            type="button"
            class="category-header"
            aria-expanded={!collapsedCategories.has(category)}
            onclick={() => toggleCategory(category)}
          >
            <div class="flex items-center gap-2">
              <ChevronDown
                size={14}
                class="category-chevron {collapsedCategories.has(category) ? 'collapsed' : ''}"
              />
              <span class="category-label">{category}</span>
            </div>
            <span class="category-count">{categoryDemos.length}</span>
          </button>

          {#if !collapsedCategories.has(category)}
            <ul class="demo-list animate-in">
              {#each categoryDemos as demo}
                {@const executorType = getExecutorType(demo)}
                {@const isSelected = selectedId === demo.id}
                <li>
                  <button
                    class="demo-item group w-full text-left transition-all duration-150"
                    class:selected={isSelected}
                    onclick={() => onSelect(demo)}
                  >
                    <div class="flex items-start gap-3">
                      {#if executorType}
                        <span
                          class="executor-badge mt-0.5 flex h-6 w-6 items-center justify-center rounded-md text-[10px] font-semibold shrink-0"
                          class:swarm={executorType === "swarm"}
                          class:agent={executorType === "agent"}
                          title={executorType === "swarm" ? "Uses Swarm" : "Uses Agent"}
                        >
                          {executorType === "swarm" ? "S" : "A"}
                        </span>
                      {/if}
                      <div class="min-w-0 flex-1">
                        <div class="flex items-start justify-between gap-2">
                          <span class="demo-title">
                            {demo.name}
                          </span>
                          <span
                            class="source-badge shrink-0"
                            class:configured={demo.source !== "discovered"}
                            class:discovered={demo.source === "discovered"}
                            title={getSourceTitle(demo)}
                          >
                            {getSourceLabel(demo)}
                          </span>
                        </div>

                        {#if demo.description}
                          <div class="demo-description">
                            {demo.description}
                          </div>
                        {/if}

                        {#if demo.tags.length > 0}
                          <div class="mt-1.5 flex flex-wrap items-center gap-1">
                            {#each demo.tags.slice(0, 3) as tag}
                              <span class="demo-tag">{tag}</span>
                            {/each}
                            {#if demo.tags.length > 3}
                              <span class="text-[10px] text-[var(--color-text-tertiary)]">
                                +{demo.tags.length - 3}
                              </span>
                            {/if}
                          </div>
                        {/if}
                      </div>
                    </div>
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .category-group {
    border-bottom: 1px solid var(--color-outline-variant);
  }

  .category-header {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.625rem 0.75rem;
    background: none;
    border: none;
    cursor: pointer;
    transition: background-color var(--transition-fast);
  }

  .category-header:hover {
    background: color-mix(in srgb, var(--color-bg-secondary) 72%, transparent);
  }

  .category-label {
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--color-text-secondary);
  }

  .category-count {
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--color-text-tertiary);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-full);
    padding: 0.125rem 0.375rem;
  }

  :global(.category-chevron) {
    color: var(--color-text-tertiary);
    transition: transform var(--transition-fast);
  }

  :global(.category-chevron.collapsed) {
    transform: rotate(-90deg);
  }

  .demo-list {
    padding: 0 0.5rem 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .demo-item {
    padding: 0.625rem 0.75rem;
    border-radius: var(--radius-lg);
    border: 1px solid transparent;
  }

  .demo-item:hover {
    background: color-mix(in srgb, var(--color-bg-tertiary) 70%, transparent);
    border-color: var(--color-outline-variant);
  }

  .demo-item.selected {
    background: color-mix(in srgb, var(--color-tertiary) 10%, var(--color-bg-secondary));
    border-color: color-mix(in srgb, var(--color-tertiary) 30%, var(--color-outline-variant));
  }

  .demo-title {
    font-size: 0.8125rem;
    font-weight: 600;
    line-height: 1.3;
    color: var(--color-text);
    word-break: break-word;
  }

  .demo-item:hover .demo-title,
  .demo-item.selected .demo-title {
    color: var(--color-tertiary);
  }

  .demo-description {
    margin-top: 0.25rem;
    font-size: 0.75rem;
    line-height: 1.5;
    color: var(--color-text-tertiary);
    display: -webkit-box;
    line-clamp: 2;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .demo-tag {
    font-size: 0.625rem;
    padding: 0.125rem 0.375rem;
    border-radius: var(--radius-full);
    border: 1px solid color-mix(in srgb, var(--color-outline-variant) 60%, transparent);
    color: var(--color-text-tertiary);
    background: color-mix(in srgb, var(--color-surface-variant) 30%, transparent);
  }

  .executor-badge.swarm {
    background-color: rgba(211, 188, 253, 0.15);
    color: var(--color-secondary);
  }

  .executor-badge.agent {
    background-color: rgba(177, 197, 255, 0.15);
    color: var(--color-primary);
  }

  .source-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 9999px;
    font-size: 0.5625rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    padding: 0.125rem 0.375rem;
    margin-top: 0.125rem;
  }

  .source-badge.configured {
    border: 1px solid color-mix(in srgb, var(--color-tertiary) 25%, var(--color-outline-variant));
    background: rgba(137, 208, 237, 0.12);
    color: var(--color-tertiary);
  }

  .source-badge.discovered {
    border: 1px solid color-mix(in srgb, var(--color-primary) 24%, var(--color-outline-variant));
    background: rgba(177, 197, 255, 0.12);
    color: var(--color-primary);
  }
</style>
