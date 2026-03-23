import type { ToolCard, ToolCardStatus, ToolType } from "$lib/types";

import { flushPendingAssistantChunksToTool } from "./assistant-events";
import { asRecord } from "./event-utils";
import type { SessionStoreContext } from "../types";

function resolveExistingToolCard(
  toolCards: Map<string, ToolCard>,
  rawToolId: string,
  toolType: ToolType,
  agentName: string | undefined,
): { toolId: string; card: ToolCard | undefined } {
  let toolId = rawToolId;
  let card = toolCards.get(toolId);

  if (!card && toolType === "agent" && agentName) {
    for (const [existingId, existing] of toolCards) {
      if (existing.toolType === "agent" && existing.agentName === agentName) {
        toolId = existingId;
        card = existing;
        break;
      }
    }
  }

  return { toolId, card };
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
  ctx.setChatFlowItems([
    ...ctx.getChatFlowItems(),
    {
      id: crypto.randomUUID(),
      type: "tool_card",
      timestamp: new Date().toISOString(),
      data: card,
    },
  ]);
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
