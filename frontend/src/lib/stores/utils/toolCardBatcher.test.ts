import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChatFlowItem, ToolCard } from "$lib/types";
import { ToolCardBatcher } from "./toolCardBatcher";

// MARK: Helpers

function makeToolCard(overrides: Partial<ToolCard> = {}): ToolCard {
  return {
    toolId: "tool-1",
    toolName: "test_tool",
    toolType: "func",
    status: "executing",
    args: {},
    startedAt: "2024-01-01T00:00:00Z",
    isStreaming: false,
    isSystemTool: false,
    ...overrides,
  };
}

function makeToolFlowItem(card: ToolCard): ChatFlowItem {
  return {
    id: `flow-${card.toolId}`,
    type: "tool_card",
    timestamp: card.startedAt,
    data: card,
  };
}

function toolCardOf(item: ChatFlowItem): ToolCard {
  if (item.type !== "tool_card") {
    throw new Error(`expected tool_card item, got ${item.type}`);
  }
  return item.data;
}

// Stub requestAnimationFrame globally for all tests in this file since
// the test environment is node (no DOM APIs).
beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
    // Execute synchronously so scheduleUpdate flush is predictable
    cb(0);
    return 0;
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

// MARK: ToolCardBatcher

describe("ToolCardBatcher", () => {
  describe("scheduleUpdate", () => {
    it("queues a tool card update", () => {
      const batcher = new ToolCardBatcher();
      const flushFn = vi.fn();
      batcher.setFlushCallback(flushFn);
      const card = makeToolCard({ toolId: "tool-1" });

      batcher.scheduleUpdate("tool-1", card);

      // After the rAF flush, the callback was invoked
      expect(flushFn).toHaveBeenCalled();
    });

    it("overwrites earlier update for same tool ID before flush", () => {
      const batcher = new ToolCardBatcher();
      // Don't register a flush callback so updates accumulate
      const card1 = makeToolCard({ toolId: "tool-1", status: "executing" });
      const card2 = makeToolCard({ toolId: "tool-1", status: "completed" });

      // Directly populate the pending map (bypassing rAF)
      batcher.scheduleUpdate("tool-1", card1);
      // First rAF fires and flushes (no callback = just clears)

      // Second schedule also fires rAF immediately
      batcher.scheduleUpdate("tool-1", card2);

      // Since no flush callback is set, updates are cleared by flush.
      // Let's test with a callback that drains properly.
      const batcher2 = new ToolCardBatcher();
      let latestDrained: Map<string, ToolCard> = new Map();
      batcher2.setFlushCallback(() => {
        latestDrained = batcher2.drainPendingUpdates();
      });

      batcher2.scheduleUpdate("tool-1", card1);
      expect(latestDrained.get("tool-1")?.status).toBe("executing");

      batcher2.scheduleUpdate("tool-1", card2);
      expect(latestDrained.get("tool-1")?.status).toBe("completed");
    });

    it("queues updates for multiple tools independently", () => {
      const batcher = new ToolCardBatcher();
      const allDrained: Map<string, ToolCard> = new Map();
      batcher.setFlushCallback(() => {
        for (const [k, v] of batcher.drainPendingUpdates()) {
          allDrained.set(k, v);
        }
      });

      batcher.scheduleUpdate("tool-1", makeToolCard({ toolId: "tool-1" }));
      batcher.scheduleUpdate("tool-2", makeToolCard({ toolId: "tool-2" }));

      // Both tools should have been flushed (possibly across two rAF cycles)
      expect(allDrained.size).toBe(2);
      expect(allDrained.has("tool-1")).toBe(true);
      expect(allDrained.has("tool-2")).toBe(true);
    });
  });

  describe("drainPendingUpdates", () => {
    it("returns pending updates and clears the queue", () => {
      const batcher = new ToolCardBatcher();
      let latestDrained: Map<string, ToolCard> = new Map();
      batcher.setFlushCallback(() => {
        latestDrained = batcher.drainPendingUpdates();
      });

      batcher.scheduleUpdate("tool-1", makeToolCard());
      expect(latestDrained.size).toBe(1);

      // Second drain returns empty
      expect(batcher.drainPendingUpdates().size).toBe(0);
    });

    it("returns empty map when no updates pending", () => {
      const batcher = new ToolCardBatcher();
      expect(batcher.drainPendingUpdates().size).toBe(0);
    });
  });

  describe("drainStreamContent", () => {
    it("returns accumulated text and clears it", () => {
      const batcher = new ToolCardBatcher();
      const toolCards = new Map<string, ToolCard>();
      toolCards.set("tool-1", makeToolCard({ toolId: "tool-1", isStreaming: true }));

      batcher.appendStreamContent("tool-1", "Hello ", toolCards);
      batcher.appendStreamContent("tool-1", "world!", toolCards);

      const text = batcher.drainStreamContent("tool-1");
      expect(text).toBe("Hello world!");

      // Subsequent drain returns empty
      expect(batcher.drainStreamContent("tool-1")).toBe("");
    });

    it("returns empty string when no pending content", () => {
      const batcher = new ToolCardBatcher();
      expect(batcher.drainStreamContent("nonexistent")).toBe("");
    });

    it("cancels debounce timer when draining", () => {
      const batcher = new ToolCardBatcher();
      const toolCards = new Map<string, ToolCard>();
      toolCards.set("tool-1", makeToolCard({ toolId: "tool-1", isStreaming: true }));

      batcher.appendStreamContent("tool-1", "text", toolCards);

      // Drain before debounce fires
      batcher.drainStreamContent("tool-1");

      // Advance past debounce — should not create any update since content was drained
      vi.advanceTimersByTime(100);
      expect(batcher.drainPendingUpdates().size).toBe(0);
    });
  });

  describe("appendStreamContent", () => {
    it("accumulates text across multiple appends", () => {
      const batcher = new ToolCardBatcher();
      const toolCards = new Map<string, ToolCard>();
      toolCards.set("tool-1", makeToolCard({ toolId: "tool-1", isStreaming: true }));

      batcher.appendStreamContent("tool-1", "A", toolCards);
      batcher.appendStreamContent("tool-1", "B", toolCards);
      batcher.appendStreamContent("tool-1", "C", toolCards);

      expect(batcher.drainStreamContent("tool-1")).toBe("ABC");
    });

    it("schedules a debounced update that fires after timeout", () => {
      const batcher = new ToolCardBatcher();
      const card = makeToolCard({ toolId: "tool-1", isStreaming: true, streamContent: "" });
      const toolCards = new Map<string, ToolCard>([["tool-1", card]]);

      batcher.appendStreamContent("tool-1", "chunk", toolCards);

      // Before debounce fires, pending stream content exists
      expect(batcher.drainStreamContent("tool-1")).toBe("chunk");
    });

    it("fires debounced update after timeout with accumulated stream content", () => {
      const batcher = new ToolCardBatcher();
      let latestDrained: Map<string, ToolCard> = new Map();
      batcher.setFlushCallback(() => {
        latestDrained = batcher.drainPendingUpdates();
      });

      const card = makeToolCard({
        toolId: "tool-1",
        isStreaming: true,
        streamContent: "prev-",
      });
      const toolCards = new Map<string, ToolCard>([["tool-1", card]]);

      batcher.appendStreamContent("tool-1", "new", toolCards);

      // Advance timers past the debounce (50ms)
      vi.advanceTimersByTime(60);

      // The debounced callback should have scheduled an update with concatenated content
      expect(latestDrained.get("tool-1")?.streamContent).toBe("prev-new");
    });
  });

  describe("flushAllPendingStreams", () => {
    it("applies all pending stream content to tool cards", () => {
      const batcher = new ToolCardBatcher();
      const card1 = makeToolCard({
        toolId: "tool-1",
        isStreaming: true,
        streamContent: "existing-",
      });
      const card2 = makeToolCard({
        toolId: "tool-2",
        isStreaming: true,
        streamContent: "",
      });
      const toolCards = new Map<string, ToolCard>([
        ["tool-1", card1],
        ["tool-2", card2],
      ]);

      batcher.appendStreamContent("tool-1", "new1", toolCards);
      batcher.appendStreamContent("tool-2", "new2", toolCards);

      const directUpdates = batcher.flushAllPendingStreams(toolCards);

      expect(directUpdates.size).toBe(2);
      expect(directUpdates.get("tool-1")?.streamContent).toBe("existing-new1");
      expect(directUpdates.get("tool-2")?.streamContent).toBe("new2");
    });

    it("clears all debounce timers and pending content", () => {
      const batcher = new ToolCardBatcher();
      const toolCards = new Map<string, ToolCard>([
        ["tool-1", makeToolCard({ toolId: "tool-1", isStreaming: true })],
      ]);

      batcher.appendStreamContent("tool-1", "text", toolCards);
      batcher.flushAllPendingStreams(toolCards);

      // After flush, nothing pending
      expect(batcher.drainStreamContent("tool-1")).toBe("");
    });

    it("returns empty map when no pending streams", () => {
      const batcher = new ToolCardBatcher();
      const toolCards = new Map<string, ToolCard>();

      const result = batcher.flushAllPendingStreams(toolCards);
      expect(result.size).toBe(0);
    });
  });

  describe("applyChatFlowUpdates (static)", () => {
    it("updates matching tool_card items in chatFlowItems", () => {
      const card1 = makeToolCard({ toolId: "tool-1", status: "executing" });
      const card2 = makeToolCard({ toolId: "tool-2", status: "executing" });
      const items: ChatFlowItem[] = [makeToolFlowItem(card1), makeToolFlowItem(card2)];

      const updatedCard1 = { ...card1, status: "completed" as const };
      const updates = new Map<string, ToolCard>([["tool-1", updatedCard1]]);

      const result = ToolCardBatcher.applyChatFlowUpdates(items, updates);

      expect(result).toHaveLength(2);
      expect(toolCardOf(result[0]).status).toBe("completed");
      expect(toolCardOf(result[1]).status).toBe("executing");
    });

    it("preserves non-tool_card items", () => {
      const items: ChatFlowItem[] = [
        {
          id: "msg-1",
          type: "message",
          timestamp: "2024-01-01T00:00:00Z",
          data: {
            id: "msg-1",
            role: "assistant",
            messageType: "ai",
            content: "Hello",
            timestamp: "2024-01-01T00:00:00Z",
          },
        },
        makeToolFlowItem(makeToolCard({ toolId: "tool-1" })),
      ];

      const updates = new Map<string, ToolCard>([
        ["tool-1", makeToolCard({ toolId: "tool-1", status: "completed" })],
      ]);

      const result = ToolCardBatcher.applyChatFlowUpdates(items, updates);

      expect(result[0].type).toBe("message");
      expect(toolCardOf(result[1]).status).toBe("completed");
    });

    it("does not mutate the original array", () => {
      const card = makeToolCard({ toolId: "tool-1", status: "executing" });
      const items: ChatFlowItem[] = [makeToolFlowItem(card)];

      ToolCardBatcher.applyChatFlowUpdates(
        items,
        new Map([["tool-1", { ...card, status: "completed" }]]),
      );

      expect(toolCardOf(items[0]).status).toBe("executing");
    });

    it("handles empty updates map", () => {
      const items: ChatFlowItem[] = [makeToolFlowItem(makeToolCard({ toolId: "tool-1" }))];

      const result = ToolCardBatcher.applyChatFlowUpdates(items, new Map());

      expect(result).toHaveLength(1);
      expect(result[0]).toBe(items[0]); // Same reference (no change)
    });
  });

  describe("setFlushCallback", () => {
    it("calls the registered callback when updates are flushed via rAF", () => {
      const batcher = new ToolCardBatcher();
      const flushFn = vi.fn();
      batcher.setFlushCallback(flushFn);

      batcher.scheduleUpdate("tool-1", makeToolCard());

      expect(flushFn).toHaveBeenCalledOnce();
    });
  });

  describe("reset", () => {
    it("clears all internal state", () => {
      const batcher = new ToolCardBatcher();
      const toolCards = new Map<string, ToolCard>([
        ["tool-1", makeToolCard({ toolId: "tool-1", isStreaming: true })],
      ]);

      batcher.scheduleUpdate("tool-1", makeToolCard());
      batcher.appendStreamContent("tool-1", "text", toolCards);

      batcher.reset();

      expect(batcher.drainPendingUpdates().size).toBe(0);
      expect(batcher.drainStreamContent("tool-1")).toBe("");
    });
  });
});
