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
    // Defensive: server should always supply a unique action_id per swarm
    // invocation, but if it ever omits one we mint a per-event UUID rather
    // than a name-based key. A name-based fallback would collapse every
    // invocation of the same SDK agent into one card — supervisor_loop runs
    // that redeploy `coding_agent` would all merge into a single card.
    assignmentId = `agent:${agentName}:${crypto.randomUUID()}`;
  }

  const toolCards = ctx.getToolCards();
  let card = toolCards.get(assignmentId);

  // For swarm_agent invocations the server emits TWO events per action: a
  // tool_event (tool.id = "swarm_tool_<agent>_<random>") and an
  // agent_assignment (assignment_id = "<action_uuid>"). They describe the
  // SAME action with different identifiers, so without a correlation key we
  // would render two cards per action.
  //
  // To merge them into one card, fall back to the most-recent agent-typed
  // tool card with the same agentName when assignmentId doesn't match
  // anything. The fallback is gated on action lifecycle so it does NOT
  // collapse two SEPARATE invocations of the same agent (supervisor_loop
  // redeployments) into one card:
  //
  //   * If the most-recent matching card is still executing/pending, this
  //     event must belong to the same in-flight action — merge.
  //   * If that card is already completed/failed AND this event is
  //     "executing", a fresh action is starting — do NOT merge; create a
  //     new card.
  //   * If the matching card is completed/failed AND this event is also
  //     completed/failed, treat it as an idempotent re-emit for the same
  //     action — merge.
  if (!card && agentName) {
    let lastMatching: ToolCard | undefined;
    for (const existing of toolCards.values()) {
      if (existing.toolType === "agent" && existing.agentName === agentName) {
        lastMatching = existing;
      }
    }
    if (lastMatching) {
      const lastFinished = lastMatching.status === "completed" || lastMatching.status === "failed";
      const startingNew = resolvedStatus === "executing";
      if (!(lastFinished && startingNew)) {
        assignmentId = lastMatching.toolId;
        card = lastMatching;
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

  if (!card && !swarmName && !nestedAssistantId) {
    return;
  }

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
