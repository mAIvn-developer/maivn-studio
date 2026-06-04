import type { ToolCard as ToolCardType } from "$lib/types";

function extractAgentResponse(result: unknown, depth = 0): string | null {
  if (depth > 4 || result === null || result === undefined) {
    return null;
  }

  if (typeof result === "string") {
    const trimmed = result.trim();
    return trimmed ? trimmed : null;
  }

  if (Array.isArray(result)) {
    for (const entry of result) {
      const resolved = extractAgentResponse(entry, depth + 1);
      if (resolved) return resolved;
    }
    return null;
  }

  if (result && typeof result === "object") {
    const record = result as Record<string, unknown>;
    const responses = record.responses;
    if (Array.isArray(responses)) {
      for (let i = responses.length - 1; i >= 0; i -= 1) {
        const item = responses[i];
        if (typeof item === "string") {
          const trimmed = item.trim();
          if (trimmed) {
            return trimmed;
          }
        }
      }
    }
    const response = record.response;
    if (typeof response === "string") {
      const trimmed = response.trim();
      return trimmed ? trimmed : null;
    }

    const nestedKeys = [
      "result",
      "results",
      "final_state",
      "structured_result",
      "primary_response",
    ];
    for (const key of nestedKeys) {
      if (key in record) {
        const resolved = extractAgentResponse(record[key], depth + 1);
        if (resolved) return resolved;
      }
    }
  }

  return null;
}

function sanitizeAgentResponseText(text: string | null): string | null {
  if (!text) return null;
  const trimmed = text.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith("Structured result summary:")) {
    return null;
  }
  return trimmed;
}

export function isAgentFinalOutput(invocation: ToolCardType | null): boolean {
  const args = invocation?.args;
  if (!args || typeof args !== "object") return false;
  return Boolean((args as Record<string, unknown>).use_as_final_output);
}

export function getAgentResponse(invocation: ToolCardType | null): string | null {
  if (!invocation) return null;

  if (invocation.status === "failed") {
    return invocation.error ? `Agent failed: ${invocation.error}` : "Agent failed.";
  }

  if (isAgentFinalOutput(invocation)) {
    return "See final output";
  }

  if (invocation.status === "completed") {
    const finalized = sanitizeAgentResponseText(extractAgentResponse(invocation.result)) ?? null;
    if (finalized) {
      return finalized;
    }
  }

  const streamed =
    typeof invocation.streamContent === "string" && invocation.streamContent.trim()
      ? invocation.streamContent
      : null;
  if (streamed) {
    return streamed;
  }

  if (invocation.status !== "completed") {
    return "Awaiting agent response...";
  }

  return (
    sanitizeAgentResponseText(extractAgentResponse(invocation.result)) ?? "No response available."
  );
}
