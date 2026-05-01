<script lang="ts">
  import { Check } from "lucide-svelte";

  interface Props {
    checked: boolean;
    label: string;
    onchange: () => void;
    disabled?: boolean;
    class?: string;
  }

  let { checked, label, onchange, disabled = false, class: className = "" }: Props = $props();
</script>

<label class="flex items-center gap-3 cursor-pointer group {className}" class:opacity-50={disabled}>
  <div class="relative">
    <input type="checkbox" {checked} {onchange} {disabled} class="peer sr-only" />
    <div
      class="w-5 h-5 rounded border-2 border-[var(--color-outline)]
             peer-checked:border-[var(--color-secondary)] peer-checked:bg-[var(--color-secondary)]
             transition-colors"
    ></div>
    <div
      class="absolute inset-0 flex items-center justify-center opacity-0 peer-checked:opacity-100 transition-opacity"
    >
      <Check size={14} strokeWidth={3} class="text-[var(--color-on-tertiary)]" />
    </div>
  </div>
  <span class="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text)]">
    {label}
  </span>
</label>
