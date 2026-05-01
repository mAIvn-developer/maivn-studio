<script lang="ts">
  import { X } from "lucide-svelte";
  import type { RepoScanItem } from "$lib/types";

  interface Props {
    open: boolean;
    items: RepoScanItem[];
    loading: boolean;
    error: string | null;
    selectedKeys: Set<string>;
    onClose: () => void;
    onToggle: (key: string) => void;
    onSelectAll: () => void;
    onClear: () => void;
    onRescan: () => void;
    onApply: () => void;
  }

  let {
    open,
    items,
    loading,
    error,
    selectedKeys,
    onClose,
    onToggle,
    onSelectAll,
    onClear,
    onRescan,
    onApply,
  }: Props = $props();

  const selectedCount = $derived(selectedKeys.size);
</script>

{#if open}
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <div
      class="absolute inset-0 bg-black/40 backdrop-blur-sm"
      onclick={onClose}
      role="presentation"
    ></div>

    <div
      class="relative w-full max-w-4xl max-h-[85vh] overflow-hidden rounded-2xl border
             border-[var(--color-outline-variant)] bg-[var(--color-bg)] shadow-xl"
    >
      <div
        class="flex items-center justify-between gap-4 border-b border-[var(--color-outline-variant)]
               bg-[var(--color-bg-secondary)] px-5 py-4"
      >
        <div class="flex flex-col">
          <h2 class="text-lg font-semibold text-[var(--color-text)]">Repo Discovery</h2>
          <p class="text-xs text-[var(--color-text-tertiary)]">
            Scan for Agents and Swarms, then add them to your Studio config.
          </p>
        </div>
        <button
          class="rounded-lg p-2 text-[var(--color-text-tertiary)]
                 hover:bg-[var(--color-bg-tertiary)] transition-colors"
          onclick={onClose}
          aria-label="Close"
        >
          <X size={20} />
        </button>
      </div>

      <div
        class="flex items-center justify-between px-5 py-3 border-b border-[var(--color-outline-variant)]"
      >
        <div class="text-sm text-[var(--color-text-secondary)]">
          {#if loading}
            Scanning repository...
          {:else}
            {items.length} candidates found
          {/if}
        </div>
        <div class="flex items-center gap-2">
          <button
            class="rounded-lg px-3 py-1.5 text-xs font-medium
                   bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]
                   hover:bg-[var(--color-surface-variant)] transition-colors"
            onclick={onRescan}
            disabled={loading}
          >
            Rescan
          </button>
          <button
            class="rounded-lg px-3 py-1.5 text-xs font-medium
                   bg-[var(--color-secondary)]/15 text-[var(--color-secondary)]
                   hover:bg-[var(--color-secondary)]/25 transition-colors"
            onclick={onSelectAll}
            disabled={loading || items.length === 0}
          >
            Select All
          </button>
          <button
            class="rounded-lg px-3 py-1.5 text-xs font-medium
                   bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]
                   hover:bg-[var(--color-surface-variant)] transition-colors"
            onclick={onClear}
            disabled={loading || selectedCount === 0}
          >
            Clear
          </button>
        </div>
      </div>

      <div class="max-h-[55vh] overflow-y-auto px-5 py-4">
        {#if error}
          <div
            class="rounded-lg bg-[var(--color-error-container)] p-3 text-sm text-[var(--color-error)]"
          >
            {error}
          </div>
        {:else if loading}
          <div class="flex items-center justify-center gap-3 py-10">
            <div
              class="h-8 w-8 rounded-full border-2 border-[var(--color-secondary)]/30
                     border-t-[var(--color-secondary)] animate-spin"
            ></div>
            <p class="text-sm text-[var(--color-text-secondary)]">Scanning...</p>
          </div>
        {:else if items.length === 0}
          <div class="flex flex-col items-center justify-center py-10 text-center">
            <p class="text-sm text-[var(--color-text-secondary)]">No agents or swarms found.</p>
            <p class="text-xs text-[var(--color-text-tertiary)] mt-1">
              Try updating your discovery paths or rescan.
            </p>
          </div>
        {:else}
          <div class="grid gap-3">
            {#each items as item}
              {@const key = `${item.discovery_path}::${item.file_path}`}
              <button
                class="w-full text-left rounded-xl border border-[var(--color-outline-variant)]
                       bg-[var(--color-bg-secondary)] p-4 transition-all duration-150
                       hover:bg-[var(--color-bg-tertiary)]"
                onclick={() => onToggle(key)}
              >
                <div class="flex items-start justify-between gap-4">
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      <div
                        class="h-5 w-5 rounded-md border border-[var(--color-outline-variant)]
                               flex items-center justify-center"
                      >
                        {#if selectedKeys.has(key)}
                          <div class="h-3 w-3 rounded-sm bg-[var(--color-secondary)]"></div>
                        {/if}
                      </div>
                      <div class="text-sm font-semibold text-[var(--color-text)]">{item.name}</div>
                      <span class="text-[10px] text-[var(--color-text-tertiary)]"
                        >{item.category}</span
                      >
                    </div>
                    <div class="mt-1 text-xs text-[var(--color-text-tertiary)] break-all">
                      {item.module}
                    </div>
                    {#if item.description}
                      <div class="mt-2 text-xs text-[var(--color-text-secondary)]">
                        {item.description}
                      </div>
                    {/if}
                  </div>
                  <div class="text-xs text-[var(--color-text-tertiary)] text-right">
                    <div>{item.file_path}</div>
                    <div class="mt-1">
                      {item.agents.length} agents - {item.swarms.length} swarms
                    </div>
                  </div>
                </div>
                {#if item.agents.length || item.swarms.length}
                  <div class="mt-3 flex flex-wrap gap-1.5 text-[10px]">
                    {#each item.agents as agent}
                      <span
                        class="rounded-full bg-[var(--color-surface-variant)] px-2 py-0.5
                               text-[var(--color-text-secondary)] border border-[var(--color-outline-variant)]/50"
                      >
                        Agent: {agent}
                      </span>
                    {/each}
                    {#each item.swarms as swarm}
                      <span
                        class="rounded-full bg-[var(--color-bg-tertiary)] px-2 py-0.5
                               text-[var(--color-text-secondary)] border border-[var(--color-outline-variant)]/50"
                      >
                        Swarm: {swarm}
                      </span>
                    {/each}
                  </div>
                {/if}
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <div
        class="flex items-center justify-between gap-4 border-t border-[var(--color-outline-variant)]
               bg-[var(--color-bg-secondary)] px-5 py-4"
      >
        <div class="text-xs text-[var(--color-text-tertiary)]">
          {selectedCount} selected
        </div>
        <div class="flex items-center gap-2">
          <button
            class="rounded-lg px-4 py-2 text-sm font-medium
                   bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]
                   hover:bg-[var(--color-surface-variant)] transition-colors"
            onclick={onClose}
          >
            Cancel
          </button>
          <button
            class="rounded-lg px-4 py-2 text-sm font-medium
                   bg-[var(--color-secondary)] text-[var(--color-on-secondary)]
                   hover:bg-[var(--color-secondary)]/90 transition-colors"
            onclick={onApply}
            disabled={selectedCount === 0 || loading}
          >
            Add Selected
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
