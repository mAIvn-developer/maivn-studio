<script lang="ts" generics="T extends string">
  interface Option {
    value: T;
    label: string;
    color?: string;
  }

  interface Props {
    options: Option[];
    value: T;
    onchange: (value: T) => void;
    class?: string;
  }

  let { options, value, onchange, class: className = "" }: Props = $props();
</script>

<div class="flex flex-wrap gap-1 {className}">
  {#each options as option}
    <button
      class="rounded-lg px-2.5 py-1.5 text-xs font-medium whitespace-nowrap text-center transition-colors"
      class:bg-[var(--color-secondary)]={value === option.value}
      class:text-[var(--color-on-tertiary)]={value === option.value}
      class:bg-[var(--color-bg-tertiary)]={value !== option.value}
      class:hover:bg-[var(--color-surface-variant)]={value !== option.value}
      style={value !== option.value && option.color
        ? `color: ${option.color}`
        : value !== option.value
          ? "color: var(--color-text-secondary)"
          : ""}
      onclick={() => onchange(option.value)}
    >
      {option.label}
    </button>
  {/each}
</div>
