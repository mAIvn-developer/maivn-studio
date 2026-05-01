<script lang="ts">
  import type { AppDetails, SessionStatus } from "$lib/types";
  import { ChevronRight, Menu, PanelRight, RotateCw, Square, Timer } from "lucide-svelte";
  import ThemeToggle from "../ui/ThemeToggle.svelte";
  import Tooltip from "../ui/Tooltip.svelte";

  interface Props {
    app: AppDetails | null;
    sessionStatus: SessionStatus | null;
    isActive: boolean;
    showEvents: boolean;
    onNewThread: () => void;
    onToggleEvents: () => void;
    /** Optional: only wired in mobile/tablet shells where the sidebar is a slide-in overlay. */
    onOpenMobileSidebar?: () => void;
  }

  let {
    app,
    sessionStatus,
    isActive,
    showEvents,
    onNewThread,
    onToggleEvents,
    onOpenMobileSidebar,
  }: Props = $props();

  // Status styling
  const statusStyles: Record<string, { bg: string; text: string; dot: string }> = {
    ready: {
      bg: "bg-[var(--color-secondary)]/15",
      text: "text-[var(--color-secondary)]",
      dot: "bg-[var(--color-secondary)]",
    },
    running: {
      bg: "bg-[var(--color-primary)]/15",
      text: "text-[var(--color-primary)]",
      dot: "bg-[var(--color-primary)]",
    },
    waiting_input: {
      bg: "bg-[var(--color-warning)]/15",
      text: "text-[var(--color-warning)]",
      dot: "bg-[var(--color-warning)]",
    },
    failed: {
      bg: "bg-[var(--color-error)]/15",
      text: "text-[var(--color-error)]",
      dot: "bg-[var(--color-error)]",
    },
    completed: {
      bg: "bg-[var(--color-outline)]/15",
      text: "text-[var(--color-text-secondary)]",
      dot: "bg-[var(--color-outline)]",
    },
  };

  const currentStyle = $derived(
    sessionStatus ? statusStyles[sessionStatus] || statusStyles.ready : null,
  );
  const appSummary = $derived(
    (() => {
      if (!app) return [];
      const authoredToolCount = app.tools.length;
      const runtimeToolCount = app.runtime_tool_count ?? authoredToolCount;
      return [
        runtimeToolCount !== authoredToolCount
          ? `${runtimeToolCount} runtime tools`
          : `${runtimeToolCount} tools`,
        runtimeToolCount !== authoredToolCount ? `${authoredToolCount} authored tools` : null,
        `${app.agents.length} agents`,
        app.swarms.length > 0 ? `${app.swarms.length} swarms` : null,
      ].filter((value): value is string => Boolean(value));
    })(),
  );

  // Session timer
  let sessionStartTime = $state<number | null>(null);
  let elapsed = $state("");
  let timerInterval: ReturnType<typeof setInterval> | null = null;

  function updateElapsedDisplay() {
    if (!sessionStartTime) {
      elapsed = "";
      return;
    }

    const ms = Date.now() - sessionStartTime;
    const secs = Math.floor(ms / 1000);
    const mins = Math.floor(secs / 60);
    elapsed = mins > 0 ? `${mins}m ${secs % 60}s` : `${secs}s`;
  }

  $effect(() => {
    if (sessionStatus === "running" && !sessionStartTime) {
      sessionStartTime = Date.now();
    } else if (!isActive) {
      sessionStartTime = null;
      elapsed = "";
    } else if (sessionStatus !== "running" && sessionStartTime) {
      updateElapsedDisplay();
    }
  });

  $effect(() => {
    if (timerInterval) clearInterval(timerInterval);

    if (sessionStartTime && sessionStatus === "running") {
      timerInterval = setInterval(() => {
        updateElapsedDisplay();
      }, 1000);
    } else if (!isActive || !sessionStartTime) {
      elapsed = "";
    }

    return () => {
      if (timerInterval) clearInterval(timerInterval);
    };
  });
</script>

<header
  class="studio-toolbar flex min-h-16 items-center justify-between
         border-b border-[var(--color-outline-variant)]
         px-4 py-2.5 shrink-0 backdrop-blur-md"
  role="toolbar"
  aria-label="Session controls"
>
  <div class="flex min-w-0 items-center gap-3">
    {#if onOpenMobileSidebar}
      <button
        type="button"
        class="mobile-sidebar-trigger inline-flex h-9 w-9 items-center justify-center
               rounded-xl border border-[var(--color-outline-variant)]
               bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]
               hover:bg-[var(--color-surface-variant)] transition-colors lg:hidden"
        onclick={onOpenMobileSidebar}
        aria-label="Open app catalog"
      >
        <Menu size={16} />
      </button>
    {/if}
    {#if app}
      <div
        class="hidden h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]/85 text-sm font-semibold text-[var(--color-secondary)] shadow-[var(--shadow-sm)] sm:flex"
      >
        {app.name.slice(0, 2).toUpperCase()}
      </div>
      <div class="min-w-0">
        <div class="flex min-w-0 items-center gap-2">
          <span
            class="max-w-[10rem] truncate text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-tertiary)] sm:max-w-none"
          >
            {app.category}
          </span>
          <ChevronRight size={12} class="shrink-0 text-[var(--color-text-tertiary)]" />
          <span class="truncate text-sm font-semibold text-[var(--color-text)] sm:text-base"
            >{app.name}</span
          >
        </div>
        {#if appSummary.length > 0}
          <div
            class="mt-1 hidden flex-wrap items-center gap-2 text-[11px] text-[var(--color-text-tertiary)] sm:flex"
          >
            {#each appSummary as item}
              <span
                class="rounded-full border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]/80 px-2 py-0.5"
              >
                {item}
              </span>
            {/each}
          </div>
        {/if}
      </div>
    {:else}
      <div>
        <div
          class="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-tertiary)]"
        >
          Studio Workspace
        </div>
        <div class="mt-1 text-sm text-[var(--color-text-secondary)]">
          Choose an app to start a session.
        </div>
      </div>
    {/if}

    {#if sessionStatus && currentStyle}
      <div
        class="ml-1 flex items-center gap-1.5 rounded-full border border-transparent px-2.5 py-1 {currentStyle.bg}"
      >
        <span
          class="h-1.5 w-1.5 rounded-full {currentStyle.dot}"
          class:animate-pulse={sessionStatus === "running"}
        ></span>
        <span class="text-[10px] font-medium capitalize {currentStyle.text}">
          {sessionStatus === "waiting_input" ? "waiting" : sessionStatus}
        </span>
      </div>
    {/if}

    {#if elapsed}
      <div
        class="hidden items-center gap-1 rounded-full border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]/70 px-2.5 py-1 text-[var(--color-text-tertiary)] sm:flex"
      >
        <Timer size={12} />
        <span class="text-[10px] font-mono tabular-nums">{elapsed}</span>
      </div>
    {/if}
  </div>

  <div class="flex items-center gap-2">
    <ThemeToggle compact class="hidden sm:inline-flex" />

    {#if isActive}
      <Tooltip text="End session & start new" shortcut="Ctrl+Alt+N">
        <button
          class="flex items-center gap-1.5 rounded-xl border border-[var(--color-error)]/20 px-3 py-2 text-xs font-medium
                 bg-[var(--color-error)]/12 text-[var(--color-error)] shadow-[var(--shadow-sm)]
                 hover:bg-[var(--color-error)]/20 transition-colors"
          onclick={onNewThread}
        >
          <Square size={14} />
          <span class="hidden sm:inline">New Thread</span>
        </button>
      </Tooltip>
    {:else if app}
      <!-- Show New Thread whenever an app is loaded so users always have a
           reset affordance — even before the first session, and especially
           in Schedule mode where they may want to clear the runs panel. -->
      <Tooltip text="Start a new thread" shortcut="Ctrl+Alt+N">
        <button
          class="flex items-center gap-1.5 rounded-xl border border-[var(--color-outline-variant)] px-3 py-2 text-xs font-medium
                 bg-[var(--color-bg-tertiary)]/88 text-[var(--color-text-secondary)] shadow-[var(--shadow-sm)]
                 hover:bg-[var(--color-surface-variant)] transition-colors"
          onclick={onNewThread}
        >
          <RotateCw size={14} />
          <span class="hidden sm:inline">New Thread</span>
        </button>
      </Tooltip>
    {/if}

    <Tooltip text="Toggle inspector panel" shortcut="Ctrl+Shift+E">
      <button
        class={`flex h-10 w-10 items-center justify-center rounded-xl border transition-colors ${
          showEvents
            ? "border-[var(--color-secondary)]/30 bg-[var(--color-secondary)] text-[var(--color-on-secondary)]"
            : "border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-variant)]"
        }`}
        onclick={onToggleEvents}
        aria-label={showEvents ? "Hide inspector panel" : "Show inspector panel"}
        aria-pressed={showEvents}
      >
        <PanelRight size={16} />
      </button>
    </Tooltip>
  </div>
</header>

<style>
  .studio-toolbar {
    position: relative;
    z-index: 80;
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--color-bg-secondary) 96%, transparent),
      color-mix(in srgb, var(--color-bg-secondary) 84%, transparent)
    );
  }
</style>
