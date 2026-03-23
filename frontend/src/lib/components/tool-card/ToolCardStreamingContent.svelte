<script lang="ts">
  import MarkdownContent from "../markdown/MarkdownContent.svelte";

  interface Props {
    streamContent: string;
    streamContentEl?: HTMLDivElement | undefined;
  }

  let { streamContent, streamContentEl = $bindable(undefined) }: Props = $props();
</script>

<div
  bind:this={streamContentEl}
  class="stream-content border-t border-[var(--color-outline-variant)] px-3 py-2.5 bg-black/10 max-h-96 overflow-y-auto"
>
  <div class="text-[var(--color-text-secondary)] text-sm">
    <MarkdownContent content={streamContent} streaming={true} />
  </div>
</div>
