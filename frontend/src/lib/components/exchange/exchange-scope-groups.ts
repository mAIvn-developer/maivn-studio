import type { PhaseChipData, ToolCard as ToolCardType } from "$lib/types";

// MARK: Types

/**
 * One agent invocation = one card in the UI. `invocationId` is the agent
 * tool card's unique tool_id (server-minted UUID per swarm action), so a
 * supervisor_loop that redeploys the same agent multiple times produces
 * multiple NestedAgent entries that render as separate cards.
 */
export type NestedAgent = {
  invocationId: string;
  agentName: string;
  agentId?: string;
  tools: ToolCardType[];
};

export type ScopeGroup = {
  type: "swarm" | "agent" | "system";
  name: string;
  id?: string;
  // For swarm groups: tools that belong to the swarm root (not to any specific
  // agent invocation). For agent groups: the invocation's tools (including its
  // own agent-typed card; nested non-agent tools are filtered for display via
  // getDisplayTools).
  tools: ToolCardType[];
  nestedAgents: NestedAgent[];
  // For agent-typed groups, this is the agent card's unique tool_id so the
  // Svelte {#each} can key cards by invocation rather than by agent name (the
  // latter collapses repeated invocations of the same agent into one card).
  invocationId?: string;
};

// MARK: Phase Chip Helpers

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

function getSingleSwarmName(toolCards: ToolCardType[]): string | undefined {
  const swarmNames = new Set<string>();
  for (const tool of toolCards) {
    const swarmName = normalizeScopePart(tool.swarmName);
    if (swarmName) {
      swarmNames.add(swarmName);
    }
  }
  return swarmNames.size === 1 ? [...swarmNames][0] : undefined;
}

function resolveToolSwarmName(
  tool: ToolCardType,
  inferredSwarmName: string | undefined,
): string | undefined {
  const explicitSwarmName = normalizeScopePart(tool.swarmName);
  if (explicitSwarmName) {
    return explicitSwarmName;
  }

  if (tool.agentName && inferredSwarmName) {
    return inferredSwarmName;
  }

  return undefined;
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
    // Reevaluate chips render via their own inline component so the root
    // preamble doesn't replay them as the generic "evaluating..." line.
    if (isReevaluatePhaseChip(chip)) continue;
    latest = chip;
  }
  return latest;
}

function isMemoryPhaseChip(chip: PhaseChipData): boolean {
  const normalizedPhase = typeof chip.phase === "string" ? chip.phase.trim().toLowerCase() : "";
  if (normalizedPhase.startsWith("memory_")) {
    return true;
  }
  if (
    normalizedPhase.startsWith("redaction_") ||
    normalizedPhase === "message_redaction_applied" ||
    normalizedPhase === "tool_result_redaction_applied"
  ) {
    return true;
  }
  return chip.memory !== undefined || chip.redaction !== undefined;
}

function isReevaluatePhaseChip(chip: PhaseChipData): boolean {
  if (chip.reevaluate) return true;
  const normalizedPhase = typeof chip.phase === "string" ? chip.phase.trim().toLowerCase() : "";
  return normalizedPhase === "reevaluate_accrued";
}

// Return every reevaluate_accrued chip in order so the inline trail of
// boundary firings is preserved (cycle 1, cycle 2, ...) rather than
// collapsed to the latest.
export function getReevaluatePhaseChips(phaseChips: PhaseChipData[]): PhaseChipData[] {
  return phaseChips.filter(isReevaluatePhaseChip);
}

// One panel per distinct memory/redaction phase so input redaction (multi-key)
// is not visually replaced by tool-result redaction (often a single key) when
// both fire in the same turn.
export function getMemoryPhaseChipsByPhase(phaseChips: PhaseChipData[]): PhaseChipData[] {
  const byPhase = new Map<string, PhaseChipData>();
  const order: string[] = [];
  for (const chip of phaseChips) {
    if (!isMemoryPhaseChip(chip)) continue;
    const key = typeof chip.phase === "string" ? chip.phase.trim().toLowerCase() : "";
    if (!key) continue;
    if (!byPhase.has(key)) order.push(key);
    byPhase.set(key, chip);
  }
  return order.map((key) => byPhase.get(key)!).filter((chip): chip is PhaseChipData => !!chip);
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

// MARK: Invocation Grouping

/**
 * Per-invocation scope: an agent's tool card plus every nested non-agent tool
 * that ran inside that invocation's session.
 */
type InvocationScope = {
  invocationId: string;
  agentName: string;
  agentId?: string;
  swarmName?: string;
  scopeType?: "agent" | "system";
  tools: ToolCardType[];
};

const ROOT_SYSTEM_TOOLS_SCOPE_NAME = "System tools";
const ROOT_SYSTEM_TOOLS_INVOCATION_ID = "system:tools";

/**
 * Build scope groups by walking tool cards in chronological order so each
 * agent invocation card opens a fresh InvocationScope. Subsequent non-agent
 * tools with matching agentName attach to the most recent open scope for
 * that name.
 *
 * Why this matters: the prior implementation grouped by agentName, so a
 * supervisor_loop that redeploys `coding_agent` three times merged all three
 * runs into one card. Each invocation now has its own NestedAgent (or
 * top-level "agent" ScopeGroup), keyed by the agent card's unique tool_id.
 */
export function buildScopeGroups(toolCards: ToolCardType[]): ScopeGroup[] {
  if (toolCards.length === 0) {
    return [];
  }

  const inferredSwarmName = getSingleSwarmName(toolCards);

  // Per-swarm: ordered list of agent invocations seen, plus swarm-root tools
  // (e.g., the swarm's own progress tools that aren't tied to any agent).
  const swarmRootTools = new Map<string, ToolCardType[]>();
  const swarmInvocations = new Map<string, InvocationScope[]>();
  const standaloneInvocations: InvocationScope[] = [];

  // The most recent open invocation per (swarm, agent_name) key. Nested
  // non-agent tools route to the matching open scope so a tool emitted
  // during the second invocation of `coding_agent` lands in the second
  // card, not the first.
  const openInvocationByKey = new Map<string, InvocationScope>();
  const invocationKeyFor = (swarmName: string | undefined, agentName: string): string =>
    `${swarmName ?? ""}::${agentName}`;

  const createSyntheticScope = (
    agentName: string,
    swarmName: string | undefined,
    tool: ToolCardType,
  ): InvocationScope => ({
    invocationId: swarmName ? `swarm:${swarmName}:agent:${agentName}` : `agent:${agentName}`,
    agentName,
    swarmName,
    tools: [tool],
  });

  const hasAgentAnchor = (scope: InvocationScope): boolean =>
    scope.tools.some((candidate) => candidate.toolType === "agent");

  for (const tool of toolCards) {
    const swarmName = resolveToolSwarmName(tool, inferredSwarmName);
    const agentName = tool.agentName;

    if (tool.toolType === "agent" && agentName) {
      const key = invocationKeyFor(swarmName, agentName);
      const existingScope = openInvocationByKey.get(key);
      if (existingScope && !hasAgentAnchor(existingScope)) {
        existingScope.invocationId = tool.toolId;
        existingScope.agentId = extractAgentId(tool);
        existingScope.swarmName = swarmName;
        existingScope.tools.push(tool);
        continue;
      }

      // A new invocation card. If the matching open scope already has an
      // agent anchor, this is a second session/invocation and must render as
      // a second card even when the agent name repeats.
      const scope: InvocationScope = {
        invocationId: tool.toolId,
        agentName,
        agentId: extractAgentId(tool),
        swarmName,
        tools: [tool],
      };

      if (swarmName) {
        let invocations = swarmInvocations.get(swarmName);
        if (!invocations) {
          invocations = [];
          swarmInvocations.set(swarmName, invocations);
        }
        invocations.push(scope);
      } else {
        standaloneInvocations.push(scope);
      }
      openInvocationByKey.set(key, scope);
      continue;
    }

    if (!swarmName && tool.isSystemTool) {
      if (agentName) {
        const existingScope = openInvocationByKey.get(invocationKeyFor(undefined, agentName));
        if (existingScope) {
          existingScope.tools.push(tool);
          continue;
        }
      }

      const key = invocationKeyFor(undefined, ROOT_SYSTEM_TOOLS_SCOPE_NAME);
      let systemScope = openInvocationByKey.get(key);
      if (!systemScope) {
        systemScope = {
          invocationId: ROOT_SYSTEM_TOOLS_INVOCATION_ID,
          agentName: ROOT_SYSTEM_TOOLS_SCOPE_NAME,
          scopeType: "system",
          tools: [],
        };
        standaloneInvocations.push(systemScope);
        openInvocationByKey.set(key, systemScope);
      }
      systemScope.tools.push(tool);
      continue;
    }

    if (agentName) {
      const scope = openInvocationByKey.get(invocationKeyFor(swarmName, agentName));
      if (scope) {
        scope.tools.push(tool);
        continue;
      }
      // No anchor card for this agent yet. Some execution paths emit
      // agent-owned tool events without a toolType="agent" anchor. Keep
      // those tools visible by synthesizing an InvocationScope keyed by
      // agent name, either within the current swarm or as a standalone agent.
      if (swarmName) {
        const synthetic = createSyntheticScope(agentName, swarmName, tool);
        let invocations = swarmInvocations.get(swarmName);
        if (!invocations) {
          invocations = [];
          swarmInvocations.set(swarmName, invocations);
        }
        invocations.push(synthetic);
        openInvocationByKey.set(invocationKeyFor(swarmName, agentName), synthetic);
        continue;
      } else {
        const synthetic = createSyntheticScope(agentName, undefined, tool);
        standaloneInvocations.push(synthetic);
        openInvocationByKey.set(invocationKeyFor(undefined, agentName), synthetic);
        continue;
      }
    }

    if (swarmName) {
      let rootTools = swarmRootTools.get(swarmName);
      if (!rootTools) {
        rootTools = [];
        swarmRootTools.set(swarmName, rootTools);
      }
      rootTools.push(tool);
    }
  }

  // Build a tool_id -> InvocationScope index so the second pass can find
  // the owning scope of any tool, including non-agent tools that landed in
  // a SYNTHETIC standalone scope (created above when there's no
  // toolType="agent" anchor card — typical for non-swarm runs where the
  // server only emits func-typed tool_events).
  const scopeByToolId = new Map<string, InvocationScope>();
  for (const swarmList of swarmInvocations.values()) {
    for (const scope of swarmList) {
      for (const owned of scope.tools) {
        scopeByToolId.set(owned.toolId, scope);
      }
    }
  }
  for (const scope of standaloneInvocations) {
    for (const owned of scope.tools) {
      scopeByToolId.set(owned.toolId, scope);
    }
  }

  // Emit ScopeGroups in the order swarms / standalone-agent invocations
  // first appear so the chat flow stays chronological.
  const result: ScopeGroup[] = [];
  const seenSwarms = new Set<string>();
  const emittedInvocationIds = new Set<string>();

  for (const tool of toolCards) {
    const swarmName = resolveToolSwarmName(tool, inferredSwarmName);

    if (swarmName && !seenSwarms.has(swarmName)) {
      const invocations = swarmInvocations.get(swarmName) ?? [];
      result.push({
        type: "swarm",
        name: swarmName,
        id: swarmName,
        tools: swarmRootTools.get(swarmName) ?? [],
        nestedAgents: invocations.map((scope) => ({
          invocationId: scope.invocationId,
          agentName: scope.agentName,
          agentId: scope.agentId,
          tools: scope.tools,
        })),
      });
      seenSwarms.add(swarmName);
      continue;
    }

    if (swarmName) {
      // Tool already accounted for via the swarm group emitted on first
      // sighting above.
      continue;
    }

    // Standalone path: emit the owning scope (real or synthetic) the first
    // time any of its tools appears in the chat flow.
    const ownerScope = scopeByToolId.get(tool.toolId);
    if (!ownerScope || emittedInvocationIds.has(ownerScope.invocationId)) {
      continue;
    }
    result.push({
      type: ownerScope.scopeType ?? "agent",
      name: ownerScope.agentName,
      id: ownerScope.agentId,
      invocationId: ownerScope.invocationId,
      tools: ownerScope.tools,
      nestedAgents: [],
    });
    emittedInvocationIds.add(ownerScope.invocationId);
  }

  return result;
}

// MARK: Phase Chip Resolution

export function resolveScopePhaseChips(
  group: ScopeGroup,
  phaseChips: PhaseChipData[],
): PhaseChipData[] {
  const latestRootPhaseChip = getLatestRootPhaseChip(phaseChips);
  const chipsByScope = buildLatestScopedPhaseChipByScopeKey(phaseChips);

  if (group.type === "system") {
    return latestRootPhaseChip ? [latestRootPhaseChip] : [];
  }

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
