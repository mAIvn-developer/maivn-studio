<script lang="ts">
  import { Archive, ChevronDown, Search, FileText, Bookmark, Plus } from "lucide-svelte";
  import type { PromptInfo, SavedPrompt } from "$lib/types";

  interface Props {
    discoveredPrompts: PromptInfo[];
    savedPrompts: SavedPrompt[];
    onSelect: (
      content: string,
      structuredOutput?: string,
      messageType?: string,
      variant?: string,
    ) => void;
    onSave?: () => void;
    disabled?: boolean;
  }

  let {
    discoveredPrompts = [],
    savedPrompts = [],
    onSelect,
    onSave,
    disabled = false,
  }: Props = $props();

  let isOpen = $state(false);
  let searchQuery = $state("");

  // Total prompt count for badge
  const totalCount = $derived(discoveredPrompts.length + savedPrompts.length);

  function filteredDiscovered() {
    if (!searchQuery) return discoveredPrompts;
    const query = searchQuery.toLowerCase();
    return discoveredPrompts.filter(
      (p) => p.name.toLowerCase().includes(query) || p.content.toLowerCase().includes(query),
    );
  }

  function filteredSaved() {
    if (!searchQuery) return savedPrompts;
    const query = searchQuery.toLowerCase();
    return savedPrompts.filter(
      (p) => p.name.toLowerCase().includes(query) || p.content.toLowerCase().includes(query),
    );
  }

  function handleSelect(
    content: string,
    structuredOutput?: string,
    messageType?: string,
    variant?: string,
  ) {
    onSelect(content, structuredOutput, messageType, variant);
    isOpen = false;
    searchQuery = "";
  }

  function truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + "...";
  }

  // Close dropdown when clicking outside
  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest(".prompt-dropdown")) {
      isOpen = false;
    }
  }

  $effect(() => {
    if (isOpen) {
      document.addEventListener("click", handleClickOutside);
    }
    return () => document.removeEventListener("click", handleClickOutside);
  });
</script>

<div class="prompt-dropdown relative">
  <!-- Modern pill button with icon, badge, and chevron -->
  <button
    type="button"
    onclick={() => (isOpen = !isOpen)}
    {disabled}
    class="prompt-button"
    class:opacity-50={disabled}
    class:cursor-not-allowed={disabled}
    class:is-open={isOpen}
    title="Select a prompt"
  >
    <!-- Archive/folder icon -->
    <Archive size={16} class="text-[var(--color-text-tertiary)]" strokeWidth={1.5} />

    <span class="hidden sm:inline font-medium">Prompts</span>

    <!-- Count badge -->
    {#if totalCount > 0}
      <span
        class="flex items-center justify-center min-w-[18px] h-[18px] px-1
               rounded-full bg-[var(--color-secondary)]/20 text-[var(--color-secondary)]
               text-[10px] font-bold tabular-nums"
      >
        {totalCount}
      </span>
    {/if}

    <!-- Chevron that rotates -->
    <ChevronDown
      size={14}
      class="text-[var(--color-text-tertiary)] transition-transform duration-200 {isOpen
        ? 'rotate-180'
        : ''}"
    />
  </button>

  {#if isOpen}
    <div
      class="dropdown-panel absolute bottom-full left-0 mb-2 w-80 max-h-[400px]
             overflow-hidden rounded-xl
             border border-[var(--color-outline-variant)]
             bg-[var(--color-bg-secondary)] shadow-xl z-50 animate-in"
    >
      <!-- Search with icon inside -->
      <div class="p-3 border-b border-[var(--color-outline-variant)]">
        <div class="relative">
          <Search
            size={16}
            class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]"
          />
          <input
            type="text"
            bind:value={searchQuery}
            placeholder="Search prompts..."
            class="w-full rounded-lg border border-[var(--color-outline-variant)]
                   bg-[var(--color-bg)] pl-10 pr-3 py-2 text-sm text-[var(--color-text)]
                   placeholder-[var(--color-text-tertiary)]
                   focus:border-[var(--color-secondary)] focus:outline-none
                   focus:ring-2 focus:ring-[var(--color-secondary)]/20 transition-all"
          />
        </div>
      </div>

      <div class="max-h-[280px] overflow-y-auto custom-scrollbar">
        <!-- Discovered Prompts -->
        {#if filteredDiscovered().length > 0}
          <div class="p-2">
            <!-- Section header with overline style -->
            <div
              class="flex items-center gap-2 px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-tertiary)]"
            >
              <FileText size={12} />
              Demo Prompts
              <span
                class="ml-auto rounded-full bg-[var(--color-primary)]/15 px-1.5 py-0.5 text-[var(--color-primary)]"
              >
                {filteredDiscovered().length}
              </span>
            </div>
            {#each filteredDiscovered() as prompt}
              <button
                type="button"
                onclick={() =>
                  handleSelect(
                    prompt.content,
                    prompt.structured_output,
                    prompt.message_type,
                    prompt.variant,
                  )}
                class="prompt-item w-full flex items-start gap-3 rounded-lg px-3 py-2.5 text-left
                       hover:bg-[var(--color-bg-tertiary)] transition-colors group"
              >
                <!-- Document icon -->
                <div
                  class="flex-shrink-0 w-8 h-8 rounded-lg bg-[var(--color-primary)]/10
                         flex items-center justify-center group-hover:bg-[var(--color-primary)]/20 transition-colors"
                >
                  <FileText size={16} class="text-[var(--color-primary)]" strokeWidth={1.5} />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium text-[var(--color-text)]">{prompt.name}</div>
                  <div
                    class="text-xs text-[var(--color-text-tertiary)] line-clamp-2 mt-0.5 leading-relaxed"
                  >
                    {truncate(prompt.content, 80)}
                  </div>
                </div>
              </button>
            {/each}
          </div>
        {/if}

        <!-- Saved Prompts -->
        {#if filteredSaved().length > 0}
          <div class="p-2 border-t border-[var(--color-outline-variant)]">
            <div
              class="flex items-center gap-2 px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-tertiary)]"
            >
              <Bookmark size={12} />
              Saved Prompts
              <span
                class="ml-auto rounded-full bg-[var(--color-secondary)]/15 px-1.5 py-0.5 text-[var(--color-secondary)]"
              >
                {filteredSaved().length}
              </span>
            </div>
            {#each filteredSaved() as prompt}
              <button
                type="button"
                onclick={() => handleSelect(prompt.content)}
                class="prompt-item w-full flex items-start gap-3 rounded-lg px-3 py-2.5 text-left
                       hover:bg-[var(--color-bg-tertiary)] transition-colors group"
              >
                <!-- Bookmark icon -->
                <div
                  class="flex-shrink-0 w-8 h-8 rounded-lg bg-[var(--color-secondary)]/10
                         flex items-center justify-center group-hover:bg-[var(--color-secondary)]/20 transition-colors"
                >
                  <Bookmark size={16} class="text-[var(--color-secondary)]" strokeWidth={1.5} />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium text-[var(--color-text)]">{prompt.name}</div>
                  <div
                    class="text-xs text-[var(--color-text-tertiary)] line-clamp-2 mt-0.5 leading-relaxed"
                  >
                    {truncate(prompt.content, 80)}
                  </div>
                </div>
              </button>
            {/each}
          </div>
        {/if}

        <!-- Empty state with illustration -->
        {#if filteredDiscovered().length === 0 && filteredSaved().length === 0}
          <div class="p-6 flex flex-col items-center justify-center text-center">
            <div
              class="w-12 h-12 rounded-xl bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-3"
            >
              <Archive size={24} class="text-[var(--color-text-tertiary)]" strokeWidth={1.5} />
            </div>
            <p class="text-sm text-[var(--color-text-secondary)]">
              {searchQuery ? "No prompts match your search" : "No prompts available"}
            </p>
            {#if searchQuery}
              <button
                type="button"
                onclick={() => (searchQuery = "")}
                class="mt-2 text-xs text-[var(--color-secondary)] hover:underline"
              >
                Clear search
              </button>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Save action footer -->
      {#if onSave}
        <div class="border-t border-[var(--color-outline-variant)] p-2">
          <button
            type="button"
            onclick={() => {
              onSave?.();
              isOpen = false;
            }}
            class="w-full flex items-center justify-center gap-2 rounded-lg px-3 py-2.5
                   text-sm font-medium text-[var(--color-secondary)]
                   bg-[var(--color-secondary)]/10 hover:bg-[var(--color-secondary)]/20
                   transition-colors"
          >
            <Plus size={16} />
            Save current message
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .prompt-dropdown {
    z-index: 2;
  }

  .prompt-button {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    box-sizing: border-box;
    height: var(--composer-control-height, 2.35rem);
    min-height: var(--composer-control-height, 2.35rem);
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text-secondary);
    padding: 0 0.65rem;
    font-size: 0.78rem;
    font-weight: 600;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      box-shadow var(--transition-fast),
      color var(--transition-fast);
  }

  .prompt-button:hover:not(:disabled) {
    border-color: color-mix(in srgb, var(--color-secondary) 52%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-secondary) 8%, var(--color-bg));
    color: var(--color-text);
  }

  .prompt-button.is-open {
    border-color: color-mix(in srgb, var(--color-secondary) 58%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-secondary) 10%, var(--color-bg));
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-secondary) 18%, transparent);
  }

  .dropdown-panel {
    animation: slideUp 0.15s ease-out;
    z-index: 120;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }

  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }

  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: var(--color-outline-variant);
    border-radius: 3px;
  }

  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: var(--color-text-tertiary);
  }
</style>
