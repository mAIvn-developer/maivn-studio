import { ToolCardBatcher } from "../utils/toolCardBatcher";

interface CreateSessionBatcherRuntimeParams {
  batcher: ToolCardBatcher;
  getToolCards: () => Map<string, import("$lib/types").ToolCard>;
  setToolCards: (cards: Map<string, import("$lib/types").ToolCard>) => void;
  getChatFlowItems: () => import("$lib/types").ChatFlowItem[];
  setChatFlowItems: (items: import("$lib/types").ChatFlowItem[]) => void;
}

export function createSessionBatcherRuntime(params: CreateSessionBatcherRuntimeParams) {
  params.batcher.setFlushCallback(() => {
    const updates = params.batcher.drainPendingUpdates();
    if (updates.size === 0) return;

    const nextToolCards = params.getToolCards();
    for (const [toolId, card] of updates) {
      nextToolCards.set(toolId, card);
    }

    params.setToolCards(new Map(nextToolCards));
    params.setChatFlowItems(
      ToolCardBatcher.applyChatFlowUpdates(params.getChatFlowItems(), updates),
    );
  });

  function flushPendingStreams() {
    const currentToolCards = params.getToolCards();
    const directUpdates = params.batcher.flushAllPendingStreams(currentToolCards);
    params.setToolCards(new Map(currentToolCards));
    if (directUpdates.size > 0) {
      params.setChatFlowItems(
        ToolCardBatcher.applyChatFlowUpdates(params.getChatFlowItems(), directUpdates),
      );
    }
  }

  return {
    flushPendingStreams,
  };
}
