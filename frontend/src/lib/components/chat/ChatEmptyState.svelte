<script lang="ts">
  import type { DemoDetails } from "$lib/types";
  import { List, MessageSquareMore } from "lucide-svelte";

  interface Props {
    demo: DemoDetails | null;
    prompts: DemoDetails["prompts"];
    onSelectPrompt: (
      content: string,
      structuredOutputTool?: string,
      promptMessageType?: string,
      promptVariant?: string,
    ) => void;
  }

  let { demo, prompts, onSelectPrompt }: Props = $props();
</script>

<div class="empty-state-wrap">
  {#if demo}
    <div class="max-w-md">
      <div
        class="mx-auto w-16 h-16 rounded-2xl bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-4"
      >
        <MessageSquareMore size={32} class="text-[var(--color-text-tertiary)]" />
      </div>
      <h3 class="text-lg font-medium text-[var(--color-text)]">Start a conversation</h3>
      <p class="mt-2 text-sm text-[var(--color-text-secondary)]">
        Enter a message below to start interacting with {demo.name}.
      </p>

      {#if prompts.length > 0}
        <div class="mt-6">
          <p class="text-sm text-[var(--color-text-tertiary)] mb-3">Or try a pre-defined prompt:</p>
          <div class="flex flex-wrap gap-2 justify-center">
            {#each prompts as prompt}
              <button
                class="rounded-full bg-[var(--color-bg-tertiary)] px-4 py-2 text-sm
                     hover:bg-[var(--color-surface-variant)] transition-colors
                     border border-transparent hover:border-[var(--color-outline-variant)]"
                onclick={() =>
                  onSelectPrompt(
                    prompt.content,
                    prompt.structured_output,
                    prompt.message_type,
                    prompt.variant,
                  )}
              >
                {prompt.name}
              </button>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {:else}
    <div class="max-w-md">
      <div
        class="mx-auto w-16 h-16 rounded-2xl bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-4"
      >
        <List size={32} class="text-[var(--color-text-tertiary)]" />
      </div>
      <p class="text-[var(--color-text-secondary)]">
        Select a demo from the sidebar to get started.
      </p>
    </div>
  {/if}
</div>

<style>
  .empty-state-wrap {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
  }
</style>
