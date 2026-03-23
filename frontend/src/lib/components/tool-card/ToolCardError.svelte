<script lang="ts">
  import type { ToolStatusDisplayConfig } from "./tool-card-display";

  interface Props {
    error: string;
    status: ToolStatusDisplayConfig;
  }

  let { error, status }: Props = $props();
</script>

<div class="px-3 py-2.5" style="background: {status.bg}">
  <div
    class="text-[10px] uppercase tracking-wider mb-1.5 font-medium"
    style="color: {status.color}"
  >
    Error
  </div>
  <pre class="text-xs font-mono whitespace-pre-wrap" style="color: {status.color}">{error}</pre>
</div>
