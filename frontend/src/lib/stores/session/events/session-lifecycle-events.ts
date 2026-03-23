import type { ChatFlowItem, Message } from "$lib/types";

import type { SessionStoreContext } from "../types";

export function clearQueuedUserMessageFlags(
  items: ChatFlowItem[],
  consumedCount: number,
): ChatFlowItem[] {
  if (consumedCount <= 0) return items;

  let remaining = consumedCount;
  return items.map((item) => {
    if (remaining <= 0 || item.type !== "message") {
      return item;
    }

    const message = item.data as Message;
    if (message.role !== "user" || message.metadata?.queuedForNextTurn !== true) {
      return item;
    }

    remaining -= 1;
    const metadata = { ...(message.metadata ?? {}) };
    delete metadata.queuedForNextTurn;

    return {
      ...item,
      data: {
        ...message,
        metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
      },
    };
  });
}

export function handleSessionStart(ctx: SessionStoreContext, eventData: Record<string, unknown>) {
  const consumedQueuedMessageCount =
    typeof eventData.consumed_queued_message_count === "number"
      ? eventData.consumed_queued_message_count
      : 0;
  const assistantId =
    typeof eventData.assistant_id === "string" && eventData.assistant_id.trim()
      ? eventData.assistant_id.trim()
      : null;
  const session = ctx.getSession();

  const shouldBeginTurn = assistantId
    ? assistantId !== ctx.getRootAssistantId()
    : session?.status !== "running";
  if (shouldBeginTurn) {
    ctx.interruptManager.beginTurn();
    ctx.assistantSnapshots.clear();
  }

  if (consumedQueuedMessageCount > 0) {
    ctx.setChatFlowItems(
      clearQueuedUserMessageFlags(ctx.getChatFlowItems(), consumedQueuedMessageCount),
    );
  }

  if (assistantId) {
    ctx.setRootAssistantId(assistantId);
  }

  if (session) {
    ctx.setSession({
      ...session,
      status: "running",
      can_send_message: false,
      can_stage_message: true,
      queued_message_count:
        typeof eventData.queued_message_count === "number"
          ? eventData.queued_message_count
          : session.queued_message_count,
    });
  }
  ctx.setLoading(true);
}
