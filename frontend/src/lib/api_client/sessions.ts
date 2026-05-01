import type {
  BatchInvocationConfig,
  InvocationConfig,
  MessageAttachmentPayload,
  MessageType,
  Session,
  StructuredOutputConfig,
} from "../types";

import { API_BASE, buildStructuredOutputPayload, extractErrorDetail } from "./shared";

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
    batch?: BatchInvocationConfig;
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
      batch: options?.batch,
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
  batch?: BatchInvocationConfig,
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
      batch,
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
    signal: AbortSignal.timeout(5_000),
  });
  if (!res.ok) throw new Error("Failed to end session");
}

export async function cancelSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/cancel`, {
    method: "POST",
    signal: AbortSignal.timeout(5_000),
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
      const eventData = payload?.data ?? payload;
      const eventId = (
        typeof e.lastEventId === "string" && e.lastEventId.trim()
          ? e.lastEventId
          : typeof payload?.id === "string"
            ? payload.id
            : undefined
      ) as string | undefined;
      const eventType =
        type === "message" && typeof payload?.type === "string" && payload.type.trim()
          ? payload.type.trim()
          : type;
      onEvent({ type: eventType, data: eventData, eventId });
    } catch {
      console.error("Failed to parse event:", e.data);
    }
  };

  const eventTypes = [
    "tool_event",
    "session_start",
    "system_tool_start",
    "system_tool_chunk",
    "system_tool_complete",
    "update",
    "assistant_chunk",
    "progress_update",
    "status_message",
    "agent_assignment",
    "batch_start",
    "batch_item_complete",
    "batch_complete",
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

  es.onmessage = (e) => {
    handleMessageEvent("message", e);
  };

  if (onError) {
    es.onerror = onError;
  }

  return es;
}
