<script lang="ts">
  import MaivnIcon from "$lib/assets/maivn_icon_dark_mode.svg";
  import MaivnLogo from "$lib/assets/maivn_logo_dark_mode.svg";
  import { Command, PanelLeftClose } from "lucide-svelte";

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
      <img src={MaivnLogo} alt="mAIvn" class="h-4.5 shrink-0" />

      <span class="text-sm font-semibold tracking-tight text-[var(--color-text)]">Studio</span>

      <span
        class="status-dot shrink-0"
        class:connected
        title={connected ? "Connected" : "Disconnected"}
      ></span>
    </div>

    <div class="flex items-center">
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
        <img src={MaivnIcon} alt="mAIvn" class="h-6 w-6 object-contain" />
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
</style>
