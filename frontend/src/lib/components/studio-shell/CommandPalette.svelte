<script lang="ts">
  import type { Demo } from "$lib/types";
  import { Bot, Clock, Command, FolderSearch, PanelRight, Plus, Search } from "lucide-svelte";

  // MARK: Types

  interface ActionItem {
    id: string;
    label: string;
    icon: typeof Plus;
    shortcut?: string;
  }

  interface Props {
    open: boolean;
    demos: Record<string, Demo[]>;
    onClose: () => void;
    onSelectDemo: (demo: Demo) => void;
    onAction: (actionId: string) => void;
  }

  // MARK: Props & State

  let { open, demos, onClose, onSelectDemo, onAction }: Props = $props();

  let searchQuery = $state("");
  let selectedIndex = $state(0);
  let searchInput: HTMLInputElement | undefined = $state();

  const RECENT_STORAGE_KEY = "maivn-studio-recent";
  const MAX_RECENT = 5;

  // MARK: Actions

  const actions: ActionItem[] = [
    { id: "new-thread", label: "New Thread", icon: Plus, shortcut: "Ctrl+N" },
    {
      id: "toggle-events",
      label: "Toggle Events Panel",
      icon: PanelRight,
      shortcut: "Ctrl+Shift+E",
    },
    { id: "scan-repo", label: "Scan Repo", icon: FolderSearch },
  ];

  function getSourceLabel(demo: Demo): string {
    return demo.source === "discovered" ? "Auto" : "Config";
  }

  // MARK: Recent Items

  function getRecentItems(): string[] {
    try {
      const stored = localStorage.getItem(RECENT_STORAGE_KEY);
      if (!stored) return [];
      return JSON.parse(stored) as string[];
    } catch {
      return [];
    }
  }

  function addRecentItem(id: string): void {
    const recent = getRecentItems().filter((r) => r !== id);
    recent.unshift(id);
    if (recent.length > MAX_RECENT) recent.length = MAX_RECENT;
    try {
      localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(recent));
    } catch {
      // localStorage may be unavailable
    }
  }

  // MARK: All Demos Flat List

  const allDemos = $derived.by(() => {
    const result: Demo[] = [];
    for (const categoryDemos of Object.values(demos)) {
      result.push(...categoryDemos);
    }
    return result;
  });

  // MARK: Fuzzy Search

  function matchesQuery(demo: Demo, query: string): boolean {
    const q = query.toLowerCase();
    if (demo.name.toLowerCase().includes(q)) return true;
    if (demo.description?.toLowerCase().includes(q)) return true;
    if (demo.category.toLowerCase().includes(q)) return true;
    if (demo.tags.some((tag) => tag.toLowerCase().includes(q))) return true;
    return false;
  }

  // MARK: Filtered Results

  const filteredDemos = $derived.by(() => {
    if (!searchQuery.trim()) return [];
    return allDemos.filter((demo) => matchesQuery(demo, searchQuery.trim()));
  });

  const filteredActions = $derived.by(() => {
    if (!searchQuery.trim()) return actions;
    const q = searchQuery.toLowerCase();
    return actions.filter((a) => a.label.toLowerCase().includes(q));
  });

  // MARK: Recent Demos

  const recentDemos = $derived.by(() => {
    if (searchQuery.trim()) return [];
    const recentIds = getRecentItems();
    const result: Demo[] = [];
    for (const id of recentIds) {
      const found = allDemos.find((d) => d.id === id);
      if (found) result.push(found);
    }
    return result;
  });

  // MARK: Navigable Items

  interface FlatItem {
    type: "demo" | "action" | "recent";
    demo?: Demo;
    action?: ActionItem;
  }

  const flatItems = $derived.by(() => {
    const items: FlatItem[] = [];

    if (!searchQuery.trim()) {
      // No query: show recent + actions
      for (const demo of recentDemos) {
        items.push({ type: "recent", demo });
      }
      for (const action of filteredActions) {
        items.push({ type: "action", action });
      }
    } else {
      // With query: show filtered demos + filtered actions
      for (const demo of filteredDemos) {
        items.push({ type: "demo", demo });
      }
      for (const action of filteredActions) {
        items.push({ type: "action", action });
      }
    }

    return items;
  });

  // MARK: Selection Management

  // Reset selection when items change
  $effect(() => {
    // Access flatItems.length to create dependency
    if (flatItems.length >= 0) {
      selectedIndex = 0;
    }
  });

  // Auto-focus search input when opened
  $effect(() => {
    if (open) {
      searchQuery = "";
      selectedIndex = 0;
      // Tick delay to let DOM render
      setTimeout(() => searchInput?.focus(), 0);
    }
  });

  // MARK: Text Highlighting

  function highlightMatch(
    text: string,
    query: string,
  ): { before: string; match: string; after: string } | null {
    if (!query.trim()) return null;
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return null;
    return {
      before: text.slice(0, idx),
      match: text.slice(idx, idx + query.length),
      after: text.slice(idx + query.length),
    };
  }

  // MARK: Event Handlers

  function selectItem(item: FlatItem): void {
    if (item.type === "action" && item.action) {
      onAction(item.action.id);
      addRecentItem(item.action.id);
    } else if ((item.type === "demo" || item.type === "recent") && item.demo) {
      onSelectDemo(item.demo);
      addRecentItem(item.demo.id);
    }
    onClose();
  }

  function handleKeydown(event: KeyboardEvent): void {
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        if (flatItems.length > 0) {
          selectedIndex = (selectedIndex + 1) % flatItems.length;
          scrollSelectedIntoView();
        }
        break;
      case "ArrowUp":
        event.preventDefault();
        if (flatItems.length > 0) {
          selectedIndex = (selectedIndex - 1 + flatItems.length) % flatItems.length;
          scrollSelectedIntoView();
        }
        break;
      case "Enter":
        event.preventDefault();
        if (flatItems.length > 0 && selectedIndex < flatItems.length) {
          selectItem(flatItems[selectedIndex]);
        }
        break;
      case "Escape":
        event.preventDefault();
        onClose();
        break;
    }
  }

  function scrollSelectedIntoView(): void {
    // Use tick delay to let DOM update
    setTimeout(() => {
      const el = document.querySelector('[data-command-selected="true"]');
      el?.scrollIntoView({ block: "nearest" });
    }, 0);
  }

  function handleOverlayClick(): void {
    onClose();
  }

  // MARK: Section Helpers

  /**
   * Determine section boundaries for rendering section headers.
   * Returns the start index of each section in flatItems.
   */
  const sections = $derived.by(() => {
    const result: {
      label: string;
      icon: typeof Clock | typeof Bot | typeof Command;
      startIndex: number;
    }[] = [];
    let currentSection = "";

    for (let i = 0; i < flatItems.length; i++) {
      const item = flatItems[i];
      let section = "";

      if (item.type === "recent") section = "Recent";
      else if (item.type === "demo") section = "Demos";
      else if (item.type === "action") section = "Actions";

      if (section !== currentSection) {
        const icon = section === "Recent" ? Clock : section === "Demos" ? Bot : Command;
        result.push({ label: section, icon, startIndex: i });
        currentSection = section;
      }
    }

    return result;
  });

  function isSectionStart(index: number): boolean {
    return sections.some((s) => s.startIndex === index);
  }

  function getSectionAt(index: number) {
    return sections.find((s) => s.startIndex === index);
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]"
    onkeydown={handleKeydown}
  >
    <!-- Overlay -->
    <div
      class="absolute inset-0 bg-black/65 backdrop-blur-md animate-in"
      onclick={handleOverlayClick}
      role="presentation"
    ></div>

    <!-- Modal -->
    <div
      class="relative w-full max-w-2xl overflow-hidden rounded-[1.75rem] border
             border-[var(--color-outline-variant)] bg-[linear-gradient(180deg,rgba(30,31,37,0.98),rgba(18,19,24,0.98))]
             shadow-2xl animate-in"
      role="dialog"
      aria-label="Command palette"
    >
      <!-- Search Input -->
      <div class="border-b border-[var(--color-outline-variant)] px-4 py-3.5">
        <div class="mb-2 flex items-center justify-between gap-3">
          <div>
            <div
              class="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--color-text-tertiary)]"
            >
              Command Palette
            </div>
            <div class="mt-1 text-sm text-[var(--color-text-secondary)]">
              Jump to demos and workspace actions.
            </div>
          </div>
          <kbd
            class="shrink-0 rounded-md bg-[var(--color-bg-tertiary)] px-1.5 py-0.5
                   text-[10px] font-mono text-[var(--color-text-tertiary)]
                   border border-[var(--color-outline-variant)]"
          >
            Esc
          </kbd>
        </div>
        <div
          class="flex items-center gap-3 rounded-2xl border border-[var(--color-outline-variant)] bg-[var(--color-bg-secondary)]/88 px-4 py-3 shadow-[var(--shadow-sm)]"
        >
          <Search size={18} class="shrink-0 text-[var(--color-text-tertiary)]" />
          <input
            bind:this={searchInput}
            bind:value={searchQuery}
            type="text"
            placeholder="Search demos, actions..."
            class="flex-1 bg-transparent text-base text-[var(--color-text)]
                 placeholder-[var(--color-text-tertiary)] outline-none"
          />
          <span
            class="hidden rounded-full border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]/80 px-2 py-0.5 text-[10px] text-[var(--color-text-tertiary)] sm:inline-flex"
          >
            {searchQuery.trim() ? `${flatItems.length} matches` : `${recentDemos.length} recent`}
          </span>
        </div>
      </div>

      <!-- Results -->
      <div class="max-h-[55vh] overflow-y-auto px-2 py-2">
        {#if flatItems.length === 0}
          <div class="flex flex-col items-center justify-center py-12 text-center">
            <div
              class="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]"
            >
              <Search size={24} class="text-[var(--color-text-tertiary)]" />
            </div>
            <p class="text-sm font-medium text-[var(--color-text-secondary)]">No results found</p>
            <p class="mt-1 text-xs text-[var(--color-text-tertiary)]">
              Try a different search term
            </p>
          </div>
        {:else}
          {#each flatItems as item, index}
            <!-- Section header -->
            {#if isSectionStart(index)}
              {@const section = getSectionAt(index)}
              {#if section}
                {@const SectionIcon = section.icon}
                <div class="flex items-center gap-2 px-3 pb-1.5 pt-3">
                  <SectionIcon size={12} class="text-[var(--color-text-tertiary)]" />
                  <span
                    class="text-[10px] font-semibold uppercase tracking-widest text-[var(--color-text-tertiary)]"
                  >
                    {section.label}
                  </span>
                </div>
              {/if}
            {/if}

            <!-- Item -->
            <button
              class="flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition-colors duration-75
                     {index === selectedIndex
                ? 'border-[var(--color-tertiary)]/30 bg-[var(--color-bg-tertiary)] shadow-[var(--shadow-sm)]'
                : 'border-transparent bg-transparent hover:border-[var(--color-outline-variant)] hover:bg-[var(--color-bg-secondary)]/75'}"
              data-command-selected={index === selectedIndex}
              onclick={() => selectItem(item)}
              onmouseenter={() => (selectedIndex = index)}
            >
              {#if item.type === "action" && item.action}
                <!-- Action item -->
                {@const ActionIcon = item.action.icon}
                <div
                  class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl
                         bg-[var(--color-bg-tertiary)]"
                >
                  <ActionIcon size={16} class="text-[var(--color-text-secondary)]" />
                </div>
                <div class="flex-1 min-w-0">
                  <span class="text-sm font-medium text-[var(--color-text)]"
                    >{item.action.label}</span
                  >
                  <div class="mt-0.5 text-[11px] text-[var(--color-text-tertiary)]">
                    Workspace action
                  </div>
                </div>
                {#if item.action.shortcut}
                  <kbd
                    class="shrink-0 rounded-md bg-[var(--color-bg-tertiary)] px-1.5 py-0.5
                           text-[10px] font-mono text-[var(--color-text-tertiary)]
                           border border-[var(--color-outline-variant)]"
                  >
                    {item.action.shortcut}
                  </kbd>
                {/if}
              {:else if item.demo}
                <!-- Demo or Recent item -->
                <div
                  class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl
                         bg-[var(--color-bg-tertiary)]"
                >
                  {#if item.type === "recent"}
                    <Clock size={16} class="text-[var(--color-text-secondary)]" />
                  {:else}
                    <Bot size={16} class="text-[var(--color-text-secondary)]" />
                  {/if}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    {#if searchQuery.trim()}
                      {@const match = highlightMatch(item.demo.name, searchQuery.trim())}
                      {#if match}
                        <span class="text-sm text-[var(--color-text)] truncate">
                          {match.before}<mark
                            class="bg-[var(--color-tertiary)]/30 text-[var(--color-tertiary)] rounded-sm px-0.5"
                            >{match.match}</mark
                          >{match.after}
                        </span>
                      {:else}
                        <span class="text-sm text-[var(--color-text)] truncate"
                          >{item.demo.name}</span
                        >
                      {/if}
                    {:else}
                      <span class="text-sm text-[var(--color-text)] truncate">{item.demo.name}</span
                      >
                    {/if}
                    <span
                      class="shrink-0 rounded-full bg-[var(--color-surface-variant)] px-2 py-0.5
                             text-[10px] text-[var(--color-text-tertiary)]"
                    >
                      {item.demo.category}
                    </span>
                    <span
                      class={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                        item.demo.source === "discovered"
                          ? "border-[var(--color-primary)]/25 bg-[var(--color-primary)]/10 text-[var(--color-primary)]"
                          : "border-[var(--color-tertiary)]/25 bg-[var(--color-tertiary)]/10 text-[var(--color-tertiary)]"
                      }`}
                    >
                      {getSourceLabel(item.demo)}
                    </span>
                  </div>
                  {#if item.demo.description}
                    <p class="mt-0.5 text-xs text-[var(--color-text-tertiary)] truncate">
                      {item.demo.description}
                    </p>
                  {/if}
                </div>
              {/if}
            </button>
          {/each}
        {/if}
      </div>

      <!-- Footer -->
      <div
        class="flex items-center gap-4 border-t border-[var(--color-outline-variant)]
               bg-[var(--color-bg-tertiary)]/50 px-4 py-3"
      >
        <div class="flex items-center gap-4 text-[11px] text-[var(--color-text-tertiary)]">
          <span class="flex items-center gap-1">
            <kbd class="font-mono">&#8593;&#8595;</kbd>
            Navigate
          </span>
          <span class="flex items-center gap-1">
            <kbd class="font-mono">&#8629;</kbd>
            Select
          </span>
          <span class="flex items-center gap-1">
            <kbd class="font-mono">Esc</kbd>
            Close
          </span>
        </div>
      </div>
    </div>
  </div>
{/if}
