<script lang="ts">
  import type { AppDetails, SavedPrompt, SendableMessageType } from "$lib/types";
  import { CalendarClock, MessageSquareMore, Paperclip } from "lucide-svelte";
  import MessageTypeSelector from "./MessageTypeSelector.svelte";
  import PromptDropdown from "./PromptDropdown.svelte";

  type ComposerMode = "chat" | "schedule";

  interface Props {
    hasApp: boolean;
    hasActiveSession: boolean;
    canSend: boolean;
    loading: boolean;
    messageType: SendableMessageType;
    discoveredPrompts: AppDetails["prompts"];
    savedPrompts: SavedPrompt[];
    inputValue: string;
    composerMode: ComposerMode;
    onOpenFilePicker: () => void;
    onMessageTypeChange: (type: SendableMessageType) => void;
    onComposerModeChange?: (mode: ComposerMode) => void;
    onSavePrompt?: () => void;
    onSelectPrompt: (
      content: string,
      structuredOutputTool?: string,
      promptMessageType?: string,
      promptVariant?: string,
    ) => void;
    onFileInputChange: (event: Event) => void;
    bindFileInput?: HTMLInputElement | undefined;
  }

  let {
    hasApp,
    hasActiveSession,
    canSend,
    loading,
    messageType,
    discoveredPrompts,
    savedPrompts,
    inputValue,
    composerMode,
    onOpenFilePicker,
    onMessageTypeChange,
    onComposerModeChange,
    onSavePrompt,
    onSelectPrompt,
    onFileInputChange,
    bindFileInput = $bindable<HTMLInputElement | undefined>(undefined),
  }: Props = $props();
</script>

<div class="composer-toolbar">
  <button
    type="button"
    onclick={onOpenFilePicker}
    disabled={!hasApp || (hasActiveSession && !canSend) || loading}
    class="toolbar-button"
    title="Attach files"
    aria-label="Attach files"
  >
    <Paperclip size={14} />
    <span>Attach</span>
  </button>

  <PromptDropdown
    {savedPrompts}
    {discoveredPrompts}
    onSelect={onSelectPrompt}
    onSave={inputValue.trim() ? onSavePrompt : undefined}
    disabled={!hasApp}
  />

  <MessageTypeSelector value={messageType} onchange={onMessageTypeChange} disabled={!hasApp} />

  <div class="composer-mode-tabs" role="tablist" aria-label="Composer mode">
    <button
      type="button"
      class="composer-mode-tab"
      class:active={composerMode === "chat"}
      disabled={!hasApp}
      role="tab"
      aria-selected={composerMode === "chat"}
      onclick={() => onComposerModeChange?.("chat")}
    >
      <MessageSquareMore size={13} />
      <span>Send once</span>
    </button>
    <button
      type="button"
      class="composer-mode-tab"
      class:active={composerMode === "schedule"}
      disabled={!hasApp}
      role="tab"
      aria-selected={composerMode === "schedule"}
      onclick={() => onComposerModeChange?.("schedule")}
    >
      <CalendarClock size={13} />
      <span>Schedule</span>
    </button>
  </div>

  <input
    type="file"
    multiple
    class="hidden"
    bind:this={bindFileInput}
    onchange={onFileInputChange}
  />

  {#if inputValue.length > 100}
    <span class="char-count">
      {inputValue.length}
    </span>
  {/if}
</div>

<style>
  .composer-toolbar {
    --composer-control-height: 2.35rem;
    --composer-inner-control-height: var(--composer-control-height);
    display: flex;
    align-items: center;
    gap: 0.45rem;
    min-height: 2.85rem;
    border-bottom: 1px solid var(--color-outline-variant);
    border-radius: calc(var(--radius-lg) - 1px) calc(var(--radius-lg) - 1px) 0 0;
    background: color-mix(in srgb, var(--color-bg-secondary) 72%, transparent);
    padding: 0.5rem 0.65rem;
  }

  .toolbar-button {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    box-sizing: border-box;
    height: var(--composer-control-height);
    min-height: var(--composer-control-height);
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text-secondary);
    padding: 0 0.6rem;
    font-size: 0.75rem;
    font-weight: 600;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast);
  }

  .toolbar-button:hover:not(:disabled) {
    border-color: color-mix(in srgb, var(--color-secondary) 52%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-secondary) 8%, var(--color-bg));
    color: var(--color-text);
  }

  .toolbar-button:disabled {
    cursor: not-allowed;
    opacity: 0.42;
  }

  .char-count {
    margin-left: auto;
    color: var(--color-text-tertiary);
    font-size: 0.72rem;
    font-variant-numeric: tabular-nums;
  }

  .composer-mode-tabs {
    display: inline-flex;
    align-items: center;
    gap: 0.15rem;
    box-sizing: border-box;
    height: var(--composer-control-height);
    min-height: var(--composer-control-height);
    width: fit-content;
    padding: 0;
    border: 0;
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-bg) 82%, transparent);
    box-shadow: inset 0 0 0 1px var(--color-outline-variant);
  }

  .composer-mode-tab {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    box-sizing: border-box;
    height: var(--composer-inner-control-height);
    min-height: var(--composer-inner-control-height);
    border: 0;
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--color-text-tertiary);
    padding: 0 0.7rem;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0;
    white-space: nowrap;
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast),
      box-shadow var(--transition-fast);
  }

  .composer-mode-tab:hover:not(:disabled) {
    color: var(--color-text);
    background: color-mix(in srgb, var(--color-bg-tertiary) 46%, transparent);
  }

  .composer-mode-tab.active {
    color: var(--color-on-secondary);
    background: var(--color-secondary);
    box-shadow: 0 1px 2px color-mix(in srgb, var(--color-secondary) 32%, transparent);
  }

  .composer-mode-tab.active:nth-of-type(2) {
    color: var(--color-on-tertiary);
    background: var(--color-tertiary);
  }

  .composer-mode-tab:disabled {
    cursor: not-allowed;
    opacity: 0.42;
  }

  @media (max-width: 560px) {
    .composer-toolbar {
      flex-wrap: wrap;
    }

    .composer-mode-tabs {
      order: 4;
      width: 100%;
    }

    .composer-mode-tab {
      flex: 1;
    }
  }
</style>
