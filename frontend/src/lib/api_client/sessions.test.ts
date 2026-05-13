import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { connectToEvents } from "./sessions";

function makeMockEventSource() {
  const listeners: Record<string, ((e: MessageEvent) => void)[]> = {};
  const instance = {
    addEventListener: vi.fn((type: string, cb: (e: MessageEvent) => void) => {
      if (!listeners[type]) listeners[type] = [];
      listeners[type].push(cb);
    }),
    onmessage: null as ((e: MessageEvent) => void) | null,
    onerror: null as ((e: Event) => void) | null,
    close: vi.fn(),
  };

  function MockEventSource() {
    return instance;
  }

  return { MockEventSource, listeners };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api_client connectToEvents", () => {
  it("prefers the native SSE lastEventId over a payload id", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    listeners["tool_event"]?.[0]?.({
      data: JSON.stringify({ id: "payload-id", data: { toolId: "t1" } }),
      lastEventId: "42",
    } as MessageEvent);

    expect(onEvent).toHaveBeenCalledWith({
      type: "tool_event",
      data: { toolId: "t1" },
      eventId: "42",
    });
  });

  it("falls back to the payload id when lastEventId is absent", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    listeners["assistant_chunk"]?.[0]?.({
      data: JSON.stringify({ id: "payload-id", data: { text: "hello" } }),
      lastEventId: "",
    } as MessageEvent);

    expect(onEvent).toHaveBeenCalledWith({
      type: "assistant_chunk",
      data: { text: "hello" },
      eventId: "payload-id",
    });
  });

  it("subscribes to batch lifecycle events", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    connectToEvents("s1", vi.fn());

    expect(Object.keys(listeners)).toEqual(
      expect.arrayContaining(["batch_start", "batch_item_complete", "batch_complete"]),
    );
  });

  it("subscribes to hook_fired so hook events reach the session store", () => {
    // Regression: hook_fired wasn't in the named-events list, so the browser
    // dropped every hook event before it ever reached processEvent. Tools and
    // scope cards therefore rendered without their header/footer markers even
    // though the backend was emitting them correctly.
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    connectToEvents("s1", vi.fn());

    expect(Object.keys(listeners)).toContain("hook_fired");
  });

  it("dispatches hook_fired events to the onEvent callback", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    listeners["hook_fired"]?.[0]?.({
      data: JSON.stringify({
        id: "evt-99",
        data: {
          name: "audit_log",
          stage: "before",
          status: "completed",
          target_type: "tool",
          target_id: "tool-1",
        },
      }),
      lastEventId: "99",
    } as MessageEvent);

    expect(onEvent).toHaveBeenCalledWith({
      type: "hook_fired",
      data: {
        name: "audit_log",
        stage: "before",
        status: "completed",
        target_type: "tool",
        target_id: "tool-1",
      },
      eventId: "99",
    });
  });
});
