import type { MemoryActivityData } from "$lib/types";

export function formatMemoryIndexedToastDetails(details?: MemoryActivityData): string {
  if (!details) return "";

  const parts: string[] = [];
  if (typeof details.extractedCount === "number") {
    parts.push(`${details.extractedCount} extracted`);
  }
  if (typeof details.persistedCount === "number") {
    parts.push(`${details.persistedCount} persisted`);
  }
  if (typeof details.vectorRows === "number") {
    parts.push(`${details.vectorRows} vectors`);
  }
  if (typeof details.graphEdges === "number") {
    parts.push(`${details.graphEdges} graph edges`);
  }
  if (typeof details.latencyMs === "number") {
    parts.push(`${details.latencyMs} ms`);
  }

  return parts.join(" | ");
}
