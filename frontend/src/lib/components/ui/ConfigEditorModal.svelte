<script lang="ts">
  import { X } from "lucide-svelte";
  import { onMount } from "svelte";

  interface Props {
    open: boolean;
    title: string;
    subtitle?: string;
    onClose: () => void;
    children?: import("svelte").Snippet;
  }

  let { open, title, subtitle = "", onClose, children }: Props = $props();

  let portalTarget = $state<HTMLElement | null>(null);

  function portal(node: HTMLElement, target: HTMLElement): { destroy: () => void } {
    target.appendChild(node);
    return {
      destroy() {
        if (node.parentNode) {
          node.parentNode.removeChild(node);
        }
      },
    };
  }

  onMount(() => {
    portalTarget = document.body;
  });
</script>

{#if open && portalTarget}
  <div
    use:portal={portalTarget}
    class="fixed inset-0 z-50 flex items-center justify-center px-4 py-5"
  >
    <button
      type="button"
      class="absolute inset-0 bg-black/50 backdrop-blur-sm"
      aria-label="Close editor backdrop"
      onclick={onClose}
    ></button>

    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      class="relative modal-shell w-full max-w-5xl max-h-[92vh] overflow-hidden rounded-2xl
             border border-[var(--color-outline-variant)] bg-[var(--color-bg)] shadow-2xl"
    >
      <div
        class="modal-header flex items-center justify-between gap-4 border-b
               border-[var(--color-outline-variant)] bg-[var(--color-bg-secondary)] px-5 py-4"
      >
        <div class="min-w-0">
          <h2 class="text-base font-semibold text-[var(--color-text)] truncate">{title}</h2>
          {#if subtitle}
            <p class="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{subtitle}</p>
          {/if}
        </div>
        <button
          type="button"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg
                 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]
                 hover:bg-[var(--color-bg-tertiary)] transition-colors"
          aria-label="Close editor"
          onclick={onClose}
        >
          <X size={18} />
        </button>
      </div>

      <div class="modal-body max-h-[calc(92vh-5.25rem)] overflow-y-auto px-5 py-4">
        {#if children}
          {@render children()}
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-shell {
    animation: modalIn 0.16s ease-out;
  }

  @keyframes modalIn {
    from {
      opacity: 0;
      transform: translateY(10px) scale(0.985);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }
</style>
