<script lang="ts">
  type Variant = "spinner" | "skeleton" | "dots";
  type Size = "sm" | "md" | "lg";

  interface Props {
    variant?: Variant;
    size?: Size;
    label?: string;
    class?: string;
  }

  let { variant = "spinner", size = "md", label, class: className = "" }: Props = $props();

  const sizes: Record<Size, { spinner: string; dots: string; skeleton: string; text: string }> = {
    sm: {
      spinner: "h-4 w-4 border-2",
      dots: "h-1.5 w-1.5",
      skeleton: "h-3",
      text: "text-xs",
    },
    md: {
      spinner: "h-8 w-8 border-2",
      dots: "h-2 w-2",
      skeleton: "h-4",
      text: "text-sm",
    },
    lg: {
      spinner: "h-12 w-12 border-3",
      dots: "h-3 w-3",
      skeleton: "h-5",
      text: "text-base",
    },
  };

  const currentSize = $derived(sizes[size]);
</script>

<div class="loading-state flex flex-col items-center justify-center gap-3 {className}">
  {#if variant === "spinner"}
    <div
      class="rounded-full border-[var(--color-tertiary)]/30 border-t-[var(--color-tertiary)] animate-spin {currentSize.spinner}"
    ></div>
  {:else if variant === "dots"}
    <div class="flex items-center gap-1.5">
      {#each [0, 1, 2] as i}
        <div
          class="rounded-full bg-[var(--color-tertiary)] {currentSize.dots}"
          style="animation: bounce 1.4s infinite ease-in-out; animation-delay: {i * 0.16}s"
        ></div>
      {/each}
    </div>
  {:else if variant === "skeleton"}
    <div class="w-full space-y-2">
      <div class="skeleton rounded {currentSize.skeleton} w-3/4"></div>
      <div class="skeleton rounded {currentSize.skeleton} w-full"></div>
      <div class="skeleton rounded {currentSize.skeleton} w-5/6"></div>
    </div>
  {/if}

  {#if label}
    <p class="text-[var(--color-text-secondary)] {currentSize.text}">{label}</p>
  {/if}
</div>

<style>
  @keyframes bounce {
    0%,
    80%,
    100% {
      transform: scale(0.8);
      opacity: 0.5;
    }
    40% {
      transform: scale(1);
      opacity: 1;
    }
  }

  .skeleton {
    background: linear-gradient(
      90deg,
      var(--color-bg-tertiary) 25%,
      var(--color-surface-variant) 50%,
      var(--color-bg-tertiary) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }
</style>
