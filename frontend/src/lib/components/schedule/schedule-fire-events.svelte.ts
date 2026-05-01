import { connectToEvents } from "$lib/api_client/sessions";
import type {
  ChatFlowItem,
  Message,
  PhaseChipData,
  TokenUsage,
  ToolCard,
  ToolType,
} from "$lib/types";

import { API_BASE } from "$lib/api_client/shared";

// MARK: - Types

interface ScheduleFireEventStream {
  /** Chat flow items captured for this fire — same shape the chat panel renders. */
  readonly chatFlowItems: ChatFlowItem[];
  /** True until the backend emits a terminal event (turn_complete / error). */
  readonly isLive: boolean;
  /** Set when the bridge errors. */
  readonly error: string | null;
  /** Closes the SSE connection and stops mutating state. */
  close(): void;
}

// MARK: - Implementation

/**
 * Subscribe to a single scheduled fire's event stream and build a
 * ChatFlowItem array that mirrors what the chat panel renders for a normal
 * invocation. The function is intentionally narrower than the main session
 * store: it covers the events the user expects to see (assistant streaming,
 * tool cards, phase chips, status messages, terminal events) but skips the
 * shared-state machinery (interrupts, batch matrix, memory side-panel) that
 * the chat session store provides.
 *
 * Called from `ScheduleRunCard` once the fire has an `event_session_id`. The
 * returned object is reactive (declared with $state) so callers can pass
 * `stream.chatFlowItems` straight into `ChatExchangeList`.
 */
export function createScheduleFireEventStream(
  demoId: string,
  fireId: string,
  _eventSessionId: string,
): ScheduleFireEventStream {
  const state = $state({
    chatFlowItems: [] as ChatFlowItem[],
    isLive: true,
    error: null as string | null,
  });

  // Per-stream mutable maps mirror the session store but are scoped to this
  // single fire. Keeping them outside `state` avoids reactivity overhead on
  // bookkeeping data the UI never reads directly.
  const toolCards = new Map<string, ToolCard>();
  const itemIdByToolId = new Map<string, string>();
  let streamingAssistantItemId: string | null = null;

  const url = `${API_BASE}/schedules/${encodeURIComponent(demoId)}/fires/${encodeURIComponent(fireId)}/events`;
  let es: EventSource | null = null;
  let closed = false;

  function tagOrigin<T extends ChatFlowItem>(item: T): T {
    item.origin = "schedule";
    item.scheduleFireId = fireId;
    return item;
  }

  function appendItem(item: ChatFlowItem): void {
    state.chatFlowItems = [...state.chatFlowItems, tagOrigin(item)];
  }

  function replaceItem(itemId: string, next: ChatFlowItem): void {
    state.chatFlowItems = state.chatFlowItems.map((existing) =>
      existing.id === itemId ? tagOrigin({ ...next, id: itemId }) : existing,
    );
  }

  function findItem(itemId: string): ChatFlowItem | undefined {
    return state.chatFlowItems.find((item) => item.id === itemId);
  }

  function ensureUserMessage(prompt: string): void {
    const hasUserMessage = state.chatFlowItems.some(
      (item) => item.type === "message" && (item.data as Message).role === "user",
    );
    if (hasUserMessage) return;
    const message: Message = {
      id: crypto.randomUUID(),
      role: "user",
      messageType: "human",
      content: prompt,
      timestamp: new Date().toISOString(),
    };
    appendItem({
      id: crypto.randomUUID(),
      type: "message",
      timestamp: message.timestamp,
      data: message,
    });
  }

  function ensureStreamingAssistantItem(): string {
    if (streamingAssistantItemId) return streamingAssistantItemId;
    const message: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      messageType: "ai",
      content: "",
      timestamp: new Date().toISOString(),
      metadata: { isStreaming: true },
    };
    const itemId = crypto.randomUUID();
    streamingAssistantItemId = itemId;
    appendItem({
      id: itemId,
      type: "message",
      timestamp: message.timestamp,
      data: message,
    });
    return itemId;
  }

  function appendAssistantText(text: string): void {
    const itemId = ensureStreamingAssistantItem();
    const item = findItem(itemId);
    if (!item || item.type !== "message") return;
    const msg = item.data as Message;
    replaceItem(itemId, {
      ...item,
      data: {
        ...msg,
        content: (msg.content ?? "") + text,
      },
    });
  }

  function finalizeAssistantStreaming(): void {
    if (!streamingAssistantItemId) return;
    const item = findItem(streamingAssistantItemId);
    if (!item || item.type !== "message") {
      streamingAssistantItemId = null;
      return;
    }
    const msg = item.data as Message;
    replaceItem(streamingAssistantItemId, {
      ...item,
      data: {
        ...msg,
        metadata: { ...(msg.metadata ?? {}), isStreaming: false },
      },
    });
    streamingAssistantItemId = null;
  }

  function asRecord(value: unknown): Record<string, unknown> | undefined {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return value as Record<string, unknown>;
    }
    return undefined;
  }

  function latestResponseText(value: unknown): string | undefined {
    if (!Array.isArray(value)) return undefined;
    for (let index = value.length - 1; index >= 0; index -= 1) {
      const item = value[index];
      if (typeof item !== "string") continue;
      if (item.trim()) return item;
    }
    return undefined;
  }

  function applyTerminalResponse(eventData: Record<string, unknown>): void {
    const output = asRecord(eventData.output);
    const responseRaw =
      latestResponseText(eventData.responses) ?? output?.response ?? eventData.response;
    const response = typeof responseRaw === "string" && responseRaw.trim() ? responseRaw : "";
    const structuredResult = output?.result ?? eventData.result;
    const tokenUsage = (output?.token_usage ?? eventData.token_usage) as TokenUsage | undefined;
    const durationMs =
      typeof eventData.duration_ms === "number" ? eventData.duration_ms : undefined;

    if (streamingAssistantItemId) {
      const item = findItem(streamingAssistantItemId);
      if (!item || item.type !== "message") {
        streamingAssistantItemId = null;
        return;
      }
      const msg = item.data as Message;
      replaceItem(streamingAssistantItemId, {
        ...item,
        data: {
          ...msg,
          content: response || msg.content || "",
          structuredResult:
            structuredResult !== undefined ? structuredResult : msg.structuredResult,
          sessionDetails: {
            duration_ms: durationMs,
            token_usage: tokenUsage,
          },
          metadata: { ...(msg.metadata ?? {}), isStreaming: false },
        },
      });
      streamingAssistantItemId = null;
      return;
    }

    if (!response && structuredResult === undefined) return;

    const message: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      messageType: "ai",
      content: response,
      timestamp: new Date().toISOString(),
      structuredResult,
      sessionDetails: {
        duration_ms: durationMs,
        token_usage: tokenUsage,
      },
    };
    appendItem({
      id: crypto.randomUUID(),
      type: "message",
      timestamp: message.timestamp,
      data: message,
    });
  }

  function ingestToolEvent(data: Record<string, unknown>): void {
    // Bridge events nest the canonical fields under `tool` and duplicate
    // some at the top level. Mirror what stores/session/events/tool-events.ts
    // does: prefer `tool.*` and fall back to top-level keys.
    const toolField = (data.tool ?? null) as Record<string, unknown> | null;
    const toolId = String(toolField?.id ?? data.tool_id ?? "");
    if (!toolId) return;

    const incomingStatus = (
      (toolField?.status as string | undefined) ??
      (data.status as string | undefined) ??
      "executing"
    ).toLowerCase();
    const status = (
      incomingStatus === "succeeded" ? "completed" : incomingStatus
    ) as ToolCard["status"];

    const existing = toolCards.get(toolId);
    const startedAt = existing?.startedAt ?? new Date().toISOString();

    const card: ToolCard = {
      toolId,
      toolName:
        (toolField?.name as string | undefined) ??
        (data.tool_name as string | undefined) ??
        existing?.toolName ??
        toolId,
      toolType: ((toolField?.type as ToolType | undefined) ??
        (data.tool_type as ToolType | undefined) ??
        existing?.toolType ??
        "func") as ToolType,
      status,
      args:
        (toolField?.args as Record<string, unknown> | undefined) ??
        (data.args as Record<string, unknown> | undefined) ??
        existing?.args ??
        ({} as Record<string, unknown>),
      result: (toolField?.result as unknown) ?? (data.result as unknown) ?? existing?.result,
      error:
        (toolField?.error as string | undefined) ??
        (data.error as string | undefined) ??
        existing?.error,
      startedAt,
      completedAt:
        status === "completed" || status === "failed"
          ? new Date().toISOString()
          : existing?.completedAt,
      isStreaming: status === "executing" ? (existing?.isStreaming ?? false) : false,
      streamContent: existing?.streamContent,
      isSystemTool: existing?.isSystemTool ?? false,
      agentName: (data.agent_name as string | undefined) ?? existing?.agentName,
      swarmName: (data.swarm_name as string | undefined) ?? existing?.swarmName,
    };

    toolCards.set(toolId, card);

    const existingItemId = itemIdByToolId.get(toolId);
    if (existingItemId) {
      const existingItem = findItem(existingItemId);
      if (existingItem) {
        replaceItem(existingItemId, {
          ...existingItem,
          data: card,
          timestamp: card.completedAt ?? card.startedAt,
        });
        return;
      }
    }

    const itemId = crypto.randomUUID();
    itemIdByToolId.set(toolId, itemId);
    appendItem({
      id: itemId,
      type: "tool_card",
      timestamp: card.startedAt,
      data: card,
    });
  }

  function ingestSystemTool(
    phase: "start" | "chunk" | "complete",
    data: Record<string, unknown>,
  ): void {
    const toolId = String(data.tool_id ?? "");
    if (!toolId) return;
    const existing = toolCards.get(toolId);

    if (phase === "start") {
      const card: ToolCard = {
        toolId,
        toolName: (data.tool_name as string | undefined) ?? existing?.toolName ?? toolId,
        toolType: ((data.tool_type as ToolType | undefined) ?? "system") as ToolType,
        status: "executing",
        args: (data.args as Record<string, unknown> | undefined) ?? existing?.args ?? {},
        startedAt: (data.started_at as string | undefined) ?? new Date().toISOString(),
        isStreaming: true,
        streamContent: "",
        isSystemTool: true,
      };
      toolCards.set(toolId, card);
      const itemId = crypto.randomUUID();
      itemIdByToolId.set(toolId, itemId);
      appendItem({
        id: itemId,
        type: "tool_card",
        timestamp: card.startedAt,
        data: card,
      });
      return;
    }

    if (!existing) return;

    if (phase === "chunk") {
      const delta = typeof data.text === "string" ? data.text : "";
      const updated: ToolCard = {
        ...existing,
        isStreaming: true,
        streamContent: (existing.streamContent ?? "") + delta,
      };
      toolCards.set(toolId, updated);
      const itemId = itemIdByToolId.get(toolId);
      if (!itemId) return;
      const item = findItem(itemId);
      if (!item) return;
      replaceItem(itemId, { ...item, data: updated });
      return;
    }

    if (phase === "complete") {
      const updated: ToolCard = {
        ...existing,
        status: data.error ? "failed" : "completed",
        isStreaming: false,
        completedAt: (data.completed_at as string | undefined) ?? new Date().toISOString(),
        result: data.result ?? existing.result,
        error: typeof data.error === "string" ? data.error : existing.error,
      };
      toolCards.set(toolId, updated);
      const itemId = itemIdByToolId.get(toolId);
      if (!itemId) return;
      const item = findItem(itemId);
      if (!item) return;
      replaceItem(itemId, {
        ...item,
        data: updated,
        timestamp: updated.completedAt ?? item.timestamp,
      });
    }
  }

  function ingestEnrichment(data: Record<string, unknown>): void {
    const phase = (data.phase as string | undefined) ?? "";
    const message = (data.message as string | undefined) ?? "";
    if (!phase || !message) return;
    const phaseChip: PhaseChipData = {
      phase,
      message,
      timestamp: (data.timestamp as string | undefined) ?? new Date().toISOString(),
      memory: data.memory as PhaseChipData["memory"],
      redaction: data.redaction as PhaseChipData["redaction"],
      scopeId: data.scope_id as string | undefined,
      scopeName: data.scope_name as string | undefined,
      scopeType: data.scope_type as PhaseChipData["scopeType"],
    };
    appendItem({
      id: crypto.randomUUID(),
      type: "phase_chip",
      timestamp: phaseChip.timestamp,
      data: phaseChip,
    });
  }

  function ingestStatusMessage(data: Record<string, unknown>): void {
    const text = typeof data.text === "string" ? data.text : (data.message as string | undefined);
    if (!text || !text.trim()) return;
    const message: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      messageType: "status",
      content: text,
      timestamp: new Date().toISOString(),
    };
    appendItem({
      id: crypto.randomUUID(),
      type: "message",
      timestamp: message.timestamp,
      data: message,
    });
  }

  function handleEvent(type: string, data: unknown): void {
    if (closed) return;
    const eventData = (data as Record<string, unknown> | null) ?? {};

    switch (type) {
      case "session_start": {
        const prompt = typeof eventData.prompt === "string" ? eventData.prompt.trim() : "";
        if (prompt) ensureUserMessage(prompt);
        break;
      }
      case "assistant_chunk": {
        const assistantData = (eventData.assistant ?? null) as Record<string, unknown> | null;
        const delta =
          (assistantData?.delta as string | undefined) ?? (eventData.text as string | undefined);
        if (typeof delta === "string" && delta.length > 0) {
          appendAssistantText(delta);
        }
        break;
      }
      case "tool_event": {
        ingestToolEvent(eventData);
        break;
      }
      case "system_tool_start": {
        ingestSystemTool("start", eventData);
        break;
      }
      case "system_tool_chunk": {
        ingestSystemTool("chunk", eventData);
        break;
      }
      case "system_tool_complete": {
        ingestSystemTool("complete", eventData);
        break;
      }
      case "enrichment": {
        ingestEnrichment(eventData);
        break;
      }
      case "status_message": {
        ingestStatusMessage(eventData);
        break;
      }
      case "turn_complete":
      case "final": {
        applyTerminalResponse(eventData);
        finalizeAssistantStreaming();
        state.isLive = false;
        break;
      }
      case "error": {
        finalizeAssistantStreaming();
        state.isLive = false;
        const errMsg = eventData.error;
        if (typeof errMsg === "string") state.error = errMsg;
        break;
      }
    }
  }

  // Open the SSE connection. The chat panel's connectToEvents helper hits
  // /sessions/{id}/events; for fires we built /schedules/{demo}/fires/{id}/
  // events which delivers the same EventBridge stream, so we use the URL
  // override branch.
  void connectScheduleFireStream();

  async function connectScheduleFireStream(): Promise<void> {
    try {
      es = new EventSource(url);
      // EventBridge.generate_sse wraps every event as a JSON envelope
      // {id, type, data}. The chat panel's connectToEvents helper does the
      // same unwrap (see api_client/sessions.ts). Without this, the inner
      // payload looks like the wrapper itself and every event handler
      // reads undefined fields — which is why the card body was empty.
      const handleNamedMessage = (type: string, e: MessageEvent<string>) => {
        if (!e.data) return;
        try {
          const payload = JSON.parse(e.data) as {
            type?: string;
            data?: unknown;
          };
          const eventType =
            type === "message" && typeof payload?.type === "string" && payload.type.trim()
              ? payload.type.trim()
              : type;
          const eventData = (payload?.data ?? payload) as Record<string, unknown>;
          handleEvent(eventType, eventData);
        } catch {
          /* ignore malformed JSON */
        }
      };

      es.addEventListener("message", (e: MessageEvent<string>) => handleNamedMessage("message", e));
      const namedEvents = [
        "session_start",
        "assistant_chunk",
        "tool_event",
        "system_tool_start",
        "system_tool_chunk",
        "system_tool_complete",
        "enrichment",
        "status_message",
        "agent_assignment",
        "turn_complete",
        "session_end",
        "final",
        "error",
      ];
      for (const name of namedEvents) {
        es.addEventListener(name, (e: MessageEvent<string>) => handleNamedMessage(name, e));
      }
      es.addEventListener("error", () => {
        if (state.isLive) {
          state.error = "Event stream disconnected";
        }
      });
    } catch (err) {
      state.error = err instanceof Error ? err.message : String(err);
    }
  }

  // connectToEvents is a session-bound helper; we mirror its envelope
  // handling above so the linter doesn't drop the import as unused.
  void connectToEvents;

  return {
    get chatFlowItems() {
      return state.chatFlowItems;
    },
    get isLive() {
      return state.isLive;
    },
    get error() {
      return state.error;
    },
    close() {
      closed = true;
      if (es) {
        es.close();
        es = null;
      }
    },
  };
}
