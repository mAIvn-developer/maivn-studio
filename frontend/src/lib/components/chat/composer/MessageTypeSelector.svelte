<script lang="ts">
  import { User, EyeOff } from "lucide-svelte";
  import type { SendableMessageType } from "$lib/types";

  interface Props {
    value: SendableMessageType;
    onchange?: (value: SendableMessageType) => void;
    disabled?: boolean;
  }

  let { value = "human", onchange, disabled = false }: Props = $props();

  const baseOptions: {
    value: SendableMessageType;
    label: string;
    icon: typeof User;
    baseTooltip: string;
  }[] = [
    {
      value: "human",
      label: "Human",
      icon: User,
      baseTooltip: "Standard user message",
    },
    {
      value: "redacted",
      label: "Redacted",
      icon: EyeOff,
      baseTooltip: "Message hidden from AI context",
    },
  ];

  function selectOption(optionValue: SendableMessageType) {
    if (disabled) return;
    onchange?.(optionValue);
  }
</script>

<div class="message-type-selector" class:opacity-50={disabled} class:pointer-events-none={disabled}>
  {#each baseOptions as option}
    <button
      type="button"
      onclick={() => selectOption(option.value)}
      title={option.baseTooltip}
      class="segment"
      class:active={value === option.value}
    >
      <option.icon size={14} />
      <span class="hidden sm:inline">{option.label}</span>
    </button>
  {/each}
</div>

<style>
  .message-type-selector {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    box-sizing: border-box;
    height: var(--composer-control-height, 2.35rem);
    min-height: var(--composer-control-height, 2.35rem);
    border-radius: var(--radius-md);
    border: 0;
    background: var(--color-bg);
    padding: 0;
    box-shadow: inset 0 0 0 1px var(--color-outline-variant);
  }

  .segment {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    box-sizing: border-box;
    height: var(--composer-control-height, 2.35rem);
    min-height: var(--composer-control-height, 2.35rem);
    min-width: 2rem;
    border: 0;
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--color-text-secondary);
    padding: 0 0.6rem;
    font-size: 0.75rem;
    font-weight: 650;
    cursor: pointer;
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast),
      transform var(--transition-fast);
  }

  .segment:hover:not(.active) {
    background: color-mix(in srgb, var(--color-bg-tertiary) 44%, transparent);
    color: var(--color-text);
  }

  .segment.active {
    background: var(--color-secondary);
    color: var(--color-on-secondary);
    justify-content: center;
  }

  /* Show tooltip on hover */
  .segment[title] {
    position: relative;
  }

  .segment[title]:hover::after {
    content: attr(title);
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    padding: 6px 10px;
    background: var(--color-bg);
    border: 1px solid var(--color-outline-variant);
    border-radius: 6px;
    font-size: 11px;
    font-weight: 400;
    color: var(--color-text-secondary);
    white-space: nowrap;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    animation: tooltipFade 0.15s ease-out;
  }

  .segment[title]:hover::before {
    content: "";
    position: absolute;
    bottom: calc(100% + 4px);
    left: 50%;
    transform: translateX(-50%);
    border: 4px solid transparent;
    border-top-color: var(--color-outline-variant);
    z-index: 101;
  }

  @keyframes tooltipFade {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(4px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }
</style>
