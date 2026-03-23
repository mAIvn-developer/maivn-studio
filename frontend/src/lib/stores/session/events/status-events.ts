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
      },
    },
  ]);
}
