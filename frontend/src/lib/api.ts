import type {
  AgentInfo,
  App,
  AppDetails,
  AppVariant,
  InvocationConfig,
  MessageAttachmentPayload,
  MessageType,
  RepoScanItem,
  RepoScanSelection,
  SavedPrompt,
  Session,
  StructuredOutputConfig,
  SwarmInfo,
} from "./types";

const API_BASE = "/api";

// MARK: Helpers

function buildStructuredOutputPayload(
  config: StructuredOutputConfig | undefined,
): { enabled: true; tool_name: string; schema_name?: string; json_schema?: unknown } | undefined {
  if (!config?.enabled || !config.selectedTool) {
    return undefined;
  }
  return {
    enabled: true,
    tool_name: config.selectedTool,
    schema_name: config.schema?.name,
    json_schema: config.schema?.schema,
  };
}

async function extractErrorDetail(response: Response, fallback: string): Promise<string> {
  const clone = response.clone();
  const errorData = await response.json().catch(() => null);

  if (errorData && typeof errorData === "object") {
    if ("detail" in errorData && typeof errorData.detail === "string" && errorData.detail.trim()) {
      return errorData.detail;
    }
    if (
      "message" in errorData &&
      typeof errorData.message === "string" &&
      errorData.message.trim()
    ) {
      return errorData.message;
    }
  }

  const raw = await clone.text().catch(() => "");
  return raw.trim() || fallback;
}

// MARK: Apps API

export async function fetchApps(): Promise<App[]> {
  const res = await fetch(`${API_BASE}/apps`);
  if (!res.ok) throw new Error("Failed to fetch apps");
  const data = await res.json();
  return data.apps;
}

export async function fetchAppsByCategory(): Promise<Record<string, App[]>> {
  const res = await fetch(`${API_BASE}/apps`);
  if (!res.ok) throw new Error("Failed to fetch apps");
  const data = await res.json();
  // Group apps by category
  const byCategory: Record<string, App[]> = {};
  for (const app of data.apps as App[]) {
    if (!byCategory[app.category]) {
      byCategory[app.category] = [];
    }
    byCategory[app.category].push(app);
  }
  return byCategory;
}

export async function fetchApp(id: string): Promise<AppDetails> {
  const res = await fetch(`${API_BASE}/apps/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch app ${id}`);
  const data = await res.json();
  // API returns { app, variants } - merge into AppDetails
  return {
    ...data.app,
    variants: data.variants,
    // These fields aren't returned by API yet, provide defaults
    agents: [],
    swarms: [],
    tools: [],
    prompts: [],
    privateDataSchema: [],
  } as AppDetails;
}

export async function fetchAppFullDetails(id: string, variant?: string): Promise<AppDetails> {
  const params = new URLSearchParams();
  if (variant) {
    params.set("variant", variant);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/apps/${id}/details${suffix}`);
  if (!res.ok) throw new Error(`Failed to fetch app details ${id}`);
  return res.json();
}

// MARK: Repo Discovery API

export async function scanRepo(): Promise<RepoScanItem[]> {
  const res = await fetch(`${API_BASE}/discovery/scan`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to scan repo");
  const data = await res.json();
  return data.items as RepoScanItem[];
}

export async function applyRepoSelection(selections: RepoScanSelection[]): Promise<number> {
  const res = await fetch(`${API_BASE}/discovery/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selections }),
  });
  if (!res.ok) throw new Error("Failed to apply selections");
  const data = await res.json();
  return data.added as number;
}

// MARK: Sessions API

export async function createSession(
  appId: string,
  message: string,
  options?: {
    variant?: string;
    threadId?: string;
    messageType?: MessageType;
    attachments?: MessageAttachmentPayload[];
    privateData?: Record<string, unknown>;
    structuredOutput?: StructuredOutputConfig;
    invocation?: InvocationConfig;
    systemMessage?: string;
  },
): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      app_id: appId,
      message,
      variant: options?.variant,
      thread_id: options?.threadId,
      message_type: options?.messageType ?? "human",
      attachments: options?.attachments,
      private_data: options?.privateData,
      structured_output: buildStructuredOutputPayload(options?.structuredOutput),
      invocation: options?.invocation,
      system_message: options?.systemMessage,
    }),
  });
  if (!res.ok) {
    throw new Error(await extractErrorDetail(res, "Failed to create session"));
  }
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to fetch session ${sessionId}`);
  return res.json();
}

export async function sendMessage(
  sessionId: string,
  message: string,
  messageType: MessageType = "human",
  structuredOutput?: StructuredOutputConfig,
  invocation?: InvocationConfig,
  attachments?: MessageAttachmentPayload[],
): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      message_type: messageType,
      attachments,
      structured_output: buildStructuredOutputPayload(structuredOutput),
      invocation,
    }),
  });
  if (!res.ok) {
    throw new Error(await extractErrorDetail(res, "Failed to send message"));
  }
  return res.json();
}

export async function endSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/end`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to end session");
}

export async function cancelSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to cancel session");
}

export async function submitInterrupt(
  sessionId: string,
  interruptId: string,
  dataKey: string,
  value: unknown,
): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/interrupt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      interrupt_id: interruptId,
      data_key: dataKey,
      value,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to submit interrupt");
  }
  return res.json();
}

// MARK: SSE Connection

export function connectToEvents(
  sessionId: string,
  onEvent: (event: { type: string; data: unknown; eventId?: string }) => void,
  onError?: (error: Event) => void,
  lastEventId?: string,
): EventSource {
  const url = lastEventId
    ? `${API_BASE}/sessions/${sessionId}/events?last_event_id=${encodeURIComponent(lastEventId)}`
    : `${API_BASE}/sessions/${sessionId}/events`;
  const es = new EventSource(url);

  const handleMessageEvent = (type: string, e: MessageEvent) => {
    try {
      const payload = JSON.parse(e.data);
      // The payload structure is { id, type, data, timestamp }
      // Extract the actual event data from payload.data
      const eventData = payload?.data ?? payload;
      // Prefer the native SSE event ID so reconnects resume from the actual
      // last delivered event even when the payload omits an embedded id field.
      const eventId = (
        typeof e.lastEventId === "string" && e.lastEventId.trim()
          ? e.lastEventId
          : typeof payload?.id === "string"
            ? payload.id
            : undefined
      ) as string | undefined;
      onEvent({ type, data: eventData, eventId });
    } catch {
      console.error("Failed to parse event:", e.data);
    }
  };

  // Listen for named SSE events emitted by the backend (EventSourceResponse 'event' field)
  const eventTypes = [
    "tool_event",
    "session_start",
    "system_tool_start",
    "system_tool_chunk",
    "system_tool_complete",
    "assistant_chunk",
    "progress_update",
    "status_message",
    "agent_assignment",
    "turn_complete",
    "session_end",
    "interrupt_required",
    "enrichment",
    "error",
    "final",
    "heartbeat",
  ] as const;

  for (const type of eventTypes) {
    es.addEventListener(type, (evt) => {
      handleMessageEvent(type, evt as MessageEvent);
    });
  }

  // Backward compatibility: also handle default "message" events if emitted
  es.onmessage = (e) => {
    handleMessageEvent("message", e);
  };

  if (onError) {
    es.onerror = onError;
  }

  return es;
}

// MARK: Prompts API

export async function fetchSavedPrompts(appId?: string): Promise<SavedPrompt[]> {
  const url = appId ? `${API_BASE}/prompts?app_id=${appId}` : `${API_BASE}/prompts`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch saved prompts");
  return res.json();
}

export async function savePrompt(prompt: {
  name: string;
  content: string;
  description?: string;
  appId: string;
  messageType?: MessageType;
}): Promise<SavedPrompt> {
  const res = await fetch(`${API_BASE}/prompts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: prompt.name,
      content: prompt.content,
      description: prompt.description ?? "",
      app_id: prompt.appId,
      message_type: prompt.messageType ?? "human",
    }),
  });
  if (!res.ok) throw new Error("Failed to save prompt");
  return res.json();
}

export async function deletePrompt(promptId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/prompts/${promptId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete prompt");
}

// MARK: App Update API

export async function updateApp(
  appId: string,
  updates: {
    name?: string;
    description?: string;
    category?: string;
    tags?: string[];
    variants?: Record<string, AppVariant>;
    private_data?: Record<string, string | number | boolean>;
  },
): Promise<App> {
  const res = await fetch(`${API_BASE}/apps/${appId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update app ${appId}`);
  const data = await res.json();
  return data.app;
}

export async function updateAgent(
  appId: string,
  agentName: string,
  updates: {
    description?: string;
    system_prompt?: string;
    tags?: string[];
    memory_config?: import("$lib/types").InvocationMemoryConfig;
    system_tools_config?: import("$lib/types").InvocationSystemToolsConfig;
    orchestration_config?: import("$lib/types").InvocationOrchestrationConfig;
    timeout?: number;
    max_results?: number;
    included_nested_synthesis?: boolean | "auto";
    allow_private_in_system_tools?: boolean;
    private_data?: Record<string, unknown>;
  },
): Promise<AgentInfo> {
  const res = await fetch(`${API_BASE}/apps/${appId}/agents/${encodeURIComponent(agentName)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update agent ${agentName}`);
  return res.json();
}

export async function updateSwarm(
  appId: string,
  swarmName: string,
  updates: {
    description?: string;
    system_prompt?: string;
    tags?: string[];
    memory_config?: import("$lib/types").InvocationMemoryConfig;
    system_tools_config?: import("$lib/types").InvocationSystemToolsConfig;
    orchestration_config?: import("$lib/types").InvocationOrchestrationConfig;
    allow_private_in_system_tools?: boolean;
    private_data?: Record<string, unknown>;
  },
): Promise<SwarmInfo> {
  const res = await fetch(`${API_BASE}/apps/${appId}/swarms/${encodeURIComponent(swarmName)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update swarm ${swarmName}`);
  return res.json();
}
