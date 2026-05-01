import type { ScopeType } from "./scope-group-helpers";

export interface ScopeGroupStatusColors {
  color: string;
  bg: string;
}

export const scopeGroupStatusColors: Record<
  ScopeType,
  Record<"pending" | "executing" | "completed" | "failed", ScopeGroupStatusColors>
> = {
  agent: {
    pending: { color: "var(--color-warning)", bg: "rgba(245, 158, 11, 0.1)" },
    executing: { color: "var(--color-secondary)", bg: "rgba(137, 208, 237, 0.1)" },
    completed: { color: "var(--color-success)", bg: "rgba(52, 211, 153, 0.1)" },
    failed: { color: "var(--color-error)", bg: "rgba(255, 180, 171, 0.1)" },
  },
  swarm: {
    pending: { color: "var(--color-warning)", bg: "rgba(245, 158, 11, 0.1)" },
    executing: { color: "var(--color-primary)", bg: "rgba(255, 147, 97, 0.1)" },
    completed: { color: "var(--color-success)", bg: "rgba(52, 211, 153, 0.1)" },
    failed: { color: "var(--color-error)", bg: "rgba(255, 180, 171, 0.1)" },
  },
};

export function getScopeGroupCurrentStatus(
  scopeType: ScopeType,
  aggregateStatus: "pending" | "executing" | "failed" | "completed",
): ScopeGroupStatusColors {
  return (
    scopeGroupStatusColors[scopeType][aggregateStatus] || scopeGroupStatusColors[scopeType].pending
  );
}

export function getScopeGroupIconSize(compact: boolean, scopeType: ScopeType): string {
  return compact ? "w-6 h-6" : scopeType === "swarm" ? "w-10 h-10" : "w-8 h-8";
}

export function getScopeGroupInnerIconSizePx(compact: boolean, scopeType: ScopeType): number {
  return compact ? 12 : scopeType === "swarm" ? 20 : 16;
}

export function getScopeGroupExpandIconSizePx(compact: boolean, scopeType: ScopeType): number {
  return scopeType === "swarm" && !compact ? 20 : 16;
}
