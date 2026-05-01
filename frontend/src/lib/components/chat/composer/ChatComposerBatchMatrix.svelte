<script lang="ts">
  import type { BatchInvocationRow, AppDetails, InvocationConfig } from "$lib/types";
  import { Copy, Plus, SlidersHorizontal, Trash2 } from "lucide-svelte";

  interface Props {
    rows?: BatchInvocationRow[];
    variants: Array<[string, AppDetails["variants"][string]]>;
    tools?: AppDetails["tools"];
    selectedVariant?: string | undefined;
  }

  let {
    rows = $bindable<BatchInvocationRow[]>([]),
    variants,
    tools = [],
    selectedVariant,
  }: Props = $props();

  const modelOptions: NonNullable<InvocationConfig["model"]>[] = ["fast", "balanced", "max"];
  const reasoningOptions: NonNullable<InvocationConfig["reasoning"]>[] = [
    "minimal",
    "low",
    "medium",
    "high",
  ];

  const completedRows = $derived(rows.filter((row) => row.message.trim()).length);
  const rowWord = $derived(completedRows === 1 ? "row" : "rows");
  const toolNames = $derived(
    tools
      .map((tool) => tool.name)
      .filter((name, index, names) => name && names.indexOf(name) === index)
      .sort((left, right) => left.localeCompare(right)),
  );

  function makeRow(message = ""): BatchInvocationRow {
    return {
      id: crypto.randomUUID(),
      label: "",
      message,
    };
  }

  function ensureRowIds(): void {
    if (rows.every((row) => row.id)) {
      return;
    }
    rows = rows.map((row) => ({ ...row, id: row.id ?? crypto.randomUUID() }));
  }

  $effect(() => {
    if (rows.length === 0) {
      rows = [makeRow()];
      return;
    }
    ensureRowIds();
  });

  function updateRow(id: string | undefined, patch: Partial<BatchInvocationRow>): void {
    rows = rows.map((row) => (row.id === id ? { ...row, ...patch } : row));
  }

  function updateSelectField(
    id: string | undefined,
    key: "variant" | "model" | "reasoning",
    value: string,
  ): void {
    updateRow(id, { [key]: value || undefined });
  }

  function updateTargetedTools(id: string | undefined, value: string): void {
    const targetedTools = value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    updateRow(id, { targeted_tools: targetedTools.length > 0 ? targetedTools : undefined });
  }

  function addRow(): void {
    rows = [...rows, makeRow()];
  }

  function duplicateRow(row: BatchInvocationRow): void {
    rows = [
      ...rows,
      {
        ...row,
        id: crypto.randomUUID(),
        label: row.label ? `${row.label} copy` : "",
      },
    ];
  }

  function removeRow(id: string | undefined): void {
    const nextRows = rows.filter((row) => row.id !== id);
    rows = nextRows.length > 0 ? nextRows : [makeRow()];
  }
</script>

<section class="matrix-panel" aria-label="Batch matrix">
  <header class="matrix-header">
    <div class="matrix-title">
      <SlidersHorizontal size={14} />
      <span>Batch Matrix</span>
      <span class="matrix-count">{completedRows} {rowWord}</span>
    </div>
    <button type="button" class="matrix-add" onclick={addRow} title="Add row" aria-label="Add row">
      <Plus size={14} />
    </button>
  </header>

  <div class="matrix-rows">
    {#each rows as row, index (row.id)}
      <article class="matrix-row">
        <div class="row-topline">
          <span class="row-number">#{index + 1}</span>
          <input
            type="text"
            class="row-label"
            value={row.label ?? ""}
            placeholder="Label"
            oninput={(event) =>
              updateRow(row.id, { label: (event.target as HTMLInputElement).value })}
          />
          <div class="row-actions">
            <button
              type="button"
              onclick={() => duplicateRow(row)}
              title="Duplicate row"
              aria-label={`Duplicate row ${index + 1}`}
            >
              <Copy size={13} />
            </button>
            <button
              type="button"
              onclick={() => removeRow(row.id)}
              title="Remove row"
              aria-label={`Remove row ${index + 1}`}
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>

        <textarea
          class="row-message"
          value={row.message}
          placeholder="Prompt"
          rows={2}
          oninput={(event) =>
            updateRow(row.id, { message: (event.target as HTMLTextAreaElement).value })}
        ></textarea>

        <div class="row-grid">
          <label>
            <span>Variant</span>
            <select
              value={row.variant ?? ""}
              onchange={(event) =>
                updateSelectField(row.id, "variant", (event.target as HTMLSelectElement).value)}
            >
              <option value="">
                {selectedVariant ? `Session: ${selectedVariant}` : "Default"}
              </option>
              {#each variants as [id, variant]}
                <option value={id}>{id} - {variant.description}</option>
              {/each}
            </select>
          </label>

          <label>
            <span>Model</span>
            <select
              value={row.model ?? ""}
              onchange={(event) =>
                updateSelectField(row.id, "model", (event.target as HTMLSelectElement).value)}
            >
              <option value="">Global</option>
              {#each modelOptions as option}
                <option value={option}>{option}</option>
              {/each}
            </select>
          </label>

          <label>
            <span>Reasoning</span>
            <select
              value={row.reasoning ?? ""}
              onchange={(event) =>
                updateSelectField(row.id, "reasoning", (event.target as HTMLSelectElement).value)}
            >
              <option value="">Global</option>
              {#each reasoningOptions as option}
                <option value={option}>{option}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="row-grid wide">
          <label>
            <span>Targeted Tools</span>
            <input
              type="text"
              list="batch-targeted-tools"
              value={row.targeted_tools?.join(", ") ?? ""}
              placeholder="tool_name, other_tool"
              oninput={(event) =>
                updateTargetedTools(row.id, (event.target as HTMLInputElement).value)}
            />
          </label>

          <label>
            <span>System Message</span>
            <input
              type="text"
              value={row.system_message ?? ""}
              placeholder="Row system override"
              oninput={(event) =>
                updateRow(row.id, {
                  system_message: (event.target as HTMLInputElement).value || undefined,
                })}
            />
          </label>
        </div>

        <!--
          SDK overrides per row. Tri-state checkboxes feel ambiguous in
          batch UI, so we use 3-way selects instead: Global = inherit the
          batch-level invocation config; True/False = explicit per-row
          override.
        -->
        <div class="row-grid">
          <label>
            <span>Force final tool</span>
            <select
              value={row.force_final_tool === undefined
                ? ""
                : row.force_final_tool
                  ? "true"
                  : "false"}
              onchange={(event) => {
                const v = (event.target as HTMLSelectElement).value;
                updateRow(row.id, {
                  force_final_tool: v === "" ? undefined : v === "true",
                });
              }}
            >
              <option value="">Global</option>
              <option value="true">On</option>
              <option value="false">Off</option>
            </select>
          </label>

          <label>
            <span>Stream response</span>
            <select
              value={row.stream_response === undefined
                ? ""
                : row.stream_response
                  ? "true"
                  : "false"}
              onchange={(event) => {
                const v = (event.target as HTMLSelectElement).value;
                updateRow(row.id, {
                  stream_response: v === "" ? undefined : v === "true",
                });
              }}
            >
              <option value="">Global</option>
              <option value="true">Stream</option>
              <option value="false">Invoke</option>
            </select>
          </label>
        </div>
      </article>
    {/each}
  </div>

  {#if toolNames.length > 0}
    <datalist id="batch-targeted-tools">
      {#each toolNames as toolName}
        <option value={toolName}></option>
      {/each}
    </datalist>
  {/if}
</section>

<style>
  .matrix-panel {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-bg-secondary) 65%, transparent);
    overflow: hidden;
  }

  .matrix-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.625rem 0.75rem;
    border-bottom: 1px solid var(--color-outline-variant);
  }

  .matrix-title {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    min-width: 0;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--color-text-secondary);
  }

  .matrix-count {
    border-radius: var(--radius-full);
    padding: 0.08rem 0.45rem;
    font-size: 0.625rem;
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 14%, transparent);
  }

  .matrix-add,
  .row-actions button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-tertiary) 62%, transparent);
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast);
  }

  .matrix-add:hover,
  .row-actions button:hover {
    border-color: color-mix(in srgb, var(--color-secondary) 44%, var(--color-outline-variant));
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 10%, transparent);
  }

  .matrix-rows {
    display: grid;
    gap: 0.625rem;
    max-height: 32rem;
    overflow: auto;
    padding: 0.75rem;
  }

  .matrix-row {
    display: grid;
    gap: 0.55rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    padding: 0.625rem;
    background: color-mix(in srgb, var(--color-bg) 36%, transparent);
  }

  .row-topline {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.5rem;
    align-items: center;
  }

  .row-number {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.6875rem;
    font-weight: 700;
    color: var(--color-text-tertiary);
  }

  .row-actions {
    display: inline-flex;
    gap: 0.25rem;
  }

  .row-grid {
    display: grid;
    grid-template-columns: minmax(8rem, 1fr) minmax(7rem, 0.7fr) minmax(7rem, 0.7fr);
    gap: 0.5rem;
  }

  .row-grid.wide {
    grid-template-columns: minmax(8rem, 0.8fr) minmax(10rem, 1fr);
  }

  label {
    display: grid;
    gap: 0.25rem;
    min-width: 0;
  }

  label span {
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--color-text-tertiary);
  }

  input,
  select,
  textarea {
    width: 100%;
    min-width: 0;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: var(--color-bg-secondary);
    color: var(--color-text);
    padding: 0.42rem 0.5rem;
    font-size: 0.75rem;
    line-height: 1.35;
    outline: none;
  }

  textarea {
    min-height: 3.25rem;
    max-height: 8rem;
    resize: vertical;
  }

  input:focus,
  select:focus,
  textarea:focus {
    border-color: color-mix(in srgb, var(--color-secondary) 55%, var(--color-outline-variant));
  }

  input::placeholder,
  textarea::placeholder {
    color: var(--color-text-tertiary);
  }

  @media (max-width: 760px) {
    .row-grid,
    .row-grid.wide {
      grid-template-columns: 1fr;
    }
  }
</style>
