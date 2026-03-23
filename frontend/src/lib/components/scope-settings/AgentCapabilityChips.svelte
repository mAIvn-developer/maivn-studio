<script lang="ts">
  interface Props {
    useAsFinalOutput?: boolean;
    hasBeforeHook?: boolean;
    hasAfterHook?: boolean;
    hookExecutionMode?: string;
    mcpServerNames?: string[];
  }

  let {
    useAsFinalOutput = false,
    hasBeforeHook = false,
    hasAfterHook = false,
    hookExecutionMode = "sequential",
    mcpServerNames = [],
  }: Props = $props();
</script>

<div class="chip-row">
  {#if useAsFinalOutput}
    <span class="chip chip-tertiary">Final output</span>
  {/if}
  {#if hasBeforeHook}
    <span class="chip chip-primary">Before hook</span>
  {/if}
  {#if hasAfterHook}
    <span class="chip chip-primary">After hook</span>
  {/if}
  {#if hookExecutionMode !== "sequential"}
    <span class="chip chip-default">{hookExecutionMode}</span>
  {/if}
  {#each mcpServerNames as mcp}
    <span class="chip chip-warning">MCP: {mcp}</span>
  {/each}
</div>

<style>
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

  .chip-default {
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-outline) 20%, transparent);
  }

  .chip-primary {
    color: var(--color-primary);
    background: color-mix(in srgb, var(--color-primary) 16%, transparent);
  }

  .chip-tertiary {
    color: var(--color-tertiary);
    background: color-mix(in srgb, var(--color-tertiary) 16%, transparent);
  }

  .chip-warning {
    color: var(--color-warning);
    background: color-mix(in srgb, var(--color-warning) 16%, transparent);
  }
</style>
