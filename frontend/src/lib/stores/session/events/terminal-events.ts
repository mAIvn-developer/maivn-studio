import type { Message, TokenUsage } from "$lib/types";

import { asRecord } from "./event-utils";
import type { SessionStoreContext } from "../types";

interface TerminalEventHelpers {
  consumePendingAssistantChunks: (ctx: SessionStoreContext) => string;
  appendAssistantMessageChunk: (ctx: SessionStoreContext, text: string) => void;
  finalizeStreamingAssistantMessage: (ctx: SessionStoreContext) => void;
}

function getLatestResponseText(value: unknown): string | undefined {
  if (!Array.isArray(value)) return undefined;
  for (let i = value.length - 1; i >= 0; i -= 1) {
    const item = value[i];
    if (typeof item === "string") {
      const trimmed = item.trim();
      if (trimmed) return trimmed;
    }
  }
  return undefined;
}

function reconcileTerminalToolCards(
  ctx: SessionStoreContext,
  terminalStatus: "completed" | "failed",
) {
  const currentToolCards = ctx.getToolCards();
  const nextToolCards = new Map(currentToolCards);
  const changedIds = new Set<string>();
  const completedAt = new Date().toISOString();

  for (const [toolId, card] of currentToolCards) {
    if (card.status !== "pending" && card.status !== "executing") {
      continue;
    }

    nextToolCards.set(toolId, {
      ...card,
      status: terminalStatus,
      isStreaming: false,
      completedAt,
    });
    changedIds.add(toolId);
  }

  if (changedIds.size === 0) {
    return;
  }

  ctx.setToolCards(nextToolCards);
  ctx.setChatFlowItems(
    ctx.getChatFlowItems().map((item) => {
      if (item.type !== "tool_card") {
        return item;
      }

      const card = item.data;
      if (!changedIds.has(card.toolId)) {
        return item;
      }

      return {
        ...item,
        data: nextToolCards.get(card.toolId) ?? card,
      };
    }),
  );
}

export function handleTurnCompleteOrFinal(
  ctx: SessionStoreContext,
  type: "turn_complete" | "final",
  eventData: Record<string, unknown>,
  helpers: TerminalEventHelpers,
) {
  ctx.flushPendingStreams();
  reconcileTerminalToolCards(ctx, "completed");

  const outputData = asRecord(eventData.output);
  const responseRaw =
    getLatestResponseText(eventData.responses) ?? outputData?.response ?? eventData.response;
  const response = typeof responseRaw === "string" ? responseRaw : undefined;
  const structuredResult = outputData?.result ?? (eventData.result as unknown);
  const durationMs = eventData.duration_ms as number | undefined;
  const tokenUsage =
    (outputData?.token_usage as TokenUsage | undefined) ??
    (eventData.token_usage as TokenUsage | undefined);
  const streamingAssistantItemId = ctx.getStreamingAssistantItemId();
  const hasStreamingAssistant = streamingAssistantItemId !== null;
  const queuedMessageCount =
    typeof eventData.queued_message_count === "number" ? eventData.queued_message_count : 0;
  const orphanedPendingAssistantText = helpers.consumePendingAssistantChunks(ctx);
  const isBatchTurn = asRecord(eventData.batch) !== undefined;

  if (isBatchTurn && !response && !orphanedPendingAssistantText) {
    // The batch result card owns the visible output for grouped executions.
  } else if (hasStreamingAssistant) {
    const targetItemId = streamingAssistantItemId;
    ctx.setChatFlowItems(
      ctx.getChatFlowItems().map((item) => {
        if (item.id !== targetItemId || item.type !== "message") {
          return item;
        }
        const existing = item.data;
        return {
          ...item,
          data: {
            ...existing,
            content: response ?? `${existing.content ?? ""}${orphanedPendingAssistantText}`,
            timestamp: new Date().toISOString(),
            structuredResult:
              structuredResult !== undefined ? structuredResult : existing.structuredResult,
            sessionDetails: {
              duration_ms: durationMs,
              token_usage: tokenUsage,
            },
            metadata: {
              ...(existing.metadata ?? {}),
              isStreaming: false,
            },
          },
        };
      }),
    );
  } else {
    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      messageType: "ai",
      content: response ?? orphanedPendingAssistantText,
      timestamp: new Date().toISOString(),
      structuredResult: structuredResult,
      sessionDetails: {
        duration_ms: durationMs,
        token_usage: tokenUsage,
      },
    };

    ctx.setChatFlowItems([
      ...ctx.getChatFlowItems(),
      {
        id: crypto.randomUUID(),
        type: "message",
        timestamp: new Date().toISOString(),
        data: assistantMessage,
      },
    ]);
  }

  ctx.setStreamingAssistantItemId(null);
  ctx.finalizeActiveExecutionPhaseChips("complete");
  ctx.resetEnrichmentPhaseTracking();

  const session = ctx.getSession();
  if (type === "final") {
    ctx.setLoading(false);
    if (session) {
      ctx.setSession({
        ...session,
        status: "completed",
        can_send_message: false,
        can_stage_message: false,
        queued_message_count: 0,
        is_active: false,
      });
    }
  } else if (session) {
    const continueWithQueuedMessages = queuedMessageCount > 0;
    ctx.setLoading(continueWithQueuedMessages);
    ctx.setSession({
      ...session,
      status: continueWithQueuedMessages ? "running" : "ready",
      can_send_message: !continueWithQueuedMessages,
      can_stage_message: continueWithQueuedMessages,
      queued_message_count: queuedMessageCount,
    });
  }
}

export function handleSessionEndOrError(
  ctx: SessionStoreContext,
  type: "session_end" | "error",
  eventData: Record<string, unknown>,
  helpers: TerminalEventHelpers,
) {
  ctx.flushPendingStreams();
  reconcileTerminalToolCards(ctx, type === "error" ? "failed" : "completed");
  const orphanedPendingAssistantText = helpers.consumePendingAssistantChunks(ctx);
  if (orphanedPendingAssistantText) {
    helpers.appendAssistantMessageChunk(ctx, orphanedPendingAssistantText);
    helpers.finalizeStreamingAssistantMessage(ctx);
  }
  ctx.setStreamingAssistantItemId(null);
  ctx.finalizeActiveExecutionPhaseChips(type === "error" ? "failed" : "complete");
  ctx.resetEnrichmentPhaseTracking();

  const session = ctx.getSession();
  if (session) {
    ctx.setSession({
      ...session,
      status: type === "error" ? "failed" : "completed",
      can_send_message: false,
      can_stage_message: false,
      queued_message_count: 0,
      is_active: false,
    });
  }
  if (type === "error") {
    const errorInfo = asRecord(eventData.error_info);
    ctx.setError(
      ((errorInfo?.message as string | undefined) ?? (eventData.error as string)) ||
        "Session error",
    );
  }
  ctx.setLoading(false);
}
