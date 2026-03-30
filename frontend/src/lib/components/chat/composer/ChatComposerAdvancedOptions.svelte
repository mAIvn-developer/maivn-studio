<script lang="ts">
  import type { DemoDetails } from "$lib/types";
  import { ChevronRight, SquareTerminal } from "lucide-svelte";

  interface Props {
    hasDemo: boolean;
    hasActiveSession: boolean;
    showSystemInput?: boolean;
    selectedVariant?: string | undefined;
    localSystemMessage?: string;
    variants: Array<[string, DemoDetails["variants"][string]]>;
    onSelectedVariantChange?: (variant: string | undefined) => void;
  }

  let {
    hasDemo,
    hasActiveSession,
    showSystemInput = $bindable(false),
    selectedVariant = $bindable<string | undefined>(undefined),
    localSystemMessage = $bindable(""),
    variants,
    onSelectedVariantChange,
  }: Props = $props();

  function handleVariantChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value || undefined;
    selectedVariant = value;
    onSelectedVariantChange?.(selectedVariant);
  }
</script>

{#if !hasActiveSession && hasDemo}
  <div class="mb-3">
    <button
      type="button"
      onclick={() => (showSystemInput = !showSystemInput)}
      class="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]
           hover:text-[var(--color-text-secondary)] transition-colors"
      aria-expanded={showSystemInput}
    >
      <ChevronRight
        size={14}
        class="transition-transform duration-200 {showSystemInput ? 'rotate-90' : ''}"
      />
      <SquareTerminal size={14} />
      <span>Advanced</span>
      {#if localSystemMessage.trim() || selectedVariant}
        <span
          class="px-1.5 py-0.5 rounded-full text-[10px] bg-[var(--color-tertiary)]/20 text-[var(--color-tertiary)]"
        >
          {localSystemMessage.trim() && selectedVariant ? "2" : "1"} set
        </span>
      {/if}
    </button>

    {#if showSystemInput}
      <div class="mt-2 animate-in space-y-3">
        {#if variants.length > 0}
          <div class="flex items-center gap-2">
            <label for="variant-select" class="text-xs text-[var(--color-text-secondary)] shrink-0"
              >Variant</label
            >
            <select
              id="variant-select"
              value={selectedVariant ?? ""}
              onchange={handleVariantChange}
              class="flex-1 rounded-lg border border-[var(--color-outline-variant)] bg-[var(--color-bg-tertiary)]
                   px-2.5 py-1.5 text-xs text-[var(--color-text)]
                   focus:outline-none focus:border-[var(--color-tertiary)]/50"
            >
              <option value="">Default</option>
              {#each variants as [id, variant]}
                <option value={id}>{id} - {variant.description}</option>
              {/each}
            </select>
          </div>
        {/if}

        <div>
          <label for="system-message" class="text-xs text-[var(--color-text-secondary)] block mb-1"
            >System Message</label
          >
          <textarea
            id="system-message"
            bind:value={localSystemMessage}
            placeholder="Enter system instructions..."
            rows={2}
            class="w-full rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-outline-variant)]
                 px-3 py-2 text-xs text-[var(--color-text)] placeholder-[var(--color-text-tertiary)]
                 focus:outline-none focus:border-[var(--color-tertiary)]/50
                 resize-none min-h-[48px] max-h-[120px]"
            style="field-sizing: content;"
          ></textarea>
        </div>
      </div>
    {/if}
  </div>
{/if}
