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

<div
  class="message-type-selector inline-flex rounded-lg p-0.5 bg-[var(--color-bg-tertiary)]"
  class:opacity-50={disabled}
  class:pointer-events-none={disabled}
>
  {#each baseOptions as option}
    <button
      type="button"
      onclick={() => selectOption(option.value)}
      title={option.baseTooltip}
      class="segment flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium
             transition-all duration-200"
      class:active={value === option.value}
      class:text-[var(--color-on-tertiary)]={value === option.value}
      class:bg-[var(--color-tertiary)]={value === option.value}
      class:shadow-sm={value === option.value}
      class:text-[var(--color-text-secondary)]={value !== option.value}
      class:hover:text-[var(--color-text)]={value !== option.value}
      class:hover:bg-[var(--color-bg-secondary)]={value !== option.value}
    >
      <option.icon size={14} />
      <span class="hidden sm:inline">{option.label}</span>
    </button>
  {/each}
</div>

<style>
  .message-type-selector {
    border: 1px solid var(--color-outline-variant);
  }

  .segment {
    min-width: 32px;
    justify-content: center;
  }

  .segment.active {
    transform: scale(1.02);
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
