<script lang="ts">
  import { Inbox } from "lucide-svelte";
  import type { Snippet } from "svelte";

  interface Props {
    title: string;
    description?: string;
    actionLabel?: string;
    onAction?: () => void;
    icon?: Snippet;
    class?: string;
  }

  let { title, description, actionLabel, onAction, icon, class: className = "" }: Props = $props();
</script>

<div class="empty-state flex flex-col items-center justify-center text-center p-6 {className}">
  <!-- Icon container -->
  <div
    class="w-16 h-16 rounded-2xl bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-4"
  >
    {#if icon}
      {@render icon()}
    {:else}
      <!-- Default empty icon -->
      <Inbox size={32} strokeWidth={1.5} class="text-[var(--color-text-tertiary)]" />
    {/if}
  </div>

  <!-- Title -->
  <h3 class="text-lg font-medium text-[var(--color-text)]">{title}</h3>

  <!-- Description -->
  {#if description}
    <p class="mt-2 text-sm text-[var(--color-text-secondary)] max-w-sm">{description}</p>
  {/if}

  <!-- Action button -->
  {#if actionLabel && onAction}
    <button
      class="mt-4 px-4 py-2 rounded-lg text-sm font-medium
             bg-[var(--color-secondary)] text-[var(--color-on-secondary)]
             hover:bg-[var(--color-accent-hover)] transition-colors"
      onclick={onAction}
    >
      {actionLabel}
    </button>
  {/if}
</div>
