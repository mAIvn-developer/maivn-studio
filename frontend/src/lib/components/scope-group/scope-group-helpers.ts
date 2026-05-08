import type { PhaseChipData, ToolCard as ToolCardType } from "$lib/types";

export type ScopeType = "agent" | "swarm";

/**
 * One agent invocation. `invocationId` is the agent tool card's unique
 * tool_id, so a swarm that redeploys the same agent multiple times produces
 * separate NestedAgent entries (and therefore separate cards) keyed by
 * invocation rather than by agent name.
 */
export interface NestedAgent {
  invocationId: string;
  agentName: string;
  agentId?: string;
  tools: ToolCardType[];
}

export function normalizeScopePart(value: string | undefined): string | undefined {
  if (typeof value !== "string") return undefined;
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : undefined;
}

export function scopePartMatches(left: string | undefined, right: string | undefined): boolean {
  const normalizedLeft = normalizeScopePart(left);
  const normalizedRight = normalizeScopePart(right);
  return normalizedLeft !== undefined && normalizedLeft === normalizedRight;
}

export function resolveDirectPhaseChip(
  scopeType: ScopeType,
  scopeName: string,
  scopeId: string | undefined,
  phaseChips: PhaseChipData[],
): PhaseChipData | null {
  let latest: PhaseChipData | null = null;
  const normalizedScopeName = normalizeScopePart(scopeName);
  const normalizedScopeId = normalizeScopePart(scopeId);

  for (const chip of phaseChips) {
    if (scopeType === "swarm") {
      if (chip.scopeType !== "swarm") continue;
    } else {
      if (chip.scopeType === "swarm") continue;
      if (!chip.scopeType) {
        if (!latest) {
          latest = chip;
        }
        continue;
      }
      if (chip.scopeType !== "agent") continue;
    }

    const idMatch = scopePartMatches(chip.scopeId, normalizedScopeId);
    const nameMatch = scopePartMatches(chip.scopeName, normalizedScopeName);
    if (!idMatch && !nameMatch) {
      continue;
    }
    latest = chip;
  }

  return latest;
}

const ENRICHMENT_PHASE_LABELS: Record<string, string> = {
  evaluating: "Evaluating...",
  planning: "Planning actions...",
  planning_actions: "Planning actions...",
  searching_tools: "Searching for tools...",
  loading_tools: "Loading tools...",
  planning_assignments: "Planning assignments...",
  executing_assignments: "Executing assignments...",
  executing_actions: "Executing actions...",
  synthesizing: "Synthesizing response...",
  memory_skill_extracting: "Extracting skills from execution trace...",
  memory_insight_extracting: "Extracting insights from execution trace...",
  resource_registering: "Registering resource...",
  resource_registered: "Resource registered.",
  resource_dedup_reused: "Resource already registered (reused).",
  resource_version_superseded: "Superseded an older resource version.",
  resource_extracting: "Extracting resource passages...",
  resource_extracted: "Resource extraction complete.",
  redaction_previewed: "Redaction preview completed.",
  message_redaction_applied: "Input redaction applied.",
  tool_result_redaction_applied: "Tool-result redaction applied.",
  complete: "Complete",
  completed: "Complete",
  failed: "Failed",
};

export function resolvePhaseMessage(chip: PhaseChipData): string {
  const phase =
    typeof chip.phase === "string" && chip.phase.trim() ? chip.phase.trim().toLowerCase() : "";
  return ENRICHMENT_PHASE_LABELS[phase] ?? chip.message ?? chip.phase ?? "";
}

export function getDisplayPhaseMessage(
  directPhaseChip: PhaseChipData | null,
  aggregateStatus: string,
  scopeType: ScopeType,
  latestStatusMessage?: string | null,
): string | null {
  if (aggregateStatus === "completed") {
    return "Complete";
  }
  if (aggregateStatus === "failed") {
    return "Failed";
  }
  if (
    scopeType === "swarm" &&
    typeof latestStatusMessage === "string" &&
    latestStatusMessage.trim()
  ) {
    return latestStatusMessage.trim();
  }
  if (!directPhaseChip) {
    return null;
  }
  return resolvePhaseMessage(directPhaseChip);
}

export function buildNestedAgentPhaseChipsMap(
  scopeType: ScopeType,
  phaseChips: PhaseChipData[],
): Map<string, PhaseChipData[]> {
  if (scopeType !== "swarm") return new Map<string, PhaseChipData[]>();

  const map = new Map<string, PhaseChipData[]>();
  for (const chip of phaseChips) {
    if (chip.scopeType !== "agent") continue;
    const candidateKeys = [normalizeScopePart(chip.scopeId), normalizeScopePart(chip.scopeName)];
    for (const key of candidateKeys) {
      if (!key) continue;
      map.set(key, [chip]);
    }
  }
  return map;
}

export function resolveNestedAgentPhaseChips(
  nestedAgentPhaseChips: Map<string, PhaseChipData[]>,
  agent: NestedAgent,
): PhaseChipData[] {
  const normalizedAgentId = normalizeScopePart(agent.agentId);
  if (normalizedAgentId) {
    const idChips = nestedAgentPhaseChips.get(normalizedAgentId);
    if (idChips) {
      return idChips;
    }
  }

  const normalizedAgentName = normalizeScopePart(agent.agentName);
  if (normalizedAgentName) {
    const nameChips = nestedAgentPhaseChips.get(normalizedAgentName);
    if (nameChips) {
      return nameChips;
    }
  }

  return [];
}

export function getDisplayTools(tools: ToolCardType[]): ToolCardType[] {
  return tools.filter((tool) => tool.toolType !== "agent");
}

export function getStatusTools(
  scopeType: ScopeType,
  tools: ToolCardType[],
  nestedAgents: NestedAgent[],
): ToolCardType[] {
  const displayTools = getDisplayTools(tools);

  if (scopeType === "agent") {
    return displayTools.length > 0 ? displayTools : tools;
  }

  const nestedStatus = nestedAgents.flatMap((agent) => {
    const nestedDisplay = agent.tools.filter((tool) => tool.toolType !== "agent");
    return nestedDisplay.length > 0 ? nestedDisplay : agent.tools;
  });

  return [...displayTools, ...nestedStatus];
}

export function getControlStatusTools(
  scopeType: ScopeType,
  tools: ToolCardType[],
  nestedAgents: NestedAgent[],
): ToolCardType[] {
  if (scopeType === "agent") {
    return tools.filter((tool) => tool.toolType === "agent");
  }

  return nestedAgents.flatMap((agent) => agent.tools.filter((tool) => tool.toolType === "agent"));
}

export function getAggregateStatus(
  scopeType: ScopeType,
  tools: ToolCardType[],
  nestedAgents: NestedAgent[],
): "pending" | "executing" | "failed" | "completed" {
  const control = getControlStatusTools(scopeType, tools, nestedAgents);
  if (control.length > 0) {
    const hasControlExecuting = control.some((tool) => tool.status === "executing");
    const hasControlFailed = control.some((tool) => tool.status === "failed");
    const hasControlPending = control.some((tool) => tool.status === "pending");

    if (hasControlExecuting) return "executing";
    if (hasControlFailed) return "failed";
    if (hasControlPending) return "pending";
  }

  const all = getStatusTools(scopeType, tools, nestedAgents);
  if (all.length === 0) return "pending";

  const hasExecuting = all.some((tool) => tool.status === "executing");
  const hasFailed = all.some((tool) => tool.status === "failed");
  const hasPending = all.some((tool) => tool.status === "pending");
  const allCompleted = all.every((tool) => tool.status === "completed");

  if (hasExecuting) return "executing";
  if (hasFailed) return "failed";
  if (hasPending) return "pending";
  if (allCompleted) return "completed";
  return "pending";
}

export function getActiveAgentCount(scopeType: ScopeType, nestedAgents: NestedAgent[]): number {
  if (scopeType !== "swarm") return 0;
  return nestedAgents.filter((agent) => agent.tools.some((tool) => tool.status === "executing"))
    .length;
}

export interface ScopeGroupCounts {
  completedCount: number;
  failedCount: number;
  executingCount: number;
  totalCount: number;
  progress: number;
}

export function getScopeGroupCounts(statusTools: ToolCardType[]): ScopeGroupCounts {
  const completedCount = statusTools.filter((tool) => tool.status === "completed").length;
  const failedCount = statusTools.filter((tool) => tool.status === "failed").length;
  const executingCount = statusTools.filter((tool) => tool.status === "executing").length;
  const totalCount = statusTools.length;
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  return {
    completedCount,
    failedCount,
    executingCount,
    totalCount,
    progress,
  };
}
