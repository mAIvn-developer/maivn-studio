<script lang="ts">
  import { onMount } from "svelte";

  interface Props {
    side: "left" | "right";
    defaultWidth?: number;
    minWidth?: number;
    maxWidth?: number;
    children?: import("svelte").Snippet;
  }

  let { side, defaultWidth = 320, minWidth = 200, maxWidth = 600, children }: Props = $props();

  let width = $state(0);
  let isResizing = $state(false);
  let isHovering = $state(false);
  let panelRef: HTMLElement;

  $effect(() => {
    width = Math.min(maxWidth, Math.max(minWidth, defaultWidth));
  });

  function handleMouseDown(e: MouseEvent) {
    e.preventDefault();
    isResizing = true;
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }

  function handleMouseMove(e: MouseEvent) {
    if (!isResizing || !panelRef) return;

    const rect = panelRef.getBoundingClientRect();
    let newWidth: number;

    if (side === "left") {
      newWidth = e.clientX - rect.left;
    } else {
      newWidth = rect.right - e.clientX;
    }

    width = Math.min(maxWidth, Math.max(minWidth, newWidth));
  }

  function handleMouseUp() {
    isResizing = false;
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }

  function handleDoubleClick() {
    width = Math.min(maxWidth, Math.max(minWidth, defaultWidth));
  }

  function handleKeyDown(e: KeyboardEvent) {
    const step = e.shiftKey ? 50 : 10;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      width = Math.max(minWidth, width - step);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      width = Math.min(maxWidth, width + step);
    } else if (e.key === "Home") {
      e.preventDefault();
      width = minWidth;
    } else if (e.key === "End") {
      e.preventDefault();
      width = maxWidth;
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleDoubleClick();
    }
  }

  onMount(() => {
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  });
</script>

<aside bind:this={panelRef} class="relative flex-shrink-0 flex flex-col" style="width: {width}px">
  <!-- Resize handle with wider hit area -->
  <button
    type="button"
    class="resize-handle {side === 'left' ? 'resize-handle-right' : 'resize-handle-left'}"
    class:active={isResizing}
    class:hovering={isHovering}
    role="slider"
    aria-orientation="vertical"
    aria-valuenow={width}
    aria-valuemin={minWidth}
    aria-valuemax={maxWidth}
    aria-label="Resize panel. Use arrow keys to adjust width, Enter or double-click to reset."
    onmousedown={handleMouseDown}
    ondblclick={handleDoubleClick}
    onkeydown={handleKeyDown}
    onmouseenter={() => (isHovering = true)}
    onmouseleave={() => (isHovering = false)}
    onfocus={() => (isHovering = true)}
    onblur={() => (isHovering = false)}
  >
    <!-- Centered indicator pill -->
    <div class="resize-indicator"></div>
  </button>

  <!-- Panel content -->
  <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
    {@render children?.()}
  </div>
</aside>

<style>
  .resize-handle {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 12px;
    cursor: col-resize;
    background: transparent;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .resize-handle-left {
    left: -6px;
  }

  .resize-handle-right {
    right: -6px;
  }

  /* Indicator pill */
  .resize-indicator {
    width: 3px;
    height: 0;
    border-radius: 2px;
    background-color: var(--color-outline-variant);
    transition:
      height var(--transition-normal) ease,
      background-color var(--transition-fast) ease,
      width var(--transition-fast) ease;
  }

  /* Hover state - show indicator */
  .resize-handle.hovering .resize-indicator,
  .resize-handle:focus-visible .resize-indicator {
    height: 48px;
    background-color: var(--color-secondary);
  }

  /* Active state - larger indicator */
  .resize-handle.active .resize-indicator {
    height: 64px;
    width: 4px;
    background-color: var(--color-secondary);
    box-shadow: var(--shadow-glow-tertiary);
  }

  /* Focus visible ring */
  .resize-handle:focus-visible {
    outline: none;
  }

  .resize-handle:focus-visible .resize-indicator {
    box-shadow: var(--shadow-glow-tertiary);
  }

  /* Border line on edge */
  .resize-handle::before {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background-color: var(--color-outline-variant);
    transition: background-color var(--transition-fast) ease;
  }

  .resize-handle-left::before {
    left: 6px;
  }

  .resize-handle-right::before {
    right: 6px;
  }

  .resize-handle.hovering::before,
  .resize-handle.active::before,
  .resize-handle:focus-visible::before {
    background-color: var(--color-secondary);
  }
</style>
