export function asRecord(value: unknown): Record<string, unknown> | undefined {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return undefined;
}

export function readScopeValue(
  eventData: Record<string, unknown>,
  key: "id" | "name" | "type",
): unknown {
  return asRecord(eventData.scope)?.[key];
}
