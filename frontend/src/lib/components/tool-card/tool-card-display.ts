import type { ToolCard, ToolCardStatus, ToolType } from "$lib/types";

export interface ToolTypeDisplayConfig {
  label: string;
  color: string;
  bg: string;
}

export interface ToolStatusDisplayConfig {
  color: string;
  bg: string;
}

const toolTypeConfig: Record<ToolType, ToolTypeDisplayConfig> = {
  func: {
    label: "FUNC",
    color: "#A78BFA",
    bg: "rgba(167, 139, 250, 0.15)",
  },
  model: {
    label: "MODEL",
    color: "#34D399",
    bg: "rgba(52, 211, 153, 0.15)",
  },
  mcp: {
    label: "MCP",
    color: "#FB923C",
    bg: "rgba(251, 146, 60, 0.15)",
  },
  agent: {
    label: "AGENT",
    color: "#60A5FA",
    bg: "rgba(96, 165, 250, 0.15)",
  },
  system: {
    label: "SYS",
    color: "#9CA3AF",
    bg: "rgba(156, 163, 175, 0.15)",
  },
};

const statusConfig: Record<ToolCardStatus, ToolStatusDisplayConfig> = {
  pending: {
    color: "var(--color-warning)",
    bg: "rgba(245, 158, 11, 0.1)",
  },
  executing: {
    color: "var(--color-secondary)",
    bg: "rgba(137, 208, 237, 0.1)",
  },
  completed: {
    color: "var(--color-success)",
    bg: "rgba(52, 211, 153, 0.1)",
  },
  failed: {
    color: "var(--color-error)",
    bg: "rgba(255, 180, 171, 0.1)",
  },
};

export function getToolTypeDisplayConfig(toolType: ToolType): ToolTypeDisplayConfig {
  return toolTypeConfig[toolType] || toolTypeConfig.func;
}

export function getToolStatusDisplayConfig(status: ToolCardStatus): ToolStatusDisplayConfig {
  return statusConfig[status];
}

export function getToolDuration(card: ToolCard): string | null {
  if (!card.completedAt) return null;
  const start = new Date(card.startedAt).getTime();
  const end = new Date(card.completedAt).getTime();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatToolValue(value: unknown, truncate = true): string {
  if (value === undefined || value === null) return "null";
  if (typeof value === "string") {
    if (!truncate) return value;
    return value.length > 200 ? value.slice(0, 200) + "..." : value;
  }
  const str = JSON.stringify(value, null, 2);
  if (!truncate) return str;
  return str.length > 400 ? str.slice(0, 400) + "..." : str;
}

export function isToolValueTruncated(value: unknown): boolean {
  if (value === undefined || value === null) return false;
  if (typeof value === "string") {
    return value.length > 200;
  }
  const str = JSON.stringify(value, null, 2);
  return str.length > 400;
}

export function getCompactArgsPreview(args: Record<string, unknown>): string {
  const preview = Object.entries(args)
    .slice(0, 2)
    .map(
      ([key, value]) =>
        `${key}: ${typeof value === "string" ? value.slice(0, 20) : JSON.stringify(value).slice(0, 20)}`,
    )
    .join(" | ");

  return Object.keys(args).length > 2 ? `${preview} ...` : preview;
}
