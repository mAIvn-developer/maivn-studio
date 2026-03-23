<script lang="ts">
  type BadgeVariant =
    | "default"
    | "primary"
    | "secondary"
    | "tertiary"
    | "error"
    | "warning"
    | "success"
    | "outline";

  interface Props {
    variant?: BadgeVariant;
    pill?: boolean;
    class?: string;
    children?: import("svelte").Snippet;
  }

  let { variant = "default", pill = false, class: className = "", children }: Props = $props();

  const variantClasses: Record<BadgeVariant, string> = {
    default: "bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]",
    primary: "bg-[var(--color-primary)]/15 text-[var(--color-primary)]",
    secondary: "bg-[var(--color-secondary)]/15 text-[var(--color-secondary)]",
    tertiary: "bg-[var(--color-tertiary)]/15 text-[var(--color-tertiary)]",
    error: "bg-[var(--color-error)]/15 text-[var(--color-error)]",
    warning: "bg-[var(--color-warning)]/15 text-[var(--color-warning)]",
    success: "bg-[var(--color-success)]/15 text-[var(--color-success)]",
    outline: "border border-[var(--color-outline-variant)] text-[var(--color-text-secondary)]",
  };
</script>

<span
  class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium whitespace-nowrap
         {pill ? 'rounded-full px-2' : 'rounded'}
         {variantClasses[variant]} {className}"
>
  {#if children}
    {@render children()}
  {/if}
</span>
