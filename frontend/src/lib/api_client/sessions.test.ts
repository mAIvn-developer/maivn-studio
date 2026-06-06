import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { InvocationConfig } from "../types";

import {
  cancelSession,
  connectToEvents,
  createSession,
  endSession,
  fetchSession,
  sendMessage,
  submitInterrupt,
} from "./sessions";

// MARK: Helpers

function mockFetchOk(data: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data)),
      clone: () => ({
        text: () => Promise.resolve(JSON.stringify(data)),
      }),
    }),
  );
}

function mockFetchError(status: number, body?: Record<string, unknown>): void {
  const bodyStr = JSON.stringify(body ?? {});
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      json: () => (body ? Promise.resolve(body) : Promise.reject(new Error("no json"))),
      text: () => Promise.resolve(bodyStr),
      clone: () => ({
        text: () => Promise.resolve(bodyStr),
      }),
    }),
  );
}

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

  return { MockEventSource, instance, listeners };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// MARK: Sessions API

describe("createSession", () => {
  it("creates a session with minimal args", async () => {
    const session = { id: "s1", status: "running" };
    mockFetchOk(session);

    const result = await createSession("d1", "hello");
    expect(result).toEqual(session);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/sessions");
    const body = JSON.parse(call[1].body);
    expect(body.app_id).toBe("d1");
    expect(body.message).toBe("hello");
    expect(body.message_type).toBe("human");
  });

  it("sends structured output payload when enabled", async () => {
    mockFetchOk({ id: "s1" });

    await createSession("d1", "hello", {
      structuredOutput: {
        enabled: true,
        selectedTool: "my_tool",
        schema: { name: "MySchema", schema: { type: "object" } },
      },
    });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.structured_output).toEqual({
      enabled: true,
      tool_name: "my_tool",
      schema_name: "MySchema",
      json_schema: { type: "object" },
    });
  });

  it("sends structured output intent when enabled without a hand-picked tool", async () => {
    mockFetchOk({ id: "s1" });

    await createSession("d1", "hello", {
      structuredOutput: { enabled: true },
    });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.structured_output).toEqual({ enabled: true });
  });

  it("omits structured output when disabled", async () => {
    mockFetchOk({ id: "s1" });

    await createSession("d1", "hello", {
      structuredOutput: { enabled: false },
    });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.structured_output).toBeUndefined();
  });

  it("throws with error detail from response", async () => {
    mockFetchError(400, { detail: "App not found" });
    await expect(createSession("bad", "hello")).rejects.toThrow("App not found");
  });

  it("throws with message field from error response", async () => {
    mockFetchError(400, { message: "Invalid input" });
    await expect(createSession("bad", "hello")).rejects.toThrow("Invalid input");
  });

  it("falls back to raw text when error json has no detail/message", async () => {
    // Override to return json without detail or message fields
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ error: "something" }),
        text: () => Promise.resolve("raw error text"),
        clone: () => ({
          text: () => Promise.resolve("raw error text"),
        }),
      }),
    );
    await expect(createSession("bad", "hello")).rejects.toThrow("raw error text");
  });

  it("uses fallback message when error body is empty", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error("no json")),
        text: () => Promise.resolve(""),
        clone: () => ({
          text: () => Promise.resolve(""),
        }),
      }),
    );
    await expect(createSession("bad", "hello")).rejects.toThrow("Failed to create session");
  });
});

describe("fetchSession", () => {
  it("returns session data", async () => {
    const session = { id: "s1", status: "running" };
    mockFetchOk(session);

    const result = await fetchSession("s1");
    expect(result).toEqual(session);
    expect(fetch).toHaveBeenCalledWith("/api/sessions/s1");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(404);
    await expect(fetchSession("s1")).rejects.toThrow("Failed to fetch session s1");
  });
});

describe("sendMessage", () => {
  it("sends a message with default type", async () => {
    mockFetchOk({ session_id: "s1", queued_message_count: 0 });

    const result = await sendMessage("s1", "hello");

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/sessions/s1/messages");
    const body = JSON.parse(call[1].body);
    expect(body.message).toBe("hello");
    expect(body.message_type).toBe("human");
    expect(result.session_id).toBe("s1");
  });

  it("sends with custom message type and invocation", async () => {
    mockFetchOk({ session_id: "s1", queued_message_count: 1 });

    const invocation: InvocationConfig = { force_final_tool: true, metadata: { temperature: 0.5 } };
    const result = await sendMessage("s1", "test", "system", undefined, invocation);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.message_type).toBe("system");
    expect(body.invocation).toEqual({ force_final_tool: true, metadata: { temperature: 0.5 } });
    expect(result.queued_message_count).toBe(1);
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400, { detail: "Failed to send message" });
    await expect(sendMessage("s1", "hello")).rejects.toThrow("Failed to send message");
  });
});

describe("endSession", () => {
  it("sends POST to end endpoint", async () => {
    mockFetchOk(undefined);

    await endSession("s1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/sessions/s1/end",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(endSession("s1")).rejects.toThrow("Failed to end session");
  });
});

describe("cancelSession", () => {
  it("sends POST to cancel endpoint", async () => {
    mockFetchOk(undefined);

    await cancelSession("s1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/sessions/s1/cancel",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(cancelSession("s1")).rejects.toThrow("Failed to cancel session");
  });
});

describe("submitInterrupt", () => {
  it("submits interrupt and returns session", async () => {
    const session = { id: "s1", status: "running" };
    mockFetchOk(session);

    const result = await submitInterrupt("s1", "int-1", "answer", "yes");
    expect(result).toEqual(session);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.interrupt_id).toBe("int-1");
    expect(body.data_key).toBe("answer");
    expect(body.value).toBe("yes");
  });

  it("throws with detail from error response", async () => {
    mockFetchError(400, { detail: "Interrupt expired" });
    await expect(submitInterrupt("s1", "int-1", "key", "val")).rejects.toThrow("Interrupt expired");
  });

  it("throws default message when error has no detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: () => Promise.resolve({}),
      }),
    );
    await expect(submitInterrupt("s1", "int-1", "key", "val")).rejects.toThrow(
      "Failed to submit interrupt",
    );
  });
});

// MARK: SSE Connection

describe("api_client connectToEvents", () => {
  it("creates EventSource and dispatches tool_event payloads", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    const instance = connectToEvents("s1", onEvent);
    expect(instance.addEventListener).toHaveBeenCalled();

    const toolEventHandler = listeners["tool_event"]?.[0];
    expect(toolEventHandler).toBeDefined();
    toolEventHandler!({
      data: JSON.stringify({ data: { toolId: "t1" } }),
    } as MessageEvent);

    expect(onEvent).toHaveBeenCalledWith({
      type: "tool_event",
      data: { toolId: "t1" },
      eventId: undefined,
    });
  });

  it("forwards assistant_chunk events", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    listeners["assistant_chunk"]?.[0]?.({
      data: JSON.stringify({ data: { assistant_id: "assistant", text: "hel" } }),
    } as MessageEvent);

    expect(onEvent).toHaveBeenCalledWith({
      type: "assistant_chunk",
      data: { assistant_id: "assistant", text: "hel" },
      eventId: undefined,
    });
  });

  it("promotes the payload type on default message events", () => {
    // The live client reads payload.type for default "message" events, so a
    // payload tagged { type: "test" } is dispatched as that concrete type
    // rather than the generic "message" channel.
    const { MockEventSource, instance } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    instance.onmessage!({ data: JSON.stringify({ type: "test" }) } as MessageEvent);
    expect(onEvent).toHaveBeenCalledWith({
      type: "test",
      data: { type: "test" },
      eventId: undefined,
    });
  });

  it("registers error handler when provided", () => {
    const { MockEventSource, instance } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onError = vi.fn();
    connectToEvents("s1", vi.fn(), onError);

    expect(instance.onerror).toBe(onError);
  });

  it("handles parse errors gracefully", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    listeners["tool_event"]?.[0]?.({ data: "not json" } as MessageEvent);
    expect(onEvent).not.toHaveBeenCalled();
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it("uses the full payload when no nested data key is present", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    listeners["heartbeat"]?.[0]?.({
      data: JSON.stringify({ timestamp: 123 }),
    } as MessageEvent);

    expect(onEvent).toHaveBeenCalledWith({
      type: "heartbeat",
      data: { timestamp: 123 },
      eventId: undefined,
    });
  });

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
