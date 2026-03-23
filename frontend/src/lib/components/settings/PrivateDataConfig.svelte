<script lang="ts">
  import { Lock, ChevronDown } from "lucide-svelte";
  import type { PrivateDataField } from "$lib/types";

  interface Props {
    schema: PrivateDataField[];
    values: Record<string, unknown>;
    onchange?: (values: Record<string, unknown>) => void;
    disabled?: boolean;
  }

  let { schema, values = {}, onchange, disabled = false }: Props = $props();

  let isExpanded = $state(true);

  // Count filled fields
  const filledCount = $derived(() => {
    return Object.values(values).filter((v) => v !== undefined && v !== "").length;
  });

  // Initialize values from schema defaults
  $effect(() => {
    if (schema.length > 0 && Object.keys(values).length === 0) {
      const defaultValues: Record<string, unknown> = {};
      for (const field of schema) {
        if (field.default_value !== undefined) {
          defaultValues[field.key] = field.default_value;
        }
      }
      if (Object.keys(defaultValues).length > 0) {
        onchange?.(defaultValues);
      }
    }
  });

  function handleFieldChange(key: string, value: string | number | boolean) {
    const newValues = { ...values, [key]: value };
    onchange?.(newValues);
  }

  function getFieldValue(key: string, default_value?: string | number | boolean): string {
    const val = values[key];
    if (val !== undefined) return String(val);
    if (default_value !== undefined) return String(default_value);
    return "";
  }
</script>

{#if schema.length > 0}
  <div class="private-data-config">
    <!-- Header -->
    <button
      class="header-btn w-full flex items-center gap-3 text-left transition-colors rounded-lg p-2
             hover:bg-[var(--color-bg-tertiary)]/50"
      onclick={() => (isExpanded = !isExpanded)}
      {disabled}
    >
      <!-- Icon -->
      <div
        class="flex h-8 w-8 items-center justify-center rounded-lg shrink-0 {disabled
          ? 'bg-[var(--color-outline)]/15'
          : 'bg-[var(--color-warning)]/15'}"
      >
        <Lock
          size={16}
          class={disabled ? "text-[var(--color-outline)]" : "text-[var(--color-warning)]"}
        />
      </div>

      <!-- Title and count -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="font-medium text-sm text-[var(--color-text)]">Private Data</span>
          <span
            class="text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--color-warning)]/15 text-[var(--color-warning)]"
          >
            {filledCount()}/{schema.length}
          </span>
          {#if disabled}
            <span
              class="text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--color-outline)]/15 text-[var(--color-text-tertiary)]"
            >
              Locked
            </span>
          {/if}
        </div>
        <p class="text-xs text-[var(--color-text-tertiary)] mt-0.5">
          Server-side injected configuration
        </p>
      </div>

      <!-- Expand indicator -->
      <ChevronDown
        size={16}
        class="text-[var(--color-text-tertiary)] transition-transform shrink-0 {isExpanded
          ? 'rotate-180'
          : ''}"
      />
    </button>

    <!-- Fields -->
    {#if isExpanded}
      <div class="fields-container mt-2 space-y-3 animate-in">
        {#each schema as field}
          <div class="field-wrapper">
            <label for="private-data-{field.key}" class="field-label">
              <span class="label-text">
                {field.label || field.key}
                {#if field.required}
                  <span class="text-[var(--color-error)]">*</span>
                {/if}
              </span>
              {#if field.description}
                <span class="label-description">{field.description}</span>
              {/if}
            </label>

            {#if field.type === "boolean"}
              <label class="toggle-wrapper" class:disabled>
                <div class="relative">
                  <input
                    id="private-data-{field.key}"
                    type="checkbox"
                    checked={values[field.key] === true || values[field.key] === "true"}
                    onchange={(e) =>
                      handleFieldChange(field.key, (e.target as HTMLInputElement).checked)}
                    {disabled}
                    class="peer sr-only"
                  />
                  <div
                    class="toggle-track w-9 h-5 rounded-full transition-colors
                           peer-checked:bg-[var(--color-warning)] bg-[var(--color-outline)]/30"
                    class:opacity-50={disabled}
                  ></div>
                  <div
                    class="toggle-thumb absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-white
                           transition-transform peer-checked:translate-x-4"
                    class:opacity-50={disabled}
                  ></div>
                </div>
                <span class="text-xs text-[var(--color-text-secondary)]">
                  {values[field.key] ? "Enabled" : "Disabled"}
                </span>
              </label>
            {:else}
              <input
                id="private-data-{field.key}"
                type={field.type === "number" ? "number" : "text"}
                value={getFieldValue(field.key, field.default_value)}
                oninput={(e) => handleFieldChange(field.key, (e.target as HTMLInputElement).value)}
                {disabled}
                class="field-input"
                class:disabled
                placeholder={field.default_value !== undefined
                  ? String(field.default_value)
                  : "Enter value..."}
              />
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .fields-container {
    padding: 0.5rem;
    border-radius: var(--radius-lg);
    background-color: var(--color-bg-tertiary);
  }

  .field-wrapper {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .field-label {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .label-text {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  .label-description {
    font-size: 0.625rem;
    color: var(--color-text-tertiary);
  }

  .field-input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-outline-variant);
    background-color: var(--color-bg);
    font-size: 0.875rem;
    color: var(--color-text);
    transition:
      border-color 0.2s,
      box-shadow 0.2s;
  }

  .field-input::placeholder {
    color: var(--color-text-tertiary);
  }

  .field-input:focus {
    outline: none;
    border-color: var(--color-warning);
    box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.15);
  }

  .field-input.disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background-color: var(--color-bg-secondary);
  }

  .toggle-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
  }

  .toggle-wrapper.disabled {
    cursor: not-allowed;
  }

  .animate-in {
    animation: slideIn 0.2s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
