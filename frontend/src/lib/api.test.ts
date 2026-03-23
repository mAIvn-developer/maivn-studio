import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  applyRepoSelection,
  cancelSession,
  connectToEvents,
  createSession,
  deletePrompt,
  endSession,
  fetchDemo,
  fetchDemoFullDetails,
  fetchDemos,
  fetchDemosByCategory,
  fetchSavedPrompts,
  fetchSession,
  savePrompt,
  scanRepo,
  sendMessage,
  submitInterrupt,
  updateAgent,
  updateDemo,
  updateSwarm,
} from "./api";
import type { InvocationConfig, RepoScanSelection } from "./types";

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

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// MARK: Demos API

describe("fetchDemos", () => {
  it("returns list of demos", async () => {
    const demos = [{ id: "d1", name: "Demo 1" }];
    mockFetchOk({ demos });

    const result = await fetchDemos();
    expect(result).toEqual(demos);
    expect(fetch).toHaveBeenCalledWith("/api/demos");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchDemos()).rejects.toThrow("Failed to fetch demos");
  });
});

describe("fetchDemosByCategory", () => {
  it("groups demos by category", async () => {
    const demos = [
      { id: "d1", name: "Demo 1", category: "core" },
      { id: "d2", name: "Demo 2", category: "core" },
      { id: "d3", name: "Demo 3", category: "advanced" },
    ];
    mockFetchOk({ demos });

    const result = await fetchDemosByCategory();
    expect(result).toEqual({
      core: [demos[0], demos[1]],
      advanced: [demos[2]],
    });
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchDemosByCategory()).rejects.toThrow("Failed to fetch demos");
  });
});

describe("fetchDemo", () => {
  it("merges demo and variants into DemoDetails", async () => {
    const demo = { id: "d1", name: "Demo 1" };
    const variants = [{ args: [], description: "default" }];
    mockFetchOk({ demo, variants });

    const result = await fetchDemo("d1");
    expect(result.id).toBe("d1");
    expect(result.variants).toEqual(variants);
    expect(result.agents).toEqual([]);
    expect(result.tools).toEqual([]);
  });

  it("throws on non-ok response", async () => {
    mockFetchError(404);
    await expect(fetchDemo("d1")).rejects.toThrow("Failed to fetch demo d1");
  });
});

describe("fetchDemoFullDetails", () => {
  it("returns full demo details", async () => {
    const details = { id: "d1", name: "Demo 1", agents: [], tools: [] };
    mockFetchOk(details);

    const result = await fetchDemoFullDetails("d1");
    expect(result).toEqual(details);
    expect(fetch).toHaveBeenCalledWith("/api/demos/d1/details");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchDemoFullDetails("d1")).rejects.toThrow("Failed to fetch demo details d1");
  });
});

// MARK: Repo Discovery API

describe("scanRepo", () => {
  it("returns scan items", async () => {
    const items = [{ path: "src/main.py", type: "file" }];
    mockFetchOk({ items });

    const result = await scanRepo();
    expect(result).toEqual(items);
    expect(fetch).toHaveBeenCalledWith("/api/discovery/scan", { method: "POST" });
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(scanRepo()).rejects.toThrow("Failed to scan repo");
  });
});

describe("applyRepoSelection", () => {
  it("returns number of added items", async () => {
    mockFetchOk({ added: 3 });

    const selections: RepoScanSelection[] = [{ file_path: "a", discovery_path: "a" }];
    const result = await applyRepoSelection(selections);
    expect(result).toBe(3);
    expect(fetch).toHaveBeenCalledWith(
      "/api/discovery/apply",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(applyRepoSelection([])).rejects.toThrow("Failed to apply selections");
  });
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
    expect(body.demo_id).toBe("d1");
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
    mockFetchError(400, { detail: "Demo not found" });
    await expect(createSession("bad", "hello")).rejects.toThrow("Demo not found");
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
    expect(fetch).toHaveBeenCalledWith("/api/sessions/s1/end", { method: "POST" });
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
    expect(fetch).toHaveBeenCalledWith("/api/sessions/s1/cancel", { method: "POST" });
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

describe("connectToEvents", () => {
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

  it("creates EventSource with correct URL", () => {
    const { MockEventSource, instance, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    expect(instance.addEventListener).toHaveBeenCalled();

    // Simulate a tool_event
    const toolEventHandler = listeners["tool_event"]?.[0];
    expect(toolEventHandler).toBeDefined();
    toolEventHandler!({
      data: JSON.stringify({ data: { toolId: "t1" } }),
    } as MessageEvent);

    expect(onEvent).toHaveBeenCalledWith({
      type: "tool_event",
      data: { toolId: "t1" },
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
    });
  });

  it("handles default message events", () => {
    const { MockEventSource, instance } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    // Simulate onmessage
    instance.onmessage!({ data: JSON.stringify({ type: "test" }) } as MessageEvent);
    expect(onEvent).toHaveBeenCalledWith({
      type: "message",
      data: { type: "test" },
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

    // Send invalid JSON
    listeners["tool_event"]?.[0]?.({ data: "not json" } as MessageEvent);
    expect(onEvent).not.toHaveBeenCalled();
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it("extracts nested data payload", () => {
    const { MockEventSource, listeners } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);

    const onEvent = vi.fn();
    connectToEvents("s1", onEvent);

    // Payload without .data key — uses the full payload
    listeners["heartbeat"]?.[0]?.({
      data: JSON.stringify({ timestamp: 123 }),
    } as MessageEvent);

    expect(onEvent).toHaveBeenCalledWith({
      type: "heartbeat",
      data: { timestamp: 123 },
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
});

// MARK: Prompts API

describe("fetchSavedPrompts", () => {
  it("fetches all prompts", async () => {
    const prompts = [{ id: "p1", name: "Prompt 1" }];
    mockFetchOk(prompts);

    const result = await fetchSavedPrompts();
    expect(result).toEqual(prompts);
    expect(fetch).toHaveBeenCalledWith("/api/prompts");
  });

  it("fetches prompts filtered by demoId", async () => {
    mockFetchOk([]);

    await fetchSavedPrompts("d1");
    expect(fetch).toHaveBeenCalledWith("/api/prompts?demo_id=d1");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchSavedPrompts()).rejects.toThrow("Failed to fetch saved prompts");
  });
});

describe("savePrompt", () => {
  it("saves a prompt and returns it", async () => {
    const saved = { id: "p1", name: "My Prompt" };
    mockFetchOk(saved);

    const result = await savePrompt({
      name: "My Prompt",
      content: "Test content",
      demoId: "d1",
    });
    expect(result).toEqual(saved);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.name).toBe("My Prompt");
    expect(body.content).toBe("Test content");
    expect(body.demo_id).toBe("d1");
    expect(body.description).toBe("");
    expect(body.message_type).toBe("human");
  });

  it("sends optional description and messageType", async () => {
    mockFetchOk({ id: "p1" });

    await savePrompt({
      name: "Test",
      content: "Content",
      description: "A description",
      demoId: "d1",
      messageType: "system",
    });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.description).toBe("A description");
    expect(body.message_type).toBe("system");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(savePrompt({ name: "Test", content: "C", demoId: "d1" })).rejects.toThrow(
      "Failed to save prompt",
    );
  });
});

describe("deletePrompt", () => {
  it("sends DELETE request", async () => {
    mockFetchOk(undefined);

    await deletePrompt("p1");
    expect(fetch).toHaveBeenCalledWith("/api/prompts/p1", { method: "DELETE" });
  });

  it("throws on non-ok response", async () => {
    mockFetchError(404);
    await expect(deletePrompt("p1")).rejects.toThrow("Failed to delete prompt");
  });
});

// MARK: Demo Update API

describe("updateDemo", () => {
  it("sends PATCH request with updates", async () => {
    mockFetchOk({ demo: { id: "d1", name: "Updated" } });

    const result = await updateDemo("d1", { name: "Updated" });
    expect(result).toEqual({ id: "d1", name: "Updated" });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/demos/d1");
    expect(call[1].method).toBe("PATCH");
    const body = JSON.parse(call[1].body);
    expect(body.name).toBe("Updated");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(updateDemo("d1", {})).rejects.toThrow("Failed to update demo d1");
  });
});

describe("updateAgent", () => {
  it("sends PATCH request with encoded agent name", async () => {
    const agent = { name: "Agent One", description: "Updated" };
    mockFetchOk(agent);

    const result = await updateAgent("d1", "Agent One", { description: "Updated" });
    expect(result).toEqual(agent);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/demos/d1/agents/Agent%20One");
    expect(call[1].method).toBe("PATCH");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(updateAgent("d1", "agent", {})).rejects.toThrow("Failed to update agent agent");
  });
});

describe("updateSwarm", () => {
  it("sends PATCH request with encoded swarm name", async () => {
    const swarm = { name: "My Swarm", description: "Updated" };
    mockFetchOk(swarm);

    const result = await updateSwarm("d1", "My Swarm", { description: "Updated" });
    expect(result).toEqual(swarm);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/demos/d1/swarms/My%20Swarm");
    expect(call[1].method).toBe("PATCH");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(updateSwarm("d1", "swarm", {})).rejects.toThrow("Failed to update swarm swarm");
  });
});
