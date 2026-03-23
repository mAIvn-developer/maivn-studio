<script lang="ts">
  import { ChevronDown } from "lucide-svelte";
  import type { Snippet } from "svelte";

  interface Props {
    children?: Snippet;
    title: string;
    subtitle: string;
    open: boolean;
    onToggle: () => void;
  }

  let { children, title, subtitle, open, onToggle }: Props = $props();
</script>

<section class="config-section">
  <button type="button" class="section-toggle" aria-expanded={open} onclick={onToggle}>
    <div class="section-copy">
      <span class="section-title">{title}</span>
      <span class="section-subtitle">{subtitle}</span>
    </div>
    <ChevronDown size={16} class="section-icon {open ? 'rotate-180' : ''}" />
  </button>

  {#if open}
    <div class="section-body animate-in">
      {@render children?.()}
    </div>
  {/if}
</section>

<style>
  .config-section {
    border-bottom: 1px solid var(--color-outline-variant);
  }

  .section-toggle {
    width: 100%;
    border: 0;
    background: transparent;
    padding: 0.875rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    text-align: left;
    cursor: pointer;
    transition: background-color var(--transition-fast);
  }

  .section-toggle:hover {
    background: color-mix(in srgb, var(--color-bg-secondary) 72%, transparent);
  }

  .section-copy {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }

  .section-title {
    font-size: 0.8125rem;
    line-height: 1.2;
    font-weight: 600;
    color: var(--color-text);
  }

  .section-subtitle {
    font-size: 0.6875rem;
    line-height: 1.25;
    color: var(--color-text-tertiary);
  }

  :global(.section-icon) {
    flex-shrink: 0;
    color: var(--color-text-tertiary);
    transition:
      transform var(--transition-fast),
      color var(--transition-fast);
  }

  .section-toggle:hover :global(.section-icon) {
    color: var(--color-text-secondary);
  }

  .section-body {
    padding: 0 1rem 1rem;
  }

  @media (max-width: 640px) {
    .section-toggle {
      padding: 0.75rem;
    }

    .section-body {
      padding: 0 0.75rem 0.75rem;
    }
  }
</style>
