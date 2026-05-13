import { describe, expect, test } from "vitest";

import type { UIEvent } from "$lib/types";
import { processEvent } from "./events";

// MARK: Fake Context

function createCtx() {
  let events: UIEvent[] = [];

  // Most processEvent dispatch arms are no-ops or guard against absent state.
  // We don't exercise them here; this test focuses on the raw-event-history
  // append behavior.
  const ctx = {
    getEvents: () => events,
    setEvents: (next: UIEvent[]) => {
      events = next;
    },
    // Stubs for the dispatcher's incidental reads (kept loose intentionally).
    setToolCards: () => undefined,
    getToolCards: () => new Map(),
    setScopeHookFirings: () => undefined,
    getScopeHookFirings: () => new Map(),
    setChatFlowItems: () => undefined,
    getChatFlowItems: () => [],
    setStatusMessages: () => undefined,
    getStatusMessages: () => [],
    setInterruptCards: () => undefined,
    getInterruptCards: () => new Map(),
    setSession: () => undefined,
    getSession: () => null,
    setCurrentPhase: () => undefined,
    getCurrentPhase: () => null,
    setCurrentPhaseMessage: () => undefined,
    getCurrentPhaseMessage: () => null,
    setProcessingScopeKey: () => undefined,
    getProcessingScopeKey: () => null,
    setProcessingScopePriority: () => undefined,
    getProcessingScopePriority: () => 0,
    setLoading: () => undefined,
    getLoading: () => false,
    setError: () => undefined,
    getError: () => null,
    setRootAssistantId: () => undefined,
    getRootAssistantId: () => null,
    setStreamingAssistantItemId: () => undefined,
    getStreamingAssistantItemId: () => null,
    assistantIdToToolId: new Map<string, string>(),
    pendingAssistantChunks: new Map<string, string>(),
    assistantSnapshots: new Map<string, string>(),
  };

  return { ctx, getEvents: () => events };
}

// MARK: Raw History Cap

describe("processEvent raw event history", () => {
  test("retains every event when under the cap", () => {
    const { ctx, getEvents } = createCtx();

    for (let i = 0; i < 50; i++) {
      processEvent(ctx as never, "heartbeat", { i });
    }

    expect(getEvents()).toHaveLength(50);
    expect(getEvents()[0].data).toMatchObject({ i: 0 });
    expect(getEvents()[49].data).toMatchObject({ i: 49 });
  });

  test("caps history at 1000 entries, dropping oldest first", () => {
    const { ctx, getEvents } = createCtx();

    for (let i = 0; i < 1100; i++) {
      processEvent(ctx as never, "heartbeat", { i });
    }

    const events = getEvents();
    expect(events).toHaveLength(1000);
    // Oldest 100 entries should have been evicted; window starts at i=100.
    expect(events[0].data).toMatchObject({ i: 100 });
    expect(events[999].data).toMatchObject({ i: 1099 });
  });
});
