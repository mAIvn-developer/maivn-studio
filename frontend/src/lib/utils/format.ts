/**
 * Shared formatting utilities used across multiple components.
 * Extracted from EventPanel, MessageCard, ExchangeContainer, and ToolCard.
 */

export function formatDuration(ms: number): string {
  if (ms >= 60000) {
    const mins = Math.floor(ms / 60000);
    const secs = ((ms % 60000) / 1000).toFixed(1);
    return `${mins}m ${secs}s`;
  }
  return (ms / 1000).toFixed(1) + "s";
}

export function formatTokens(count: number): string {
  return count.toLocaleString();
}

export function formatValue(value: unknown, truncate: boolean = true): string {
  if (value === undefined || value === null) return "null";
  if (typeof value === "string") {
    if (!truncate) return value;
    return value.length > 200 ? value.slice(0, 200) + "..." : value;
  }
  const str = JSON.stringify(value, null, 2);
  if (!truncate) return str;
  return str.length > 400 ? str.slice(0, 400) + "..." : str;
}

export function isValueTruncated(value: unknown): boolean {
  if (value === undefined || value === null) return false;
  if (typeof value === "string") {
    return value.length > 200;
  }
  const str = JSON.stringify(value, null, 2);
  return str.length > 400;
}

export function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTimeWithSeconds(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString();
}
