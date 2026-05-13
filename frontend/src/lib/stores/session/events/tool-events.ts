import type { ToolCard, ToolCardStatus, ToolType } from "$lib/types";

import { flushPendingAssistantChunksToTool } from "./assistant-events";
import { asRecord } from "./event-utils";
import type { SessionStoreContext } from "../types";

function resolveExistingToolCard(
  toolCards: Map<string, ToolCard>,
  rawToolId: string,
  toolType: ToolType,
  agentName: string | undefined,
  status: ToolCardStatus,
): { toolId: string; card: ToolCard | undefined } {
  // First: exact tool_id match. Each unique tool_id is its own card so that
  // multiple invocations of the same SDK agent render as separate cards.
  const direct = toolCards.get(rawToolId);
  if (direct) {
    return { toolId: rawToolId, card: direct };
  }

  // Lifecycle-gated fallback for agent-typed cards: a swarm_agent action
  // emits TWO different events that describe the SAME action — a tool_event
  // (tool.id = "swarm_tool_<agent>_<random>") and an agent_assignment
  // (assignment_id = "<action_uuid>"). Without this fallback the studio
  // would render two cards per action.
  //
  // Merge into the most-recent agent-typed card with the same agentName, but
  // ONLY when that card is still in flight. If the previous card has
  // completed/failed and this event is "executing", a NEW action is starting
  // — create a fresh card so supervisor_loop redeployments stay visible as
  // separate cards.
  if (toolType === "agent" && agentName) {
    let lastMatching: { id: string; card: ToolCard } | undefined;
    for (const [existingId, existing] of toolCards) {
      if (existing.toolType === "agent" && existing.agentName === agentName) {
        lastMatching = { id: existingId, card: existing };
      }
    }
    if (lastMatching) {
      const lastFinished =
        lastMatching.card.status === "completed" || lastMatching.card.status === "failed";
      const startingNew = status === "executing";
      if (!(lastFinished && startingNew)) {
        return { toolId: lastMatching.id, card: lastMatching.card };
      }
    }
  }

  return { toolId: rawToolId, card: undefined };
}

function createToolCard(
  toolId: string,
  toolName: string,
  toolType: ToolType,
  incomingArgs: Record<string, unknown>,
  agentName: string | undefined,
  swarmName: string | undefined,
): ToolCard {
  return {
    toolId,
    toolName,
    toolType,
    status: "pending",
    args: incomingArgs,
    startedAt: new Date().toISOString(),
    isStreaming: false,
    isSystemTool: false,
    agentName,
    swarmName,
  };
}

function appendToolCardToChatFlow(ctx: SessionStoreContext, card: ToolCard) {
  // Svelte 5 $state arrays fire reactivity on ``push``. Cloning the whole
  // ``chatFlowItems`` array on every new tool card was O(N) work for an
  // append the consumer can observe through the existing reference.
  ctx.getChatFlowItems().push({
    id: crypto.randomUUID(),
    type: "tool_card",
    timestamp: new Date().toISOString(),
    data: card,
  });
}

function buildUpdatedToolCard(
  card: ToolCard,
  status: ToolCardStatus,
  agentName: string | undefined,
  swarmName: string | undefined,
  incomingArgs: Record<string, unknown>,
  toolData: Record<string, unknown> | undefined,
  eventData: Record<string, unknown>,
): ToolCard {
  const mergedArgs =
    Object.keys(incomingArgs).length > 0 ? { ...(card.args ?? {}), ...incomingArgs } : card.args;
  const updatedCard: ToolCard = {
    ...card,
    status,
    agentName: card.agentName ?? agentName,
    swarmName: card.swarmName ?? swarmName,
    args: mergedArgs ?? card.args,
    isStreaming: status === "executing" ? card.isStreaming : false,
  };

  if (status === "completed") {
    updatedCard.result = toolData?.result ?? eventData.result;
    updatedCard.completedAt = new Date().toISOString();
  } else if (status === "failed") {
    updatedCard.error = (toolData?.error as string | undefined) ?? (eventData.error as string);
    updatedCard.completedAt = new Date().toISOString();
  }

  return updatedCard;
}

export function handleToolEvent(ctx: SessionStoreContext, eventData: Record<string, unknown>) {
  const toolData = asRecord(eventData.tool);
  const rawToolId = ((toolData?.id as string | undefined) ?? "").trim();
  if (!rawToolId) {
    return;
  }
  const toolName = (
    (toolData?.name as string | undefined) ??
    (eventData.tool_name as string | undefined) ??
    rawToolId
  ).trim();
  const status = ((toolData?.status as ToolCardStatus | undefined) ??
    (eventData.status as ToolCardStatus | undefined) ??
    "executing") as ToolCardStatus;
  const toolType = ((toolData?.type as ToolType | undefined) ??
    (eventData.tool_type as ToolType | undefined) ??
    "func") as ToolType;
  const agentName = eventData.agent_name as string | undefined;
  const swarmName = eventData.swarm_name as string | undefined;
  const incomingArgs = (asRecord(toolData?.args) as Record<string, unknown> | undefined) ?? {};

  const toolCards = ctx.getToolCards();

  // Get or create tool card
  const { toolId, card: existingCard } = resolveExistingToolCard(
    toolCards,
    rawToolId,
    toolType,
    agentName,
    status,
  );
  let card = existingCard;

  if (!card) {
    // Create new card
    card = createToolCard(toolId, toolName, toolType, incomingArgs, agentName, swarmName);

    toolCards.set(toolId, card);
    ctx.setToolCards(toolCards);

    // Add to chat flow
    appendToolCardToChatFlow(ctx, card);
  }

  const incomingAgentId =
    typeof incomingArgs.agent_id === "string" ? incomingArgs.agent_id : undefined;
  if (toolType === "agent" && incomingAgentId) {
    ctx.assistantIdToToolId.set(incomingAgentId, toolId);
    flushPendingAssistantChunksToTool(ctx, incomingAgentId, toolId);
  }

  // Update card status
  const updatedCard = buildUpdatedToolCard(
    card,
    status,
    agentName,
    swarmName,
    incomingArgs,
    toolData,
    eventData,
  );

  // Use batched update for performance
  ctx.batcher.scheduleUpdate(toolId, updatedCard);
}
