import type { Message, ToolCard } from "$lib/types";

import { asRecord } from "./event-utils";
import type { SessionStoreContext } from "../types";

function resolveAgentToolIdByAssistantId(
  ctx: SessionStoreContext,
  assistantId: string,
): string | null {
  const mapped = ctx.assistantIdToToolId.get(assistantId);
  if (mapped && ctx.getToolCards().has(mapped)) {
    return mapped;
  }

  for (const [toolId, card] of ctx.getToolCards()) {
    if (card.toolType !== "agent") continue;
    const cardArgs = card.args as Record<string, unknown> | undefined;
    const cardAgentId = cardArgs?.agent_id;
    if (typeof cardAgentId === "string" && cardAgentId === assistantId) {
      ctx.assistantIdToToolId.set(assistantId, toolId);
      return toolId;
    }
  }

  return null;
}

function appendPendingAssistantChunk(ctx: SessionStoreContext, assistantId: string, text: string) {
  const existing = ctx.pendingAssistantChunks.get(assistantId) ?? "";
  ctx.pendingAssistantChunks.set(assistantId, existing + text);
}

function resolveAssistantChunkText(
  eventData: Record<string, unknown>,
): { assistantId: string; hasExplicitAssistantId: boolean; text: string } | null {
  const assistantData = asRecord(eventData.assistant);
  const assistantIdRaw = assistantData?.id ?? eventData.assistant_id;
  const hasExplicitAssistantId =
    typeof assistantIdRaw === "string" && assistantIdRaw.trim().length > 0;
  const assistantId = hasExplicitAssistantId ? assistantIdRaw.trim() : "assistant";

  const chunkText =
    (assistantData?.delta as string | undefined) ?? (eventData.text as string | undefined);
  if (typeof chunkText !== "string" || chunkText.length === 0) {
    return null;
  }

  return {
    assistantId,
    hasExplicitAssistantId,
    text: chunkText,
  };
}

export function consumePendingAssistantChunks(ctx: SessionStoreContext): string {
  if (ctx.pendingAssistantChunks.size === 0) {
    return "";
  }

  // If a nested assistant never gets mapped to a tool card before the turn
  // ends, fall back to a plain assistant message rather than dropping content.
  const combined = Array.from(ctx.pendingAssistantChunks.values()).join("");
  ctx.pendingAssistantChunks.clear();
  return combined;
}

function isFinalOutputAgentCard(card: ToolCard | undefined): boolean {
  if (!card || card.toolType !== "agent") return false;
  const cardArgs = card.args as Record<string, unknown> | undefined;
  return cardArgs?.use_as_final_output === true;
}

function createStreamingAssistantMessageItem() {
  const assistantMessage: Message = {
    id: crypto.randomUUID(),
    role: "assistant",
    messageType: "ai",
    content: "",
    timestamp: new Date().toISOString(),
    metadata: {
      isStreaming: true,
    },
  };

  const itemId = crypto.randomUUID();
  return {
    itemId,
    item: {
      id: itemId,
      type: "message" as const,
      timestamp: assistantMessage.timestamp,
      data: assistantMessage,
    },
  };
}

function ensureStreamingAssistantItemId(ctx: SessionStoreContext): string {
  const existingItemId = ctx.getStreamingAssistantItemId();
  if (existingItemId) {
    return existingItemId;
  }

  const { itemId, item } = createStreamingAssistantMessageItem();
  ctx.setStreamingAssistantItemId(itemId);
  ctx.setChatFlowItems([...ctx.getChatFlowItems(), item]);
  return itemId;
}

function updateStreamingAssistantMessage(
  ctx: SessionStoreContext,
  targetItemId: string,
  updater: (message: Message) => Message,
) {
  ctx.setChatFlowItems(
    ctx.getChatFlowItems().map((item) => {
      if (item.id !== targetItemId || item.type !== "message") {
        return item;
      }

      const msg = item.data as Message;
      return {
        ...item,
        data: updater(msg),
      };
    }),
  );
}

export function appendAssistantMessageChunk(ctx: SessionStoreContext, text: string) {
  const targetItemId = ensureStreamingAssistantItemId(ctx);
  updateStreamingAssistantMessage(ctx, targetItemId, (msg) => ({
    ...msg,
    content: (msg.content ?? "") + text,
    metadata: {
      ...(msg.metadata ?? {}),
      isStreaming: true,
    },
  }));
}

export function finalizeStreamingAssistantMessage(ctx: SessionStoreContext) {
  const streamingAssistantItemId = ctx.getStreamingAssistantItemId();
  if (!streamingAssistantItemId) {
    return;
  }

  updateStreamingAssistantMessage(ctx, streamingAssistantItemId, (msg) => ({
    ...msg,
    metadata: {
      ...(msg.metadata ?? {}),
      isStreaming: false,
    },
  }));
}

function appendChunkToAgentTool(ctx: SessionStoreContext, toolId: string, text: string) {
  const existing = ctx.getToolCards().get(toolId);
  if (existing) {
    const updatedCard: ToolCard = {
      ...existing,
      isStreaming: true,
      status: existing.status === "pending" ? "executing" : existing.status,
    };
    ctx.batcher.scheduleUpdate(toolId, updatedCard);
    ctx.batcher.appendStreamContent(toolId, text, ctx.getToolCards());

    if (isFinalOutputAgentCard(existing)) {
      appendAssistantMessageChunk(ctx, text);
    }
  }
}

export function flushPendingAssistantChunksToTool(
  ctx: SessionStoreContext,
  assistantId: string,
  toolId: string,
) {
  const pendingText = ctx.pendingAssistantChunks.get(assistantId);
  if (!pendingText) {
    return;
  }

  ctx.pendingAssistantChunks.delete(assistantId);
  appendChunkToAgentTool(ctx, toolId, pendingText);
}

function shouldAppendToRootAssistant(
  ctx: SessionStoreContext,
  assistantId: string,
  hasExplicitAssistantId: boolean,
): boolean {
  // When a nested agent is executing inside a swarm, its assistant text
  // should NOT be promoted to a root message — hold as pending until the
  // agent completes or the mapping is established.  This check must happen
  // BEFORE the rootAssistantId match to prevent session_start from
  // pre-setting a root ID that bypasses the gate.
  const hasExecutingAgentCards = Array.from(ctx.getToolCards().values()).some(
    (card) => card.toolType === "agent" && card.status !== "completed" && card.status !== "failed",
  );

  if (hasExecutingAgentCards) {
    return false;
  }

  const rootAssistantId = ctx.getRootAssistantId();
  if (rootAssistantId && assistantId === rootAssistantId) {
    return true;
  }

  if (!hasExplicitAssistantId || assistantId === "assistant") {
    if (!rootAssistantId) {
      ctx.setRootAssistantId(assistantId);
    }
    return true;
  }

  if (!rootAssistantId) {
    ctx.setRootAssistantId(assistantId);
    return true;
  }

  return false;
}

export function handleAssistantChunk(ctx: SessionStoreContext, eventData: Record<string, unknown>) {
  const chunk = resolveAssistantChunkText(eventData);
  if (!chunk) {
    return;
  }
  const { assistantId, hasExplicitAssistantId, text } = chunk;

  const agentToolId = resolveAgentToolIdByAssistantId(ctx, assistantId);

  if (agentToolId) {
    flushPendingAssistantChunksToTool(ctx, assistantId, agentToolId);
    appendChunkToAgentTool(ctx, agentToolId, text);
    return;
  }

  if (shouldAppendToRootAssistant(ctx, assistantId, hasExplicitAssistantId)) {
    appendAssistantMessageChunk(ctx, text);
    return;
  }

  appendPendingAssistantChunk(ctx, assistantId, text);
}
