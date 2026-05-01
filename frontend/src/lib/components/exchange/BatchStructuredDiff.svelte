<script lang="ts">
  import type { StructuredDiffColumn } from "./batch-structured-diff";
  import { buildStructuredDiff } from "./batch-structured-diff";

  interface Props {
    columns: StructuredDiffColumn[];
  }

  let { columns }: Props = $props();

  const rows = $derived(buildStructuredDiff(columns));
  const changedCount = $derived(rows.filter((row) => row.changed).length);
</script>

<section class="structured-diff" aria-label="Structured result differences">
  <header class="diff-header">
    <div>
      <h3>Structured Result Diff</h3>
      <span>{changedCount}/{rows.length} fields changed</span>
    </div>
  </header>

  {#if rows.length === 0}
    <p class="empty-diff">No structured output is available for the selected batch items.</p>
  {:else}
    <div class="diff-table-wrap">
      <table class="diff-table">
        <thead>
          <tr>
            <th scope="col">Field</th>
            {#each columns as column (column.id)}
              <th scope="col">{column.label}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each rows as row (row.path)}
            <tr class:changed={row.changed}>
              <th scope="row">{row.path}</th>
              {#each row.cells as cell}
                <td class:missing={cell.missing} class:changed={cell.changed && !cell.missing}>
                  <code>{cell.displayValue}</code>
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>

<style>
  .structured-diff {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    overflow: hidden;
    background: color-mix(in srgb, var(--color-bg-tertiary) 55%, transparent);
  }

  .diff-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 0.875rem;
    border-bottom: 1px solid var(--color-outline-variant);
  }

  .diff-header h3 {
    margin: 0;
    font-size: 0.8125rem;
    line-height: 1.2;
    font-weight: 700;
    color: var(--color-text);
  }

  .diff-header span {
    display: block;
    margin-top: 0.125rem;
    font-size: 0.6875rem;
    color: var(--color-text-tertiary);
  }

  .empty-diff {
    margin: 0;
    padding: 0.875rem;
    font-size: 0.75rem;
    color: var(--color-text-tertiary);
  }

  .diff-table-wrap {
    overflow-x: auto;
  }

  .diff-table {
    width: 100%;
    min-width: 42rem;
    border-collapse: collapse;
    font-size: 0.75rem;
  }

  .diff-table th,
  .diff-table td {
    border-bottom: 1px solid color-mix(in srgb, var(--color-outline-variant) 70%, transparent);
    padding: 0.55rem 0.7rem;
    vertical-align: top;
    text-align: left;
  }

  .diff-table thead th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: color-mix(in srgb, var(--color-bg-secondary) 94%, transparent);
    color: var(--color-text-secondary);
    font-weight: 700;
  }

  .diff-table tbody th {
    width: 12rem;
    color: var(--color-text-secondary);
    font-weight: 700;
    word-break: break-word;
  }

  .diff-table td {
    min-width: 11rem;
    color: var(--color-text-secondary);
  }

  .diff-table tr.changed {
    background: color-mix(in srgb, var(--color-secondary) 7%, transparent);
  }

  .diff-table td.changed {
    box-shadow: inset 3px 0 0 color-mix(in srgb, var(--color-secondary) 62%, transparent);
  }

  .diff-table td.missing {
    color: var(--color-error);
    background: color-mix(in srgb, var(--color-error) 8%, transparent);
  }

  .diff-table code {
    display: block;
    max-width: 22rem;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.6875rem;
    line-height: 1.45;
  }
</style>
