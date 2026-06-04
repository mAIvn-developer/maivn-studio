import type { Message, ToolCard as ToolCardType } from "$lib/types";

export function hasAiTextResponse(aiMessage: Message | null): boolean {
  return !!(aiMessage && aiMessage.content && aiMessage.content.trim());
}

function isMetadataOnlyResponseEnvelope(value: unknown): boolean {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record);
  if (keys.length === 0) return false;

  const internalKeys = new Set([
    "action_id",
    "status",
    "assistant_id",
    "responses",
    "response",
    "response_text",
    "final_response_text",
    "error",
    "result",
    "token_usage",
    "detailed_token_usage",
    "metadata",
  ]);
  if (!keys.every((key) => internalKeys.has(key))) return false;

  const resultValue = record.result;
  const hasNoStructuredResult =
    resultValue == null ||
    (typeof resultValue === "object" &&
      !Array.isArray(resultValue) &&
      Object.keys(resultValue as Record<string, unknown>).length === 0);
  return hasNoStructuredResult;
}

export function getFinalStructuredResult(
  aiMessage: Message | null,
  toolCards: ToolCardType[],
): unknown {
  if (aiMessage?.structuredResult !== undefined && aiMessage.structuredResult !== null) {
    if (!isMetadataOnlyResponseEnvelope(aiMessage.structuredResult)) {
      return aiMessage.structuredResult;
    }
    return null;
  }

  if (hasAiTextResponse(aiMessage)) {
    return null;
  }

  const completedTools = toolCards.filter((tool) => tool.status === "completed");
  if (completedTools.length === 0) return null;

  for (let index = completedTools.length - 1; index >= 0; index -= 1) {
    const candidate = completedTools[index]?.result;
    if (candidate === undefined) continue;
    if (isMetadataOnlyResponseEnvelope(candidate)) continue;
    return candidate;
  }

  return null;
}

export function getStructuredOutputPayload(
  finalResult: unknown,
  toolsWithResults: ToolCardType[],
): unknown {
  if (finalResult) return finalResult;
  if (toolsWithResults.length > 0) {
    return toolsWithResults[toolsWithResults.length - 1]?.result;
  }
  return null;
}
