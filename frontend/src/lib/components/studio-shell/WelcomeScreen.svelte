<script lang="ts">
  import MaivnLogo from "$lib/assets/maivn_logo_dark_mode.svg";
  import type { Demo } from "$lib/types";
  import { Clock, FolderSearch, MessageSquareText } from "lucide-svelte";

  interface Props {
    onOpenCommandPalette?: () => void;
    onScanRepo?: () => void;
    recentDemos?: Demo[];
    onSelectDemo?: (demo: Demo) => void;
    demoCount?: number;
    connected?: boolean;
  }

  let {
    onOpenCommandPalette,
    onScanRepo,
    recentDemos = [],
    onSelectDemo,
    demoCount = 0,
    connected = true,
  }: Props = $props();
</script>

<div class="welcome-root">
  <div class="welcome-backdrop" aria-hidden="true"></div>
  <div class="welcome-shell">
    <!-- Logo and branding -->
    <div class="welcome-grid">
      <div class="welcome-content">
        <div class="mb-6 flex items-center gap-3">
          <img src={MaivnLogo} alt="mAIvn" class="h-6" />
          <span class="text-xl font-semibold tracking-tight text-[var(--color-text)]">Studio</span>
        </div>

        <div class="mb-4 flex flex-wrap items-center gap-2 text-xs">
          <span
            class="welcome-pill"
            class:welcome-pill_connected={connected}
            class:welcome-pill_disconnected={!connected}
          >
            <span class="welcome-status-dot" class:welcome-status-dot_disconnected={!connected}
            ></span>
            {connected ? "Connected" : "Offline"}
          </span>
          <span class="welcome-pill">{demoCount} demos ready</span>
        </div>

        <h1
          class="max-w-3xl text-left text-3xl font-semibold tracking-tight text-[var(--color-text)] sm:text-4xl lg:text-[2.75rem]"
        >
          Build, debug, and validate agent experiences without leaving Studio.
        </h1>

        <p
          class="mt-4 max-w-2xl text-left text-sm leading-7 text-[var(--color-text-secondary)] sm:text-base"
        >
          Launch curated demos, inspect runtime behavior, and discover new experiments in your repo
          from one focused workspace.
        </p>

        <!-- Quick action cards -->
        <div class="mt-8 flex flex-col gap-3 sm:flex-row">
          {#if onOpenCommandPalette}
            <button class="welcome-primary-action" onclick={onOpenCommandPalette}>
              <span class="welcome-action-icon welcome-action-icon_primary">
                <MessageSquareText size={20} />
              </span>
              <span class="min-w-0 flex-1 text-left">
                <span class="block text-sm font-semibold text-[var(--color-text)]"
                  >Select a demo</span
                >
                <span class="mt-1 block text-xs text-[var(--color-text-tertiary)]">
                  Browse the demo catalog or launch the command palette.
                </span>
              </span>
              <kbd class="welcome-shortcut-key">Ctrl+K</kbd>
            </button>
          {/if}

          {#if onScanRepo}
            <button class="welcome-secondary-action" onclick={onScanRepo}>
              <span class="welcome-action-icon welcome-action-icon_secondary">
                <FolderSearch size={20} />
              </span>
              <span class="min-w-0 flex-1 text-left">
                <span class="block text-sm font-semibold text-[var(--color-text)]"
                  >Scan repository</span
                >
                <span class="mt-1 block text-xs text-[var(--color-text-tertiary)]">
                  Discover new demos and register them in Studio.
                </span>
              </span>
            </button>
          {/if}
        </div>

        <!-- Keyboard shortcuts hint -->
        <div class="mt-8 flex flex-wrap gap-3">
          <div class="welcome-shortcut-chip">
            <kbd class="welcome-shortcut-key">Ctrl+K</kbd>
            <span class="text-xs text-[var(--color-text-secondary)]">Command palette</span>
          </div>
          <div class="welcome-shortcut-chip">
            <kbd class="welcome-shortcut-key">Ctrl+N</kbd>
            <span class="text-xs text-[var(--color-text-secondary)]">New thread</span>
          </div>
          <div class="welcome-shortcut-chip">
            <kbd class="welcome-shortcut-key">Ctrl+Shift+E</kbd>
            <span class="text-xs text-[var(--color-text-secondary)]">Inspector</span>
          </div>
        </div>
      </div>

      <!-- Recent demos -->
      <div class="welcome-side-panel">
        {#if recentDemos.length > 0 && onSelectDemo}
          <div class="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]">
            <Clock size={12} />
            <span>Recent demos</span>
          </div>
          <div class="mt-4 space-y-2">
            {#each recentDemos.slice(0, 5) as demo}
              <button class="welcome-recent-item" onclick={() => onSelectDemo?.(demo)}>
                <span class="min-w-0 flex-1 text-left">
                  <span class="block truncate text-sm font-medium text-[var(--color-text)]"
                    >{demo.name}</span
                  >
                  <span class="mt-1 block truncate text-xs text-[var(--color-text-tertiary)]">
                    {demo.category}
                  </span>
                </span>
                <span class="welcome-open-pill">Open</span>
              </button>
            {/each}
          </div>
        {:else}
          <div class="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]">
            <Clock size={12} />
            <span>Getting started</span>
          </div>
          <div class="mt-4 space-y-3">
            <div class="welcome-step">
              <span class="welcome-step-index">1</span>
              <div>
                <div class="text-sm font-medium text-[var(--color-text)]">Choose a demo</div>
                <div class="mt-1 text-xs leading-6 text-[var(--color-text-tertiary)]">
                  Open the command palette to browse the full Studio catalog.
                </div>
              </div>
            </div>
            <div class="welcome-step">
              <span class="welcome-step-index">2</span>
              <div>
                <div class="text-sm font-medium text-[var(--color-text)]">Start a session</div>
                <div class="mt-1 text-xs leading-6 text-[var(--color-text-tertiary)]">
                  Send a prompt, attach inputs, and watch the runtime flow evolve.
                </div>
              </div>
            </div>
            <div class="welcome-step">
              <span class="welcome-step-index">3</span>
              <div>
                <div class="text-sm font-medium text-[var(--color-text)]">Inspect the run</div>
                <div class="mt-1 text-xs leading-6 text-[var(--color-text-tertiary)]">
                  Use the inspector to review tools, events, memory, and outputs.
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .welcome-root {
    position: relative;
    display: flex;
    min-height: 100%;
    align-items: center;
    justify-content: center;
    overflow: auto;
    padding: 1.5rem;
  }

  .welcome-backdrop {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(circle at top left, rgba(177, 197, 255, 0.16), transparent 38%),
      radial-gradient(circle at 82% 18%, rgba(137, 208, 237, 0.14), transparent 32%),
      linear-gradient(180deg, rgba(18, 19, 24, 0.12), rgba(18, 19, 24, 0));
    pointer-events: none;
  }

  .welcome-shell {
    position: relative;
    width: 100%;
    max-width: 76rem;
  }

  .welcome-grid {
    display: grid;
    gap: 1.25rem;
  }

  .welcome-content,
  .welcome-side-panel {
    border: 1px solid color-mix(in srgb, var(--color-outline) 24%, var(--color-outline-variant));
    background:
      linear-gradient(180deg, rgba(30, 31, 37, 0.96), rgba(18, 19, 24, 0.94)),
      var(--color-bg-secondary);
    box-shadow: var(--shadow-lg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
  }

  .welcome-content {
    border-radius: 2rem;
    padding: 2rem;
  }

  .welcome-side-panel {
    border-radius: 1.75rem;
    padding: 1.5rem;
  }

  .welcome-shortcut-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    border-radius: 9999px;
    border: 1px solid color-mix(in srgb, var(--color-outline) 20%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-bg-secondary) 80%, transparent);
    padding: 0.35rem 0.75rem 0.35rem 0.4rem;
  }

  .welcome-shortcut-key {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.375rem;
    border: 1px solid color-mix(in srgb, var(--color-outline) 28%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-bg-tertiary) 82%, transparent);
    padding: 0.2rem 0.45rem;
    font-size: 0.625rem;
    font-family: var(--font-mono, monospace);
    color: var(--color-text-secondary);
  }

  .welcome-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    border-radius: 9999px;
    border: 1px solid color-mix(in srgb, var(--color-outline) 22%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-bg-secondary) 86%, transparent);
    padding: 0.45rem 0.75rem;
    color: var(--color-text-secondary);
  }

  .welcome-pill_connected {
    border-color: color-mix(in srgb, var(--color-tertiary) 28%, var(--color-outline-variant));
    color: var(--color-tertiary);
  }

  .welcome-pill_disconnected {
    border-color: color-mix(in srgb, var(--color-error) 28%, var(--color-outline-variant));
    color: var(--color-error);
  }

  .welcome-status-dot {
    height: 0.45rem;
    width: 0.45rem;
    border-radius: 9999px;
    background: var(--color-tertiary);
    box-shadow: 0 0 0 4px rgba(137, 208, 237, 0.12);
  }

  .welcome-status-dot_disconnected {
    background: var(--color-error);
    box-shadow: 0 0 0 4px rgba(255, 180, 171, 0.12);
  }

  .welcome-primary-action,
  .welcome-secondary-action,
  .welcome-recent-item,
  .welcome-step {
    border: 1px solid color-mix(in srgb, var(--color-outline) 24%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-bg-secondary) 94%, transparent);
  }

  .welcome-primary-action,
  .welcome-secondary-action {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 0.9rem;
    border-radius: 1.25rem;
    padding: 1rem 1.1rem;
    text-align: left;
    transition:
      transform var(--transition-fast),
      border-color var(--transition-fast),
      background-color var(--transition-fast),
      box-shadow var(--transition-fast);
  }

  .welcome-primary-action:hover,
  .welcome-secondary-action:hover,
  .welcome-recent-item:hover {
    transform: translateY(-1px);
  }

  .welcome-primary-action:hover {
    border-color: color-mix(in srgb, var(--color-tertiary) 36%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-tertiary) 10%, var(--color-bg-secondary));
    box-shadow: var(--shadow-md);
  }

  .welcome-secondary-action:hover {
    border-color: color-mix(in srgb, var(--color-primary) 34%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-primary) 8%, var(--color-bg-secondary));
    box-shadow: var(--shadow-md);
  }

  .welcome-action-icon {
    display: inline-flex;
    height: 2.75rem;
    width: 2.75rem;
    align-items: center;
    justify-content: center;
    border-radius: 1rem;
  }

  .welcome-action-icon_primary {
    background: rgba(137, 208, 237, 0.14);
    color: var(--color-tertiary);
  }

  .welcome-action-icon_secondary {
    background: rgba(177, 197, 255, 0.14);
    color: var(--color-primary);
  }

  .welcome-recent-item,
  .welcome-step {
    border-radius: 1.1rem;
    padding: 0.95rem 1rem;
  }

  .welcome-recent-item {
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
    gap: 0.75rem;
    text-align: left;
    transition:
      transform var(--transition-fast),
      border-color var(--transition-fast),
      background-color var(--transition-fast);
  }

  .welcome-recent-item:hover {
    border-color: color-mix(in srgb, var(--color-tertiary) 28%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-tertiary) 8%, var(--color-bg-secondary));
  }

  .welcome-open-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 9999px;
    padding: 0.35rem 0.7rem;
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--color-tertiary);
    background: rgba(137, 208, 237, 0.12);
  }

  .welcome-step {
    display: flex;
    align-items: flex-start;
    gap: 0.9rem;
  }

  .welcome-step-index {
    display: inline-flex;
    height: 1.65rem;
    width: 1.65rem;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    border-radius: 9999px;
    background: rgba(137, 208, 237, 0.14);
    color: var(--color-tertiary);
    font-size: 0.75rem;
    font-weight: 700;
  }

  @media (min-width: 1024px) {
    .welcome-grid {
      grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
      align-items: stretch;
    }

    .welcome-content {
      padding: 2.4rem;
    }
  }

  @media (max-width: 640px) {
    .welcome-root {
      padding: 1rem;
    }

    .welcome-content,
    .welcome-side-panel {
      border-radius: 1.5rem;
    }

    .welcome-content {
      padding: 1.4rem;
    }

    .welcome-side-panel {
      padding: 1.1rem;
    }
  }
</style>
