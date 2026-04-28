import { describe, expect, it } from "vitest";

import type { BatchResult, ChatFlowItem, Message } from "$lib/types";
import { buildExchanges } from "./chat-exchanges";

describe("buildExchanges", () => {
  it("groups batch results with the originating user message", () => {
    const userMessage: Message = {
      id: "user-1",
      role: "user",
      messageType: "human",
      content: "1. alpha\n2. beta",
      timestamp: "2026-01-01T00:00:00.000Z",
    };
    const batchResult: BatchResult = {
      batchId: "batch-1",
      mode: "abatch",
      status: "completed",
      itemCount: 2,
      asyncMode: true,
      startedAt: "2026-01-01T00:00:01.000Z",
      completedAt: "2026-01-01T00:00:02.000Z",
      items: [
        { index: 0, input: "alpha", status: "completed", response: "done alpha" },
        { index: 1, input: "beta", status: "completed", response: "done beta" },
      ],
    };
    const items: ChatFlowItem[] = [
      {
        id: "flow-user",
        type: "message",
        timestamp: userMessage.timestamp,
        data: userMessage,
      },
      {
        id: "flow-batch",
        type: "batch_result",
        timestamp: batchResult.completedAt ?? batchResult.startedAt,
        data: batchResult,
      },
    ];

    const exchanges = buildExchanges(items);

    expect(exchanges).toHaveLength(1);
    expect(exchanges[0].humanMessage).toBe(userMessage);
    expect(exchanges[0].batchResults).toEqual([batchResult]);
    expect(exchanges[0].aiMessage).toBeNull();
  });
});
