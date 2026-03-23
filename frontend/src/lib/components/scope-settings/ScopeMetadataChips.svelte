<script lang="ts">
  interface Props {
    members?: string[];
    privateDataKeys?: string[];
  }

  let { members = [], privateDataKeys = [] }: Props = $props();
</script>

{#if members.length > 0}
  <div class="chip-block">
    <span class="chip-label">Members</span>
    <div class="chip-row">
      {#each members as name}
        <span class="chip chip-secondary">{name}</span>
      {/each}
    </div>
  </div>
{/if}

{#if privateDataKeys.length > 0}
  <div class="chip-block">
    <span class="chip-label">Private Data Keys</span>
    <div class="chip-row">
      {#each privateDataKeys as key}
        <span class="chip chip-warning">{key}</span>
      {/each}
    </div>
  </div>
{/if}

<style>
  .chip-block {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .chip-label {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-tertiary);
  }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    border-radius: var(--radius-full);
    padding: 0.1875rem 0.5625rem;
    font-size: 0.6875rem;
    line-height: 1.2;
    font-weight: 600;
    white-space: nowrap;
  }

  .chip-secondary {
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 16%, transparent);
  }

  .chip-warning {
    color: var(--color-warning);
    background: color-mix(in srgb, var(--color-warning) 16%, transparent);
  }
</style>
