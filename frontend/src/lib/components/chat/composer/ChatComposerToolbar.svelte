<script lang="ts">
  import type { DemoDetails, SavedPrompt, SendableMessageType } from "$lib/types";
  import { Paperclip } from "lucide-svelte";
  import MessageTypeSelector from "./MessageTypeSelector.svelte";
  import PromptDropdown from "./PromptDropdown.svelte";

  interface Props {
    hasDemo: boolean;
    hasActiveSession: boolean;
    canSend: boolean;
    loading: boolean;
    messageType: SendableMessageType;
    discoveredPrompts: DemoDetails["prompts"];
    savedPrompts: SavedPrompt[];
    inputValue: string;
    onOpenFilePicker: () => void;
    onMessageTypeChange: (type: SendableMessageType) => void;
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
    hasDemo,
    hasActiveSession,
    canSend,
    loading,
    messageType,
    discoveredPrompts,
    savedPrompts,
    inputValue,
    onOpenFilePicker,
    onMessageTypeChange,
    onSavePrompt,
    onSelectPrompt,
    onFileInputChange,
    bindFileInput = $bindable<HTMLInputElement | undefined>(undefined),
  }: Props = $props();
</script>

<div class="flex items-center gap-2 px-3 py-2 border-b border-[var(--color-outline-variant)]">
  <button
    type="button"
    onclick={onOpenFilePicker}
    disabled={!hasDemo || (hasActiveSession && !canSend) || loading}
    class="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-outline-variant)]
         px-2 py-1 text-xs text-[var(--color-text-secondary)]
         hover:border-[var(--color-tertiary)]/50 hover:text-[var(--color-text)]
         disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
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
    disabled={!hasDemo}
  />

  <MessageTypeSelector value={messageType} onchange={onMessageTypeChange} disabled={!hasDemo} />

  <input
    type="file"
    multiple
    class="hidden"
    bind:this={bindFileInput}
    onchange={onFileInputChange}
  />

  {#if inputValue.length > 100}
    <span class="ml-auto text-xs text-[var(--color-text-tertiary)] tabular-nums">
      {inputValue.length}
    </span>
  {/if}
</div>
