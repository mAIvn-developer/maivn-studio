<script lang="ts">
  import type { App } from "$lib/types";
  import { AlertCircle, Command, Search } from "lucide-svelte";

  interface Props {
    connecting: boolean;
    loading: boolean;
    error: string | null;
    selectedAppId?: string | null;
    selectedAppName?: string | null;
    recentApps: App[];
    onOpenCommandPalette: () => void;
    onOpenDiscovery: () => void;
    onSelectApp: (app: App) => void;
    getCollapsedAppLabel: (name: string) => string;
  }

  let {
    connecting,
    loading,
    error,
    selectedAppId = null,
    selectedAppName = null,
    recentApps,
    onOpenCommandPalette,
    onOpenDiscovery,
    onSelectApp,
    getCollapsedAppLabel,
  }: Props = $props();
</script>

<div class="flex-1 min-h-0 flex flex-col collapsed-rail">
  <div
    class="shrink-0 px-1.5 py-2 border-b border-[var(--color-outline-variant)] flex flex-col items-center gap-1.5"
  >
    <button
      type="button"
      class="collapsed-quick-action"
      title="Command palette (Ctrl+K)"
      onclick={onOpenCommandPalette}
    >
      <Command size={15} />
    </button>
    <button
      type="button"
      class="collapsed-quick-action"
      title="Scan repository"
      onclick={onOpenDiscovery}
    >
      <Search size={15} />
    </button>
  </div>

  <div class="flex-1 min-h-0 overflow-y-auto px-1.5 py-2 flex flex-col items-center gap-2">
    {#if connecting || loading}
      <div class="flex justify-center py-1">
        <div
          class="h-4 w-4 rounded-full border-2 border-[var(--color-secondary)]/30
                 border-t-[var(--color-secondary)] animate-spin"
        ></div>
      </div>
    {:else if error}
      <div class="flex justify-center py-0.5">
        <div
          class="flex h-8 w-8 items-center justify-center rounded-lg
                 bg-[var(--color-error-container)]/80 text-[var(--color-error)]"
          title={error}
        >
          <AlertCircle size={14} />
        </div>
      </div>
    {/if}

    {#if selectedAppName}
      <button
        type="button"
        class="collapsed-active-btn"
        onclick={onOpenCommandPalette}
        title={`Active app: ${selectedAppName}. Open command palette to switch.`}
      >
        {getCollapsedAppLabel(selectedAppName)}
      </button>
    {:else}
      <button
        type="button"
        class="collapsed-empty-btn"
        onclick={onOpenCommandPalette}
        title="No app selected. Open command palette."
      >
        Pick
      </button>
    {/if}

    {#if recentApps.length > 0}
      <div class="collapsed-divider" aria-hidden="true"></div>
      <div class="collapsed-recent-list">
        {#each recentApps.slice(0, 6) as app (app.id)}
          <button
            type="button"
            class="collapsed-app-btn"
            class:selected={selectedAppId === app.id}
            onclick={() => onSelectApp(app)}
            title={`Recent: ${app.name}`}
          >
            {getCollapsedAppLabel(app.name)}
          </button>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .collapsed-rail {
    background:
      linear-gradient(
        180deg,
        color-mix(in srgb, var(--color-bg-secondary) 34%, transparent),
        transparent 35%
      ),
      var(--color-bg);
  }

  .collapsed-quick-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: var(--radius-lg);
    border: 1px solid transparent;
    color: var(--color-text-tertiary);
    background: color-mix(in srgb, var(--color-bg-secondary) 70%, transparent);
    transition:
      color var(--transition-fast),
      background-color var(--transition-fast),
      border-color var(--transition-fast);
  }

  .collapsed-quick-action:hover {
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-tertiary) 86%, transparent);
    border-color: color-mix(in srgb, var(--color-outline) 42%, var(--color-outline-variant));
  }

  .collapsed-active-btn,
  .collapsed-empty-btn,
  .collapsed-app-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: var(--radius-lg);
    border: 1px solid transparent;
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-secondary) 74%, transparent);
    font-size: 0.625rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    line-height: 1;
    text-transform: uppercase;
    transition:
      color var(--transition-fast),
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      transform var(--transition-fast);
  }

  .collapsed-active-btn {
    width: 2.25rem;
    height: 2.25rem;
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 15%, var(--color-bg-secondary));
    border-color: color-mix(in srgb, var(--color-secondary) 38%, var(--color-outline-variant));
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-secondary) 15%, transparent);
  }

  .collapsed-empty-btn {
    width: 2.25rem;
    height: 2.25rem;
    font-size: 0.5625rem;
    letter-spacing: 0.06em;
    color: var(--color-text-tertiary);
    background: color-mix(in srgb, var(--color-bg-secondary) 86%, transparent);
    border-color: var(--color-outline-variant);
  }

  .collapsed-empty-btn:hover {
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-tertiary) 90%, transparent);
  }

  .collapsed-divider {
    width: 1.25rem;
    height: 1px;
    background: color-mix(in srgb, var(--color-outline) 38%, transparent);
    margin: 0.125rem 0;
  }

  .collapsed-recent-list {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
  }

  .collapsed-app-btn:hover {
    color: var(--color-text);
    background: color-mix(in srgb, var(--color-bg-tertiary) 90%, transparent);
    border-color: color-mix(in srgb, var(--color-outline) 45%, var(--color-outline-variant));
  }

  .collapsed-app-btn.selected {
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 14%, var(--color-bg-secondary));
    border-color: color-mix(in srgb, var(--color-secondary) 42%, var(--color-outline-variant));
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-secondary) 18%, transparent);
  }

  .collapsed-app-btn:active {
    transform: scale(0.96);
  }
</style>
