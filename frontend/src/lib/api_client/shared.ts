import type { StructuredOutputConfig } from "../types";

export const API_BASE = "/api";

export function buildStructuredOutputPayload(
  config: StructuredOutputConfig | undefined,
): { enabled: true; tool_name: string; schema_name?: string; json_schema?: unknown } | undefined {
  if (!config?.enabled || !config.selectedTool) {
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
