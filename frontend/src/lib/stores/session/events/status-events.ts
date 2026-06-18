import { asRecord } from "./event-utils";
import type { SessionStoreContext } from "../types";

export function readStatusMessageText(eventData: Record<string, unknown>): string | undefined {
  const nestedStatus = asRecord(eventData.status);
  if (typeof nestedStatus?.message === "string") {
    return nestedStatus.message;
  }
  if (typeof eventData.message === "string") {
    return eventData.message;
  }
  return undefined;
}

export function commitStatusMessage(ctx: SessionStoreContext, text: string) {
  const ts = new Date().toISOString();
  ctx.setChatFlowItems([
    ...ctx.getChatFlowItems(),
    {
      id: crypto.randomUUID(),
      type: "message",
      timestamp: ts,
      data: {
        id: crypto.randomUUID(),
        role: "assistant" as const,
        messageType: "status" as const,
        content: text,
        timestamp: ts,
        metadata: {
          isStreaming: false,
        },
      },
    },
  ]);
}

function readText(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function readStatusChunk(eventData: Record<string, unknown>): {
  statusId: string;
  text: string;
  replaceContent: boolean;
  final: boolean;
} | null {
  const statusData = asRecord(eventData.status);
  const assistantData = asRecord(eventData.assistant);
  const assistantId =
    readText(eventData.assistant_id)?.trim() || readText(assistantData?.id)?.trim() || "assistant";
  const statusId =
    readText(eventData.status_id)?.trim() ||
    readText(statusData?.id)?.trim() ||
    `status:${assistantId}`;
  const text = readText(eventData.text) ?? readText(statusData?.delta) ?? "";
  const replaceContent = eventData.replace_content === true || statusData?.replace_content === true;
  const final =
    eventData.final === true ||
    eventData.is_final === true ||
    eventData.done === true ||
    statusData?.final === true ||
    statusData?.is_final === true ||
    statusData?.done === true;

  if (!statusId || (!text && !final)) {
    return null;
  }

  return { statusId, text, replaceContent, final };
}

function createStreamingStatusMessage(ctx: SessionStoreContext, statusId: string): string {
  const existingItemId = ctx.statusMessageItemIds.get(statusId);
  if (existingItemId) {
    return existingItemId;
  }

  const ts = new Date().toISOString();
  const itemId = crypto.randomUUID();
  ctx.statusMessageItemIds.set(statusId, itemId);
  ctx.setChatFlowItems([
    ...ctx.getChatFlowItems(),
    {
      id: itemId,
      type: "message",
      timestamp: ts,
      data: {
        id: crypto.randomUUID(),
        role: "assistant",
        messageType: "status",
        content: "",
        timestamp: ts,
        metadata: {
          isStreaming: true,
        },
      },
    },
  ]);
  return itemId;
}

export function handleStatusMessageChunk(
  ctx: SessionStoreContext,
  eventData: Record<string, unknown>,
) {
  const chunk = readStatusChunk(eventData);
  if (!chunk) {
    return;
  }

  const itemId = createStreamingStatusMessage(ctx, chunk.statusId);
  ctx.setChatFlowItems(
    ctx.getChatFlowItems().map((item) => {
      if (item.id !== itemId || item.type !== "message") {
        return item;
      }

      const nextContent = chunk.replaceContent
        ? chunk.text
        : `${item.data.content ?? ""}${chunk.text}`;
      return {
        ...item,
        data: {
          ...item.data,
          content: nextContent,
          metadata: {
            ...(item.data.metadata ?? {}),
            isStreaming: !chunk.final,
          },
        },
      };
    }),
  );

  if (chunk.final) {
    ctx.statusMessageItemIds.delete(chunk.statusId);
  }
}

export function completeStreamingStatusMessage(
  ctx: SessionStoreContext,
  eventData: Record<string, unknown>,
): boolean {
  const statusData = asRecord(eventData.status);
  const statusId = readText(eventData.status_id)?.trim() || readText(statusData?.id)?.trim();
  if (!statusId || !ctx.statusMessageItemIds.has(statusId)) {
    return false;
  }

  const text = readStatusMessageText(eventData) ?? "";
  handleStatusMessageChunk(ctx, {
    ...eventData,
    status_id: statusId,
    text,
    replace_content: true,
    final: true,
  });
  return true;
}
