<script lang="ts">
  import type { InterruptData } from "$lib/types";
  import InterruptInlineCard from "../interrupts/InterruptInlineCard.svelte";

  interface Props {
    interruptCards: InterruptData[];
    onSubmitInterrupt?: (interruptId: string, value: string) => void;
    onCancelInterrupt?: (interruptId: string) => void;
  }

  let { interruptCards, onSubmitInterrupt, onCancelInterrupt }: Props = $props();
</script>

{#if interruptCards.length > 0}
  <div class="interrupt-section max-w-[85%] space-y-2">
    {#each interruptCards as interrupt (interrupt.cardId)}
      <InterruptInlineCard
        {interrupt}
        onSubmit={(id: string, value: string) => onSubmitInterrupt?.(id, value)}
        onCancel={(id: string) => onCancelInterrupt?.(id)}
      />
    {/each}
  </div>
{/if}

<style>
  .interrupt-section {
    margin-left: auto;
    margin-right: auto;
    animation: slideIn 0.2s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
