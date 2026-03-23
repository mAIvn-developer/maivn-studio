<script lang="ts">
  import type { InvocationConfig, InvocationMode, ModelTier, ReasoningLevel } from "$lib/types";
  import { applyInvocationMode, getInvocationMode } from "$lib/utils/invocationMode";
  import ConfigEditorModal from "../ui/ConfigEditorModal.svelte";
  import InvocationSettingsFields from "./InvocationSettingsFields.svelte";

  interface Props {
    config: InvocationConfig;
    availableTools?: string[];
    disabled?: boolean;
    structuredOutputEnabled?: boolean;
    onChange: (config: InvocationConfig) => void;
  }

  let {
    config,
    availableTools = [],
    disabled = false,
    structuredOutputEnabled = false,
    onChange,
  }: Props = $props();

  const invocationMode = $derived<InvocationMode>(
    getInvocationMode(config, structuredOutputEnabled),
  );
  const statusMessagesDisabled = $derived(
    disabled || structuredOutputEnabled || invocationMode === "invoke",
  );

  let isEditorOpen = $state(false);

  const invocationModes: { value: InvocationMode; label: string }[] = [
    { value: "stream", label: "Stream" },
    { value: "invoke", label: "Invoke" },
  ];

  const modelTiers: { value: ModelTier | undefined; label: string }[] = [
    { value: undefined, label: "Auto" },
    { value: "fast", label: "Fast" },
    { value: "balanced", label: "Balanced" },
    { value: "max", label: "Max" },
  ];

  const reasoningLevels: { value: ReasoningLevel | undefined; label: string }[] = [
    { value: undefined, label: "Auto" },
    { value: "minimal", label: "Min" },
    { value: "low", label: "Low" },
    { value: "medium", label: "Med" },
    { value: "high", label: "High" },
  ];

  function update(partial: Partial<InvocationConfig>) {
    onChange({ ...config, ...partial });
  }

  function updateInvocationMode(mode: InvocationMode) {
    onChange(applyInvocationMode(config, mode));
  }

  function toggleTargetedTool(toolName: string) {
    const current = config.targeted_tools ?? [];
    const next = current.includes(toolName)
      ? current.filter((t) => t !== toolName)
      : [...current, toolName];
    update({ targeted_tools: next.length > 0 ? next : undefined });
  }

  function isToolSelected(toolName: string): boolean {
    return config.targeted_tools?.includes(toolName) ?? false;
  }
</script>

<div class="invocation-settings">
  <div class="head-row">
    <span class="head-label">Runtime controls</span>
    <button type="button" class="editor-open-btn" onclick={() => (isEditorOpen = true)} {disabled}>
      Open large editor
    </button>
  </div>

  <InvocationSettingsFields
    {config}
    {invocationMode}
    {invocationModes}
    {modelTiers}
    {reasoningLevels}
    {availableTools}
    {disabled}
    {structuredOutputEnabled}
    {statusMessagesDisabled}
    onUpdate={update}
    onUpdateInvocationMode={updateInvocationMode}
    onToggleTargetedTool={toggleTargetedTool}
    {isToolSelected}
  />
</div>

<ConfigEditorModal
  open={isEditorOpen}
  title="Edit Invocation Config"
  subtitle="Large editor for model selection, reasoning, and targeted tools."
  onClose={() => (isEditorOpen = false)}
>
  <div class="modal-layout">
    <InvocationSettingsFields
      {config}
      {invocationMode}
      {invocationModes}
      {modelTiers}
      {reasoningLevels}
      {availableTools}
      {disabled}
      {structuredOutputEnabled}
      {statusMessagesDisabled}
      modal={true}
      onUpdate={update}
      onUpdateInvocationMode={updateInvocationMode}
      onToggleTargetedTool={toggleTargetedTool}
      {isToolSelected}
    />
  </div>
</ConfigEditorModal>

<style>
  .invocation-settings {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }

  .head-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .head-label {
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

  .modal-layout {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }
</style>
