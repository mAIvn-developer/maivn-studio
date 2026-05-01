<script lang="ts">
  import ThemeLogo from "$lib/components/ui/ThemeLogo.svelte";
  import { externalLinks } from "$lib/utils/external-links";
  import { Command, ExternalLink, PanelLeftClose } from "lucide-svelte";

  interface Props {
    collapsed?: boolean;
    connected?: boolean;
    onToggleCollapse?: () => void;
    onOpenCommandPalette?: () => void;
  }

  let {
    collapsed = false,
    connected = true,
    onToggleCollapse,
    onOpenCommandPalette,
  }: Props = $props();

  let appSwitcherOpen = $state(false);
  let appSwitcherEl = $state<HTMLDivElement | null>(null);

  const appSwitcherLinks = [
    { label: "Developer Portal", href: externalLinks.developerPortal() },
    { label: "Documentation", href: externalLinks.developerPortalDocs() },
    { label: "mAIvn home", href: externalLinks.marketingSite() },
  ];

  function toggleAppSwitcher() {
    appSwitcherOpen = !appSwitcherOpen;
  }

  function closeAppSwitcher() {
    appSwitcherOpen = false;
  }

  function handleDocumentClick(event: MouseEvent) {
    if (!appSwitcherEl) return;
    if (!appSwitcherEl.contains(event.target as Node)) {
      closeAppSwitcher();
    }
  }

  function handleDocumentKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      closeAppSwitcher();
    }
  }

  $effect(() => {
    if (!appSwitcherOpen) return;
    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("keydown", handleDocumentKeydown);
    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("keydown", handleDocumentKeydown);
    };
  });
</script>

<div
  class="sidebar-header shrink-0 flex items-center border-b border-[var(--color-outline-variant)]"
  class:h-12={!collapsed}
  class:h-14={collapsed}
  class:px-3={!collapsed}
  class:justify-center={collapsed}
>
  {#if !collapsed}
    <!-- Expanded: logo + Studio label + status + actions -->
    <div class="flex min-w-0 flex-1 items-center gap-2">
      <ThemeLogo alt="mAIvn" class="h-4.5 shrink-0" />

      <span class="text-sm font-semibold tracking-tight text-[var(--color-text)]">Studio</span>

      <span
        class="status-dot shrink-0"
        class:connected
        title={connected ? "Connected" : "Disconnected"}
      ></span>
    </div>

    <div class="flex items-center" bind:this={appSwitcherEl}>
      <div class="relative">
        <button
          type="button"
          class="sidebar-btn"
          onclick={toggleAppSwitcher}
          title="Switch app"
          aria-haspopup="menu"
          aria-expanded={appSwitcherOpen}
        >
          <ExternalLink size={14} />
        </button>
        {#if appSwitcherOpen}
          <div class="app-switcher-menu" role="menu">
            <p class="app-switcher-label">Open elsewhere</p>
            {#each appSwitcherLinks as link (link.href)}
              <a
                class="app-switcher-link"
                href={link.href}
                target="_blank"
                rel="noreferrer"
                role="menuitem"
                onclick={closeAppSwitcher}
              >
                <span>{link.label}</span>
                <ExternalLink size={11} class="text-[var(--color-text-tertiary)]" />
              </a>
            {/each}
          </div>
        {/if}
      </div>

      {#if onOpenCommandPalette}
        <button
          type="button"
          class="sidebar-btn"
          onclick={onOpenCommandPalette}
          title="Command palette (Ctrl+K)"
        >
          <Command size={14} />
        </button>
      {/if}

      {#if onToggleCollapse}
        <button
          type="button"
          class="sidebar-btn"
          onclick={onToggleCollapse}
          title="Collapse sidebar"
        >
          <PanelLeftClose size={14} />
        </button>
      {/if}
    </div>
  {:else}
    <!-- Collapsed: just the icon + expand button -->
    <div class="flex flex-col items-center gap-2">
      <button
        type="button"
        class="collapsed-logo-btn"
        onclick={onToggleCollapse}
        title="Expand sidebar"
      >
        <ThemeLogo icon alt="mAIvn" class="h-6 w-6 object-contain" />
        <span class="status-dot-mini" class:connected></span>
      </button>
    </div>
  {/if}
</div>

<style>
  .sidebar-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: var(--radius-md);
    color: var(--color-text-tertiary);
    transition:
      background-color 150ms,
      color 150ms;
  }

  .sidebar-btn:hover {
    background: var(--color-bg-tertiary);
    color: var(--color-text-secondary);
  }

  .status-dot {
    width: 0.375rem;
    height: 0.375rem;
    border-radius: 9999px;
    background: var(--color-error);
  }

  .status-dot.connected {
    background: var(--color-success);
  }

  .collapsed-logo-btn {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.25rem;
    border-radius: var(--radius-md);
    transition: background-color 150ms;
  }

  .collapsed-logo-btn:hover {
    background: var(--color-bg-tertiary);
  }

  .status-dot-mini {
    position: absolute;
    bottom: 0.125rem;
    right: 0.125rem;
    width: 0.375rem;
    height: 0.375rem;
    border-radius: 9999px;
    background: var(--color-error);
    border: 1.5px solid var(--color-bg);
  }

  .status-dot-mini.connected {
    background: var(--color-success);
  }

  .app-switcher-menu {
    position: absolute;
    top: calc(100% + 0.35rem);
    right: 0;
    z-index: 60;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 12rem;
    padding: 0.4rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-outline-variant);
    background: var(--color-bg-secondary);
    box-shadow: var(--shadow-lg);
  }

  .app-switcher-label {
    padding: 0.35rem 0.5rem 0.5rem;
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--color-text-tertiary);
  }

  .app-switcher-link {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.45rem 0.55rem;
    border-radius: var(--radius-md);
    font-size: 0.8125rem;
    color: var(--color-text-secondary);
    transition:
      background-color 150ms,
      color 150ms;
  }

  .app-switcher-link:hover {
    background: var(--color-bg-tertiary);
    color: var(--color-text);
  }
</style>
