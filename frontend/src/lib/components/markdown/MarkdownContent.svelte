<script lang="ts">
  import { Check, Copy } from "lucide-svelte";
  import {
    decodeHtml as decodeMarkdownHtml,
    parseMarkdown as parseMarkdownContent,
  } from "./markdown-parser";

  interface Props {
    content: string;
    streaming?: boolean;
  }

  let { content, streaming = false }: Props = $props();
  let container: HTMLDivElement | null = null;
  let codeBlocks: { wrapper: HTMLElement; code: string }[] = $state([]);
  let copiedIndex: number | null = $state(null);

  function portal(node: HTMLElement, target: HTMLElement): { destroy: () => void } {
    target.appendChild(node);
    return {
      destroy() {
        if (node.parentNode) {
          node.parentNode.removeChild(node);
        }
      },
    };
  }

  let copyTimeout: number | undefined;

  async function handleCopyClick(index: number): Promise<void> {
    const block = codeBlocks[index];
    if (!block) return;

    const raw = block.code;
    const code = decodeMarkdownHtml(raw);

    try {
      await navigator.clipboard.writeText(code);
      copiedIndex = index;
      if (copyTimeout) {
        window.clearTimeout(copyTimeout);
      }
      copyTimeout = window.setTimeout(() => {
        copiedIndex = null;
      }, 2000);
    } catch {
      return;
    }
  }

  $effect(() => {
    void content;
    if (!container) return;

    queueMicrotask(() => {
      if (!container) return;
      const wrappers = container.querySelectorAll<HTMLElement>(".code-block-wrapper");
      codeBlocks = Array.from(wrappers).map((wrapper) => ({
        wrapper,
        code: wrapper.dataset.code || "",
      }));
    });
  });
</script>

<div class="markdown-content" class:streaming bind:this={container}>
  <!-- eslint-disable-next-line svelte/no-at-html-tags -- Markdown rendering requires HTML; input is sanitized via entity escaping -->
  {@html parseMarkdownContent(content)}
  {#if streaming}
    <span class="cursor"></span>
  {/if}
</div>

<!-- Copy buttons rendered via Svelte and portaled into {@html} code block wrappers -->
{#each codeBlocks as block, i}
  <button
    type="button"
    class="copy-btn"
    aria-label="Copy code"
    title={copiedIndex === i ? "Copied" : "Copy code"}
    use:portal={block.wrapper}
    onclick={() => handleCopyClick(i)}
    class:copied={copiedIndex === i}
  >
    {#if copiedIndex === i}
      <Check size={14} />
      <span class="copy-label">Copied</span>
    {:else}
      <Copy size={14} />
      <span class="copy-label">Copy code</span>
    {/if}
  </button>
{/each}

<style>
  .markdown-content {
    font-size: 0.875rem;
    line-height: 1.6;
    word-wrap: break-word;
    --md-accent: var(--color-secondary);
    --md-accent-muted: color-mix(in srgb, var(--color-secondary) 22%, transparent);
    --md-accent-strong: color-mix(in srgb, var(--color-primary) 55%, var(--color-text));
    --md-accent-warm: color-mix(in srgb, var(--color-secondary) 55%, var(--color-text));
    --md-code-text: color-mix(in srgb, var(--color-secondary) 70%, var(--color-text));
    --md-surface: color-mix(in srgb, var(--color-bg-tertiary) 85%, transparent);
  }

  .markdown-content :global(p) {
    margin-bottom: 0.75rem;
  }

  .markdown-content :global(p:last-child) {
    margin-bottom: 0;
  }

  .markdown-content :global(h1),
  .markdown-content :global(h2),
  .markdown-content :global(h3),
  .markdown-content :global(h4),
  .markdown-content :global(h5),
  .markdown-content :global(h6) {
    font-weight: 600;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    color: var(--color-text);
    letter-spacing: 0.01em;
  }

  .markdown-content :global(h1) {
    font-size: 1.5rem;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid var(--md-accent-muted);
    color: color-mix(in srgb, var(--color-secondary) 70%, var(--color-text));
  }

  .markdown-content :global(h2) {
    font-size: 1.25rem;
    padding: 0.2rem 0 0.25rem 0.75rem;
    border-bottom: 1px solid color-mix(in srgb, var(--color-secondary) 18%, transparent);
    position: relative;
  }

  .markdown-content :global(h2)::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0.35rem;
    bottom: 0.35rem;
    width: 3px;
    border-radius: 999px;
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--color-secondary) 70%, transparent),
      color-mix(in srgb, var(--color-secondary) 40%, transparent)
    );
  }

  .markdown-content :global(h3) {
    font-size: 1.125rem;
    color: color-mix(in srgb, var(--color-secondary) 65%, var(--color-text));
  }

  .markdown-content :global(h4) {
    font-size: 1rem;
    color: color-mix(in srgb, var(--color-secondary) 55%, var(--color-text));
  }

  .markdown-content :global(code) {
    background-color: var(--md-surface);
    padding: 0.2rem 0.4rem;
    border-radius: 999px;
    font-family: monospace;
    font-size: 0.8125rem;
    border: 1px solid color-mix(in srgb, var(--color-secondary) 20%, transparent);
    color: var(--md-code-text);
  }

  .markdown-content :global(.code-block-wrapper) {
    position: relative;
    margin: 0.5rem 0;
  }

  .markdown-content :global(.copy-btn) {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    padding: 0.4rem;
    background: color-mix(in srgb, var(--color-bg-secondary) 90%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-secondary) 25%, transparent);
    border-radius: 0.375rem;
    color: var(--color-text-tertiary);
    cursor: pointer;
    opacity: 0;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }

  .markdown-content :global(.code-block-wrapper:hover .copy-btn) {
    opacity: 1;
  }

  .markdown-content :global(.code-block-wrapper:focus-within .copy-btn),
  .markdown-content :global(.copy-btn:focus-visible) {
    opacity: 1;
  }

  .markdown-content :global(.copy-btn:hover) {
    background: var(--color-bg-secondary);
    color: var(--color-text);
    border-color: color-mix(in srgb, var(--color-secondary) 40%, transparent);
  }

  .markdown-content :global(.copy-btn:focus-visible) {
    outline: 2px solid color-mix(in srgb, var(--color-secondary) 45%, transparent);
    outline-offset: 2px;
  }

  .markdown-content :global(.copy-btn.copied) {
    color: var(--color-success);
    border-color: var(--color-success);
  }

  .copy-label {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .markdown-content :global(pre) {
    background: #1e1e2e;
    padding: 0.9rem;
    border-radius: 0.5rem;
    overflow-x: auto;
    margin: 0;
    border: 1px solid color-mix(in srgb, var(--color-secondary) 18%, transparent);
    position: relative;
  }

  .markdown-content :global(pre code) {
    background: none;
    padding: 0;
    border: none;
    border-radius: 0;
    color: var(--color-text);
    font-size: 0.82rem;
    line-height: 1.5;
  }

  .markdown-content :global(.hl-keyword) {
    color: #c792ea;
    font-weight: 500;
  }

  .markdown-content :global(.hl-string) {
    color: #c3e88d;
  }

  .markdown-content :global(.hl-comment) {
    color: #697098;
    font-style: italic;
  }

  .markdown-content :global(.hl-number) {
    color: #f78c6c;
  }

  .markdown-content :global(.hl-function) {
    color: #82aaff;
  }

  .markdown-content :global(.hl-builtin) {
    color: #ffcb6b;
  }

  .markdown-content :global(.hl-decorator) {
    color: #ff5370;
  }

  .markdown-content :global(.hl-variable) {
    color: #89ddff;
  }

  .markdown-content :global(pre[data-lang]) {
    padding-top: 1.6rem;
  }

  .markdown-content :global(pre[data-lang])::before {
    content: attr(data-lang);
    position: absolute;
    top: 0.35rem;
    left: 0.6rem;
    font-size: 0.6rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--md-accent);
    background: color-mix(in srgb, var(--color-secondary) 18%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-secondary) 30%, transparent);
    padding: 0.1rem 0.4rem;
    border-radius: 999px;
  }

  @media (hover: none) {
    .markdown-content :global(.copy-btn) {
      opacity: 1;
    }
  }

  .markdown-content :global(ul),
  .markdown-content :global(ol) {
    margin-left: 1.5rem;
    margin-bottom: 0.75rem;
    padding-left: 0.25rem;
  }

  .markdown-content :global(li) {
    margin-bottom: 0.25rem;
  }

  .markdown-content :global(li::marker) {
    color: var(--md-accent);
  }

  .markdown-content :global(strong) {
    font-weight: 600;
    color: var(--md-accent-strong);
  }

  .markdown-content :global(em) {
    color: var(--md-accent-warm);
  }

  .markdown-content :global(del) {
    color: var(--color-text-tertiary);
  }

  /* Private data badge styles are in app.css (global) so they
     render correctly in <pre>, tool cards, and other non-markdown contexts. */

  .markdown-content :global(a) {
    color: var(--md-accent);
    text-decoration: underline;
    text-decoration-thickness: 1px;
    text-underline-offset: 2px;
  }

  .markdown-content :global(blockquote) {
    margin: 0.75rem 0;
    padding: 0.6rem 0.8rem;
    border-left: 3px solid var(--md-accent);
    background: color-mix(in srgb, var(--color-secondary) 14%, transparent);
    border-radius: 0.4rem;
    color: var(--color-text);
  }

  .markdown-content :global(hr) {
    border: none;
    border-top: 1px solid color-mix(in srgb, var(--color-secondary) 25%, transparent);
    margin: 1rem 0;
  }

  .markdown-content :global(.md-table-wrap) {
    margin: 0.85rem 0 1rem;
    overflow-x: auto;
    border-radius: 0.6rem;
    border: 1px solid color-mix(in srgb, var(--color-secondary) 18%, transparent);
    background: color-mix(in srgb, var(--color-bg-tertiary) 85%, transparent);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }

  .markdown-content :global(.md-table) {
    width: 100%;
    min-width: 520px;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.85rem;
    overflow: hidden;
    font-variant-numeric: tabular-nums;
  }

  .markdown-content :global(.md-table th),
  .markdown-content :global(.md-table td) {
    border-bottom: 1px solid color-mix(in srgb, var(--color-secondary) 16%, transparent);
    padding: 0.5rem 0.7rem;
    text-align: left;
  }

  .markdown-content :global(.md-table th) {
    background: linear-gradient(
      135deg,
      color-mix(in srgb, var(--color-secondary) 20%, var(--color-bg-tertiary)),
      color-mix(in srgb, var(--color-secondary) 10%, var(--color-bg-tertiary))
    );
    color: color-mix(in srgb, var(--color-secondary) 65%, var(--color-text));
    font-weight: 600;
    text-transform: none;
    white-space: nowrap;
  }

  .markdown-content :global(.md-table thead th) {
    border-bottom: 1px solid color-mix(in srgb, var(--color-secondary) 30%, transparent);
  }

  .markdown-content :global(.md-table tbody tr:nth-child(even)) {
    background: color-mix(in srgb, var(--color-bg-tertiary) 80%, transparent);
  }

  .markdown-content :global(.md-table tbody tr:hover) {
    background: color-mix(in srgb, var(--color-secondary) 14%, transparent);
  }

  .markdown-content :global(.md-table_no-header) {
    border-top: 3px dashed color-mix(in srgb, var(--color-secondary) 35%, transparent);
  }

  .markdown-content :global(.md-table_no-header tbody tr:first-child td) {
    background: color-mix(in srgb, var(--color-secondary) 10%, var(--color-bg-tertiary));
    border-top: none;
  }

  .markdown-content :global(.md-table_no-header tbody tr td:first-child) {
    color: color-mix(in srgb, var(--color-secondary) 58%, var(--color-text));
    font-weight: 500;
  }

  .markdown-content :global(.md-table td:first-child),
  .markdown-content :global(.md-table th:first-child) {
    border-left: none;
  }

  .markdown-content :global(.md-table td:last-child),
  .markdown-content :global(.md-table th:last-child) {
    border-right: none;
  }

  .streaming .cursor {
    display: inline-block;
    width: 2px;
    height: 1em;
    background-color: var(--color-accent);
    margin-left: 2px;
    animation: blink 1s step-end infinite;
  }

  @keyframes blink {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0;
    }
  }
</style>
