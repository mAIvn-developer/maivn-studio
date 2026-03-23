import type { InvocationConfig, MemoryConfig, Message, SendableMessageType } from "$lib/types";

import { buildInvocationMemoryConfig } from "../memory";
import type { SessionStoreContext } from "../types";

export function applyInterruptStatusUpdate(
  ctx: SessionStoreContext,
  interruptId: string,
  changes: Record<string, unknown>,
) {
  const result = ctx.interruptManager.updateStatus(interruptId, changes, ctx.getChatFlowItems());
  ctx.setInterruptCards(result.cards);
  ctx.setChatFlowItems(result.chatFlowItems);
  return result;
}

export function handleSessionStreamError(
  ctx: SessionStoreContext,
  getEventSource: () => EventSource | null,
  error: unknown,
) {
  console.error("SSE error:", error);
  const session = ctx.getSession();
  const status = session?.status;
  const hasTerminalStatus = status === "failed" || status === "completed" || status === "cancelled";

  // Preserve explicit backend errors and ignore expected close behavior.
  if (hasTerminalStatus || (ctx.getError() !== null && ctx.getError() !== "Connection lost")) {
    return;
  }

  // EventSource uses CONNECTING (0) while auto-retrying. Avoid surfacing
  // noisy transient reconnects as hard failures.
  const currentEs = getEventSource();
  if (currentEs?.readyState === 0 || status === "ready") {
    return;
  }

  ctx.setError("Connection lost");
}

export function markActiveToolCardsCancelled(ctx: SessionStoreContext) {
  const toolCards = ctx.getToolCards();
  for (const [toolId, card] of toolCards) {
    if (card.status === "executing" || card.status === "pending") {
      const updatedCard = {
        ...card,
        status: "failed" as const,
        error: "Cancelled by user",
        completedAt: new Date().toISOString(),
      };
      ctx.batcher.scheduleUpdate(toolId, updatedCard);
    }
  }
}

export function clearSessionRuntimeState(
  ctx: SessionStoreContext,
  resetEnrichmentTracking: () => void,
  clearMemoryIndexedToastTimer: () => void,
) {
  ctx.setChatFlowItems([]);
  ctx.setToolCards(new Map());
  ctx.setEvents([]);
  ctx.setRootAssistantId(null);
  ctx.setStreamingAssistantItemId(null);
  resetEnrichmentTracking();
  clearMemoryIndexedToastTimer();
  ctx.setMemoryIndexedToast(null);

  ctx.batcher.reset();
  ctx.assistantIdToToolId.clear();
  ctx.pendingAssistantChunks.clear();
  ctx.assistantSnapshots.clear();
}

export function appendUserMessageToChatFlow(
  ctx: SessionStoreContext,
  content: string,
  messageType: SendableMessageType,
  options?: {
    queuedForNextTurn?: boolean;
  },
) {
  const userMessage: Message = {
    id: crypto.randomUUID(),
    role: "user",
    messageType,
    content,
    timestamp: new Date().toISOString(),
    metadata: options?.queuedForNextTurn ? { queuedForNextTurn: true } : undefined,
  };

  ctx.setChatFlowItems([
    ...ctx.getChatFlowItems(),
    {
      id: crypto.randomUUID(),
      type: "message",
      timestamp: new Date().toISOString(),
      data: userMessage,
    },
  ]);
}

export function buildEffectiveInvocationConfig(
  invocationConfig: InvocationConfig,
  memoryConfig: MemoryConfig,
  memoryConfigBase: InvocationConfig["memory_config"] | undefined,
): InvocationConfig {
  const effectiveInvocation = { ...invocationConfig };
  effectiveInvocation.memory_config = buildInvocationMemoryConfig(memoryConfig, memoryConfigBase);
  return effectiveInvocation;
}
