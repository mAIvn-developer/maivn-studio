import { asRecord } from "./event-utils";
import type { SessionStoreContext } from "../types";

// MARK: Types

export interface NormalizedIncomingEvent {
  type: string;
  data: Record<string, unknown>;
}

// MARK: Helpers

function readTrimmedString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function readNonEmptyText(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  // Preserve original chunk spacing for streaming concatenation while still
  // rejecting empty payloads.
  return value.length > 0 ? value : undefined;
}

function buildAssistantChunkEvent(
  assistantId: string,
  text: string,
  options: { replaceContent?: boolean } = {},
): NormalizedIncomingEvent | null {
  if (text.length === 0) {
    return null;
  }

  return {
    type: "assistant_chunk",
    data: {
      assistant_id: assistantId,
      text,
      replace_content: options.replaceContent === true,
      assistant: {
        id: assistantId,
        delta: text,
        replace_content: options.replaceContent === true,
      },
    },
  };
}

function buildStatusMessageEvent(
  assistantId: string,
  message: string,
): NormalizedIncomingEvent | null {
  const normalizedMessage = message.trim();
  if (!normalizedMessage) {
    return null;
  }

  return {
    type: "status_message",
    data: {
      assistant_id: assistantId,
      message,
      assistant: {
        id: assistantId,
      },
      status: {
        message,
      },
    },
  };
}

function computeStreamingDelta(
  ctx: SessionStoreContext,
  assistantId: string,
  streamingContent: string,
): { text: string; replaceContent: boolean } {
  const previousSnapshot = ctx.assistantSnapshots.get(assistantId) ?? "";
  ctx.assistantSnapshots.set(assistantId, streamingContent);

  if (!streamingContent) {
    return { text: "", replaceContent: false };
  }

  if (!previousSnapshot) {
    return { text: streamingContent, replaceContent: false };
  }

  if (streamingContent.startsWith(previousSnapshot)) {
    return { text: streamingContent.slice(previousSnapshot.length), replaceContent: false };
  }

  if (previousSnapshot.startsWith(streamingContent)) {
    return { text: "", replaceContent: false };
  }

  return { text: streamingContent, replaceContent: true };
}

function normalizeAssistantChunkEvent(
  eventData: Record<string, unknown>,
): NormalizedIncomingEvent | null {
  const assistantData = asRecord(eventData.assistant);
  const assistantId =
    readTrimmedString(eventData.assistant_id) ??
    readTrimmedString(assistantData?.id) ??
    "assistant";
  const text = readNonEmptyText(eventData.text) ?? readNonEmptyText(assistantData?.delta) ?? "";
  // ``replace_content`` is the wire signal from the SDK that this chunk
  // should overwrite the existing assistant bubble's content rather than
  // append onto it. It's set on the first chunk after a reevaluate cycle
  // so the second cycle's text doesn't visually concatenate onto the
  // first cycle's text. Either top-level or nested under ``assistant``
  // is accepted (the bridge payload sets both, but defensive readers may
  // see only one).
  const replaceContent =
    eventData.replace_content === true || assistantData?.replace_content === true;
  return buildAssistantChunkEvent(assistantId, text, { replaceContent });
}

function normalizeProgressUpdateEvent(
  eventData: Record<string, unknown>,
): NormalizedIncomingEvent | null {
  const assistantId = readTrimmedString(eventData.assistant_id) ?? "assistant";
  const text = readNonEmptyText(eventData.text) ?? "";
  return buildAssistantChunkEvent(assistantId, text);
}

function normalizeLegacyUpdateEvent(
  ctx: SessionStoreContext,
  eventData: Record<string, unknown>,
): NormalizedIncomingEvent[] {
  const assistantId = readTrimmedString(eventData.assistant_id) ?? "assistant";
  const streamingContent = readNonEmptyText(eventData.streaming_content);
  if (!streamingContent) {
    return [];
  }

  const delta = computeStreamingDelta(ctx, assistantId, streamingContent);
  const assistantChunk = buildAssistantChunkEvent(assistantId, delta.text, {
    replaceContent: delta.replaceContent,
  });
  return assistantChunk ? [assistantChunk] : [];
}

function normalizeToolEvent(eventData: Record<string, unknown>): NormalizedIncomingEvent | null {
  const toolData = asRecord(eventData.tool);
  const valueData = asRecord(eventData.value);
  const rawToolCall = asRecord(valueData?.tool_call);
  const toolCalls = Array.isArray(valueData?.tool_calls) ? valueData.tool_calls : [];
  const firstToolCall = asRecord(toolCalls[0]);
  const rawBackendToolCall = rawToolCall ?? firstToolCall;

  const toolId =
    readTrimmedString(toolData?.id) ??
    readTrimmedString(eventData.tool_id) ??
    readTrimmedString(eventData.id) ??
    readTrimmedString(rawBackendToolCall?.tool_id);
  if (!toolId) {
    return null;
  }

  const toolName =
    readTrimmedString(toolData?.name) ??
    readTrimmedString(eventData.tool_name) ??
    readTrimmedString(rawBackendToolCall?.tool_id) ??
    toolId;
  const toolType =
    readTrimmedString(toolData?.type) ?? readTrimmedString(eventData.tool_type) ?? "func";
  const status =
    readTrimmedString(toolData?.status) ?? readTrimmedString(eventData.status) ?? "executing";
  const args =
    asRecord(toolData?.args) ??
    asRecord(rawBackendToolCall?.args) ??
    asRecord(eventData.args) ??
    {};
  const result = toolData?.result ?? eventData.result;
  const error =
    readTrimmedString(toolData?.error) ?? readTrimmedString(eventData.error) ?? undefined;
  const agentName = readTrimmedString(eventData.agent_name);
  const swarmName = readTrimmedString(eventData.swarm_name);

  return {
    type: "tool_event",
    data: {
      tool_id: toolId,
      tool_name: toolName,
      tool_type: toolType,
      status,
      args,
      result,
      error,
      agent_name: agentName,
      swarm_name: swarmName,
      tool: {
        id: toolId,
        name: toolName,
        type: toolType,
        status,
        args,
        result,
        error,
      },
    },
  };
}

function normalizeSystemToolStartEvent(
  eventData: Record<string, unknown>,
): NormalizedIncomingEvent | null {
  const toolData = asRecord(eventData.tool);
  const toolId =
    readTrimmedString(toolData?.id) ??
    readTrimmedString(eventData.tool_id) ??
    readTrimmedString(eventData.assignment_id);
  if (!toolId) {
    return null;
  }

  const toolName =
    readTrimmedString(toolData?.name) ??
    readTrimmedString(eventData.tool_type) ??
    readTrimmedString(eventData.tool_name) ??
    "system";
  const params = asRecord(toolData?.args) ?? asRecord(eventData.params) ?? {};
  const agentName = readTrimmedString(eventData.agent_name);
  const swarmName = readTrimmedString(eventData.swarm_name);

  return {
    type: "system_tool_start",
    data: {
      tool_id: toolId,
      tool_type: toolName,
      params,
      agent_name: agentName,
      swarm_name: swarmName,
      tool: {
        id: toolId,
        name: toolName,
        type: "system",
        status: "executing",
        args: params,
      },
    },
  };
}

function normalizeSystemToolChunkEvent(
  eventData: Record<string, unknown>,
): NormalizedIncomingEvent | null {
  const toolData = asRecord(eventData.tool);
  const chunkData = asRecord(eventData.chunk);
  const toolId =
    readTrimmedString(toolData?.id) ??
    readTrimmedString(eventData.tool_id) ??
    readTrimmedString(eventData.assignment_id);
  if (!toolId) {
    return null;
  }

  const normalizedText =
    readNonEmptyText(chunkData?.text) ?? readNonEmptyText(eventData.text) ?? "";
  const progress =
    typeof chunkData?.progress === "number"
      ? chunkData.progress
      : typeof eventData.progress === "number"
        ? eventData.progress
        : undefined;

  return {
    type: "system_tool_chunk",
    data: {
      tool_id: toolId,
      text: normalizedText,
      progress,
      tool: {
        id: toolId,
        type: "system",
      },
      chunk: {
        text: normalizedText,
        progress,
      },
    },
  };
}

function normalizeSystemToolCompleteEvent(
  eventData: Record<string, unknown>,
): NormalizedIncomingEvent | null {
  const toolData = asRecord(eventData.tool);
  const toolId =
    readTrimmedString(toolData?.id) ??
    readTrimmedString(eventData.tool_id) ??
    readTrimmedString(eventData.assignment_id);
  if (!toolId) {
    return null;
  }

  const result = toolData?.result ?? eventData.result;
  return {
    type: "system_tool_complete",
    data: {
      tool_id: toolId,
      result,
      tool: {
        id: toolId,
        type: "system",
        status: "completed",
        result,
      },
    },
  };
}

function normalizeStatusMessageEvent(
  eventData: Record<string, unknown>,
): NormalizedIncomingEvent | null {
  const statusData = asRecord(eventData.status);
  const assistantData = asRecord(eventData.assistant);
  const assistantId =
    readTrimmedString(eventData.assistant_id) ??
    readTrimmedString(assistantData?.id) ??
    "assistant";
  const message =
    readNonEmptyText(eventData.message) ?? readNonEmptyText(statusData?.message) ?? "";
  return buildStatusMessageEvent(assistantId, message);
}

// MARK: Ingress Normalization

export function normalizeIncomingEvents(
  ctx: SessionStoreContext,
  type: string,
  data: unknown,
): NormalizedIncomingEvent[] {
  const eventData = asRecord(data) ?? {};

  switch (type) {
    case "assistant_chunk": {
      const normalized = normalizeAssistantChunkEvent(eventData);
      return normalized ? [normalized] : [];
    }

    case "progress_update": {
      const normalized = normalizeProgressUpdateEvent(eventData);
      return normalized ? [normalized] : [];
    }

    case "update":
      return normalizeLegacyUpdateEvent(ctx, eventData);

    case "tool_event": {
      const normalized = normalizeToolEvent(eventData);
      return normalized ? [normalized] : [];
    }

    case "system_tool_start": {
      const normalized = normalizeSystemToolStartEvent(eventData);
      return normalized ? [normalized] : [];
    }

    case "system_tool_chunk": {
      const normalized = normalizeSystemToolChunkEvent(eventData);
      return normalized ? [normalized] : [];
    }

    case "system_tool_complete": {
      const normalized = normalizeSystemToolCompleteEvent(eventData);
      return normalized ? [normalized] : [];
    }

    case "status_message": {
      const normalized = normalizeStatusMessageEvent(eventData);
      return normalized ? [normalized] : [];
    }

    default:
      return [{ type, data: eventData }];
  }
}
