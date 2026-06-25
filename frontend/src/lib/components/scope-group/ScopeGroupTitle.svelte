<script lang="ts">
  import type { ScopeType } from "./scope-group-helpers";

  interface Props {
    scopeType: ScopeType;
    scopeName: string;
    compact?: boolean;
  }

  let { scopeType, scopeName, compact = false }: Props = $props();
</script>

<span
  class="font-medium text-[var(--color-text)]"
  class:text-base={scopeType === "swarm" && !compact}
  class:font-semibold={scopeType === "swarm"}
  class:text-sm={scopeType !== "swarm" || compact}
>
  {scopeName}
</span>
