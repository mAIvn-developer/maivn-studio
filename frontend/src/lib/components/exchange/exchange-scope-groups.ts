import type { PhaseChipData, ToolCard as ToolCardType } from "$lib/types";

export type NestedAgent = {
  agentName: string;
  agentId?: string;
  tools: ToolCardType[];
};

export type ScopeGroup = {
  type: "swarm" | "agent";
  name: string;
  id?: string;
  tools: ToolCardType[];
  nestedAgents: NestedAgent[];
};

function normalizeScopePart(value: string | undefined): string | undefined {
  if (typeof value !== "string") return undefined;
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : undefined;
}

function extractAgentId(tool: ToolCardType): string | undefined {
  const args = tool.args as Record<string, unknown> | undefined;
  const raw = args?.agent_id;
  if (typeof raw !== "string") return undefined;
  const normalized = raw.trim();
  return normalized.length > 0 ? normalized : undefined;
}

function scopeKeyFor(
  scopeType: "agent" | "swarm",
  scopeId: string | undefined,
  scopeName: string | undefined,
): string[] {
  const keys: string[] = [];
  const id = normalizeScopePart(scopeId);
  const name = normalizeScopePart(scopeName);
  if (id) keys.push(`${scopeType}:${id}`);
  if (name) keys.push(`${scopeType}:${name}`);
  return keys;
}

export function getLatestRootPhaseChip(phaseChips: PhaseChipData[]): PhaseChipData | null {
  let latest: PhaseChipData | null = null;
  for (const chip of phaseChips) {
    if (chip.scopeType) continue;
    latest = chip;
  }
  return latest;
}

export function isMemoryPhaseChip(chip: PhaseChipData): boolean {
  const normalizedPhase = typeof chip.phase === "string" ? chip.phase.trim().toLowerCase() : "";
  if (normalizedPhase.startsWith("memory_")) {
    return true;
  }
  if (normalizedPhase.startsWith("redaction_") || normalizedPhase === "message_redaction_applied") {
    return true;
  }
  return chip.memory !== undefined || chip.redaction !== undefined;
}

export function getLatestMemoryPhaseChip(phaseChips: PhaseChipData[]): PhaseChipData | null {
  let latest: PhaseChipData | null = null;
  for (const chip of phaseChips) {
    if (!isMemoryPhaseChip(chip)) continue;
    latest = chip;
  }
  return latest;
}

function buildLatestScopedPhaseChipByScopeKey(
  phaseChips: PhaseChipData[],
): Map<string, PhaseChipData> {
  const map = new Map<string, PhaseChipData>();
  for (const chip of phaseChips) {
    if (chip.scopeType !== "agent" && chip.scopeType !== "swarm") {
      continue;
    }
    const keys = scopeKeyFor(chip.scopeType, chip.scopeId, chip.scopeName);
    for (const key of keys) {
      map.set(key, chip);
    }
  }
  return map;
}

function getLatestScopedPhaseChip(
  chipsByScope: Map<string, PhaseChipData>,
  scopeType: "agent" | "swarm",
  scopeId: string | undefined,
  scopeName: string | undefined,
): PhaseChipData | null {
  const keys = scopeKeyFor(scopeType, scopeId, scopeName);
  for (const key of keys) {
    const chip = chipsByScope.get(key);
    if (chip) return chip;
  }
  return null;
}

export function buildScopeGroups(toolCards: ToolCardType[]): ScopeGroup[] {
  if (toolCards.length === 0) {
    return [];
  }

  const result: ScopeGroup[] = [];
  const swarms = new Map<
    string,
    {
      tools: ToolCardType[];
      agents: Map<string, { agentId?: string; tools: ToolCardType[] }>;
    }
  >();
  const standaloneAgents = new Map<string, { agentId?: string; tools: ToolCardType[] }>();

  for (const tool of toolCards) {
    const swarmName = tool.swarmName;
    const agentName = tool.agentName;

    if (swarmName) {
      let swarm = swarms.get(swarmName);
      if (!swarm) {
        swarm = { tools: [], agents: new Map() };
        swarms.set(swarmName, swarm);
      }

      if (agentName) {
        let agentScope = swarm.agents.get(agentName);
        if (!agentScope) {
          agentScope = { tools: [] };
          swarm.agents.set(agentName, agentScope);
        }
        if (!agentScope.agentId) {
          const agentId = extractAgentId(tool);
          if (agentId) {
            agentScope.agentId = agentId;
          }
        }
        agentScope.tools.push(tool);
      } else {
        swarm.tools.push(tool);
      }
    } else if (agentName) {
      let agentScope = standaloneAgents.get(agentName);
      if (!agentScope) {
        agentScope = { tools: [] };
        standaloneAgents.set(agentName, agentScope);
      }
      if (!agentScope.agentId) {
        const agentId = extractAgentId(tool);
        if (agentId) {
          agentScope.agentId = agentId;
        }
      }
      agentScope.tools.push(tool);
    }
  }

  const processedSwarms = new Set<string>();
  const processedAgents = new Set<string>();

  for (const tool of toolCards) {
    const swarmName = tool.swarmName;
    const agentName = tool.agentName;

    if (swarmName && !processedSwarms.has(swarmName)) {
      const swarm = swarms.get(swarmName)!;
      const nestedAgents: NestedAgent[] = [];

      for (const [name, agentScope] of swarm.agents) {
        nestedAgents.push({
          agentName: name,
          agentId: agentScope.agentId,
          tools: agentScope.tools,
        });
      }

      result.push({
        type: "swarm",
        name: swarmName,
        id: swarmName,
        tools: swarm.tools,
        nestedAgents,
      });
      processedSwarms.add(swarmName);
    } else if (!swarmName && agentName && !processedAgents.has(agentName)) {
      const agentScope = standaloneAgents.get(agentName)!;
      result.push({
        type: "agent",
        name: agentName,
        id: agentScope.agentId,
        tools: agentScope.tools,
        nestedAgents: [],
      });
      processedAgents.add(agentName);
    }
  }

  return result;
}

export function resolveScopePhaseChips(
  group: ScopeGroup,
  phaseChips: PhaseChipData[],
): PhaseChipData[] {
  const latestRootPhaseChip = getLatestRootPhaseChip(phaseChips);
  const chipsByScope = buildLatestScopedPhaseChipByScopeKey(phaseChips);

  if (group.type === "agent") {
    const scopedChip = getLatestScopedPhaseChip(chipsByScope, "agent", group.id, group.name);
    if (scopedChip) {
      return [scopedChip];
    }

    return latestRootPhaseChip ? [latestRootPhaseChip] : [];
  }

  const chips: PhaseChipData[] = [];
  const swarmChip = getLatestScopedPhaseChip(chipsByScope, "swarm", group.id, group.name);
  if (swarmChip) {
    chips.push(swarmChip);
  }

  for (const nestedAgent of group.nestedAgents) {
    const nestedChip = getLatestScopedPhaseChip(
      chipsByScope,
      "agent",
      nestedAgent.agentId,
      nestedAgent.agentName,
    );
    if (nestedChip) {
      chips.push(nestedChip);
    }
  }

  return chips;
}
