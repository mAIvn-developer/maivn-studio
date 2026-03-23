import type { ChatFlowFilters, ChatFlowItem, EventSummary, Message, ToolCard } from "$lib/types";
import type { AccumulatedStats } from "./types";

function resolveAgentGroupKey(card: ToolCard): string | null {
  const rawAgentName = typeof card.agentName === "string" ? card.agentName.trim() : "";
  const rawToolName = typeof card.toolName === "string" ? card.toolName.trim() : "";
  const agentName = rawAgentName || (card.toolType === "agent" ? rawToolName : "");
  if (!agentName) {
    return null;
  }

  const swarmName = typeof card.swarmName === "string" ? card.swarmName.trim() : "";
  return `${swarmName}::${agentName}`;
}

function resolveGroupStatus(cards: ToolCard[]): ToolCard["status"] | null {
  if (cards.length === 0) {
    return null;
  }

  const controlCards = cards.filter((card) => card.toolType === "agent");
  const statusCards = controlCards.length > 0 ? controlCards : cards;

  if (statusCards.some((card) => card.status === "executing")) {
    return "executing";
  }
  if (statusCards.some((card) => card.status === "failed")) {
    return "failed";
  }
  if (statusCards.some((card) => card.status === "pending")) {
    return "pending";
  }
  if (statusCards.every((card) => card.status === "completed")) {
    return "completed";
  }

  return null;
}

// MARK: Event Summary

export function computeEventSummary(items: ChatFlowItem[]): EventSummary {
  let pendingTools = 0;
  let executingTools = 0;
  let completedTools = 0;
  let failedTools = 0;
  let pendingAgents = 0;
  let executingAgents = 0;
  let completedAgents = 0;
  let failedAgents = 0;
  let totalMessages = 0;
  const logicalAgentGroups = new Map<string, ToolCard[]>();

  for (const item of items) {
    if (item.type === "message") {
      totalMessages++;
    } else if (item.type === "tool_card") {
      const card = item.data as ToolCard;
      if (card.toolType !== "agent") {
        switch (card.status) {
          case "pending":
            pendingTools++;
            break;
          case "executing":
            executingTools++;
            break;
          case "completed":
            completedTools++;
            break;
          case "failed":
            failedTools++;
            break;
        }
      }

      const groupKey = resolveAgentGroupKey(card);
      if (groupKey) {
        const existing = logicalAgentGroups.get(groupKey) ?? [];
        existing.push(card);
        logicalAgentGroups.set(groupKey, existing);
      }
    }
  }

  for (const cards of logicalAgentGroups.values()) {
    const status = resolveGroupStatus(cards);
    switch (status) {
      case "pending":
        pendingAgents++;
        break;
      case "executing":
        executingAgents++;
        break;
      case "completed":
        completedAgents++;
        break;
      case "failed":
        failedAgents++;
        break;
    }
  }

  return {
    totalTools: pendingTools + executingTools + completedTools + failedTools,
    pendingTools,
    executingTools,
    completedTools,
    failedTools,
    totalAgents: pendingAgents + executingAgents + completedAgents + failedAgents,
    pendingAgents,
    executingAgents,
    completedAgents,
    failedAgents,
    totalMessages,
  };
}

// MARK: Filtering

export function filterChatFlowItems(
  items: ChatFlowItem[],
  filterOpts: ChatFlowFilters,
): ChatFlowItem[] {
  return items.filter((item) => {
    if (filterOpts.itemType === "messages" && item.type !== "message") return false;
    if (filterOpts.itemType === "tools" && item.type !== "tool_card") return false;

    if (item.type === "tool_card" && filterOpts.toolStatus !== "all") {
      const card = item.data as ToolCard;
      if (card.status !== filterOpts.toolStatus) return false;
    }

    return true;
  });
}

// MARK: Accumulated Stats

export function computeAccumulatedStats(items: ChatFlowItem[]): AccumulatedStats {
  const stats: AccumulatedStats = {
    totalDurationMs: 0,
    totalTokens: 0,
    inputTokens: 0,
    outputTokens: 0,
    reasoningTokens: 0,
    cacheReadTokens: 0,
    cacheCreationTokens: 0,
    sessionCount: 0,
  };

  for (const item of items) {
    if (item.type === "message") {
      const message = item.data as Message;
      if (message.role === "assistant" && message.sessionDetails) {
        stats.sessionCount++;
        if (message.sessionDetails.duration_ms !== undefined) {
          stats.totalDurationMs += message.sessionDetails.duration_ms;
        }
        if (message.sessionDetails.token_usage) {
          stats.totalTokens += message.sessionDetails.token_usage.total_tokens;
          stats.inputTokens += message.sessionDetails.token_usage.input_tokens;
          stats.outputTokens += message.sessionDetails.token_usage.output_tokens;
          stats.reasoningTokens += message.sessionDetails.token_usage.reasoning_tokens;
          stats.cacheReadTokens += message.sessionDetails.token_usage.cache_read_tokens;
          stats.cacheCreationTokens += message.sessionDetails.token_usage.cache_creation_tokens;
        }
      }
    }
  }

  return stats;
}
