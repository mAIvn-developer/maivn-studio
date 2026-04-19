import type { ChatFlowItem, PhaseChipData } from "$lib/types";

// MARK: Constants

export const ROOT_ENRICHMENT_SCOPE_KEY = "__root_scope__";

/**
 * Memory phases use per-operation scope keys so each memory operation gets its
 * own persistent card that is not overwritten by execution phases or other
 * memory operations. The "extracting" and "extracted" phases for the same
 * operation share a scope so the card updates in-place.
 */
export const MEMORY_PHASE_SCOPE_MAP: Record<string, string> = {
  memory_retrieving: "__memory:retrieve__",
  memory_retrieved: "__memory:retrieve__",
  memory_summarizing: "__memory:summarize__",
  memory_summarized: "__memory:summarize__",
  memory_skill_extracting: "__memory:extract_skills__",
  memory_skill_extracted: "__memory:extract_skills__",
  memory_insight_extracting: "__memory:extract_insights__",
  memory_insight_extracted: "__memory:extract_insights__",
  memory_indexing: "__memory:index__",
  memory_indexed: "__memory:index__",
  memory_graph_extracting: "__memory:index__",
  redaction_previewed: "__redaction:preview__",
  message_redaction_applied: "__redaction:session_start__",
  tool_result_redaction_applied: "__redaction:tool_results__",
};

export const PERSISTENT_MEMORY_PHASES = new Set<string>(Object.keys(MEMORY_PHASE_SCOPE_MAP));

export const KNOWN_ENRICHMENT_PHASE_ORDER: Record<string, number> = {
  evaluating: 0,
  planning: 1,
  planning_actions: 1,
  searching_tools: 2,
  loading_tools: 3,
  planning_assignments: 4,
  executing_assignments: 5,
  executing_actions: 6,
  synthesizing: 7,
  complete: 8,
  completed: 8,
  failed: 8,
};

// Re-planning can re-enter earlier phases (for example, planning/searching)
// without always emitting an explicit `evaluating` transition first.
// Treat these as valid cycle reset markers rather than stale regressions.
export const PHASE_RESET_MARKERS = new Set<string>([
  "evaluating",
  "planning",
  "planning_actions",
  "searching_tools",
  "loading_tools",
  "planning_assignments",
]);

export const ENRICHMENT_PHASE_LABELS: Record<string, string> = {
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
  memory_skill_extracted: "Skills extracted from execution trace.",
  memory_insight_extracting: "Extracting insights from execution trace...",
  memory_insight_extracted: "Insights extracted from execution trace.",
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

// MARK: Scope Helpers

/**
 * Returns a dedicated memory scope key for memory-related phases, or `null`
 * if the phase is a normal execution phase that should use the default scope.
 */
export function resolveMemoryScopeKey(phase: string): string | null {
  const normalizedPhase = phase.trim().toLowerCase();
  return MEMORY_PHASE_SCOPE_MAP[normalizedPhase] ?? null;
}

export function resolveKnownPhaseRank(phase: string): number | null {
  const normalizedPhase = phase.trim().toLowerCase();
  const rank = KNOWN_ENRICHMENT_PHASE_ORDER[normalizedPhase];
  return typeof rank === "number" ? rank : null;
}

export function resolveEnrichmentDisplayMessage(
  phase: string,
  message: string | undefined,
): string {
  const normalizedPhase = phase.trim().toLowerCase();
  return ENRICHMENT_PHASE_LABELS[normalizedPhase] ?? message ?? phase;
}

export function normalizeScopeValue(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : undefined;
}

export function normalizeScopeType(value: unknown): "agent" | "swarm" | undefined {
  return value === "agent" || value === "swarm" ? value : undefined;
}

export function buildEnrichmentScopeKey(
  scopeType: "agent" | "swarm" | undefined,
  scopeId: string | undefined,
  scopeName: string | undefined,
): string {
  if (!scopeType) return ROOT_ENRICHMENT_SCOPE_KEY;
  return `${scopeType}:${scopeId ?? scopeName ?? "unknown"}`;
}

export function resolveProcessingScopePriority(scopeType: "agent" | "swarm" | undefined): number {
  // Prefer root/unscoped updates, then swarm, then agent-specific updates.
  // This keeps the lower Processing card aligned with top-level execution,
  // while still allowing basic single-agent runs (agent-only scope) to work.
  if (!scopeType) return 3;
  if (scopeType === "swarm") return 2;
  return 1;
}

// MARK: EnrichmentTracker

/**
 * Tracks enrichment phase state across scopes.
 *
 * Manages the 3 scope-tracking Maps (lastEnrichmentEventByScope,
 * phaseChipItemIdByScope, highestKnownPhaseRankByScope) and provides
 * methods for processing enrichment events.
 */
export class EnrichmentTracker {
  readonly lastEnrichmentEventByScope = new Map<string, string>();
  readonly phaseChipItemIdByScope = new Map<string, string>();
  readonly highestKnownPhaseRankByScope = new Map<string, number>();

  /** Reset all tracking state. Called on session start, turn complete, etc. */
  reset(): void {
    this.lastEnrichmentEventByScope.clear();
    this.phaseChipItemIdByScope.clear();
    this.highestKnownPhaseRankByScope.clear();
  }

  /**
   * Determine whether an incoming enrichment phase should be ignored as a
   * stale regression (i.e. lower rank than what we already saw for that scope).
   *
   * Returns `true` if the event should be skipped.
   */
  shouldSkipPhase(scopeKey: string, phase: string): boolean {
    const incomingRank = resolveKnownPhaseRank(phase);
    const currentRank = this.highestKnownPhaseRankByScope.get(scopeKey);
    if (incomingRank !== null && currentRank !== undefined && incomingRank < currentRank) {
      const normalizedPhase = phase.trim().toLowerCase();
      const isPhaseReset = PHASE_RESET_MARKERS.has(normalizedPhase);
      if (!isPhaseReset) {
        return true;
      }
    }
    return false;
  }

  /**
   * Check whether this enrichment event is an exact repeat for the same scope
   * (same phase + message combination). Returns `true` if it should be skipped.
   */
  isDuplicateEvent(scopeKey: string, phase: string, message: string): boolean {
    const enrichmentSignature = `${phase}:${message}`;
    if (this.lastEnrichmentEventByScope.get(scopeKey) === enrichmentSignature) {
      return true;
    }
    this.lastEnrichmentEventByScope.set(scopeKey, enrichmentSignature);
    return false;
  }

  /**
   * Record the incoming phase rank for the scope.
   */
  recordPhaseRank(scopeKey: string, phase: string): void {
    const incomingRank = resolveKnownPhaseRank(phase);
    if (incomingRank !== null) {
      this.highestKnownPhaseRankByScope.set(scopeKey, incomingRank);
    }
  }

  /**
   * Build a PhaseChipData object and either update an existing chat flow item
   * or create a new one.
   *
   * Returns `{ chatFlowItems, created }` where `created` indicates whether a
   * new item was appended (vs an existing one updated in-place).
   */
  applyPhaseChip(
    scopeKey: string,
    chipData: PhaseChipData,
    chatFlowItems: ChatFlowItem[],
  ): { chatFlowItems: ChatFlowItem[]; created: boolean } {
    const existingChipItemId = this.phaseChipItemIdByScope.get(scopeKey);
    if (existingChipItemId) {
      const updatedItems = chatFlowItems.map((item) => {
        if (item.id !== existingChipItemId || item.type !== "phase_chip") {
          return item;
        }
        return {
          ...item,
          timestamp: chipData.timestamp,
          data: chipData,
        };
      });
      return { chatFlowItems: updatedItems, created: false };
    }

    const chipItemId = crypto.randomUUID();
    this.phaseChipItemIdByScope.set(scopeKey, chipItemId);
    const updatedItems = [
      ...chatFlowItems,
      {
        id: chipItemId,
        type: "phase_chip" as const,
        timestamp: chipData.timestamp,
        data: chipData,
      },
    ];
    return { chatFlowItems: updatedItems, created: true };
  }
}
