<script lang="ts">
  import { updateSwarm } from "$lib/api_client/demo-config";
  import ScopeMetadataChips from "$lib/components/scope-settings/ScopeMetadataChips.svelte";
  import ScopePromptPanel from "$lib/components/scope-settings/ScopePromptPanel.svelte";
  import ScopeSaveActions from "$lib/components/scope-settings/ScopeSaveActions.svelte";
  import { saveScopeItemChanges } from "$lib/components/scope-settings/save";
  import {
    buildItemPrivateDataSchema,
    buildItemScopeMemoryEdit,
    discardItemEdit,
    getItemEdit,
    getItemEditTags,
    getItemEditValue,
    getItemPrivateDataValues,
    getItemScopeMemoryConfig,
    hasItemChanges,
    parseTagInput,
    setItemEdit,
    toggleExpandedItem,
  } from "$lib/components/scope-settings/shared";
  import type {
    InvocationMemoryConfig,
    MemoryConfig,
    PrivateDataField,
    SwarmInfo,
  } from "$lib/types";
  import { ChevronDown, Users } from "lucide-svelte";
  import ConfigEditorModal from "../ui/ConfigEditorModal.svelte";
  import MemorySettings from "./MemorySettings.svelte";
  import PrivateDataConfig from "./PrivateDataConfig.svelte";

  interface Props {
    swarms: SwarmInfo[];
    demoId: string;
    disabled?: boolean;
    onSwarmUpdated?: () => void;
  }

  let { swarms, demoId, disabled = false, onSwarmUpdated }: Props = $props();

  // Track which swarms are expanded
  let expandedSwarms = $state<Set<string>>(new Set());
  // Track edited values per swarm
  let edits = $state<Record<string, Partial<SwarmInfo>>>({});
  // Track saving state per swarm
  let saving = $state<Record<string, boolean>>({});
  // Track save errors per swarm
  let saveErrors = $state<Record<string, string>>({});
  // Track full-screen editor state
  let editingSwarmName = $state<string | null>(null);

  function toggleSwarm(name: string) {
    expandedSwarms = toggleExpandedItem(expandedSwarms, name);
  }

  function getEdit(swarmName: string): Partial<SwarmInfo> {
    return getItemEdit(edits, swarmName);
  }

  function setEdit(swarmName: string, field: string, value: unknown) {
    edits = setItemEdit(edits, swarmName, field, value);
  }

  function hasChanges(swarmName: string): boolean {
    return hasItemChanges(edits, swarmName);
  }

  function getEditValue(swarm: SwarmInfo, field: keyof SwarmInfo): unknown {
    return getItemEditValue(edits, swarm, field);
  }

  function getEditTags(swarm: SwarmInfo): string {
    return getItemEditTags(edits, swarm);
  }

  function handleTagsInput(swarmName: string, value: string) {
    setEdit(swarmName, "tags", parseTagInput(value));
  }

  function getScopeMemoryConfig(swarm: SwarmInfo): MemoryConfig {
    return getItemScopeMemoryConfig(edits, swarm);
  }

  function handleScopeMemoryChange(swarm: SwarmInfo, config: MemoryConfig) {
    setEdit(swarm.name, "memory_config", buildItemScopeMemoryEdit(edits, swarm, config));
  }

  function getPrivateDataValues(swarm: SwarmInfo): Record<string, unknown> {
    return getItemPrivateDataValues(edits, swarm);
  }

  function handlePrivateDataChange(swarmName: string, values: Record<string, unknown>) {
    setEdit(swarmName, "private_data", values);
  }

  function getPrivateDataSchema(swarm: SwarmInfo): PrivateDataField[] {
    const values = getPrivateDataValues(swarm);
    return buildItemPrivateDataSchema(swarm, values);
  }

  async function handleSave(swarm: SwarmInfo) {
    const edit = getEdit(swarm.name);
    await saveScopeItemChanges({
      itemName: swarm.name,
      edit,
      edits,
      setEdits: (nextEdits: Record<string, Partial<SwarmInfo>>) => {
        edits = nextEdits;
      },
      saving,
      setSaving: (nextSaving: Record<string, boolean>) => {
        saving = nextSaving;
      },
      saveErrors,
      setSaveErrors: (nextSaveErrors: Record<string, string>) => {
        saveErrors = nextSaveErrors;
      },
      editingName: editingSwarmName,
      setEditingName: (name: string | null) => {
        editingSwarmName = name;
      },
      onUpdated: onSwarmUpdated,
      persist: async (pendingEdit: Partial<SwarmInfo>) => {
        await updateSwarm(demoId, swarm.name, {
          description: pendingEdit.description as string | undefined,
          system_prompt: pendingEdit.system_prompt as string | undefined,
          tags: pendingEdit.tags as string[] | undefined,
          memory_config: pendingEdit.memory_config as InvocationMemoryConfig | undefined,
          allow_private_in_system_tools: pendingEdit.allow_private_in_system_tools as
            | boolean
            | undefined,
          private_data: pendingEdit.private_data as Record<string, unknown> | undefined,
        });
      },
    });
  }

  function handleDiscard(swarmName: string) {
    edits = discardItemEdit(edits, swarmName);
  }

  function openEditor(swarmName: string) {
    editingSwarmName = swarmName;
  }

  function closeEditor() {
    editingSwarmName = null;
  }
</script>

{#if swarms.length > 0}
  <section class="settings-section">
    <div class="section-header">
      <h4 class="section-title">Swarms</h4>
      <span class="section-count">{swarms.length}</span>
    </div>

    <div class="settings-list">
      {#each swarms as swarm}
        <article class="settings-card" class:dirty={hasChanges(swarm.name)}>
          <button
            type="button"
            class="settings-header"
            aria-expanded={expandedSwarms.has(swarm.name)}
            onclick={() => toggleSwarm(swarm.name)}
          >
            <div class="icon-shell">
              <Users size={14} class="text-[var(--color-primary)]" />
            </div>

            <div class="header-content">
              <div class="header-main-row">
                <span class="header-title">{swarm.name}</span>
                {#if hasChanges(swarm.name)}
                  <span class="status-pill">Unsaved</span>
                {/if}
              </div>
              <div class="header-subtitle">
                <span>{swarm.agent_count} agents</span>
                <span>
                  {#if swarm.runtime_tool_count !== swarm.tool_count}
                    {swarm.runtime_tool_count} runtime tools
                  {:else}
                    {swarm.tool_count} tools
                  {/if}
                </span>
                {#if swarm.runtime_tool_count !== swarm.tool_count}
                  <span>{swarm.tool_count} authored tools</span>
                {/if}
              </div>
            </div>

            <ChevronDown
              size={18}
              class="expand-icon {expandedSwarms.has(swarm.name) ? 'rotate-180' : ''}"
            />
          </button>

          {#if expandedSwarms.has(swarm.name)}
            <div class="settings-body animate-in">
              <div class="body-head-row">
                <span class="body-head-label">Swarm Settings</span>
                <button
                  type="button"
                  class="editor-open-btn"
                  onclick={() => openEditor(swarm.name)}
                  {disabled}
                >
                  Open large editor
                </button>
              </div>

              <ScopeMetadataChips
                members={swarm.agent_names}
                privateDataKeys={swarm.private_data_keys}
              />

              <div class="field-wrapper">
                <label class="field-label" for="swarm-desc-{swarm.name}">Description</label>
                <textarea
                  id="swarm-desc-{swarm.name}"
                  class="field-input compact-textarea"
                  class:disabled
                  {disabled}
                  rows="3"
                  oninput={(e) =>
                    setEdit(swarm.name, "description", (e.target as HTMLTextAreaElement).value)}
                  placeholder="What this swarm orchestrates..."
                  >{getEditValue(swarm, "description") as string}</textarea
                >
              </div>

              <ScopePromptPanel
                value={(getEditValue(swarm, "system_prompt") as string) ?? ""}
                {disabled}
                accent="var(--color-primary)"
                onInput={(value) => setEdit(swarm.name, "system_prompt", value)}
              />

              <div class="field-wrapper">
                <label class="field-label" for="swarm-tags-{swarm.name}">Tags</label>
                <input
                  id="swarm-tags-{swarm.name}"
                  type="text"
                  class="field-input"
                  class:disabled
                  {disabled}
                  value={getEditTags(swarm)}
                  oninput={(e) => handleTagsInput(swarm.name, (e.target as HTMLInputElement).value)}
                  placeholder="tag1, tag2, ..."
                />
                <span class="field-helper">Use commas to separate tags.</span>
              </div>

              <ScopeSaveActions
                showActions={hasChanges(swarm.name)}
                saving={saving[swarm.name] ?? false}
                error={saveErrors[swarm.name] ?? ""}
                saveDisabled={disabled || !!saving[swarm.name]}
                discardDisabled={disabled || !!saving[swarm.name]}
                onSave={() => handleSave(swarm)}
                onDiscard={() => handleDiscard(swarm.name)}
              />
            </div>
          {/if}

          <ConfigEditorModal
            open={editingSwarmName === swarm.name}
            title={`Edit Swarm Scope: ${swarm.name}`}
            subtitle="Overlay editor for swarm scope defaults, prompts, memory, and private data."
            onClose={closeEditor}
          >
            <div class="modal-layout">
              <ScopeMetadataChips
                members={swarm.agent_names}
                privateDataKeys={swarm.private_data_keys}
              />

              <div class="field-wrapper">
                <label class="field-label" for="swarm-modal-desc-{swarm.name}">Description</label>
                <textarea
                  id="swarm-modal-desc-{swarm.name}"
                  class="field-input modal-textarea"
                  class:disabled
                  {disabled}
                  rows="6"
                  oninput={(e) =>
                    setEdit(swarm.name, "description", (e.target as HTMLTextAreaElement).value)}
                  placeholder="Describe this swarm's orchestration strategy..."
                  >{getEditValue(swarm, "description") as string}</textarea
                >
              </div>

              <div class="field-wrapper">
                <label class="field-label" for="swarm-modal-system-{swarm.name}"
                  >System Prompt</label
                >
                <textarea
                  id="swarm-modal-system-{swarm.name}"
                  class="field-input modal-textarea prompt-textarea"
                  class:disabled
                  {disabled}
                  rows="14"
                  oninput={(e) =>
                    setEdit(swarm.name, "system_prompt", (e.target as HTMLTextAreaElement).value)}
                  placeholder="System prompt..."
                  >{(getEditValue(swarm, "system_prompt") as string) ?? ""}</textarea
                >
              </div>

              <div class="field-wrapper">
                <label class="field-label" for="swarm-modal-tags-{swarm.name}">Tags</label>
                <input
                  id="swarm-modal-tags-{swarm.name}"
                  type="text"
                  class="field-input"
                  class:disabled
                  {disabled}
                  value={getEditTags(swarm)}
                  oninput={(e) => handleTagsInput(swarm.name, (e.target as HTMLInputElement).value)}
                  placeholder="tag1, tag2, ..."
                />
              </div>

              <label class="toggle-card" class:is-disabled={disabled}>
                <div class="toggle-copy">
                  <span class="toggle-title">Allow private data in system tools</span>
                  <span class="toggle-description">
                    Lets this swarm pass private values to system-level tools when needed.
                  </span>
                </div>
                <div class="switch-shell">
                  <input
                    type="checkbox"
                    class="peer sr-only"
                    checked={(getEditValue(swarm, "allow_private_in_system_tools") as boolean) ??
                      false}
                    onchange={(e) =>
                      setEdit(
                        swarm.name,
                        "allow_private_in_system_tools",
                        (e.target as HTMLInputElement).checked,
                      )}
                    {disabled}
                  />
                  <span class="switch-track"></span>
                  <span class="switch-thumb"></span>
                </div>
              </label>

              <div class="modal-section">
                <span class="field-label">Memory Defaults</span>
                <MemorySettings
                  config={getScopeMemoryConfig(swarm)}
                  {disabled}
                  onChange={(config) => handleScopeMemoryChange(swarm, config)}
                />
              </div>

              {#if getPrivateDataSchema(swarm).length > 0}
                <div class="modal-section">
                  <PrivateDataConfig
                    schema={getPrivateDataSchema(swarm)}
                    values={getPrivateDataValues(swarm)}
                    onchange={(values) => handlePrivateDataChange(swarm.name, values)}
                    {disabled}
                  />
                </div>
              {/if}

              <ScopeSaveActions
                saving={saving[swarm.name] ?? false}
                error={saveErrors[swarm.name] ?? ""}
                saveDisabled={disabled || !!saving[swarm.name] || !hasChanges(swarm.name)}
                discardDisabled={disabled || !!saving[swarm.name] || !hasChanges(swarm.name)}
                onSave={() => handleSave(swarm)}
                onDiscard={() => handleDiscard(swarm.name)}
              />
            </div>
          </ConfigEditorModal>
        </article>
      {/each}
    </div>
  </section>
{/if}

<style>
  .settings-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .section-title {
    margin: 0;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--color-text-tertiary);
  }

  .section-count {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-full);
    padding: 0.125rem 0.5rem;
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-secondary) 75%, transparent);
  }

  .settings-list {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
  }

  .settings-card {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-xl);
    background:
      linear-gradient(
        180deg,
        color-mix(in srgb, var(--color-bg-tertiary) 82%, transparent),
        transparent
      ),
      var(--color-bg-secondary);
    overflow: hidden;
    transition:
      border-color var(--transition-fast),
      box-shadow var(--transition-fast);
  }

  .settings-card:hover {
    border-color: color-mix(in srgb, var(--color-outline) 62%, var(--color-outline-variant));
  }

  .settings-card.dirty {
    border-color: color-mix(in srgb, var(--color-secondary) 45%, var(--color-outline-variant));
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-secondary) 18%, transparent);
  }

  .settings-header {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.875rem 0.875rem 0.825rem;
    text-align: left;
    cursor: pointer;
    background: none;
    border: 0;
    transition: background-color var(--transition-fast);
  }

  .settings-header:hover {
    background: color-mix(in srgb, var(--color-surface-variant) 34%, transparent);
  }

  .icon-shell {
    flex-shrink: 0;
    width: 2rem;
    height: 2rem;
    border-radius: var(--radius-lg);
    display: flex;
    align-items: center;
    justify-content: center;
    background:
      linear-gradient(
        160deg,
        color-mix(in srgb, var(--color-primary) 28%, transparent),
        transparent
      ),
      color-mix(in srgb, var(--color-primary-container) 32%, var(--color-bg-secondary));
    border: 1px solid color-mix(in srgb, var(--color-primary) 22%, var(--color-outline-variant));
  }

  .header-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .header-main-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .header-title {
    font-size: 0.9375rem;
    line-height: 1.2;
    font-weight: 600;
    color: var(--color-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .header-subtitle {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    font-size: 0.75rem;
    color: var(--color-text-tertiary);
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    border-radius: var(--radius-full);
    padding: 0.0625rem 0.4375rem;
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    color: var(--color-secondary);
    background: color-mix(in srgb, var(--color-secondary) 16%, transparent);
  }

  :global(.expand-icon) {
    flex-shrink: 0;
    color: var(--color-text-tertiary);
    transition:
      transform var(--transition-fast),
      color var(--transition-fast);
  }

  .settings-header:hover :global(.expand-icon) {
    color: var(--color-text-secondary);
  }

  .settings-body {
    border-top: 1px solid var(--color-outline-variant);
    padding: 0.875rem;
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }

  .body-head-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .body-head-label {
    font-size: 0.6875rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 600;
    color: var(--color-text-tertiary);
  }

  .editor-open-btn {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    padding: 0.25rem 0.5rem;
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-bg-secondary) 75%, transparent);
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast);
  }

  .editor-open-btn:hover:not(:disabled) {
    color: var(--color-text);
    background: color-mix(in srgb, var(--color-bg-tertiary) 85%, transparent);
    border-color: color-mix(in srgb, var(--color-outline) 50%, var(--color-outline-variant));
  }

  .editor-open-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .field-wrapper {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .field-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .field-helper {
    font-size: 0.6875rem;
    color: var(--color-text-tertiary);
  }

  .field-input {
    width: 100%;
    padding: 0.5625rem 0.75rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-outline-variant);
    background-color: var(--color-bg);
    font-size: 0.875rem;
    line-height: 1.35;
    color: var(--color-text);
    transition:
      border-color var(--transition-fast),
      box-shadow var(--transition-fast),
      background-color var(--transition-fast);
  }

  .field-input::placeholder {
    color: color-mix(in srgb, var(--color-text-tertiary) 88%, transparent);
  }

  .field-input:focus {
    outline: none;
    border-color: color-mix(in srgb, var(--color-primary) 70%, white);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 20%, transparent);
  }

  .field-input.disabled {
    opacity: 0.55;
    cursor: not-allowed;
    background-color: color-mix(in srgb, var(--color-bg-secondary) 72%, transparent);
  }

  .compact-textarea {
    min-height: 5.5rem;
    resize: vertical;
  }

  .modal-layout {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }

  .modal-textarea {
    resize: vertical;
    min-height: 9rem;
  }

  .prompt-textarea {
    min-height: 18rem;
    font-family: "JetBrains Mono", "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 0.8125rem;
    line-height: 1.45;
  }

  .modal-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.875rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-bg-secondary) 82%, transparent);
  }

  .animate-in {
    animation: slideIn 0.18s ease-out;
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

  @media (max-width: 480px) {
    .settings-header {
      padding: 0.75rem;
    }

    .settings-body {
      padding: 0.75rem;
      gap: 0.75rem;
    }
  }
</style>
