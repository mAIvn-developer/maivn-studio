import type { ToolCard } from "$lib/types";

import { asRecord } from "./event-utils";
import type { SessionStoreContext } from "../types";

export function handleSystemToolStart(
  ctx: SessionStoreContext,
  eventData: Record<string, unknown>,
) {
  const toolData = asRecord(eventData.tool);
  const toolId = ((toolData?.id as string | undefined) ?? "").trim();
  if (!toolId) {
    return;
  }
  // `system_tool_start` arrives here after ingress normalization. At this
  // point `tool.name` and `eventData.tool_type` carry the specific normalized
  // system tool label (for example `reevaluate` or `compose_artifact`).
  // Do not switch this to `tool.type`: normalized events intentionally set
  // `tool.type` to the generic card type `system`, which would lose the real
  // tool name and break checks like the `reevaluate` skip below.
  const toolName = (
    (toolData?.name as string | undefined) ??
    (eventData.tool_type as string | undefined) ??
    "system"
  ).trim();
  const agentName = eventData.agent_name as string | undefined;
  const swarmName = eventData.swarm_name as string | undefined;
  const incomingArgs = (asRecord(toolData?.args) as Record<string, unknown> | undefined) ?? {};

  // Skip creating tool cards for reevaluate system tool
  if (toolName === "reevaluate") {
    return;
  }

  const toolCards = ctx.getToolCards();
  const existingCard = toolCards.get(toolId);
  if (existingCard) {
    const mergedArgs =
      Object.keys(incomingArgs).length > 0
        ? { ...(existingCard.args ?? {}), ...incomingArgs }
        : existingCard.args;
    const updatedCard: ToolCard = {
      ...existingCard,
      toolName: existingCard.toolName || toolName,
      status:
        existingCard.status === "completed" || existingCard.status === "failed"
          ? existingCard.status
          : "executing",
      args: mergedArgs ?? existingCard.args,
      isStreaming:
        existingCard.status === "completed" || existingCard.status === "failed"
          ? existingCard.isStreaming
          : true,
      agentName: existingCard.agentName ?? agentName,
      swarmName: existingCard.swarmName ?? swarmName,
    };

    toolCards.set(toolId, updatedCard);
    ctx.setToolCards(toolCards);
    ctx.batcher.scheduleUpdate(toolId, updatedCard);
    return;
  }

  const card: ToolCard = {
    toolId,
    toolName,
    toolType: "system",
    status: "executing",
    args: incomingArgs,
    startedAt: new Date().toISOString(),
    isStreaming: true,
    streamContent: "",
    isSystemTool: true,
    agentName,
    swarmName,
  };

  toolCards.set(toolId, card);
  ctx.setToolCards(toolCards);

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

export function handleSystemToolChunk(
  ctx: SessionStoreContext,
  eventData: Record<string, unknown>,
) {
  const toolId = ((asRecord(eventData.tool)?.id as string | undefined) ?? "").trim();
  if (!toolId) {
    return;
  }
  const text =
    (asRecord(eventData.chunk)?.text as string | undefined) ??
    (eventData.text as string | undefined) ??
    "";
  if (text.length === 0) {
    return;
  }

  // Skip if tool card doesn't exist (e.g., reevaluate was filtered out)
  if (!ctx.getToolCards().has(toolId)) {
    return;
  }

  // Use debounced update for streaming content
  ctx.batcher.appendStreamContent(toolId, text, ctx.getToolCards());

  // Do not mirror system tool streaming into assistant output.
  // System tools (e.g. think/repl/web_search) should remain in tool cards only.
}

export function handleSystemToolComplete(
  ctx: SessionStoreContext,
  eventData: Record<string, unknown>,
) {
  const toolId = ((asRecord(eventData.tool)?.id as string | undefined) ?? "").trim();
  if (!toolId) {
    return;
  }

  // Skip if tool card doesn't exist (e.g., reevaluate was filtered out)
  if (!ctx.getToolCards().has(toolId)) {
    return;
  }

  // Flush any pending stream content first
  const pendingText = ctx.batcher.drainStreamContent(toolId);

  const card = ctx.getToolCards().get(toolId);
  if (card) {
    const updatedCard: ToolCard = {
      ...card,
      status: "completed",
      completedAt: new Date().toISOString(),
      result: asRecord(eventData.tool)?.result ?? eventData.result,
      isStreaming: false,
      streamContent: (card.streamContent ?? "") + pendingText,
    };

    ctx.batcher.scheduleUpdate(toolId, updatedCard);
  }
}
