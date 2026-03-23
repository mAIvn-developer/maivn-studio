import type { ToolCard, ToolCardStatus } from "$lib/types";

import { flushPendingAssistantChunksToTool } from "./assistant-events";
import { asRecord, readScopeValue } from "./event-utils";
import type { SessionStoreContext } from "../types";

export function handleAgentAssignment(
  ctx: SessionStoreContext,
  eventData: Record<string, unknown>,
) {
  // Create a tool card for agent assignment tracking
  const assignmentData = asRecord(eventData.assignment);
  const agentName = (
    (assignmentData?.agent_name as string | undefined) ??
    (eventData.agent_name as string | undefined)
  )?.trim();
  if (!agentName) return;

  const statusRaw = (
    (assignmentData?.status as string | undefined) ??
    (eventData.status as string | undefined) ??
    "in_progress"
  ).toLowerCase();
  const resolvedStatus: ToolCardStatus =
    statusRaw === "completed" || statusRaw === "success"
      ? "completed"
      : statusRaw === "failed" || statusRaw === "error"
        ? "failed"
        : "executing";

  let assignmentId =
    (assignmentData?.id as string | undefined) ??
    (eventData.assignment_id as string | undefined) ??
    "";
  if (!assignmentId) {
    assignmentId = `agent:${agentName}`;
  }

  const toolCards = ctx.getToolCards();
  let card = toolCards.get(assignmentId);
  if (!card) {
    for (const [toolId, existing] of toolCards) {
      if (existing.toolType === "agent" && existing.agentName === agentName) {
        assignmentId = toolId;
        card = existing;
        break;
      }
    }
  }

  const swarmName =
    (assignmentData?.swarm_name as string | undefined) ??
    (eventData.swarm_name as string | undefined) ??
    (readScopeValue(eventData, "name") as string | undefined);
  const errorMessage =
    (assignmentData?.error as string | undefined) ?? (eventData.error as string | undefined);
  const assignmentResult = assignmentData?.result ?? eventData.result;
  const resultRecord =
    assignmentResult && typeof assignmentResult === "object"
      ? (assignmentResult as Record<string, unknown>)
      : null;
  const nestedAssistantId =
    resultRecord && typeof resultRecord.assistant_id === "string"
      ? resultRecord.assistant_id
      : null;

  if (!card) {
    card = {
      toolId: assignmentId,
      toolName: `Agent: ${agentName}`,
      toolType: "agent",
      status: resolvedStatus,
      args: {},
      startedAt: new Date().toISOString(),
      isStreaming: false,
      isSystemTool: false,
      agentName,
      swarmName,
      error: resolvedStatus === "failed" ? (errorMessage ?? "Agent failed") : undefined,
      result: resolvedStatus === "completed" ? assignmentResult : undefined,
    };

    toolCards.set(assignmentId, card);
    ctx.setToolCards(toolCards);
    if (nestedAssistantId) {
      ctx.assistantIdToToolId.set(nestedAssistantId, assignmentId);
      flushPendingAssistantChunksToTool(ctx, nestedAssistantId, assignmentId);
    }

    ctx.setChatFlowItems([
      ...ctx.getChatFlowItems(),
      {
        id: crypto.randomUUID(),
        type: "tool_card",
        timestamp: new Date().toISOString(),
        data: card,
      },
    ]);
  } else {
    const pendingText =
      resolvedStatus === "completed" || resolvedStatus === "failed"
        ? ctx.batcher.drainStreamContent(assignmentId)
        : "";

    const updatedCard: ToolCard = {
      ...card,
      status: resolvedStatus,
      isStreaming: resolvedStatus === "executing",
      completedAt:
        resolvedStatus === "completed" || resolvedStatus === "failed"
          ? new Date().toISOString()
          : undefined,
      swarmName: swarmName ?? card.swarmName,
      error:
        resolvedStatus === "failed" ? (errorMessage ?? card.error ?? "Agent failed") : undefined,
      result: resolvedStatus === "completed" ? (assignmentResult ?? card.result) : card.result,
      streamContent: (card.streamContent ?? "") + pendingText,
    };

    if (nestedAssistantId) {
      ctx.assistantIdToToolId.set(nestedAssistantId, assignmentId);
      flushPendingAssistantChunksToTool(ctx, nestedAssistantId, assignmentId);
    }

    ctx.batcher.scheduleUpdate(assignmentId, updatedCard);
  }
}
