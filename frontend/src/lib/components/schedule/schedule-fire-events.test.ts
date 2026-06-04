import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createScheduleFireEventStream } from "./schedule-fire-events.svelte";

function makeMockEventSource() {
  const listeners: Record<string, ((e: MessageEvent<string>) => void)[]> = {};
  const instance = {
    addEventListener: vi.fn((type: string, cb: (e: MessageEvent<string>) => void) => {
      if (!listeners[type]) listeners[type] = [];
      listeners[type].push(cb);
    }),
    close: vi.fn(),
  };

  function MockEventSource() {
    return instance;
  }

  return { MockEventSource, instance, listeners };
}

function fireEvent(
  listeners: Record<string, ((e: MessageEvent<string>) => void)[]>,
  type: string,
  data: unknown,
) {
  listeners[type]?.[0]?.({ data: JSON.stringify({ data }) } as MessageEvent<string>);
}

let uuidCounter = 0;

beforeEach(() => {
  vi.restoreAllMocks();
  uuidCounter = 0;
  vi.stubGlobal("crypto", {
    randomUUID: () => `uuid-${++uuidCounter}`,
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("createScheduleFireEventStream", () => {
  it("keeps assistant streaming in one message after a reevaluate event", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const stream = createScheduleFireEventStream("app-1", "fire-1", "session-1");

    fireEvent(listeners, "assistant_chunk", { text: "Draft" });
    fireEvent(listeners, "enrichment", {
      phase: "reevaluate_accrued",
      message: "Reevaluate (cycle 1, 1 results collected)",
      reevaluate: {
        source: "llm",
        reevaluate_count: 1,
        collected_count: 1,
      },
    });
    fireEvent(listeners, "assistant_chunk", { text: " revised" });

    const messages = stream.chatFlowItems
      .filter((item) => item.type === "message")
      .map((item) => item.data);

    expect(messages).toHaveLength(1);
    expect(messages[0].content).toBe("Draft revised");
    expect(messages[0].metadata?.isStreaming).toBe(true);

    stream.close();
  });
});
