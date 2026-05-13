import type { InterruptRequiredEvent } from "$lib/types";
import { handleAgentAssignment } from "./agent-assignment-events";
import {
  appendAssistantMessageChunk,
  consumePendingAssistantChunks,
  finalizeStreamingAssistantMessage,
  handleAssistantChunk,
} from "./assistant-events";
import { handleBatchComplete, handleBatchItemComplete, handleBatchStart } from "./batch-events";
import { handleEnrichment } from "./enrichment-events";
import { handleHookFired } from "./hook-events";
import { handleInterruptRequired } from "./interrupt-events";
import { handleSessionStart } from "./session-lifecycle-events";
import { commitStatusMessage, readStatusMessageText } from "./status-events";
import {
  handleSystemToolChunk,
  handleSystemToolComplete,
  handleSystemToolStart,
} from "./system-tool-events";
import { handleSessionEndOrError, handleTurnCompleteOrFinal } from "./terminal-events";
import { handleToolEvent } from "./tool-events";
import { normalizeIncomingEvents } from "./ingress-normalization";
import type { SessionStoreContext } from "../types";

// MARK: Event Dispatcher

export function processEvent(ctx: SessionStoreContext, type: string, data: unknown) {
  const eventData = (data as Record<string, unknown> | null) ?? {};

  // Add to raw event history
  ctx.setEvents([
    ...ctx.getEvents(),
    {
      id: crypto.randomUUID(),
      type,
      data: eventData,
      timestamp: new Date().toISOString(),
    },
  ]);

  for (const normalizedEvent of normalizeIncomingEvents(ctx, type, eventData)) {
    processNormalizedEvent(ctx, normalizedEvent.type, normalizedEvent.data);
  }
}

function processNormalizedEvent(
  ctx: SessionStoreContext,
  type: string,
  eventData: Record<string, unknown>,
) {
  switch (type) {
    case "session_start": {
      handleSessionStart(ctx, eventData);
      break;
    }

    case "tool_event": {
      handleToolEvent(ctx, eventData);
      break;
    }

    case "system_tool_start": {
      handleSystemToolStart(ctx, eventData);
      break;
    }

    case "system_tool_chunk": {
      handleSystemToolChunk(ctx, eventData);
      break;
    }

    case "system_tool_complete": {
      handleSystemToolComplete(ctx, eventData);
      break;
    }

    case "assistant_chunk": {
      handleAssistantChunk(ctx, eventData);
      break;
    }

    case "status_message": {
      const msg = readStatusMessageText(eventData);
      if (msg) {
        commitStatusMessage(ctx, msg);
      }
      break;
    }

    case "agent_assignment": {
      handleAgentAssignment(ctx, eventData);
      break;
    }

    case "batch_start": {
      handleBatchStart(ctx, eventData);
      break;
    }

    case "batch_item_complete": {
      handleBatchItemComplete(ctx, eventData);
      break;
    }

    case "batch_complete": {
      handleBatchComplete(ctx, eventData);
      break;
    }

    // turn_complete: Backend event when SDK invocation (session) completes
    // final: Legacy terminal completion event (stream closes after this event)
    // Note: Backend uses "turn" terminology for internal reevaluation cycles,
    // but this event signals the SDK session is done responding
    case "turn_complete":
    case "final": {
      handleTurnCompleteOrFinal(ctx, type, eventData, {
        consumePendingAssistantChunks,
        appendAssistantMessageChunk,
        finalizeStreamingAssistantMessage,
      });
      break;
    }

    case "session_end":
    case "error": {
      handleSessionEndOrError(ctx, type, eventData, {
        consumePendingAssistantChunks,
        appendAssistantMessageChunk,
        finalizeStreamingAssistantMessage,
      });
      break;
    }

    case "enrichment": {
      handleEnrichment(ctx, eventData);
      break;
    }

    case "hook_fired": {
      handleHookFired(ctx, eventData);
      break;
    }

    case "heartbeat":
      // Ignore heartbeats
      break;

    case "interrupt_required": {
      handleInterruptRequired(ctx, eventData as unknown as InterruptRequiredEvent);
      break;
    }
  }
}

// MARK: Tool Events

/**
 * Returns true when the event type requires a disconnect after processing.
 * The caller (index.svelte.ts) is responsible for actually calling disconnect().
 */
export function shouldDisconnectAfterEvent(type: string): boolean {
  return type === "final" || type === "session_end" || type === "error";
}
