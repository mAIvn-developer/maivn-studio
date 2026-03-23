<script lang="ts">
  import type { InterruptData, InterruptStyle } from "$lib/types";
  import InterruptInlineCard from "./InterruptInlineCard.svelte";
  import InterruptModal from "./InterruptModal.svelte";
  import InterruptDrawer from "./InterruptDrawer.svelte";
  import InterruptFloating from "./InterruptFloating.svelte";
  import InterruptHybrid from "./InterruptHybrid.svelte";

  interface Props {
    style: InterruptStyle;
    interrupts: InterruptData[];
    onSubmit: (interruptId: string, value: string) => void;
    onCancel: (interruptId: string) => void;
  }

  let { style, interrupts, onSubmit, onCancel }: Props = $props();

  // Get the current pending interrupt (first one waiting)
  const currentInterrupt = $derived(interrupts.find((i) => i.status === "waiting"));

  // For non-hybrid styles, only show the current interrupt
  // For hybrid, pass all interrupts
</script>

{#if style === "hybrid"}
  <!-- Hybrid handles its own rendering of all interrupts -->
  <InterruptHybrid {interrupts} {onSubmit} {onCancel} />
{:else if currentInterrupt}
  <!-- Other styles only show the current pending interrupt -->
  {#if style === "inline"}
    <InterruptInlineCard interrupt={currentInterrupt} {onSubmit} {onCancel} />
  {:else if style === "modal"}
    <InterruptModal interrupt={currentInterrupt} {onSubmit} {onCancel} />
  {:else if style === "drawer"}
    <InterruptDrawer interrupt={currentInterrupt} {onSubmit} {onCancel} />
  {:else if style === "floating"}
    <InterruptFloating interrupt={currentInterrupt} {onSubmit} {onCancel} />
  {/if}
{/if}
