<script lang="ts">
  import {
    Menu,
    AppWindow,
    PanelBottom,
    MessageSquare,
    LayoutDashboard,
    ChevronDown,
    Check,
  } from "lucide-svelte";
  import type { InterruptStyle } from "$lib/types";

  interface Props {
    value: InterruptStyle;
    onChange: (style: InterruptStyle) => void;
  }

  let { value, onChange }: Props = $props();

  let isOpen = $state(false);
  let openUpward = $state(false);
  let triggerButton: HTMLButtonElement | null = $state(null);

  const styleOptions: {
    value: InterruptStyle;
    label: string;
    description: string;
    icon: typeof Menu;
  }[] = [
    {
      value: "inline",
      label: "Inline Card",
      description: "Appears in chat flow",
      icon: Menu,
    },
    {
      value: "modal",
      label: "Modal Dialog",
      description: "Centered overlay",
      icon: AppWindow,
    },
    {
      value: "drawer",
      label: "Bottom Drawer",
      description: "Slide-up panel",
      icon: PanelBottom,
    },
    {
      value: "floating",
      label: "Floating Card",
      description: "Bottom-right notification",
      icon: MessageSquare,
    },
    {
      value: "hybrid",
      label: "Hybrid",
      description: "Inline + queue drawer",
      icon: LayoutDashboard,
    },
  ];

  const currentOption = $derived(styleOptions.find((o) => o.value === value) || styleOptions[0]);
  const CurrentIcon = $derived(currentOption.icon);

  // Estimated dropdown height (5 options * ~56px each + header ~32px + padding)
  const DROPDOWN_HEIGHT = 320;

  function toggleDropdown() {
    if (!isOpen && triggerButton) {
      // Calculate if there's enough space below
      const rect = triggerButton.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;

      // Open upward if not enough space below and more space above
      openUpward = spaceBelow < DROPDOWN_HEIGHT && spaceAbove > spaceBelow;
    }
    isOpen = !isOpen;
  }

  function selectStyle(style: InterruptStyle) {
    onChange(style);
    isOpen = false;
  }

  function handleClickOutside(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target.closest(".interrupt-style-selector")) {
      isOpen = false;
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      isOpen = false;
    }
  }

  $effect(() => {
    if (isOpen) {
      window.addEventListener("click", handleClickOutside);
      window.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      window.removeEventListener("click", handleClickOutside);
      window.removeEventListener("keydown", handleKeyDown);
    };
  });
</script>

<div class="interrupt-style-selector relative">
  <!-- Trigger button -->
  <button
    bind:this={triggerButton}
    type="button"
    onclick={toggleDropdown}
    class="flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-colors
           hover:bg-[var(--color-bg-tertiary)]
           text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
    aria-haspopup="listbox"
    aria-expanded={isOpen}
  >
    <CurrentIcon size={16} />
    <span class="hidden sm:inline">{currentOption.label}</span>
    <ChevronDown size={12} class="transition-transform {isOpen ? 'rotate-180' : ''}" />
  </button>

  <!-- Dropdown menu -->
  {#if isOpen}
    <div
      class="dropdown-menu absolute right-0 w-56 rounded-lg shadow-xl z-50
             bg-[var(--color-bg-secondary)] border border-[var(--color-outline-variant)]"
      class:top-full={!openUpward}
      class:mt-1={!openUpward}
      class:bottom-full={openUpward}
      class:mb-1={openUpward}
      class:animate-fade-in-down={!openUpward}
      class:animate-fade-in-up={openUpward}
      role="listbox"
    >
      <div class="py-1">
        <div
          class="px-3 py-2 text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-semibold"
        >
          Interrupt Style
        </div>

        {#each styleOptions as option}
          {@const OptionIcon = option.icon}
          <button
            type="button"
            onclick={() => selectStyle(option.value)}
            class="w-full px-3 py-2 flex items-start gap-3 text-left transition-colors
                   hover:bg-[var(--color-bg-tertiary)]"
            class:bg-[var(--color-bg-tertiary)]={option.value === value}
            role="option"
            aria-selected={option.value === value}
          >
            <OptionIcon
              size={20}
              class="flex-shrink-0 mt-0.5 {option.value === value
                ? 'text-[var(--color-primary)]'
                : 'text-[var(--color-text-tertiary)]'}"
            />

            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span
                  class="text-sm font-medium"
                  class:text-[var(--color-text)]={option.value === value}
                  class:text-[var(--color-text-secondary)]={option.value !== value}
                >
                  {option.label}
                </span>
                {#if option.value === "inline"}
                  <span
                    class="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-primary)]/10 text-[var(--color-primary)] font-medium"
                  >
                    Default
                  </span>
                {/if}
              </div>
              <p class="text-xs text-[var(--color-text-tertiary)] mt-0.5">
                {option.description}
              </p>
            </div>

            {#if option.value === value}
              <Check size={16} class="text-[var(--color-primary)] flex-shrink-0 mt-0.5" />
            {/if}
          </button>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  /* Animation keyframes for dropdown */

  @keyframes fade-in-down {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes fade-in-up {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-fade-in-down {
    animation: fade-in-down 0.15s ease-out;
  }

  .animate-fade-in-up {
    animation: fade-in-up 0.15s ease-out;
  }
</style>
