<script lang="ts">
  import ChatPanel from "$lib/components/chat/ChatPanel.svelte";
  import InspectorPanel from "$lib/components/panels/InspectorPanel.svelte";
  import ResizablePanel from "$lib/components/ResizablePanel.svelte";
  import CollapsedSidebarRail from "$lib/components/sidebar/CollapsedSidebarRail.svelte";
  import DemoList from "$lib/components/sidebar/DemoList.svelte";
  import SidebarHeader from "$lib/components/sidebar/SidebarHeader.svelte";
  import CommandPalette from "$lib/components/studio-shell/CommandPalette.svelte";
  import RepoDiscoveryModal from "$lib/components/studio-shell/RepoDiscoveryModal.svelte";
  import StudioNotifications from "$lib/components/studio-shell/StudioNotifications.svelte";
  import Toolbar from "$lib/components/studio-shell/Toolbar.svelte";
  import WelcomeScreen from "$lib/components/studio-shell/WelcomeScreen.svelte";
  import { createDiscoveryActions } from "$lib/pages/studio/discovery-actions";
  import { formatMemoryIndexedToastDetails as formatMemoryIndexedToastDetailsHelper } from "$lib/pages/studio/memory-toast";
  import { createPromptActions } from "$lib/pages/studio/prompt-actions";
  import {
    getCollapsedDemoLabel as getCollapsedDemoLabelHelper,
    loadRecentDemos as loadStoredRecentDemos,
    updateRecentDemos,
  } from "$lib/pages/studio/recent-demos";
  import { createStudioSessionActions } from "$lib/pages/studio/session-actions";
  import { useDemos } from "$lib/stores/demos.svelte";
  import { useSession } from "$lib/stores/session/index.svelte";
  import type {
    BatchInvocationConfig,
    Demo,
    ModelToolOption,
    RepoScanItem,
    SavedPrompt,
    StructuredOutputConfig,
  } from "$lib/types";
  import { externalLinks } from "$lib/utils/external-links";
  import { handleGlobalKeydown, registerShortcut } from "$lib/utils/shortcuts";
  import { AlertCircle, RotateCw, Terminal } from "lucide-svelte";
  import { onMount } from "svelte";

  const demos = useDemos();
  const session = useSession();

  // MARK: UI State

  const SIDEBAR_COLLAPSED_KEY = "maivn.studio.sidebarCollapsed";
  const SHOW_EVENTS_KEY = "maivn.studio.showInspector";

  let showEvents = $state(true);
  let sidebarCollapsed = $state(false);
  let mobileSidebarOpen = $state(false);
  let commandPaletteOpen = $state(false);
  let savedPrompts = $state<SavedPrompt[]>([]);
  let threadResetRevision = $state(0);
  let errorDismissTimer: ReturnType<typeof setTimeout> | null = null;
  let errorProgress = $state(100);

  // Discovery modal state
  let discoveryOpen = $state(false);
  let discoveryLoading = $state(false);
  let discoveryError = $state<string | null>(null);
  let discoveryItems = $state<RepoScanItem[]>([]);
  let discoverySelections = $state(new Set<string>());

  // Recent demos for welcome screen
  let recentDemoObjects = $state<Demo[]>([]);

  // Derived state
  const isConnected = $derived(!demos.connecting && !demos.error);
  const sessionStatus = $derived(session.session?.status ?? null);

  // Structured output state (lifted from ChatPanel for cross-component sharing)
  let structuredOutputConfig = $state<StructuredOutputConfig>({ enabled: false });
  let selectedVariant = $state<string | undefined>(undefined);
  const availableModelTools = $derived<ModelToolOption[]>(
    demos.selectedDemo?.tools
      ? demos.selectedDemo.tools.map((tool) => ({
          name: tool.name,
          description: tool.description,
        }))
      : [],
  );

  // MARK: Keyboard Shortcuts

  onMount(() => {
    if (typeof localStorage !== "undefined") {
      sidebarCollapsed = localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
      const storedShowEvents = localStorage.getItem(SHOW_EVENTS_KEY);
      if (storedShowEvents !== null) {
        showEvents = storedShowEvents === "1";
      }
    }

    demos.loadDemos();
    loadRecentDemos();

    const unregisterShortcuts = [
      registerShortcut({
        key: "k",
        ctrl: true,
        label: "Command Palette",
        shortcutDisplay: "Ctrl+K",
        action: () => {
          commandPaletteOpen = !commandPaletteOpen;
        },
      }),
      registerShortcut({
        key: "n",
        ctrl: true,
        alt: true,
        label: "New Thread",
        shortcutDisplay: "Ctrl+Alt+N",
        action: handleNewThreadRequest,
      }),
      registerShortcut({
        key: "e",
        ctrl: true,
        shift: true,
        label: "Toggle Inspector Panel",
        shortcutDisplay: "Ctrl+Shift+E",
        action: () => {
          showEvents = !showEvents;
        },
      }),
      registerShortcut({
        key: "Escape",
        label: "Close",
        shortcutDisplay: "Esc",
        action: () => {
          if (commandPaletteOpen) commandPaletteOpen = false;
          else if (discoveryOpen) discoveryOpen = false;
          else if (mobileSidebarOpen) mobileSidebarOpen = false;
        },
      }),
    ];

    return () => {
      unregisterShortcuts.forEach((unregister) => unregister());
    };
  });

  // MARK: Effects

  // Persist UI preferences across reloads
  $effect(() => {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, sidebarCollapsed ? "1" : "0");
  });

  // Auto-close the mobile sidebar drawer once a demo is selected — without
  // this, the user is left looking at the still-open sidebar over their
  // freshly-loaded chat panel.
  $effect(() => {
    if (demos.selectedDemo && mobileSidebarOpen) {
      mobileSidebarOpen = false;
    }
  });

  $effect(() => {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(SHOW_EVENTS_KEY, showEvents ? "1" : "0");
  });

  // Load saved prompts when a demo is selected
  $effect(() => {
    if (demos.selectedDemo) {
      loadSavedPrompts(demos.selectedDemo.id);
    } else {
      savedPrompts = [];
    }
  });

  // Apply default invocation config when demo changes
  $effect(() => {
    const defaults = demos.selectedDemo?.defaultInvocation;
    session.setInvocationConfig({
      force_final_tool: false,
      stream_response: true,
      ...defaults,
    });
  });

  // Auto-dismiss error after 5 seconds with progress
  $effect(() => {
    const clearErrorTimer = () => {
      if (errorDismissTimer) {
        clearTimeout(errorDismissTimer);
        errorDismissTimer = null;
      }
    };

    clearErrorTimer();

    if (!session.error) {
      errorProgress = 100;
      return clearErrorTimer;
    }

    errorProgress = 100;
    const startTime = Date.now();
    const duration = 5000;

    const tick = () => {
      const elapsed = Date.now() - startTime;
      errorProgress = Math.max(0, 100 - (elapsed / duration) * 100);

      if (elapsed < duration) {
        errorDismissTimer = setTimeout(tick, 50);
      } else {
        session.clearError?.();
      }
    };

    errorDismissTimer = setTimeout(tick, 50);

    return clearErrorTimer;
  });

  // MARK: Recent Demos

  function loadRecentDemos() {
    recentDemoObjects = loadStoredRecentDemos();
  }

  function addRecentDemo(demo: Demo) {
    recentDemoObjects = updateRecentDemos(recentDemoObjects, demo);
  }

  function getCollapsedDemoLabel(name: string): string {
    return getCollapsedDemoLabelHelper(name);
  }

  function refreshSelectedDemoDetails(): void {
    if (demos.selectedDemoId) {
      void demos.selectDemo(demos.selectedDemoId, selectedVariant);
    }
  }

  function handleSelectedVariantChange(variant: string | undefined): void {
    selectedVariant = variant;
    session.setPrivateData({});
    refreshSelectedDemoDetails();
  }

  const { loadSavedPrompts, handleSavePrompt } = createPromptActions({
    getSelectedDemo: () => demos.selectedDemo,
    getMessageType: () => session.messageType,
    getSavedPrompts: () => savedPrompts,
    setSavedPrompts: (prompts) => {
      savedPrompts = prompts;
    },
  });

  // MARK: Saved Prompts

  // MARK: Discovery

  const {
    openDiscovery,
    rescanDiscovery,
    toggleDiscoverySelection,
    selectAllDiscoveries,
    clearDiscoverySelections,
    applyDiscoverySelections,
  } = createDiscoveryActions({
    getDiscoveryItems: () => discoveryItems,
    setDiscoveryItems: (items) => {
      discoveryItems = items;
    },
    getDiscoverySelections: () => discoverySelections,
    setDiscoverySelections: (selections) => {
      discoverySelections = selections;
    },
    setDiscoveryOpen: (open) => {
      discoveryOpen = open;
    },
    setDiscoveryLoading: (loading) => {
      discoveryLoading = loading;
    },
    getDiscoveryError: () => discoveryError,
    setDiscoveryError: (error) => {
      discoveryError = error;
    },
    reloadDemos: () => demos.loadDemos(),
  });

  // MARK: Session Handlers

  const {
    handleSelectDemo,
    handleStart,
    handleSend,
    handleMessageTypeChange,
    handleStructuredOutputChange,
    handlePrivateDataChange,
    handleNewThread,
    handleCommandPaletteAction,
  } = createStudioSessionActions({
    getSelectedDemo: () => demos.selectedDemo,
    selectDemo: (demoId) => {
      selectedVariant = undefined;
      void demos.selectDemo(demoId);
    },
    addRecentDemo,
    resetSession: () => {
      session.reset();
    },
    startSession: (demoId, message, options) => {
      session.startSession(demoId, message, options);
    },
    sendMessage: (
      message,
      messageType,
      structuredOutput,
      attachments,
      batch?: BatchInvocationConfig,
    ) => {
      session.send(message, messageType, structuredOutput, attachments, batch);
    },
    setMessageType: (type) => {
      session.setMessageType(type);
    },
    setPrivateData: (data) => {
      session.setPrivateData(data);
    },
    setStructuredOutputConfig: (config) => {
      structuredOutputConfig = config;
    },
    getSession: () => session.session,
    endSession: () => session.end(),
    getShowEvents: () => showEvents,
    setShowEvents: (value) => {
      showEvents = value;
    },
    openDiscovery,
  });

  function handleNewThreadRequest(): void {
    handleNewThread();
    threadResetRevision += 1;
  }

  function handleCommandPaletteActionRequest(actionId: string): void {
    if (actionId === "new-thread") {
      handleNewThreadRequest();
      return;
    }
    handleCommandPaletteAction(actionId);
  }

  function dismissError() {
    if (errorDismissTimer) {
      clearTimeout(errorDismissTimer);
    }
    session.clearError?.();
  }

  function formatMemoryIndexedToastDetails(): string {
    return formatMemoryIndexedToastDetailsHelper(session.memoryIndexedToast?.details);
  }

  // MARK: Command Palette Handlers
</script>

<svelte:window onkeydown={handleGlobalKeydown} />

<div
  class="studio-shell flex h-screen overflow-hidden bg-[var(--color-bg)]"
  class:mobile-sidebar-open={mobileSidebarOpen}
>
  {#if mobileSidebarOpen}
    <!-- Backdrop closes the mobile sidebar when tapped. Pointer-only — keyboard users have ESC. -->
    <button
      type="button"
      class="studio-mobile-backdrop"
      onclick={() => (mobileSidebarOpen = false)}
      aria-label="Close navigation"
    ></button>
  {/if}

  <!-- Sidebar -->
  <div class="studio-sidebar-wrapper" class:is-open={mobileSidebarOpen}>
    <ResizablePanel
      side="left"
      defaultWidth={sidebarCollapsed ? 72 : 320}
      minWidth={sidebarCollapsed ? 72 : 200}
      maxWidth={sidebarCollapsed ? 72 : 500}
    >
      <nav
        class="studio-sidebar h-full flex flex-col border-r border-[var(--color-outline-variant)]"
        aria-label="Demo browser"
      >
        <!-- Sidebar Header -->
        <SidebarHeader
          collapsed={sidebarCollapsed}
          connected={isConnected}
          onToggleCollapse={() => (sidebarCollapsed = !sidebarCollapsed)}
          onOpenCommandPalette={() => (commandPaletteOpen = true)}
        />

        <!-- Demo List -->
        {#if !sidebarCollapsed}
          <div class="flex-1 min-h-0 overflow-y-auto">
            {#if demos.connecting}
              <div class="flex h-40 flex-col items-center justify-center gap-3 px-4">
                <div
                  class="h-8 w-8 rounded-full border-2 border-[var(--color-secondary)]/30
                       border-t-[var(--color-secondary)] animate-spin"
                ></div>
                <p class="text-sm font-medium text-[var(--color-text-secondary)]">
                  Connecting to server...
                </p>
                <p class="text-center text-xs text-[var(--color-text-tertiary)]">
                  Fetching demo metadata and preparing the Studio catalog.
                </p>
              </div>
            {:else if demos.loading && Object.keys(demos.byCategory).length === 0}
              <div class="flex h-40 flex-col items-center justify-center gap-3 px-4">
                <div
                  class="h-8 w-8 rounded-full border-2 border-[var(--color-secondary)]/30
                       border-t-[var(--color-secondary)] animate-spin"
                ></div>
                <p class="text-sm font-medium text-[var(--color-text-secondary)]">
                  Loading demos...
                </p>
                <p class="text-center text-xs text-[var(--color-text-tertiary)]">
                  Indexing available demos so you can jump in quickly.
                </p>
              </div>
            {:else if demos.error}
              <div class="p-4">
                <div
                  class="rounded-2xl border border-[var(--color-error)]/25 bg-[var(--color-error-container)]/40
                       p-4 text-sm shadow-[var(--shadow-md)]"
                >
                  <div class="flex items-start gap-2.5 text-[var(--color-error)]">
                    <AlertCircle size={16} class="mt-0.5 shrink-0" />
                    <div class="min-w-0 flex-1">
                      <div class="font-medium">Studio backend isn't responding</div>
                      <div
                        class="mt-1 break-words text-xs text-[var(--color-on-error-container)]/90"
                      >
                        {demos.error}
                      </div>
                    </div>
                  </div>

                  <div class="mt-3 grid gap-2 text-[11px] text-[var(--color-text-tertiary)]">
                    <p
                      class="font-medium uppercase tracking-[0.12em] text-[var(--color-text-secondary)]"
                    >
                      Try this
                    </p>
                    <div class="flex items-start gap-2">
                      <Terminal size={12} class="mt-0.5 shrink-0 text-[var(--color-secondary)]" />
                      <div>
                        <p class="text-[var(--color-text)]">Launch Studio from your project</p>
                        <code
                          class="mt-1 inline-block rounded-md bg-[var(--color-bg-tertiary)] px-1.5 py-0.5
                               text-[10.5px] font-mono text-[var(--color-text-secondary)]"
                        >
                          maivn studio
                        </code>
                        <p class="mt-1 text-[var(--color-text-tertiary)]">
                          Run from the directory that holds your demos so Studio can index them. If <code
                            class="inline-code">maivn</code
                          >
                          isn't on your PATH, install with
                          <code class="inline-code">uv pip install "maivn[studio]"</code>.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div class="mt-3 flex items-center gap-2">
                    <button
                      type="button"
                      onclick={() => demos.loadDemos()}
                      class="inline-flex items-center gap-1.5 rounded-md
                           border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]/80
                           px-2.5 py-1.5 text-xs font-medium text-[var(--color-text)]
                           hover:bg-[var(--color-bg-elevated)] transition-colors"
                    >
                      <RotateCw size={12} />
                      Retry
                    </button>
                    <a
                      href={externalLinks.developerPortalDocs()}
                      target="_blank"
                      rel="noreferrer"
                      class="inline-flex items-center gap-1 text-xs text-[var(--color-text-tertiary)]
                           hover:text-[var(--color-text-secondary)] transition-colors"
                    >
                      Open setup docs
                    </a>
                  </div>
                </div>
              </div>
            {:else}
              <DemoList
                demos={demos.byCategory}
                selectedId={demos.selectedDemoId ?? demos.selectedDemo?.id}
                onSelect={handleSelectDemo}
                onScanRepo={openDiscovery}
              />
            {/if}
          </div>
        {:else}
          <CollapsedSidebarRail
            connecting={demos.connecting}
            loading={demos.loading}
            error={demos.error}
            selectedDemoId={demos.selectedDemoId ?? demos.selectedDemo?.id}
            selectedDemoName={demos.selectedDemo?.name}
            recentDemos={recentDemoObjects}
            onOpenCommandPalette={() => (commandPaletteOpen = true)}
            onOpenDiscovery={openDiscovery}
            onSelectDemo={handleSelectDemo}
            {getCollapsedDemoLabel}
          />
        {/if}
      </nav>
    </ResizablePanel>
  </div>

  <!-- Main content -->
  <main class="studio-main flex flex-1 flex-col min-w-0">
    <!-- Toolbar -->
    <Toolbar
      demo={demos.selectedDemo}
      {sessionStatus}
      isActive={session.hasActiveSession}
      {showEvents}
      onNewThread={handleNewThreadRequest}
      onToggleEvents={() => (showEvents = !showEvents)}
      onOpenMobileSidebar={() => (mobileSidebarOpen = true)}
    />

    <!-- Content area -->
    <div class="flex flex-1 min-h-0 overflow-hidden">
      <!-- Chat / Welcome -->
      <div
        class="studio-content-panel flex flex-1 min-h-0 flex-col overflow-hidden border-r border-[var(--color-outline-variant)]"
      >
        {#if demos.selectedDemo}
          <ChatPanel
            demo={demos.selectedDemo}
            chatFlowItems={session.filteredChatFlowItems}
            loading={session.loading}
            canSend={session.session?.can_send_message ?? false}
            canStageNext={session.canStageNext}
            queuedMessageCount={session.queuedMessageCount}
            hasActiveSession={session.hasActiveSession}
            messageType={session.messageType}
            bind:selectedVariant
            {structuredOutputConfig}
            {availableModelTools}
            {savedPrompts}
            showToolArgs={session.filters.showToolArgs}
            expandAllCards={session.filters.expandAllCards}
            richResultDisplay={session.filters.richResultDisplay}
            showStructuredOutput={session.filters.showStructuredOutput}
            showSessionDetails={session.filters.showSessionDetails}
            currentPhaseMessage={session.currentPhaseMessage}
            interruptStyle={session.interruptStyle}
            pendingInterrupts={session.pendingInterrupts}
            onSend={handleSend}
            onStart={handleStart}
            {threadResetRevision}
            onCancel={() => session.cancel()}
            onMessageTypeChange={handleMessageTypeChange}
            onSelectedVariantChange={handleSelectedVariantChange}
            onStructuredOutputChange={handleStructuredOutputChange}
            onSavePrompt={handleSavePrompt}
            onSubmitInterrupt={session.submitInterrupt}
            onCancelInterrupt={session.cancelInterrupt}
          />
        {:else}
          <WelcomeScreen
            onOpenCommandPalette={() => (commandPaletteOpen = true)}
            onScanRepo={openDiscovery}
            recentDemos={recentDemoObjects}
            onSelectDemo={handleSelectDemo}
            demoCount={Object.values(demos.byCategory).reduce((sum, arr) => sum + arr.length, 0)}
            connected={isConnected}
          />
        {/if}
      </div>

      <!-- Inspector panel (replaces EventPanel). Hidden on the welcome screen
           so the welcome content has room to breathe — there's nothing useful
           to inspect until a demo is selected. -->
      {#if showEvents && demos.selectedDemo}
        <ResizablePanel side="right" defaultWidth={380} minWidth={280} maxWidth={560}>
          <div
            class="studio-inspector-panel h-full overflow-hidden border-l border-[var(--color-outline-variant)]"
          >
            {#if demos.connecting || (demos.loading && !demos.selectedDemo)}
              <div class="flex h-full flex-col items-center justify-center gap-3">
                <div
                  class="h-8 w-8 rounded-full border-2 border-[var(--color-secondary)]/30
                         border-t-[var(--color-secondary)] animate-spin"
                ></div>
                <p class="text-sm text-[var(--color-text-secondary)]">
                  {demos.connecting ? "Connecting to server..." : "Loading demo..."}
                </p>
              </div>
            {:else}
              <InspectorPanel
                events={session.events}
                filters={session.filters}
                eventSummary={session.eventSummary}
                accumulatedStats={session.accumulatedStats}
                privateDataSchema={demos.selectedDemo?.privateDataSchema ?? []}
                privateData={session.privateData}
                privateDataDefaults={demos.selectedDemo?.privateDataDefaults ?? {}}
                hasActiveSession={session.hasActiveSession}
                agents={demos.selectedDemo?.agents ?? []}
                swarms={demos.selectedDemo?.swarms ?? []}
                demoId={demos.selectedDemo?.id ?? ""}
                invocationConfig={session.invocationConfig}
                availableTools={demos.selectedDemo?.tools?.map((t) => t.name) ?? []}
                {structuredOutputConfig}
                {availableModelTools}
                interruptStyle={session.interruptStyle}
                extractedSkills={session.extractedSkills}
                extractedInsights={session.extractedInsights}
                retrievedMemoryContext={session.retrievedMemoryContext}
                memoryConfig={session.memoryConfig}
                onFilterChange={session.setFilters}
                onPrivateDataChange={handlePrivateDataChange}
                onDemoRefresh={refreshSelectedDemoDetails}
                onInvocationChange={session.setInvocationConfig}
                onStructuredOutputChange={handleStructuredOutputChange}
                onInterruptStyleChange={session.setInterruptStyle}
                onMemoryConfigChange={session.setMemoryConfig}
              />
            {/if}
          </div>
        </ResizablePanel>
      {/if}
    </div>
  </main>
</div>

<!-- Command Palette -->
<CommandPalette
  open={commandPaletteOpen}
  demos={demos.byCategory}
  onClose={() => (commandPaletteOpen = false)}
  onSelectDemo={handleSelectDemo}
  onAction={handleCommandPaletteActionRequest}
/>

<!-- Repo Discovery Modal -->
<RepoDiscoveryModal
  open={discoveryOpen}
  items={discoveryItems}
  loading={discoveryLoading}
  error={discoveryError}
  selectedKeys={discoverySelections}
  onClose={() => (discoveryOpen = false)}
  onToggle={toggleDiscoverySelection}
  onSelectAll={selectAllDiscoveries}
  onClear={clearDiscoverySelections}
  onRescan={rescanDiscovery}
  onApply={applyDiscoverySelections}
/>

<StudioNotifications
  memoryIndexedToast={session.memoryIndexedToast}
  error={session.error}
  {errorProgress}
  onDismissError={dismissError}
  {formatMemoryIndexedToastDetails}
/>

<style>
  .studio-shell {
    background:
      radial-gradient(
        circle at top left,
        color-mix(in srgb, var(--color-primary) 8%, transparent),
        transparent 30%
      ),
      radial-gradient(
        circle at 84% 18%,
        color-mix(in srgb, var(--color-secondary) 8%, transparent),
        transparent 24%
      ),
      var(--color-bg);
  }

  .studio-sidebar {
    background:
      linear-gradient(
        180deg,
        color-mix(in srgb, var(--color-bg-secondary) 98%, transparent),
        color-mix(in srgb, var(--color-bg-dim) 98%, transparent)
      ),
      var(--color-bg);
  }

  .studio-main {
    background:
      linear-gradient(
        180deg,
        color-mix(in srgb, var(--color-bg-dim) 60%, transparent),
        color-mix(in srgb, var(--color-bg-dim) 92%, transparent)
      ),
      transparent;
  }

  .studio-content-panel,
  .studio-inspector-panel {
    background: var(--color-bg);
  }

  .studio-sidebar-wrapper {
    display: contents;
  }

  .studio-mobile-backdrop {
    display: none;
  }

  /*
   * Tablet + mobile: the sidebar's 320px would crush the welcome panel
   * down to a sliver, so we turn it into a slide-in overlay instead. The
   * Toolbar grows a hamburger button (`onOpenMobileSidebar`) to reveal
   * it; the backdrop and Esc both dismiss.
   */
  @media (max-width: 1023px) {
    .studio-sidebar-wrapper {
      display: block;
      position: fixed;
      inset: 0 auto 0 0;
      z-index: 70;
      width: min(320px, 88vw);
      transform: translateX(-100%);
      transition: transform 220ms cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: var(--shadow-lg);
    }

    .studio-sidebar-wrapper.is-open {
      transform: translateX(0);
    }

    .studio-mobile-backdrop {
      position: fixed;
      inset: 0;
      z-index: 60;
      background: color-mix(in srgb, var(--color-bg-dim) 70%, transparent);
      backdrop-filter: blur(2px);
      -webkit-backdrop-filter: blur(2px);
      border: 0;
      padding: 0;
      cursor: pointer;
      display: block;
    }
  }

  /* Inline `code` styling used in the empty-state guidance copy. Keeps
     command names readable without bumping the font size. */
  :global(.inline-code) {
    font-family: "JetBrains Mono", "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 0.92em;
    padding: 0 0.25rem;
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-bg-tertiary) 70%, transparent);
    color: var(--color-text-secondary);
  }
</style>
