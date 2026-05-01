<script lang="ts">
  import { theme, type ThemePreference } from "$lib/stores/theme.svelte";
  import { Laptop2, Moon, Sun } from "lucide-svelte";

  interface Props {
    compact?: boolean;
    class?: string;
  }

  let { compact = false, class: className = "" }: Props = $props();

  const options: Array<{
    value: ThemePreference;
    label: string;
    icon: typeof Laptop2;
  }> = [
    { value: "system", label: "System", icon: Laptop2 },
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
  ];
</script>

<div
  class="inline-flex items-center gap-0.5 rounded-[var(--radius-md)]
         border border-[var(--color-outline-variant)] bg-[var(--color-bg-secondary)]/80
         p-0.5 {className}"
  role="group"
  aria-label="Theme"
>
  {#each options as option (option.value)}
    {@const active = theme.preference === option.value}
    <button
      type="button"
      onclick={() => theme.set(option.value)}
      aria-pressed={active}
      aria-label={`Use ${option.label} theme`}
      title={option.label}
      class="theme-toggle-btn"
      class:active
      class:compact
    >
      <option.icon size={14} />
      {#if !compact}
        <span class="hidden sm:inline">{option.label}</span>
      {/if}
    </button>
  {/each}
</div>

<style>
  .theme-toggle-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.55rem;
    border-radius: calc(var(--radius-md) - 2px);
    color: var(--color-text-tertiary);
    font-size: 0.75rem;
    font-weight: 500;
    transition:
      background-color 150ms,
      color 150ms;
  }

  .theme-toggle-btn.compact {
    padding: 0.3rem;
  }

  .theme-toggle-btn:hover {
    color: var(--color-text);
    background: color-mix(in srgb, var(--color-bg-tertiary) 70%, transparent);
  }

  .theme-toggle-btn.active {
    background: color-mix(in srgb, var(--color-primary) 15%, transparent);
    color: var(--color-primary);
  }

  .theme-toggle-btn:focus-visible {
    outline: 2px solid var(--color-secondary);
    outline-offset: 2px;
  }
</style>
