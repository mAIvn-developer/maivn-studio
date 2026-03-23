<script lang="ts">
  import { X } from "lucide-svelte";

  interface PendingAttachmentView {
    id: string;
    name: string;
    size: number;
  }

  interface Props {
    pendingAttachments: PendingAttachmentView[];
    formatAttachmentSize: (bytes: number) => string;
    onRemoveAttachment: (attachmentId: string) => void;
    onClearAttachments: () => void;
  }

  let { pendingAttachments, formatAttachmentSize, onRemoveAttachment, onClearAttachments }: Props =
    $props();
</script>

{#if pendingAttachments.length > 0}
  <div class="px-3 py-2 border-b border-[var(--color-outline-variant)]">
    <div class="flex flex-wrap gap-2">
      {#each pendingAttachments as attachment (attachment.id)}
        <div
          class="inline-flex items-center gap-2 rounded-lg border border-[var(--color-outline-variant)]
               bg-[var(--color-bg-tertiary)] px-2 py-1"
        >
          <span class="text-xs text-[var(--color-text)] max-w-[220px] truncate">
            {attachment.name}
          </span>
          <span class="text-[10px] text-[var(--color-text-tertiary)] tabular-nums">
            {formatAttachmentSize(attachment.size)}
          </span>
          <button
            type="button"
            class="text-[var(--color-text-tertiary)] hover:text-[var(--color-text)] transition-colors"
            onclick={() => onRemoveAttachment(attachment.id)}
            aria-label="Remove attachment"
            title="Remove attachment"
          >
            <X size={14} />
          </button>
        </div>
      {/each}
      <button
        type="button"
        class="inline-flex items-center rounded-md border border-[var(--color-outline-variant)]
             px-2 py-1 text-[10px] text-[var(--color-text-secondary)]
             hover:border-[var(--color-tertiary)]/50 hover:text-[var(--color-text)] transition-colors"
        onclick={onClearAttachments}
        title="Clear attachments"
      >
        Clear
      </button>
    </div>
  </div>
{/if}
