<script lang="ts">
  import { updateAgent } from "$lib/api_client/demo-config";
  import AgentCapabilityChips from "$lib/components/scope-settings/AgentCapabilityChips.svelte";
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
    AgentInfo,
    InvocationMemoryConfig,
    MemoryConfig,
    PrivateDataField,
  } from "$lib/types";
  import { ChevronDown, User } from "lucide-svelte";
  import ConfigEditorModal from "../ui/ConfigEditorModal.svelte";
  import MemorySettings from "./MemorySettings.svelte";
  import PrivateDataConfig from "./PrivateDataConfig.svelte";

  interface Props {
    agents: AgentInfo[];
    demoId: string;
    disabled?: boolean;
    onAgentUpdated?: () => void;
  }

  let { agents, demoId, disabled = false, onAgentUpdated }: Props = $props();

  // Track which agents are expanded
  let expandedAgents = $state<Set<string>>(new Set());
  // Track edited values per agent
  let edits = $state<Record<string, Partial<AgentInfo>>>({});
  // Track saving state per agent
  let saving = $state<Record<string, boolean>>({});
  // Track save errors per agent
  let saveErrors = $state<Record<string, string>>({});
  // Track full-screen editor state
  let editingAgentName = $state<string | null>(null);

  function toggleAgent(name: string) {
    expandedAgents = toggleExpandedItem(expandedAgents, name);
  }

  function getEdit(agentName: string): Partial<AgentInfo> {
    return getItemEdit(edits, agentName);
  }

  function setEdit(agentName: string, field: string, value: unknown) {
    edits = setItemEdit(edits, agentName, field, value);
  }

  function hasChanges(agentName: string): boolean {
    return hasItemChanges(edits, agentName);
  }

  function getEditValue(agent: AgentInfo, field: keyof AgentInfo): unknown {
    return getItemEditValue(edits, agent, field);
  }

  function getEditTags(agent: AgentInfo): string {
    return getItemEditTags(edits, agent);
  }

  function handleTagsInput(agentName: string, value: string) {
    setEdit(agentName, "tags", parseTagInput(value));
  }

  function getIncludedNestedSynthesisValue(agent: AgentInfo): "auto" | "true" | "false" {
    const current = getEditValue(agent, "included_nested_synthesis");
    if (current === true) return "true";
    if (current === false) return "false";
    return "auto";
  }

  function getScopeMemoryConfig(agent: AgentInfo): MemoryConfig {
    return getItemScopeMemoryConfig(edits, agent);
  }

  function handleScopeMemoryChange(agent: AgentInfo, config: MemoryConfig) {
    setEdit(agent.name, "memory_config", buildItemScopeMemoryEdit(edits, agent, config));
  }

  function getPrivateDataValues(agent: AgentInfo): Record<string, unknown> {
    return getItemPrivateDataValues(edits, agent);
  }

  function handlePrivateDataChange(agentName: string, values: Record<string, unknown>) {
    setEdit(agentName, "private_data", values);
  }

  function getPrivateDataSchema(agent: AgentInfo): PrivateDataField[] {
    const values = getPrivateDataValues(agent);
    return buildItemPrivateDataSchema(agent, values);
  }

  async function handleSave(agent: AgentInfo) {
    const edit = getEdit(agent.name);
    await saveScopeItemChanges({
      itemName: agent.name,
      edit,
      edits,
      setEdits: (nextEdits: Record<string, Partial<AgentInfo>>) => {
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
      editingName: editingAgentName,
      setEditingName: (name: string | null) => {
        editingAgentName = name;
      },
      onUpdated: onAgentUpdated,
      persist: async (pendingEdit: Partial<AgentInfo>) => {
        await updateAgent(demoId, agent.name, {
          description: pendingEdit.description as string | undefined,
          system_prompt: pendingEdit.system_prompt as string | undefined,
          tags: pendingEdit.tags as string[] | undefined,
          memory_config: pendingEdit.memory_config as InvocationMemoryConfig | undefined,
          timeout: pendingEdit.timeout as number | undefined,
          max_results: pendingEdit.max_results as number | undefined,
          included_nested_synthesis: pendingEdit.included_nested_synthesis as
            | boolean
            | "auto"
            | undefined,
          allow_private_in_system_tools: pendingEdit.allow_private_in_system_tools as
            | boolean
            | undefined,
          private_data: pendingEdit.private_data as Record<string, unknown> | undefined,
        });
      },
    });
  }

  function handleDiscard(agentName: string) {
    edits = discardItemEdit(edits, agentName);
  }

  function openEditor(agentName: string) {
    editingAgentName = agentName;
  }

  function closeEditor() {
    editingAgentName = null;
  }
</script>

{#if agents.length > 0}
  <section class="settings-section">
    <div class="section-header">
      <h4 class="section-title">Agents</h4>
      <span class="section-count">{agents.length}</span>
    </div>

    <div class="settings-list">
      {#each agents as agent}
        <article class="settings-card" class:dirty={hasChanges(agent.name)}>
          <button
            type="button"
            class="settings-header"
            aria-expanded={expandedAgents.has(agent.name)}
            onclick={() => toggleAgent(agent.name)}
          >
            <div class="icon-shell">
              <User size={14} class="text-[var(--color-secondary)]" />
            </div>

            <div class="header-content">
              <div class="header-main-row">
                <span class="header-title">{agent.name}</span>
                {#if hasChanges(agent.name)}
                  <span class="status-pill">Unsaved</span>
                {/if}
              </div>
              <div class="header-subtitle">
                <span>
                  {#if agent.runtime_tool_count !== agent.tool_count}
                    {agent.runtime_tool_count} runtime tools
                  {:else}
                    {agent.tool_count} tools
                  {/if}
                </span>
                {#if agent.runtime_tool_count !== agent.tool_count}
                  <span>{agent.tool_count} authored tools</span>
                {/if}
                {#if agent.is_swarm_member}
                  <span>in {agent.swarm}</span>
                {/if}
              </div>
            </div>

            <ChevronDown
              size={18}
              class="expand-icon {expandedAgents.has(agent.name) ? 'rotate-180' : ''}"
            />
          </button>

          {#if expandedAgents.has(agent.name)}
            <div class="settings-body animate-in">
              <div class="body-head-row">
                <span class="body-head-label">Agent Settings</span>
                <button
                  type="button"
                  class="editor-open-btn"
                  onclick={() => openEditor(agent.name)}
                  {disabled}
                >
                  Open large editor
                </button>
              </div>

              <AgentCapabilityChips
                useAsFinalOutput={agent.use_as_final_output}
                hasBeforeHook={agent.has_before_hook}
                hasAfterHook={agent.has_after_hook}
                hookExecutionMode={agent.hook_execution_mode}
                mcpServerNames={agent.mcp_server_names}
              />

              <div class="field-wrapper">
                <label class="field-label" for="agent-desc-{agent.name}">Description</label>
                <textarea
                  id="agent-desc-{agent.name}"
                  class="field-input compact-textarea"
                  class:disabled
                  {disabled}
                  rows="3"
                  oninput={(e) =>
                    setEdit(agent.name, "description", (e.target as HTMLTextAreaElement).value)}
                  placeholder="What this agent is responsible for..."
                  >{getEditValue(agent, "description") as string}</textarea
                >
              </div>

              <ScopePromptPanel
                value={(getEditValue(agent, "system_prompt") as string) ?? ""}
                {disabled}
                accent="var(--color-secondary)"
                onInput={(value) => setEdit(agent.name, "system_prompt", value)}
              />

              <div class="field-wrapper">
                <label class="field-label" for="agent-tags-{agent.name}">Tags</label>
                <input
                  id="agent-tags-{agent.name}"
                  type="text"
                  class="field-input"
                  class:disabled
                  {disabled}
                  value={getEditTags(agent)}
                  oninput={(e) => handleTagsInput(agent.name, (e.target as HTMLInputElement).value)}
                  placeholder="tag1, tag2, ..."
                />
                <span class="field-helper">Use commas to separate tags.</span>
              </div>

              <div class="field-grid">
                <div class="field-wrapper">
                  <label class="field-label" for="agent-timeout-{agent.name}"
                    >Timeout (seconds)</label
                  >
                  <input
                    id="agent-timeout-{agent.name}"
                    type="number"
                    class="field-input"
                    class:disabled
                    {disabled}
                    value={(getEditValue(agent, "timeout") as number) ?? ""}
                    oninput={(e) => {
                      const v = (e.target as HTMLInputElement).value;
                      setEdit(agent.name, "timeout", v ? Number(v) : undefined);
                    }}
                    placeholder="No timeout"
                  />
                </div>
                <div class="field-wrapper">
                  <label class="field-label" for="agent-maxresults-{agent.name}">Max Results</label>
                  <input
                    id="agent-maxresults-{agent.name}"
                    type="number"
                    class="field-input"
                    class:disabled
                    {disabled}
                    value={(getEditValue(agent, "max_results") as number) ?? ""}
                    oninput={(e) => {
                      const v = (e.target as HTMLInputElement).value;
                      setEdit(agent.name, "max_results", v ? Number(v) : undefined);
                    }}
                    placeholder="No limit"
                  />
                </div>
              </div>

              <div class="field-wrapper">
                <label class="field-label" for="agent-included-nested-{agent.name}"
                  >Included Nested Synthesis</label
                >
                <select
                  id="agent-included-nested-{agent.name}"
                  class="field-input"
                  class:disabled
                  {disabled}
                  value={getIncludedNestedSynthesisValue(agent)}
                  onchange={(e) => {
                    const value = (e.target as HTMLSelectElement).value;
                    setEdit(
                      agent.name,
                      "included_nested_synthesis",
                      value === "true" ? true : value === "false" ? false : "auto",
                    );
                  }}
                >
                  <option value="auto">auto (recommended)</option>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
                <span class="field-helper">
                  Controls whether nested swarm-agent synthesis is included in downstream context.
                </span>
              </div>

              <label class="toggle-card" class:is-disabled={disabled}>
                <div class="toggle-copy">
                  <span class="toggle-title">Allow private data in system tools</span>
                  <span class="toggle-description">
                    Lets this agent pass private values to system-level tools when needed.
                  </span>
                </div>
                <div class="switch-shell">
                  <input
                    type="checkbox"
                    class="peer sr-only"
                    checked={(getEditValue(agent, "allow_private_in_system_tools") as boolean) ??
                      false}
                    onchange={(e) =>
                      setEdit(
                        agent.name,
                        "allow_private_in_system_tools",
                        (e.target as HTMLInputElement).checked,
                      )}
                    {disabled}
                  />
                  <span class="switch-track"></span>
                  <span class="switch-thumb"></span>
                </div>
              </label>

              <ScopeSaveActions
                showActions={hasChanges(agent.name)}
                saving={saving[agent.name] ?? false}
                error={saveErrors[agent.name] ?? ""}
                saveDisabled={disabled || !!saving[agent.name]}
                discardDisabled={disabled || !!saving[agent.name]}
                onSave={() => handleSave(agent)}
                onDiscard={() => handleDiscard(agent.name)}
              />
            </div>
          {/if}

          <ConfigEditorModal
            open={editingAgentName === agent.name}
            title={`Edit Agent Scope: ${agent.name}`}
            subtitle="Overlay editor for agent scope defaults, prompts, memory, and private data."
            onClose={closeEditor}
          >
            <div class="modal-layout">
              <AgentCapabilityChips
                useAsFinalOutput={agent.use_as_final_output}
                hasBeforeHook={agent.has_before_hook}
                hasAfterHook={agent.has_after_hook}
                hookExecutionMode={agent.hook_execution_mode}
                mcpServerNames={agent.mcp_server_names}
              />

              <div class="field-wrapper">
                <label class="field-label" for="agent-modal-desc-{agent.name}">Description</label>
                <textarea
                  id="agent-modal-desc-{agent.name}"
                  class="field-input modal-textarea"
                  class:disabled
                  {disabled}
                  rows="6"
                  oninput={(e) =>
                    setEdit(agent.name, "description", (e.target as HTMLTextAreaElement).value)}
                  placeholder="Describe this agent's role and boundaries..."
                  >{getEditValue(agent, "description") as string}</textarea
                >
              </div>

              <div class="field-wrapper">
                <label class="field-label" for="agent-modal-system-{agent.name}"
                  >System Prompt</label
                >
                <textarea
                  id="agent-modal-system-{agent.name}"
                  class="field-input modal-textarea prompt-textarea"
                  class:disabled
                  {disabled}
                  rows="14"
                  oninput={(e) =>
                    setEdit(agent.name, "system_prompt", (e.target as HTMLTextAreaElement).value)}
                  placeholder="System prompt..."
                  >{(getEditValue(agent, "system_prompt") as string) ?? ""}</textarea
                >
              </div>

              <div class="field-wrapper">
                <label class="field-label" for="agent-modal-tags-{agent.name}">Tags</label>
                <input
                  id="agent-modal-tags-{agent.name}"
                  type="text"
                  class="field-input"
                  class:disabled
                  {disabled}
                  value={getEditTags(agent)}
                  oninput={(e) => handleTagsInput(agent.name, (e.target as HTMLInputElement).value)}
                  placeholder="tag1, tag2, ..."
                />
              </div>

              <div class="field-grid">
                <div class="field-wrapper">
                  <label class="field-label" for="agent-modal-timeout-{agent.name}"
                    >Timeout (seconds)</label
                  >
                  <input
                    id="agent-modal-timeout-{agent.name}"
                    type="number"
                    class="field-input"
                    class:disabled
                    {disabled}
                    value={(getEditValue(agent, "timeout") as number) ?? ""}
                    oninput={(e) => {
                      const v = (e.target as HTMLInputElement).value;
                      setEdit(agent.name, "timeout", v ? Number(v) : undefined);
                    }}
                    placeholder="No timeout"
                  />
                </div>
                <div class="field-wrapper">
                  <label class="field-label" for="agent-modal-maxresults-{agent.name}"
                    >Max Results</label
                  >
                  <input
                    id="agent-modal-maxresults-{agent.name}"
                    type="number"
                    class="field-input"
                    class:disabled
                    {disabled}
                    value={(getEditValue(agent, "max_results") as number) ?? ""}
                    oninput={(e) => {
                      const v = (e.target as HTMLInputElement).value;
                      setEdit(agent.name, "max_results", v ? Number(v) : undefined);
                    }}
                    placeholder="No limit"
                  />
                </div>
              </div>

              <div class="field-wrapper">
                <label class="field-label" for="agent-modal-included-nested-{agent.name}"
                  >Included Nested Synthesis</label
                >
                <select
                  id="agent-modal-included-nested-{agent.name}"
                  class="field-input"
                  class:disabled
                  {disabled}
                  value={getIncludedNestedSynthesisValue(agent)}
                  onchange={(e) => {
                    const value = (e.target as HTMLSelectElement).value;
                    setEdit(
                      agent.name,
                      "included_nested_synthesis",
                      value === "true" ? true : value === "false" ? false : "auto",
                    );
                  }}
                >
                  <option value="auto">auto (recommended)</option>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
                <span class="field-helper">
                  Controls whether nested swarm-agent synthesis is included in downstream context.
                </span>
              </div>

              <label class="toggle-card" class:is-disabled={disabled}>
                <div class="toggle-copy">
                  <span class="toggle-title">Allow private data in system tools</span>
                  <span class="toggle-description">
                    Lets this agent pass private values to system-level tools when needed.
                  </span>
                </div>
                <div class="switch-shell">
                  <input
                    type="checkbox"
                    class="peer sr-only"
                    checked={(getEditValue(agent, "allow_private_in_system_tools") as boolean) ??
                      false}
                    onchange={(e) =>
                      setEdit(
                        agent.name,
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
                  config={getScopeMemoryConfig(agent)}
                  {disabled}
                  onChange={(config) => handleScopeMemoryChange(agent, config)}
                />
              </div>

              {#if getPrivateDataSchema(agent).length > 0}
                <div class="modal-section">
                  <PrivateDataConfig
                    schema={getPrivateDataSchema(agent)}
                    values={getPrivateDataValues(agent)}
                    onchange={(values) => handlePrivateDataChange(agent.name, values)}
                    {disabled}
                  />
                </div>
              {/if}

              <ScopeSaveActions
                saving={saving[agent.name] ?? false}
                error={saveErrors[agent.name] ?? ""}
                saveDisabled={disabled || !!saving[agent.name] || !hasChanges(agent.name)}
                discardDisabled={disabled || !!saving[agent.name] || !hasChanges(agent.name)}
                onSave={() => handleSave(agent)}
                onDiscard={() => handleDiscard(agent.name)}
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
        color-mix(in srgb, var(--color-secondary) 28%, transparent),
        transparent
      ),
      color-mix(in srgb, var(--color-secondary-container) 32%, var(--color-bg-secondary));
    border: 1px solid color-mix(in srgb, var(--color-secondary) 22%, var(--color-outline-variant));
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
    gap: 0.35rem;
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
    border-color: color-mix(in srgb, var(--color-secondary) 70%, white);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-secondary) 20%, transparent);
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
  }

  .prompt-textarea {
    min-height: 18rem;
    font-family: "JetBrains Mono", "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 0.8125rem;
    line-height: 1.45;
  }

  .field-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
    gap: 0.75rem;
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

  .toggle-card {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    padding: 0.625rem 0.75rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.875rem;
    cursor: pointer;
    background: color-mix(in srgb, var(--color-bg-tertiary) 45%, transparent);
  }

  .toggle-card.is-disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .toggle-copy {
    display: flex;
    flex-direction: column;
    gap: 0.1875rem;
  }

  .toggle-title {
    font-size: 0.75rem;
    line-height: 1.2;
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  .toggle-description {
    font-size: 0.6875rem;
    line-height: 1.3;
    color: var(--color-text-tertiary);
  }

  .switch-shell {
    position: relative;
    width: 2.125rem;
    height: 1.25rem;
    flex-shrink: 0;
  }

  .switch-track {
    position: absolute;
    inset: 0;
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-outline) 36%, transparent);
    transition: background-color var(--transition-fast);
  }

  .switch-thumb {
    position: absolute;
    top: 0.125rem;
    left: 0.125rem;
    width: 1rem;
    height: 1rem;
    border-radius: var(--radius-full);
    background: #fff;
    transition: transform var(--transition-fast);
  }

  .peer:checked ~ .switch-track {
    background: var(--color-secondary);
  }

  .peer:checked ~ .switch-thumb {
    transform: translateX(0.875rem);
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
