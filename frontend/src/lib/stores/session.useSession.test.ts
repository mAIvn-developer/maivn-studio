import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  InterruptData,
  InvocationConfig,
  MemoryConfig,
  Message,
  Session,
  ToolCard,
} from "$lib/types";
import { buildExchanges } from "$lib/components/chat/chat-exchanges";
import { useSession } from "./session/index.svelte";

// MARK: Helpers

const MOCK_SESSION: Session = {
  session_id: "s-123",
  app_id: "d-1",
  app_name: "Test App",
  thread_id: "t-1",
  variant: null,
  status: "running",
  created_at: "2024-01-01T00:00:00Z",
  started_at: "2024-01-01T00:00:01Z",
  completed_at: null,
  message_count: 0,
  can_send_message: false,
  can_stage_message: true,
  queued_message_count: 0,
  is_active: true,
  error: null,
};

function mockFetchOk(data: unknown) {
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

function mockFetchError(status: number, body?: Record<string, unknown>) {
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
    readyState: 1,
  };

  function MockEventSource() {
    return instance;
  }

  return { MockEventSource, instance, listeners };
}

function makeSequentialMockEventSource() {
  const sources: Array<{
    url: string;
    instance: {
      addEventListener: ReturnType<typeof vi.fn>;
      onmessage: ((e: MessageEvent) => void) | null;
      onerror: ((e: Event) => void) | null;
      close: ReturnType<typeof vi.fn>;
      readyState: number;
    };
    listeners: Record<string, ((e: MessageEvent) => void)[]>;
  }> = [];

  function MockEventSource(url: string) {
    const listeners: Record<string, ((e: MessageEvent) => void)[]> = {};
    const instance = {
      addEventListener: vi.fn((type: string, cb: (e: MessageEvent) => void) => {
        if (!listeners[type]) listeners[type] = [];
        listeners[type].push(cb);
      }),
      onmessage: null as ((e: MessageEvent) => void) | null,
      onerror: null as ((e: Event) => void) | null,
      close: vi.fn(),
      readyState: 1,
    };
    sources.push({ url, instance, listeners });
    return instance;
  }

  return { MockEventSource, sources };
}

function fireEvent(
  listeners: Record<string, ((e: MessageEvent) => void)[]>,
  type: string,
  data: unknown,
) {
  const handler = listeners[type]?.[0];
  if (handler) {
    handler({ data: JSON.stringify({ data }) } as MessageEvent);
  }
}

function fireEventEnvelope(
  listeners: Record<string, ((e: MessageEvent) => void)[]>,
  type: string,
  envelope: Record<string, unknown>,
) {
  const handler = listeners[type]?.[0];
  if (handler) {
    handler({ data: JSON.stringify(envelope) } as MessageEvent);
  }
}

let uuidCounter = 0;

beforeEach(() => {
  vi.restoreAllMocks();
  uuidCounter = 0;
  vi.stubGlobal("crypto", {
    randomUUID: () => `uuid-${++uuidCounter}`,
  });
  // Stub window so typeof window !== "undefined" checks pass (e.g. setInterruptStyle)
  vi.stubGlobal("window", globalThis);
  // Stub localStorage for interruptStyle
  vi.stubGlobal("localStorage", {
    getItem: vi.fn().mockReturnValue(null),
    setItem: vi.fn(),
  });
  // Stub requestAnimationFrame for batcher
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
    cb(0);
    return 0;
  });
  // Reset module-level shared state between tests
  const s = useSession();
  s.reset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// MARK: Initial State

describe("useSession - initial state", () => {
  it("returns expected default values", () => {
    const s = useSession();

    expect(s.session).toBeNull();
    expect(s.hasActiveSession).toBe(false);
    expect(s.chatFlowItems).toEqual([]);
    expect(s.filteredChatFlowItems).toEqual([]);
    expect(s.toolCards).toBeInstanceOf(Map);
    expect(s.toolCards.size).toBe(0);
    expect(s.messages).toEqual([]);
    expect(s.events).toEqual([]);
    expect(s.loading).toBe(false);
    expect(s.error).toBeNull();
    expect(s.isConnected).toBe(false);
    expect(s.messageType).toBe("human");
    expect(s.currentPhase).toBeNull();
    expect(s.currentPhaseMessage).toBeNull();
    expect(s.extractedSkills).toEqual([]);
    expect(s.extractedInsights).toEqual([]);
    expect(s.retrievedMemoryContext).toBeNull();
    expect(s.pendingInterrupts).toEqual([]);
    expect(s.allInterrupts).toEqual([]);
  });

  it("returns event summary with all zeros", () => {
    const s = useSession();
    expect(s.eventSummary.totalMessages).toBe(0);
    expect(s.eventSummary.totalTools).toBe(0);
    expect(s.eventSummary.totalAgents).toBe(0);
  });

  it("returns accumulated stats with all zeros", () => {
    const s = useSession();
    expect(s.accumulatedStats.sessionCount).toBe(0);
    expect(s.accumulatedStats.totalTokens).toBe(0);
  });
});

// MARK: Setters

describe("useSession - setters", () => {
  it("setMessageType updates messageType", () => {
    const s = useSession();
    s.setMessageType("redacted");
    expect(s.messageType).toBe("redacted");
  });

  it("setPrivateData updates privateData", () => {
    const s = useSession();
    s.setPrivateData({ key: "value" });
    expect(s.privateData).toEqual({ key: "value" });
  });

  it("setFilters merges with existing filters", () => {
    const s = useSession();
    const original = { ...s.filters };
    s.setFilters({ itemType: "tools" });
    expect(s.filters.itemType).toBe("tools");
    // Other fields unchanged
    expect(s.filters.toolStatus).toBe(original.toolStatus);
  });

  it("setInvocationConfig replaces config", () => {
    const s = useSession();
    const config: InvocationConfig = {
      force_final_tool: true,
      stream_response: true,
      metadata: { temperature: 0.5 },
    };
    s.setInvocationConfig(config);
    expect(s.invocationConfig).toEqual(config);
  });

  it("setInvocationConfig hydrates memoryConfig from memory_config", () => {
    const s = useSession();
    s.setInvocationConfig({
      force_final_tool: true,
      metadata: { temperature: 0.5 },
      memory_config: {
        enabled: true,
        level: "focus",
        summarization_enabled: false,
        persistence_mode: "vector_only",
        retrieval: {
          skills_enabled: false,
          insights_enabled: false,
          resources_enabled: false,
        },
        skill_extraction: {
          enabled: false,
        },
        insight_extraction: {
          enabled: true,
        },
      },
    });

    expect(s.invocationConfig).toEqual({
      force_final_tool: true,
      stream_response: true,
      metadata: { temperature: 0.5 },
    });
    expect(s.memoryConfig).toEqual({
      enabled: true,
      level: "focus",
      summarizationEnabled: false,
      skillExtractionEnabled: false,
      insightExtractionEnabled: true,
      retrievalEnabled: false,
      persistenceMode: "vector_only",
    });
  });

  it('setInvocationConfig preserves memory level "none"', () => {
    const s = useSession();
    s.setInvocationConfig({
      force_final_tool: true,
      memory_config: {
        enabled: true,
        level: "none",
      },
    });

    expect(s.memoryConfig.level).toBe("none");
  });

  it("setInvocationConfig preserves existing memoryConfig when no memory_config is provided", () => {
    const s = useSession();
    s.setMemoryConfig({
      enabled: true,
      level: "glimpse",
      summarizationEnabled: false,
      skillExtractionEnabled: true,
      insightExtractionEnabled: false,
      retrievalEnabled: true,
      persistenceMode: "vector_plus_graph",
    });

    s.setInvocationConfig({ force_final_tool: true, model: "fast" });

    expect(s.invocationConfig).toEqual({ force_final_tool: true, model: "fast" });
    expect(s.memoryConfig).toEqual({
      enabled: true,
      level: "glimpse",
      summarizationEnabled: false,
      skillExtractionEnabled: true,
      insightExtractionEnabled: false,
      retrievalEnabled: true,
      persistenceMode: "vector_plus_graph",
    });
  });

  it("clearError resets error to null", () => {
    const s = useSession();
    // Trigger an error via send without session
    s.send("hello");
    expect(s.error).toBe("Session not ready for messages");
    s.clearError();
    expect(s.error).toBeNull();
  });

  it("setMemoryConfig updates memoryConfig", () => {
    const s = useSession();
    const config: MemoryConfig = {
      enabled: true,
      level: "focus",
      summarizationEnabled: true,
      skillExtractionEnabled: false,
      insightExtractionEnabled: true,
      retrievalEnabled: false,
      persistenceMode: "vector_only",
    };
    s.setMemoryConfig(config);
    expect(s.memoryConfig).toEqual(config);
  });

  it("setInterruptStyle updates style and persists to localStorage", () => {
    const s = useSession();
    s.setInterruptStyle("modal");
    expect(s.interruptStyle).toBe("modal");
    expect(localStorage.setItem).toHaveBeenCalledWith("interruptStyle", "modal");
  });
});

// MARK: startSession

describe("useSession - startSession", () => {
  it("creates a session and adds user message to chat flow", async () => {
    const { MockEventSource } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Hello agent");

    expect(s.session).toEqual(MOCK_SESSION);
    expect(s.hasActiveSession).toBe(true);
    expect(s.loading).toBe(true);
    expect(s.isConnected).toBe(true);

    // User message should be in chat flow
    expect(s.chatFlowItems).toHaveLength(1);
    expect(s.chatFlowItems[0].type).toBe("message");
    const msg = s.chatFlowItems[0].data as Message;
    expect(msg.role).toBe("user");
    expect(msg.content).toBe("Hello agent");
  });

  it("handles session creation error", async () => {
    mockFetchError(400, { detail: "App not found" });

    const s = useSession();
    await s.startSession("bad-id", "Hello");

    expect(s.session).toBeNull();
    expect(s.error).toBe("App not found");
    expect(s.loading).toBe(false);
  });

  it("injects memory config into invocation when enabled", async () => {
    const { MockEventSource } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    s.setMemoryConfig({
      enabled: true,
      level: "clarity",
      summarizationEnabled: true,
      skillExtractionEnabled: true,
      insightExtractionEnabled: false,
      retrievalEnabled: true,
      persistenceMode: "vector_plus_graph",
    });

    await s.startSession("d-1", "Hello");

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.invocation.memory_config.enabled).toBe(true);
    expect(body.invocation.memory_config.level).toBe("clarity");
    expect(body.invocation.memory_config.summarization_enabled).toBe(true);
    expect(body.invocation.memory_config.persistence_mode).toBe("vector_plus_graph");
    expect(body.invocation.memory_config.skill_extraction.enabled).toBe(true);
    expect(body.invocation.memory_config.insight_extraction.enabled).toBe(false);
    expect(body.invocation.memory_config.retrieval.skills_enabled).toBe(true);
    expect(body.invocation.memory_config.retrieval.insights_enabled).toBe(true);
    expect(body.invocation.memory_config.retrieval.resources_enabled).toBe(true);
  });

  it("preserves advanced app memory_config defaults in the request payload", async () => {
    const { MockEventSource } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    s.setInvocationConfig({
      force_final_tool: false,
      memory_config: {
        enabled: true,
        level: "focus",
        summarization_enabled: false,
        persistence_mode: "vector_plus_graph",
        retrieval: {
          top_k: 7,
          candidate_limit: 21,
          skills_enabled: false,
          insights_enabled: false,
          resources_enabled: true,
        },
        skill_extraction: {
          enabled: true,
          sharing_scope: "project",
          confidence_threshold: 0.4,
          max_count: 5,
        },
        insight_extraction: {
          enabled: true,
          sharing_scope: "agent",
          min_relevance_score: 0.25,
          max_count: 6,
        },
      },
    });

    await s.startSession("d-1", "Hello");

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.invocation.memory_config.enabled).toBe(true);
    expect(body.invocation.memory_config.level).toBe("focus");
    expect(body.invocation.memory_config.summarization_enabled).toBe(false);
    expect(body.invocation.memory_config.retrieval.top_k).toBe(7);
    expect(body.invocation.memory_config.retrieval.candidate_limit).toBe(21);
    expect(body.invocation.memory_config.retrieval.skills_enabled).toBe(false);
    expect(body.invocation.memory_config.retrieval.insights_enabled).toBe(false);
    expect(body.invocation.memory_config.retrieval.resources_enabled).toBe(true);
    expect(body.invocation.memory_config.skill_extraction.sharing_scope).toBe("project");
    expect(body.invocation.memory_config.skill_extraction.confidence_threshold).toBe(0.4);
    expect(body.invocation.memory_config.skill_extraction.max_count).toBe(5);
    expect(body.invocation.memory_config.insight_extraction.sharing_scope).toBe("agent");
    expect(body.invocation.memory_config.insight_extraction.min_relevance_score).toBe(0.25);
    expect(body.invocation.memory_config.insight_extraction.max_count).toBe(6);
  });
});

// MARK: Event Handling

describe("useSession - event handling", () => {
  async function startWithEvents() {
    const es = makeMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Hello");

    return { s, ...es };
  }

  it("handles turn_complete event and adds assistant message", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "turn_complete", {
      responses: ["Here is my response"],
      duration_ms: 1500,
      token_usage: {
        total_tokens: 100,
        input_tokens: 40,
        output_tokens: 50,
        reasoning_tokens: 10,
        cache_read_tokens: 0,
        cache_creation_tokens: 0,
      },
    });

    expect(s.loading).toBe(false);
    expect(s.session?.status).toBe("ready");
    expect(s.session?.can_send_message).toBe(true);

    // Should have user message + assistant message
    const messages = s.messages;
    expect(messages).toHaveLength(2);
    expect(messages[1].role).toBe("assistant");
    expect(messages[1].content).toBe("Here is my response");
    expect(messages[1].sessionDetails?.duration_ms).toBe(1500);
    expect(messages[1].sessionDetails?.token_usage?.total_tokens).toBe(100);
  });

  it("finalizes an active execution phase chip on turn_complete", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "enrichment", {
      phase: "evaluating",
      message: "Evaluating...",
    });

    fireEvent(listeners, "turn_complete", {
      responses: ["Here is my response"],
    });

    const phaseChip = s.chatFlowItems.find((item) => item.type === "phase_chip");
    expect(phaseChip).toBeDefined();

    const data = phaseChip?.data as { phase: string; message: string };
    expect(data.phase).toBe("complete");
    expect(data.message).toBe("Complete");
  });

  it("handles final event and closes session", async () => {
    const { s, listeners, instance } = await startWithEvents();

    fireEvent(listeners, "final", {
      responses: ["Done"],
    });

    expect(s.loading).toBe(false);
    expect(s.session?.status).toBe("completed");
    expect(s.session?.can_send_message).toBe(false);
    expect(s.session?.is_active).toBe(false);
    expect(s.hasActiveSession).toBe(false);
    expect(instance.close).toHaveBeenCalled();
  });

  it("handles raw update events with cumulative streaming content", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "update", {
      assistant_id: "assistant-1",
      streaming_content: "Hello",
    });
    fireEvent(listeners, "update", {
      assistant_id: "assistant-1",
      streaming_content: "Hello ",
    });
    fireEvent(listeners, "update", {
      assistant_id: "assistant-1",
      streaming_content: "Hello world",
    });
    fireEvent(listeners, "final", {
      responses: ["Hello world"],
    });

    expect(s.messages).toHaveLength(2);
    expect(s.messages[1].role).toBe("assistant");
    expect(s.messages[1].content).toBe("Hello world");
  });

  it("hydrates tool cards from raw backend tool_event payloads", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "tool_event", {
      id: "tool_1_c2756e13",
      value: {
        tool_call: {
          tool_id: "validate_query_artifact",
          args: {
            query: "SELECT 1",
          },
        },
      },
    });

    const toolCard = s.toolCards.get("tool_1_c2756e13");
    expect(toolCard).toBeDefined();
    expect(toolCard?.toolName).toBe("validate_query_artifact");
    expect(toolCard?.status).toBe("executing");
    expect(toolCard?.args).toEqual({ query: "SELECT 1" });
  });

  it("deduplicates repeated system_tool_start events for the same tool id", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "system_tool_start", {
      tool_id: "compose-artifact-1",
      tool_type: "compose_artifact",
      agent_name: "Compose Artifact Agent",
      params: { prompt: "draft artifact" },
    });

    fireEvent(listeners, "system_tool_start", {
      tool_id: "compose-artifact-1",
      tool_type: "compose_artifact",
      agent_name: "Compose Artifact Agent",
      params: { prompt: "draft artifact" },
    });

    const toolItems = s.chatFlowItems.filter(
      (item) =>
        item.type === "tool_card" && (item.data as ToolCard).toolId === "compose-artifact-1",
    );

    expect(toolItems).toHaveLength(1);
    expect(s.toolCards.get("compose-artifact-1")?.toolType).toBe("system");
    expect(s.toolCards.get("compose-artifact-1")?.toolName).toBe("compose_artifact");
  });

  it("normalizes legacy system_tool_start payloads that only provide assignment_id", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "system_tool_start", {
      assignment_id: "system-tool-1",
      tool_name: "planner",
      params: { topic: "market analysis" },
    });

    const toolCard = s.toolCards.get("system-tool-1");
    expect(toolCard).toBeDefined();
    expect(toolCard?.toolId).toBe("system-tool-1");
    expect(toolCard?.toolName).toBe("planner");
    expect(toolCard?.toolType).toBe("system");
    expect(toolCard?.args).toEqual({ topic: "market analysis" });
  });

  it("keeps the normalized system tool name when tool.type is the generic system type", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "system_tool_start", {
      tool: {
        id: "system-tool-2",
        name: "compose_artifact",
        type: "system",
        args: { prompt: "draft artifact" },
      },
      tool_type: "compose_artifact",
    });

    const toolCard = s.toolCards.get("system-tool-2");
    expect(toolCard).toBeDefined();
    expect(toolCard?.toolName).toBe("compose_artifact");
    expect(toolCard?.toolType).toBe("system");
    expect(toolCard?.args).toEqual({ prompt: "draft artifact" });
  });

  it("preserves system tool chunk spacing for streamed output", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "system_tool_start", {
      tool_id: "repl-tool-1",
      tool_type: "repl",
    });
    fireEvent(listeners, "system_tool_chunk", {
      tool_id: "repl-tool-1",
      text: "line 1",
    });
    fireEvent(listeners, "system_tool_chunk", {
      tool_id: "repl-tool-1",
      text: " ",
    });
    fireEvent(listeners, "system_tool_chunk", {
      tool_id: "repl-tool-1",
      text: "\n  indented line",
    });
    fireEvent(listeners, "system_tool_complete", {
      tool_id: "repl-tool-1",
      result: "ok",
    });

    expect(s.toolCards.get("repl-tool-1")?.streamContent).toBe("line 1 \n  indented line");
  });

  it("uses the embedded event type for default SSE message events", async () => {
    const { s, instance } = await startWithEvents();

    instance.onmessage?.({
      data: JSON.stringify({
        type: "final",
        data: {
          responses: ["Done"],
        },
      }),
    } as MessageEvent);

    expect(s.session?.status).toBe("completed");
    expect(s.hasActiveSession).toBe(false);
    expect(s.loading).toBe(false);
  });

  it("reconciles lingering executing tool cards to completed on final", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "tool_event", {
      tool_id: "tc-1",
      tool_name: "search_docs",
      tool_type: "func",
      status: "executing",
      args: { query: "memory" },
    });

    fireEvent(listeners, "final", {
      responses: ["Done"],
    });

    expect(s.toolCards.get("tc-1")?.status).toBe("completed");
    const toolItem = s.chatFlowItems.find(
      (item) => item.type === "tool_card" && (item.data as ToolCard).toolId === "tc-1",
    );
    expect((toolItem?.data as ToolCard | undefined)?.status).toBe("completed");
  });

  it("handles error event", async () => {
    const { s, listeners, instance } = await startWithEvents();

    fireEvent(listeners, "error", {
      error: "Something went wrong",
    });

    expect(s.session?.status).toBe("failed");
    expect(s.error).toBe("Something went wrong");
    expect(s.loading).toBe(false);
    expect(instance.close).toHaveBeenCalled();
  });

  it("does not overwrite backend error with generic connection-lost error", async () => {
    const { s, listeners, instance } = await startWithEvents();

    fireEvent(listeners, "error", {
      error: "Something went wrong",
    });

    instance.onerror?.({} as Event);

    expect(s.error).toBe("Something went wrong");
  });

  it("sets connection lost when stream errors during active execution", async () => {
    const { s, instance } = await startWithEvents();

    // Simulate a hard stream error while still running.
    instance.readyState = 2;
    instance.onerror?.({} as Event);

    expect(s.error).toBe("Connection lost");
  });

  it("handles session_end event", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "session_end", {});

    expect(s.session?.status).toBe("completed");
    expect(s.loading).toBe(false);
  });

  it("adds raw events to events array", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "heartbeat", {});

    // Heartbeat is added to raw events
    expect(s.events.length).toBeGreaterThanOrEqual(1);
    const heartbeatEvent = s.events.find((e) => e.type === "heartbeat");
    expect(heartbeatEvent).toBeDefined();
  });

  it("handles enrichment event for memory_skill_extracted", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "enrichment", {
      phase: "memory_skill_extracted",
      message: "2 skills extracted",
      memory: {
        mode: "extract_skills",
        extracted_count: 2,
        persisted_count: 2,
        skills: [
          { name: "Skill A", description: "Desc A", confidence: 0.9, sharing_scope: "project" },
          { name: "Skill B", description: "Desc B", confidence: 0.8, sharing_scope: "agent" },
        ],
      },
    });

    expect(s.extractedSkills).toHaveLength(2);
    expect(s.extractedSkills[0].name).toBe("Skill A");
    expect(s.extractedSkills[1].name).toBe("Skill B");
  });

  it("handles enrichment event for memory_insight_extracted", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "enrichment", {
      phase: "memory_insight_extracted",
      message: "1 insight extracted",
      memory: {
        mode: "extract_insights",
        insights: [
          {
            insight_type: "lesson",
            content: "Always validate",
            relevance_score: 0.9,
            sharing_scope: "agent",
          },
        ],
      },
    });

    expect(s.extractedInsights).toHaveLength(1);
    expect(s.extractedInsights[0].content).toBe("Always validate");
  });

  it("handles enrichment event for memory_retrieved", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "enrichment", {
      phase: "memory_retrieved",
      message: "Retrieved context",
      memory: {
        mode: "retrieve",
        hit_count: 6,
        skill_count: 3,
        insight_count: 2,
        resource_count: 1,
        vector_hits: 5,
        keyword_hits: 1,
        graph_hits: 0,
        latency_ms: 120,
      },
    });

    expect(s.retrievedMemoryContext).toBeDefined();
    expect(s.retrievedMemoryContext?.hitCount).toBe(6);
    expect(s.retrievedMemoryContext?.skillHits).toBe(3);
    expect(s.retrievedMemoryContext?.insightHits).toBe(2);
    expect(s.retrievedMemoryContext?.resourceCount).toBe(1);
    expect(s.retrievedMemoryContext?.vectorHits).toBe(5);
    expect(s.retrievedMemoryContext?.latencyMs).toBe(120);
  });

  it("handles enrichment event for redaction_previewed", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "enrichment", {
      phase: "redaction_previewed",
      message: "Redaction preview completed.",
      redaction: {
        inserted_keys: ["pii_email_1"],
        added_private_data: { pii_email_1: "alice@example.com" },
        redacted_message_count: 1,
        redacted_value_count: 1,
        matched_known_pii_values: ["alice@example.com"],
        unmatched_known_pii_values: ["bob@example.com"],
      },
    });

    const phaseChip = s.chatFlowItems.find((item) => item.type === "phase_chip");
    expect(phaseChip).toBeDefined();
    expect(phaseChip?.type).toBe("phase_chip");

    const data = phaseChip?.data as { redaction?: Record<string, unknown> };
    expect(data.redaction).toBeDefined();
    expect(data.redaction?.insertedKeys).toEqual(["pii_email_1"]);
    expect(data.redaction?.redactedValueCount).toBe(1);
    expect(data.redaction?.matchedKnownPiiValues).toEqual(["alice@example.com"]);
    expect(data.redaction?.unmatchedKnownPiiValues).toEqual(["bob@example.com"]);
  });

  it("handles tool_event for new tool", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "tool_event", {
      tool_id: "tc-1",
      tool_name: "search",
      tool_type: "func",
      status: "executing",
      args: { query: "test" },
    });

    expect(s.toolCards.size).toBe(1);
    expect(s.toolCards.get("tc-1")?.toolName).toBe("search");
    expect(s.toolCards.get("tc-1")?.status).toBe("executing");

    // Should appear in chat flow
    const toolItems = s.chatFlowItems.filter((i) => i.type === "tool_card");
    expect(toolItems).toHaveLength(1);
  });

  it("handles tool_event completion update", async () => {
    const { s, listeners } = await startWithEvents();

    // Start tool
    fireEvent(listeners, "tool_event", {
      tool_id: "tc-1",
      tool_name: "search",
      tool_type: "func",
      status: "executing",
      args: {},
    });

    // Complete tool
    fireEvent(listeners, "tool_event", {
      tool_id: "tc-1",
      tool_name: "search",
      tool_type: "func",
      status: "completed",
      result: "found results",
    });

    expect(s.toolCards.get("tc-1")?.status).toBe("completed");
    expect(s.toolCards.get("tc-1")?.result).toBe("found results");
  });

  it("handles progress_update streaming", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "progress_update", { text: "Hello" });
    fireEvent(listeners, "progress_update", { text: " " });
    fireEvent(listeners, "progress_update", { text: "world!" });

    // Should have a streaming assistant message
    const assistantItems = s.chatFlowItems.filter(
      (i) => i.type === "message" && (i.data as Message).role === "assistant",
    );
    expect(assistantItems).toHaveLength(1);
    expect((assistantItems[0].data as Message).content).toBe("Hello world!");
    expect((assistantItems[0].data as Message).metadata?.isStreaming).toBe(true);
  });

  it("handles legacy flat status_message payloads", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "status_message", {
      message: "Planning complete",
    });

    const statusItems = s.chatFlowItems.filter(
      (item) => item.type === "message" && (item.data as Message).messageType === "status",
    );
    expect(statusItems).toHaveLength(1);
    expect((statusItems[0].data as Message).content).toBe("Planning complete");
  });

  it("deduplicates repeated SSE deliveries with the same event id", async () => {
    const { s, listeners, instance } = await startWithEvents();

    fireEventEnvelope(listeners, "status_message", {
      id: "evt-status-1",
      data: {
        assistant_id: "orchestrator_agent",
        message: "Dispatching 3 agents",
      },
    });

    instance.onmessage?.({
      data: JSON.stringify({
        id: "evt-status-1",
        type: "status_message",
        data: {
          assistant_id: "orchestrator_agent",
          message: "Dispatching 3 agents",
        },
      }),
    } as MessageEvent);

    const statusItems = s.chatFlowItems.filter(
      (item) => item.type === "message" && (item.data as Message).messageType === "status",
    );
    expect(statusItems).toHaveLength(1);
    expect((statusItems[0].data as Message).content).toBe("Dispatching 3 agents");
  });

  it("mirrors final-output agent assistant chunks into the live assistant message", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "tool_event", {
      tool_id: "agent-tool-1",
      tool_name: "investment_director",
      tool_type: "agent",
      status: "executing",
      agent_name: "Investment Director",
      args: {
        agent_id: "agent-1",
        use_as_final_output: true,
      },
    });

    fireEvent(listeners, "progress_update", { assistant_id: "agent-1", text: "Memo " });
    fireEvent(listeners, "progress_update", { assistant_id: "agent-1", text: "draft" });

    const assistantItems = s.chatFlowItems.filter(
      (i) => i.type === "message" && (i.data as Message).role === "assistant",
    );
    expect(assistantItems).toHaveLength(1);
    expect((assistantItems[0].data as Message).content).toBe("Memo draft");
    expect((assistantItems[0].data as Message).metadata?.isStreaming).toBe(true);
    expect(s.toolCards.get("agent-tool-1")?.status).toBe("executing");
  });

  it("does not misroute unresolved nested assistant chunks into a final-output agent stream", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "tool_event", {
      tool_id: "final-agent-tool",
      tool_name: "investment_director",
      tool_type: "agent",
      status: "executing",
      agent_name: "Investment Director",
      args: {
        agent_id: "final-agent",
        use_as_final_output: true,
      },
    });

    fireEvent(listeners, "progress_update", { assistant_id: "nested-agent", text: "Nested " });
    fireEvent(listeners, "progress_update", { assistant_id: "nested-agent", text: "analysis" });

    const assistantItems = s.chatFlowItems.filter(
      (i) => i.type === "message" && (i.data as Message).role === "assistant",
    );
    expect(assistantItems).toHaveLength(0);
    expect(s.toolCards.get("final-agent-tool")?.streamContent).toBeUndefined();

    fireEvent(listeners, "agent_assignment", {
      agent_name: "Data Analyzer",
      status: "in_progress",
      result: {
        assistant_id: "nested-agent",
      },
    });

    fireEvent(listeners, "turn_complete", {
      responses: ["Done"],
      duration_ms: 100,
    });

    // The agent_assignment event omits assignment_id, so the studio mints a
    // per-event UUID (rather than a stable "agent:<name>" key that would
    // collapse separate invocations of the same agent). Look the card up by
    // agentName instead of by the synthetic id.
    const dataAnalyzerCard = Array.from(s.toolCards.values()).find(
      (card) => card.toolType === "agent" && card.agentName === "Data Analyzer",
    );
    expect(dataAnalyzerCard?.streamContent).toBe("Nested analysis");
    expect(s.toolCards.get("final-agent-tool")?.streamContent).toBeUndefined();
  });

  it("buffers explicit nested assistant chunks instead of rendering them as top-level assistant messages", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "tool_event", {
      tool_id: "parent-agent-tool",
      tool_name: "research_coordinator",
      tool_type: "agent",
      status: "executing",
      agent_name: "Research Coordinator",
      args: {
        agent_id: "parent-agent",
      },
    });

    fireEvent(listeners, "progress_update", { assistant_id: "child-agent", text: "Nested " });
    fireEvent(listeners, "progress_update", { assistant_id: "child-agent", text: "draft" });

    const assistantItems = s.chatFlowItems.filter(
      (i) => i.type === "message" && (i.data as Message).role === "assistant",
    );
    expect(assistantItems).toHaveLength(0);
  });

  it("flushes buffered nested assistant chunks into the mapped agent card", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "tool_event", {
      tool_id: "parent-agent-tool",
      tool_name: "research_coordinator",
      tool_type: "agent",
      status: "executing",
      agent_name: "Research Coordinator",
      args: {
        agent_id: "parent-agent",
      },
    });

    fireEvent(listeners, "progress_update", { assistant_id: "child-agent", text: "Nested " });
    fireEvent(listeners, "progress_update", { assistant_id: "child-agent", text: "draft" });

    fireEvent(listeners, "tool_event", {
      tool_id: "child-agent-tool",
      tool_name: "data_analyzer",
      tool_type: "agent",
      status: "executing",
      agent_name: "Data Analyzer",
      args: {
        agent_id: "child-agent",
      },
    });

    fireEvent(listeners, "turn_complete", {
      responses: ["Done"],
      duration_ms: 100,
    });

    expect(s.toolCards.get("child-agent-tool")?.streamContent).toBe("Nested draft");
  });

  it("falls back to an assistant message when nested assistant chunks remain unresolved", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "tool_event", {
      tool_id: "parent-agent-tool",
      tool_name: "research_coordinator",
      tool_type: "agent",
      status: "executing",
      agent_name: "Research Coordinator",
      args: {
        agent_id: "parent-agent",
      },
    });

    fireEvent(listeners, "progress_update", { assistant_id: "child-agent", text: "Nested " });
    fireEvent(listeners, "progress_update", { assistant_id: "child-agent", text: "draft" });

    fireEvent(listeners, "turn_complete", {
      duration_ms: 100,
    });

    const assistantItems = s.chatFlowItems.filter(
      (item) => item.type === "message" && (item.data as Message).role === "assistant",
    );
    expect(assistantItems).toHaveLength(1);
    expect((assistantItems[0].data as Message).content).toBe("Nested draft");
    expect((assistantItems[0].data as Message).metadata?.isStreaming).not.toBe(true);
  });

  it("handles interrupt_required event", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "interrupt_required", {
      tool_name: "ask_user",
      interrupt_id: "int-1",
      data_key: "answer",
      prompt: "What is your name?",
      tool_call_id: "tc-1",
    });

    expect(s.loading).toBe(false);
    expect(s.session?.status).toBe("waiting_input");
    expect(s.interruptCards.size).toBe(1);
    expect(s.pendingInterrupts).toHaveLength(1);
  });

  it("deduplicates repeated interrupt_required events for the same interrupt id", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "interrupt_required", {
      tool_name: "greet_user",
      interrupt_id: "int-1",
      data_key: "name",
      prompt: "Please enter your name:",
      timestamp: "2024-01-01T00:00:00Z",
    });

    fireEvent(listeners, "interrupt_required", {
      tool_name: "greet_user",
      interrupt_id: "int-1",
      data_key: "name",
      prompt: "Please enter your full name:",
      timestamp: "2024-01-01T00:01:00Z",
    });

    expect(s.interruptCards.size).toBe(1);
    expect(s.pendingInterrupts).toHaveLength(1);
    const interruptItems = s.chatFlowItems.filter((item) => item.type === "interrupt_card");
    expect(interruptItems).toHaveLength(1);
    expect((interruptItems[0].data as InterruptData).prompt).toBe("Please enter your full name:");
  });

  it("appends a new inline card when the same interrupt id is reused on a follow-up turn", async () => {
    const es = makeSequentialMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Hello");

    const initialTurnSource = es.sources[0];
    fireEvent(initialTurnSource.listeners, "session_start", {
      assistant_id: "assistant-1",
      queued_message_count: 0,
    });
    fireEvent(initialTurnSource.listeners, "interrupt_required", {
      tool_name: "personalize_profile",
      interrupt_id: "int-1",
      data_key: "favorite_color",
      prompt: "What is your favorite color?",
      timestamp: "2024-01-01T00:00:00Z",
    });

    mockFetchOk({
      ...MOCK_SESSION,
      status: "running",
      can_send_message: false,
      can_stage_message: true,
      is_active: true,
    });
    await s.submitInterrupt("int-1", "red");

    const resumedTurnSource = es.sources[1];
    fireEvent(resumedTurnSource.listeners, "turn_complete", {
      responses: ["Saved"],
      queued_message_count: 0,
    });

    mockFetchOk({
      ...MOCK_SESSION,
      status: "running",
      can_send_message: false,
      can_stage_message: true,
      is_active: true,
    });
    await s.send("I need to change the color");

    const followupTurnSource = es.sources[2];
    fireEvent(followupTurnSource.listeners, "session_start", {
      assistant_id: "assistant-2",
      queued_message_count: 0,
    });
    fireEvent(followupTurnSource.listeners, "interrupt_required", {
      tool_name: "personalize_profile",
      interrupt_id: "int-1",
      data_key: "favorite_color",
      prompt: "What color should I change it to?",
      timestamp: "2024-01-01T00:05:00Z",
    });

    const interruptItems = s.chatFlowItems.filter((item) => item.type === "interrupt_card");
    expect(interruptItems).toHaveLength(2);

    const firstInterrupt = interruptItems[0].data as InterruptData;
    const secondInterrupt = interruptItems[1].data as InterruptData;
    expect(firstInterrupt.interruptId).toBe("int-1");
    expect(secondInterrupt.interruptId).toBe("int-1");
    expect(firstInterrupt.cardId).not.toBe(secondInterrupt.cardId);
    expect(firstInterrupt.status).toBe("completed");
    expect(secondInterrupt.status).toBe("waiting");

    const exchanges = buildExchanges(s.chatFlowItems);
    const latestExchange = exchanges.at(-1);
    expect(latestExchange?.humanMessage.content).toBe("I need to change the color");
    expect(latestExchange?.interruptCards).toHaveLength(1);
    expect(latestExchange?.interruptCards[0]?.prompt).toBe("What color should I change it to?");
  });

  it("does not create a new interrupt card when session_start is replayed for the same turn", async () => {
    const { s, listeners } = await startWithEvents();

    fireEvent(listeners, "session_start", {
      assistant_id: "assistant-1",
      queued_message_count: 0,
    });
    fireEvent(listeners, "interrupt_required", {
      tool_name: "greet_user",
      interrupt_id: "int-1",
      data_key: "user_name",
      prompt: "Please enter your name:",
      timestamp: "2024-01-01T00:00:00Z",
    });

    fireEvent(listeners, "session_start", {
      assistant_id: "assistant-1",
      queued_message_count: 0,
    });
    fireEvent(listeners, "interrupt_required", {
      tool_name: "greet_user",
      interrupt_id: "int-1",
      data_key: "user_name",
      prompt: "Please enter your full name:",
      timestamp: "2024-01-01T00:01:00Z",
    });

    const interruptItems = s.chatFlowItems.filter((item) => item.type === "interrupt_card");
    expect(interruptItems).toHaveLength(1);
    expect((interruptItems[0].data as InterruptData).prompt).toBe("Please enter your full name:");
  });
});

// MARK: Memory Persistence

describe("useSession - memory persistence", () => {
  async function startWithEvents() {
    const es = makeMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Hello");

    return { s, ...es };
  }

  function fireMemoryRetrieved(listeners: Record<string, ((e: MessageEvent) => void)[]>) {
    fireEvent(listeners, "enrichment", {
      phase: "memory_retrieved",
      message: "Retrieved 2 memory hits",
      memory: {
        mode: "retrieve",
        hit_count: 2,
        skill_count: 1,
        insight_count: 1,
        resource_count: 0,
        vector_hits: 2,
        keyword_hits: 0,
        graph_hits: 0,
        latency_ms: 500,
      },
    });
  }

  function fireSkillExtracted(listeners: Record<string, ((e: MessageEvent) => void)[]>) {
    fireEvent(listeners, "enrichment", {
      phase: "memory_skill_extracted",
      message: "1 skill extracted",
      memory: {
        mode: "extract_skills",
        extracted_count: 1,
        persisted_count: 1,
        skills: [
          { name: "Test Skill", description: "A skill", confidence: 0.9, sharing_scope: "project" },
        ],
      },
    });
  }

  function fireInsightExtracted(listeners: Record<string, ((e: MessageEvent) => void)[]>) {
    fireEvent(listeners, "enrichment", {
      phase: "memory_insight_extracted",
      message: "1 insight extracted",
      memory: {
        mode: "extract_insights",
        insights: [
          {
            insight_type: "lesson",
            content: "Always validate inputs",
            relevance_score: 0.85,
            sharing_scope: "agent",
          },
        ],
      },
    });
  }

  it("preserves retrievedMemoryContext after turn_complete", async () => {
    const { s, listeners } = await startWithEvents();

    fireMemoryRetrieved(listeners);
    expect(s.retrievedMemoryContext).not.toBeNull();
    expect(s.retrievedMemoryContext?.hitCount).toBe(2);
    expect(s.retrievedMemoryContext?.vectorHits).toBe(2);

    fireEvent(listeners, "turn_complete", { responses: ["Done"], duration_ms: 100 });

    // Memory context should still be available after turn completes
    expect(s.retrievedMemoryContext).not.toBeNull();
    expect(s.retrievedMemoryContext?.hitCount).toBe(2);
    expect(s.retrievedMemoryContext?.vectorHits).toBe(2);
  });

  it("preserves extractedSkills after turn_complete", async () => {
    const { s, listeners } = await startWithEvents();

    fireSkillExtracted(listeners);
    expect(s.extractedSkills).toHaveLength(1);

    fireEvent(listeners, "turn_complete", { responses: ["Done"], duration_ms: 100 });

    expect(s.extractedSkills).toHaveLength(1);
    expect(s.extractedSkills[0].name).toBe("Test Skill");
  });

  it("preserves extractedInsights after turn_complete", async () => {
    const { s, listeners } = await startWithEvents();

    fireInsightExtracted(listeners);
    expect(s.extractedInsights).toHaveLength(1);

    fireEvent(listeners, "turn_complete", { responses: ["Done"], duration_ms: 100 });

    expect(s.extractedInsights).toHaveLength(1);
    expect(s.extractedInsights[0].content).toBe("Always validate inputs");
  });

  it("preserves all memory state after final event", async () => {
    const { s, listeners } = await startWithEvents();

    fireMemoryRetrieved(listeners);
    fireSkillExtracted(listeners);
    fireInsightExtracted(listeners);

    fireEvent(listeners, "final", { responses: ["All done"] });

    expect(s.retrievedMemoryContext).not.toBeNull();
    expect(s.extractedSkills).toHaveLength(1);
    expect(s.extractedInsights).toHaveLength(1);
  });

  it("preserves memory state after session_end event", async () => {
    const { s, listeners } = await startWithEvents();

    fireMemoryRetrieved(listeners);
    fireSkillExtracted(listeners);

    fireEvent(listeners, "session_end", {});

    expect(s.retrievedMemoryContext).not.toBeNull();
    expect(s.extractedSkills).toHaveLength(1);
  });

  it("preserves memory state after error event", async () => {
    const { s, listeners } = await startWithEvents();

    fireMemoryRetrieved(listeners);

    fireEvent(listeners, "error", { error: "Something failed" });

    expect(s.retrievedMemoryContext).not.toBeNull();
    expect(s.retrievedMemoryContext?.vectorHits).toBe(2);
  });

  it("clears memory state on explicit reset", async () => {
    const { s, listeners } = await startWithEvents();

    fireMemoryRetrieved(listeners);
    fireSkillExtracted(listeners);
    fireInsightExtracted(listeners);

    expect(s.retrievedMemoryContext).not.toBeNull();
    expect(s.extractedSkills).toHaveLength(1);
    expect(s.extractedInsights).toHaveLength(1);

    s.reset();

    expect(s.retrievedMemoryContext).toBeNull();
    expect(s.extractedSkills).toEqual([]);
    expect(s.extractedInsights).toEqual([]);
  });

  it("clears memory state on startSession (new session)", async () => {
    const { s, listeners } = await startWithEvents();

    fireMemoryRetrieved(listeners);
    fireSkillExtracted(listeners);

    expect(s.extractedSkills).toHaveLength(1);

    // Start a new session - memory should be cleared
    mockFetchOk(MOCK_SESSION);
    await s.startSession("d-2", "New session");

    expect(s.retrievedMemoryContext).toBeNull();
    expect(s.extractedSkills).toEqual([]);
    expect(s.extractedInsights).toEqual([]);
  });
});

// MARK: send

describe("useSession - send", () => {
  it("rejects when no active session", async () => {
    const s = useSession();
    await s.send("hello");
    expect(s.error).toBe("Session not ready for messages");
  });

  it("queues a message for the next turn while the session is running", async () => {
    const es = makeMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Hello");

    mockFetchOk({
      ...MOCK_SESSION,
      queued_message_count: 1,
    });

    await s.send("Queue this next");

    expect(s.session?.queued_message_count).toBe(1);
    expect(s.canStageNext).toBe(true);
    const lastMessage = s.messages.at(-1);
    expect(lastMessage?.content).toBe("Queue this next");
    expect(lastMessage?.metadata?.queuedForNextTurn).toBe(true);

    fireEvent(es.listeners, "session_start", {
      queued_message_count: 0,
      consumed_queued_message_count: 1,
    });

    const queuedMessageItem = s.chatFlowItems.find((item) => {
      if (item.type !== "message") {
        return false;
      }
      return (item.data as Message).content === "Queue this next";
    });
    expect(queuedMessageItem?.type).toBe("message");
    if (queuedMessageItem?.type === "message") {
      const queuedMessage = queuedMessageItem.data as Message;
      expect(queuedMessage.metadata?.queuedForNextTurn).toBeUndefined();
    }
  });
});

// MARK: submitInterrupt

describe("useSession - submitInterrupt", () => {
  it("reconnects the event stream after submitting an interrupt", async () => {
    const es = makeMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Hello");

    fireEvent(es.listeners, "interrupt_required", {
      tool_name: "greet_user",
      interrupt_id: "int-1",
      data_key: "user_name",
      prompt: "Please enter your name:",
    });
    fireEvent(es.listeners, "final", {
      responses: ["Interrupted"],
    });

    expect(s.isConnected).toBe(false);

    mockFetchOk({
      ...MOCK_SESSION,
      status: "running",
      can_send_message: false,
      can_stage_message: true,
      is_active: true,
    });

    await s.submitInterrupt("int-1", "Chad");

    expect(s.session?.status).toBe("running");
    expect(s.isConnected).toBe(true);
    expect(s.interruptCards.get("int-1")?.status).toBe("completed");
    expect(s.interruptCards.get("int-1")?.submittedValue).toBe("Chad");
  });

  it("ignores stale SSE callbacks after reconnecting", async () => {
    const es = makeSequentialMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Hello");

    const originalSource = es.sources[0];

    fireEvent(originalSource.listeners, "interrupt_required", {
      tool_name: "greet_user",
      interrupt_id: "int-1",
      data_key: "user_name",
      prompt: "Please enter your name:",
    });

    mockFetchOk({
      ...MOCK_SESSION,
      status: "running",
      can_send_message: false,
      can_stage_message: true,
      is_active: true,
    });

    await s.submitInterrupt("int-1", "Chad");

    expect(es.sources).toHaveLength(2);
    expect(s.session?.status).toBe("running");
    expect(s.isConnected).toBe(true);

    fireEvent(originalSource.listeners, "session_end", {});
    originalSource.instance.onerror?.({} as Event);

    expect(s.session?.status).toBe("running");
    expect(s.error).toBeNull();
    expect(s.isConnected).toBe(true);
  });
});

// MARK: reset

describe("useSession - reset", () => {
  it("clears all session state", async () => {
    const { MockEventSource } = makeMockEventSource();
    vi.stubGlobal("EventSource", MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Hello");

    s.reset();

    expect(s.session).toBeNull();
    expect(s.hasActiveSession).toBe(false);
    expect(s.chatFlowItems).toEqual([]);
    expect(s.toolCards.size).toBe(0);
    expect(s.events).toEqual([]);
    expect(s.loading).toBe(false);
    expect(s.error).toBeNull();
    expect(s.currentPhase).toBeNull();
    expect(s.extractedSkills).toEqual([]);
    expect(s.extractedInsights).toEqual([]);
    expect(s.retrievedMemoryContext).toBeNull();
  });

  it("resets memoryConfig back to defaults", () => {
    const s = useSession();
    s.setMemoryConfig({
      enabled: true,
      level: "glimpse",
      summarizationEnabled: false,
      skillExtractionEnabled: false,
      insightExtractionEnabled: false,
      retrievalEnabled: false,
      persistenceMode: "vector_only",
    });

    expect(s.memoryConfig).toEqual({
      enabled: true,
      level: "glimpse",
      summarizationEnabled: false,
      skillExtractionEnabled: false,
      insightExtractionEnabled: false,
      retrievalEnabled: false,
      persistenceMode: "vector_only",
    });

    s.reset();

    expect(s.memoryConfig).toEqual({
      enabled: false,
      level: "clarity",
      summarizationEnabled: true,
      skillExtractionEnabled: true,
      insightExtractionEnabled: true,
      retrievalEnabled: true,
      persistenceMode: "vector_plus_graph",
    });
  });
});

// MARK: end / cancel

describe("useSession - end and cancel", () => {
  it("end does nothing when no session", async () => {
    mockFetchOk(undefined);
    const s = useSession();
    await s.end(); // Should not throw
    expect(s.error).toBeNull();
  });

  it("cancel does nothing when no session", async () => {
    mockFetchOk(undefined);
    const s = useSession();
    await s.cancel(); // Should not throw
    expect(s.error).toBeNull();
  });
});

// MARK: Swarm action card merging

describe("useSession - swarm action card merging", () => {
  // For swarm_agent invocations the server emits TWO events per action: a
  // tool_event (tool.id = "swarm_tool_<agent>_<random>") and an
  // agent_assignment (assignment_id = "<action_uuid>"). They describe the
  // SAME action with different identifiers; the studio must collapse them
  // into one card. AND when the swarm redeploys the same agent for a
  // follow-up (supervisor_loop), each redeployment must render as its OWN
  // card — only co-temporal events for the same in-flight action merge.

  it("merges tool_event and agent_assignment for the SAME swarm action into one card", async () => {
    const es = makeMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Run the swarm");

    // Action 1: server sends tool_event(executing) for swarm_tool_<random>.
    fireEvent(es.listeners, "tool_event", {
      tool_id: "swarm_tool_coding_agent_aaaa",
      tool_name: "coding_agent",
      tool_type: "agent",
      status: "executing",
      agent_name: "coding_agent",
      swarm_name: "creator_swarm",
      args: { agent_id: "agent-coder" },
    });

    // ...then the server sends an agent_assignment(executing) for the SAME
    // action with a DIFFERENT id (the action_uuid). The studio must MERGE
    // this into the existing executing card, not create a second one.
    fireEvent(es.listeners, "agent_assignment", {
      assignment_id: "action-uuid-1",
      agent_name: "coding_agent",
      swarm_name: "creator_swarm",
      status: "in_progress",
    });

    const agentCards = Array.from(s.toolCards.values()).filter(
      (c) => c.toolType === "agent" && c.agentName === "coding_agent",
    );
    expect(agentCards).toHaveLength(1);
    expect(agentCards[0].toolId).toBe("swarm_tool_coding_agent_aaaa");
  });

  it("creates separate cards for two SEPARATE invocations of the same agent", async () => {
    const es = makeMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Run the swarm");

    // Action 1: executing -> completed.
    fireEvent(es.listeners, "tool_event", {
      tool_id: "swarm_tool_coding_agent_aaaa",
      tool_name: "coding_agent",
      tool_type: "agent",
      status: "executing",
      agent_name: "coding_agent",
      swarm_name: "creator_swarm",
      args: {},
    });
    fireEvent(es.listeners, "tool_event", {
      tool_id: "swarm_tool_coding_agent_aaaa",
      tool_name: "coding_agent",
      tool_type: "agent",
      status: "completed",
      agent_name: "coding_agent",
      swarm_name: "creator_swarm",
      args: {},
    });

    // Action 2 (supervisor_loop redeployment): a NEW swarm_tool_<random>
    // arrives while action 1 is already completed. This must produce a
    // FRESH card, not merge into action 1's card.
    fireEvent(es.listeners, "tool_event", {
      tool_id: "swarm_tool_coding_agent_bbbb",
      tool_name: "coding_agent",
      tool_type: "agent",
      status: "executing",
      agent_name: "coding_agent",
      swarm_name: "creator_swarm",
      args: {},
    });

    const agentCards = Array.from(s.toolCards.values()).filter(
      (c) => c.toolType === "agent" && c.agentName === "coding_agent",
    );
    expect(agentCards).toHaveLength(2);
    const ids = agentCards.map((c) => c.toolId).sort();
    expect(ids).toEqual(["swarm_tool_coding_agent_aaaa", "swarm_tool_coding_agent_bbbb"]);
  });

  it("merges agent_assignment(completed) into the existing executing card for the same action", async () => {
    const es = makeMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Run the swarm");

    fireEvent(es.listeners, "tool_event", {
      tool_id: "swarm_tool_coding_agent_xxxx",
      tool_name: "coding_agent",
      tool_type: "agent",
      status: "executing",
      agent_name: "coding_agent",
      swarm_name: "creator_swarm",
      args: {},
    });

    // Even though this completion event has a different id than the
    // tool_event, the lifecycle-gated fallback should route it to the
    // still-executing card so the result lands on one card.
    fireEvent(es.listeners, "agent_assignment", {
      assignment_id: "action-uuid-1",
      agent_name: "coding_agent",
      swarm_name: "creator_swarm",
      status: "completed",
      result: { response: "done" },
    });

    const agentCards = Array.from(s.toolCards.values()).filter(
      (c) => c.toolType === "agent" && c.agentName === "coding_agent",
    );
    expect(agentCards).toHaveLength(1);
    expect(agentCards[0].toolId).toBe("swarm_tool_coding_agent_xxxx");
  });
});

// MARK: Filtered items

describe("useSession - filteredChatFlowItems", () => {
  it("applies current filters to chatFlowItems", async () => {
    const es = makeMockEventSource();
    vi.stubGlobal("EventSource", es.MockEventSource);
    mockFetchOk(MOCK_SESSION);

    const s = useSession();
    await s.startSession("d-1", "Hello");

    // Add a tool
    fireEvent(es.listeners, "tool_event", {
      tool_id: "tc-1",
      tool_name: "test",
      tool_type: "func",
      status: "completed",
      args: {},
    });

    // Default filters show all
    expect(s.filteredChatFlowItems.length).toBeGreaterThan(0);

    // Filter to messages only
    s.setFilters({ itemType: "messages" });
    const filtered = s.filteredChatFlowItems;
    expect(filtered.every((i) => i.type === "message")).toBe(true);
  });
});
