import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  applyRepoSelection,
  cancelSession,
  connectToEvents,
  createSession,
  deletePrompt,
  endSession,
  fetchApp,
  fetchAppFullDetails,
  fetchApps,
  fetchAppsByCategory,
  fetchSavedPrompts,
  fetchSession,
  savePrompt,
  scanRepo,
  sendMessage,
  submitInterrupt,
  updateAgent,
  updateApp,
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

// MARK: Apps API

describe("fetchApps", () => {
  it("returns list of apps", async () => {
    const apps = [{ id: "d1", name: "App 1" }];
    mockFetchOk({ apps });

    const result = await fetchApps();
    expect(result).toEqual(apps);
    expect(fetch).toHaveBeenCalledWith("/api/apps");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchApps()).rejects.toThrow("Failed to fetch apps");
  });
});

describe("fetchAppsByCategory", () => {
  it("groups apps by category", async () => {
    const apps = [
      { id: "d1", name: "App 1", category: "core" },
      { id: "d2", name: "App 2", category: "core" },
      { id: "d3", name: "App 3", category: "advanced" },
    ];
    mockFetchOk({ apps });

    const result = await fetchAppsByCategory();
    expect(result).toEqual({
      core: [apps[0], apps[1]],
      advanced: [apps[2]],
    });
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchAppsByCategory()).rejects.toThrow("Failed to fetch apps");
  });
});

describe("fetchApp", () => {
  it("merges app and variants into AppDetails", async () => {
    const app = { id: "d1", name: "App 1" };
    const variants = [{ args: [], description: "default" }];
    mockFetchOk({ app, variants });

    const result = await fetchApp("d1");
    expect(result.id).toBe("d1");
    expect(result.variants).toEqual(variants);
    expect(result.agents).toEqual([]);
    expect(result.tools).toEqual([]);
  });

  it("throws on non-ok response", async () => {
    mockFetchError(404);
    await expect(fetchApp("d1")).rejects.toThrow("Failed to fetch app d1");
  });
});

describe("fetchAppFullDetails", () => {
  it("returns full app details", async () => {
    const details = { id: "d1", name: "App 1", agents: [], tools: [] };
    mockFetchOk(details);

    const result = await fetchAppFullDetails("d1");
    expect(result).toEqual(details);
    expect(fetch).toHaveBeenCalledWith("/api/apps/d1/details");
  });

  it("passes the selected variant in the details query string", async () => {
    const details = { id: "d1", name: "App 1", agents: [], tools: [] };
    mockFetchOk(details);

    await fetchAppFullDetails("d1", "with-private-data");

    expect(fetch).toHaveBeenCalledWith("/api/apps/d1/details?variant=with-private-data");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchAppFullDetails("d1")).rejects.toThrow("Failed to fetch app details d1");
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

  it("fetches prompts filtered by appId", async () => {
    mockFetchOk([]);

    await fetchSavedPrompts("d1");
    expect(fetch).toHaveBeenCalledWith("/api/prompts?app_id=d1");
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
      appId: "d1",
    });
    expect(result).toEqual(saved);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.name).toBe("My Prompt");
    expect(body.content).toBe("Test content");
    expect(body.app_id).toBe("d1");
    expect(body.description).toBe("");
    expect(body.message_type).toBe("human");
  });

  it("sends optional description and messageType", async () => {
    mockFetchOk({ id: "p1" });

    await savePrompt({
      name: "Test",
      content: "Content",
      description: "A description",
      appId: "d1",
      messageType: "system",
    });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.description).toBe("A description");
    expect(body.message_type).toBe("system");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(savePrompt({ name: "Test", content: "C", appId: "d1" })).rejects.toThrow(
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

// MARK: App Update API

describe("updateApp", () => {
  it("sends PATCH request with updates", async () => {
    mockFetchOk({ app: { id: "d1", name: "Updated" } });

    const result = await updateApp("d1", { name: "Updated" });
    expect(result).toEqual({ id: "d1", name: "Updated" });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/apps/d1");
    expect(call[1].method).toBe("PATCH");
    const body = JSON.parse(call[1].body);
    expect(body.name).toBe("Updated");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(updateApp("d1", {})).rejects.toThrow("Failed to update app d1");
  });
});

describe("updateAgent", () => {
  it("sends PATCH request with encoded agent name", async () => {
    const agent = { name: "Agent One", description: "Updated" };
    mockFetchOk(agent);

    const result = await updateAgent("d1", "Agent One", { description: "Updated" });
    expect(result).toEqual(agent);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/apps/d1/agents/Agent%20One");
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
    expect(call[0]).toBe("/api/apps/d1/swarms/My%20Swarm");
    expect(call[1].method).toBe("PATCH");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(updateSwarm("d1", "swarm", {})).rejects.toThrow("Failed to update swarm swarm");
  });
});
