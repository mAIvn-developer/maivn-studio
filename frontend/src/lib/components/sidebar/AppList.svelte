<script lang="ts">
  import type { App } from "$lib/types";
  import { ChevronDown, Frown, Search, X } from "lucide-svelte";

  interface Props {
    apps: Record<string, App[]>;
    selectedId?: string;
    onSelect: (app: App) => void;
    onScanRepo?: () => void;
  }

  let { apps, selectedId, onSelect, onScanRepo }: Props = $props();

  function getSourceLabel(app: App): string {
    return app.source === "discovered" ? "Auto" : "Config";
  }

  function getSourceTitle(app: App): string {
    return app.source === "discovered"
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

  // Determine if an app uses swarm or agent (based on naming conventions in tags)
  function getExecutorType(app: App): "swarm" | "agent" | null {
    const tagString = app.tags.join(" ").toLowerCase();
    if (tagString.includes("swarm")) return "swarm";
    if (tagString.includes("agent")) return "agent";
    return null;
  }

  // Filter apps by search query
  const filteredApps = $derived.by(() => {
    if (!searchQuery.trim()) return apps;

    const query = searchQuery.toLowerCase();
    const result: Record<string, App[]> = {};

    for (const [category, categoryApps] of Object.entries(apps)) {
      const filtered = categoryApps.filter(
        (app) =>
          app.name.toLowerCase().includes(query) ||
          app.description?.toLowerCase().includes(query) ||
          app.tags.some((tag) => tag.toLowerCase().includes(query)),
      );
      if (filtered.length > 0) {
        result[category] = filtered;
      }
    }

    return result;
  });

  // Total app count
  const totalCount = $derived(Object.values(apps).reduce((sum, arr) => sum + arr.length, 0));

  // Filtered count
  const filteredCount = $derived(
    Object.values(filteredApps).reduce((sum, arr) => sum + arr.length, 0),
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
    class="app-catalog-header shrink-0 border-b border-[var(--color-outline-variant)] p-3 backdrop-blur-md"
  >
    <div class="mb-2 flex items-center justify-between gap-2">
      <div>
        <div
          class="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-tertiary)]"
        >
          App Catalog
        </div>
        <div class="mt-1 text-sm font-medium text-[var(--color-text)]">
          Browse experiments and agents
        </div>
      </div>
      {#if onScanRepo}
        <button
          class="rounded-xl border border-[var(--color-secondary)]/20 px-3 py-1.5 text-[11px] font-medium
                 bg-[var(--color-secondary)]/12 text-[var(--color-secondary)] shadow-[var(--shadow-sm)]
                 hover:bg-[var(--color-secondary)]/20 transition-colors"
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
        placeholder="Search apps, tags, categories..."
        class="w-full rounded-xl border border-[var(--color-outline-variant)] bg-[var(--color-bg-secondary)]/88 py-2.5 pl-10 pr-8 text-sm
               placeholder-[var(--color-text-tertiary)] text-[var(--color-text)]
               focus:outline-none focus:border-[var(--color-secondary)]/50
               focus:shadow-[var(--shadow-glow-secondary)]
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
        <button class="text-[var(--color-secondary)] hover:underline" onclick={clearSearch}>
          Clear search
        </button>
      {/if}
    </div>
  </div>

  <!-- App List (scrollable) -->
  <div class="flex-1 min-h-0 overflow-y-auto">
    {#if Object.keys(filteredApps).length === 0}
      <!-- Empty State -->
      <div class="flex h-full flex-col items-center justify-center p-6 text-center">
        <div
          class="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]"
        >
          <Frown size={24} class="text-[var(--color-text-tertiary)]" strokeWidth={1.5} />
        </div>
        <p class="text-sm font-medium text-[var(--color-text-secondary)]">No apps found</p>
        <p class="mt-1 text-xs text-[var(--color-text-tertiary)]">
          Try a different search term or rescan the repo.
        </p>
        <button
          class="mt-4 rounded-xl border border-[var(--color-secondary)]/20 px-3 py-1.5 text-xs
                 bg-[var(--color-secondary)]/12 text-[var(--color-secondary)]
                 hover:bg-[var(--color-secondary)]/20 transition-colors"
          onclick={clearSearch}
        >
          Clear search
        </button>
      </div>
    {:else}
      {#each Object.entries(filteredApps) as [category, categoryApps]}
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
            <span class="category-count">{categoryApps.length}</span>
          </button>

          {#if !collapsedCategories.has(category)}
            <ul class="app-list animate-in">
              {#each categoryApps as app}
                {@const executorType = getExecutorType(app)}
                {@const isSelected = selectedId === app.id}
                <li>
                  <button
                    class="app-item group w-full text-left transition-all duration-150"
                    class:selected={isSelected}
                    onclick={() => onSelect(app)}
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
                          <span class="app-title">
                            {app.name}
                          </span>
                          <span
                            class="source-badge shrink-0"
                            class:configured={app.source !== "discovered"}
                            class:discovered={app.source === "discovered"}
                            title={getSourceTitle(app)}
                          >
                            {getSourceLabel(app)}
                          </span>
                        </div>

                        {#if app.description}
                          <div class="app-description">
                            {app.description}
                          </div>
                        {/if}

                        {#if app.tags.length > 0}
                          <div class="mt-1.5 flex flex-wrap items-center gap-1">
                            {#each app.tags.slice(0, 3) as tag}
                              <span class="app-tag">{tag}</span>
                            {/each}
                            {#if app.tags.length > 3}
                              <span class="text-[10px] text-[var(--color-text-tertiary)]">
                                +{app.tags.length - 3}
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
  .app-catalog-header {
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--color-bg-secondary) 96%, transparent),
      color-mix(in srgb, var(--color-bg-secondary) 82%, transparent)
    );
  }

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

  .app-list {
    padding: 0 0.5rem 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .app-item {
    padding: 0.625rem 0.75rem;
    border-radius: var(--radius-lg);
    border: 1px solid transparent;
  }

  .app-item:hover {
    background: color-mix(in srgb, var(--color-bg-tertiary) 70%, transparent);
    border-color: var(--color-outline-variant);
  }

  .app-item.selected {
    background: color-mix(in srgb, var(--color-secondary) 10%, var(--color-bg-secondary));
    border-color: color-mix(in srgb, var(--color-secondary) 30%, var(--color-outline-variant));
  }

  .app-title {
    font-size: 0.8125rem;
    font-weight: 600;
    line-height: 1.3;
    color: var(--color-text);
    word-break: break-word;
  }

  .app-item:hover .app-title,
  .app-item.selected .app-title {
    color: var(--color-secondary);
  }

  .app-description {
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

  .app-tag {
    font-size: 0.625rem;
    padding: 0.125rem 0.375rem;
    border-radius: var(--radius-full);
    border: 1px solid color-mix(in srgb, var(--color-outline-variant) 60%, transparent);
    color: var(--color-text-tertiary);
    background: color-mix(in srgb, var(--color-surface-variant) 30%, transparent);
  }

  .executor-badge.swarm {
    background-color: color-mix(in srgb, var(--color-secondary) 15%, transparent);
    color: var(--color-secondary);
  }

  .executor-badge.agent {
    background-color: color-mix(in srgb, var(--color-primary) 15%, transparent);
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
    border: 1px solid color-mix(in srgb, var(--color-secondary) 25%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-secondary) 12%, transparent);
    color: var(--color-secondary);
  }

  .source-badge.discovered {
    border: 1px solid color-mix(in srgb, var(--color-primary) 24%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
    color: var(--color-primary);
  }
</style>
