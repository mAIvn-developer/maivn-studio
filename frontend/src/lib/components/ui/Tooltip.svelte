<script lang="ts">
  interface Props {
    text: string;
    shortcut?: string;
    position?: "top" | "bottom" | "left" | "right";
    children: import("svelte").Snippet;
    class?: string;
  }

  let { text, shortcut, position = "bottom", children, class: className = "" }: Props = $props();
  let visible = $state(false);
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  function show() {
    timeoutId = setTimeout(() => {
      visible = true;
    }, 400);
  }

  function hide() {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
    visible = false;
  }

  const positionClasses: Record<string, string> = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="relative inline-flex {className}"
  onmouseenter={show}
  onmouseleave={hide}
  onfocus={show}
  onblur={hide}
>
  {@render children()}

  {#if visible}
    <div
      class="absolute z-50 px-2.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap pointer-events-none
             bg-[var(--color-bg-elevated)] text-[var(--color-text)] shadow-lg border border-[var(--color-outline-variant)]
             animate-in {positionClasses[position]}"
    >
      <span>{text}</span>
      {#if shortcut}
        <kbd
          class="ml-1.5 px-1 py-0.5 rounded bg-[var(--color-bg-tertiary)] text-[10px] font-mono text-[var(--color-text-tertiary)]"
        >
          {shortcut}
        </kbd>
      {/if}
    </div>
  {/if}
</div>
