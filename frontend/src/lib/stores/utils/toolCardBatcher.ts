import type { ChatFlowItem, ToolCard } from "$lib/types";

// MARK: Configuration

const STREAM_DEBOUNCE_MS = 50;

// MARK: ToolCardBatcher

/**
 * Consolidates all tool card update paths into a single manager.
 *
 * Handles:
 * - Batched tool card updates via requestAnimationFrame
 * - Debounced streaming content accumulation
 * - Flushing all pending state on demand (e.g. turn_complete)
 *
 * The caller is responsible for applying returned state to reactive variables
 * (toolCards and chatFlowItems) since Svelte 5 runes must live in .svelte.ts.
 */
export class ToolCardBatcher {
  private readonly pendingToolCardUpdates = new Map<string, ToolCard>();
  private readonly pendingStreamUpdates = new Map<string, string>();
  private readonly streamingDebounceTimers = new Map<string, ReturnType<typeof setTimeout>>();
  private toolCardUpdateScheduled = false;
  private onFlush: (() => void) | null = null;

  /**
   * Register a callback that fires when batched tool card updates are flushed
   * via requestAnimationFrame. The callback should read `drainPendingUpdates()`
   * and apply the results to reactive state.
   */
  setFlushCallback(cb: () => void): void {
    this.onFlush = cb;
  }

  /**
   * Schedule a tool card update to be applied in the next animation frame.
   */
  scheduleUpdate(toolId: string, card: ToolCard): void {
    this.pendingToolCardUpdates.set(toolId, card);

    if (!this.toolCardUpdateScheduled) {
      this.toolCardUpdateScheduled = true;
      requestAnimationFrame(() => {
        this.flushToolCardUpdates();
      });
    }
  }

  /**
   * Accumulate streaming text for a tool card and schedule a debounced
   * update so rapid chunks don't cause per-character re-renders.
   */
  appendStreamContent(toolId: string, text: string, toolCards: Map<string, ToolCard>): void {
    // Accumulate pending text
    const existing = this.pendingStreamUpdates.get(toolId) ?? "";
    this.pendingStreamUpdates.set(toolId, existing + text);

    // Clear existing timer
    const existingTimer = this.streamingDebounceTimers.get(toolId);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    // Schedule debounced update
    const timer = setTimeout(() => {
      const pendingText = this.pendingStreamUpdates.get(toolId);
      if (pendingText) {
        const card = toolCards.get(toolId);
        if (card) {
          const updatedCard = {
            ...card,
            streamContent: (card.streamContent ?? "") + pendingText,
          };
          this.scheduleUpdate(toolId, updatedCard);
        }
        this.pendingStreamUpdates.delete(toolId);
      }
      this.streamingDebounceTimers.delete(toolId);
    }, STREAM_DEBOUNCE_MS);

    this.streamingDebounceTimers.set(toolId, timer);
  }

  /**
   * Drain all pending stream content for a specific tool, cancelling
   * any debounce timer. Returns the accumulated text (empty string if none).
   * Used when a tool completes and we need its final stream content immediately.
   */
  drainStreamContent(toolId: string): string {
    const existingTimer = this.streamingDebounceTimers.get(toolId);
    if (existingTimer) {
      clearTimeout(existingTimer);
      this.streamingDebounceTimers.delete(toolId);
    }
    const pendingText = this.pendingStreamUpdates.get(toolId) ?? "";
    this.pendingStreamUpdates.delete(toolId);
    return pendingText;
  }

  /**
   * Flush all pending stream updates immediately (all tools), then flush
   * batched tool card updates. Used before turn_complete/session_end to
   * ensure no content is lost.
   *
   * Returns the map of tool cards that had pending stream content applied
   * directly (i.e. outside the normal scheduleUpdate path). The caller
   * should merge these into the reactive toolCards map.
   */
  flushAllPendingStreams(toolCards: Map<string, ToolCard>): Map<string, ToolCard> {
    const directUpdates = new Map<string, ToolCard>();

    for (const [toolId] of this.streamingDebounceTimers) {
      const timer = this.streamingDebounceTimers.get(toolId);
      if (timer) {
        clearTimeout(timer);
      }

      const pendingText = this.pendingStreamUpdates.get(toolId);
      if (pendingText) {
        const card = toolCards.get(toolId);
        if (card) {
          const updated = {
            ...card,
            streamContent: (card.streamContent ?? "") + pendingText,
          };
          toolCards.set(toolId, updated);
          directUpdates.set(toolId, updated);
        }
      }
    }

    this.streamingDebounceTimers.clear();
    this.pendingStreamUpdates.clear();
    this.flushToolCardUpdates();

    return directUpdates;
  }

  /**
   * Drain all pending tool card updates. Returns the entries and clears
   * the internal queue. Called by the flush callback to read what needs
   * to be applied to reactive state.
   */
  drainPendingUpdates(): Map<string, ToolCard> {
    const updates = new Map(this.pendingToolCardUpdates);
    this.pendingToolCardUpdates.clear();
    this.toolCardUpdateScheduled = false;
    return updates;
  }

  /**
   * Apply a set of pending tool card updates to chatFlowItems in a single pass.
   * Returns the updated array.
   */
  static applyChatFlowUpdates(
    chatFlowItems: ChatFlowItem[],
    updates: Map<string, ToolCard>,
  ): ChatFlowItem[] {
    const updatedIds = new Set(updates.keys());
    return chatFlowItems.map((item) => {
      if (item.type === "tool_card") {
        const cardData = item.data as ToolCard;
        if (updatedIds.has(cardData.toolId)) {
          return { ...item, data: updates.get(cardData.toolId)! };
        }
      }
      return item;
    });
  }

  /**
   * Reset all internal state. Called on session reset.
   */
  reset(): void {
    this.pendingToolCardUpdates.clear();
    this.pendingStreamUpdates.clear();
    this.streamingDebounceTimers.forEach((timer) => clearTimeout(timer));
    this.streamingDebounceTimers.clear();
    this.toolCardUpdateScheduled = false;
  }

  // MARK: Private

  private flushToolCardUpdates(): void {
    if (this.pendingToolCardUpdates.size === 0) {
      this.toolCardUpdateScheduled = false;
      return;
    }

    if (this.onFlush) {
      this.onFlush();
    } else {
      // No callback registered - just clear the queue
      this.pendingToolCardUpdates.clear();
      this.toolCardUpdateScheduled = false;
    }
  }
}
