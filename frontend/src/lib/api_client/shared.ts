import type { StructuredOutputConfig } from "../types";

export const API_BASE = "/api";

export function buildStructuredOutputPayload(
  config: StructuredOutputConfig | undefined,
):
  | { enabled: true; tool_name?: string; schema_name?: string; json_schema?: unknown }
  | undefined {
  // Send the intent whenever the toggle is on. Previously this returned
  // undefined unless a schema source was hand-picked, so flipping the switch
  // without opening the selector silently ran the normal (synthesizing) path.
  // When no tool is chosen the backend auto-resolves the app's final model tool.
  if (!config?.enabled) {
    return undefined;
  }

  return {
    enabled: true,
    tool_name: config.selectedTool,
    schema_name: config.schema?.name,
    json_schema: config.schema?.schema,
  };
}

export async function extractErrorDetail(response: Response, fallback: string): Promise<string> {
  const clone = response.clone();
  const errorData = await response.json().catch(() => null);

  if (errorData && typeof errorData === "object") {
    if ("detail" in errorData && typeof errorData.detail === "string" && errorData.detail.trim()) {
      return errorData.detail;
    }
    if (
      "message" in errorData &&
      typeof errorData.message === "string" &&
      errorData.message.trim()
    ) {
      return errorData.message;
    }
  }

  const raw = await clone.text().catch(() => "");
  return raw.trim() || fallback;
}
