<script lang="ts">
  import type { Message } from "$lib/types";
  import MessageCard from "../message/MessageCard.svelte";

  interface Props {
    statusMessages: Message[];
  }

  let { statusMessages }: Props = $props();
</script>

{#if statusMessages.length > 0}
  <div class="status-messages-section space-y-2">
    {#each statusMessages as statusMsg, idx (idx)}
      <MessageCard message={statusMsg} />
    {/each}
  </div>
{/if}
