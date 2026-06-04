import type { PhaseChipData, ReevaluateChipData } from "$lib/types";
import {
  KNOWN_ENRICHMENT_PHASE_ORDER,
  buildEnrichmentScopeKey,
  normalizeScopeType,
  normalizeScopeValue,
  resolveEnrichmentDisplayMessage,
  resolveMemoryScopeKey,
  resolveProcessingScopePriority,
} from "../../utils/enrichmentTracker";
import { asRecord, readScopeValue } from "./event-utils";
import { coerceMemoryActivityData, coerceRedactionActivityData } from "../memory";
import { resetStreamingAssistantContent } from "./assistant-events";
import type { SessionStoreContext } from "../types";

function coerceReevaluateChipData(
  raw: unknown,
  fallback: Record<string, unknown>,
): ReevaluateChipData | undefined {
  const record = asRecord(raw);
  const sourceRaw = normalizeScopeValue(record?.source ?? fallback.source);
  const source = sourceRaw === "dependency" || sourceRaw === "llm" ? sourceRaw : undefined;
  const triggerTool = normalizeScopeValue(record?.trigger_tool ?? fallback.trigger_tool);
  const targetTool = normalizeScopeValue(record?.target_tool ?? fallback.target_tool);
  const cycleRaw = record?.reevaluate_count ?? fallback.reevaluate_count;
  const collectedRaw = record?.collected_count ?? fallback.collected_count;
  const cycle = typeof cycleRaw === "number" ? cycleRaw : undefined;
  const collectedCount = typeof collectedRaw === "number" ? collectedRaw : undefined;

  if (
    !source &&
    !triggerTool &&
    !targetTool &&
    cycle === undefined &&
    collectedCount === undefined
  ) {
    return undefined;
  }
  return {
    source: source ?? "llm",
    triggerTool,
    targetTool,
    cycle,
    collectedCount,
  };
}

export function handleEnrichment(ctx: SessionStoreContext, eventData: Record<string, unknown>) {
  const enrichment = asRecord(eventData.enrichment);
  const phase = normalizeScopeValue(enrichment?.phase ?? eventData.phase);
  if (!phase) return;

  const message = resolveEnrichmentDisplayMessage(
    phase,
    normalizeScopeValue(enrichment?.message ?? eventData.message),
  );
  const memory = coerceMemoryActivityData(enrichment?.memory ?? eventData.memory);
  const redaction = coerceRedactionActivityData(enrichment?.redaction ?? eventData.redaction);
  const reevaluate = coerceReevaluateChipData(
    enrichment?.reevaluate ?? eventData.reevaluate,
    eventData,
  );
  const scopeType = normalizeScopeType(readScopeValue(eventData, "type") ?? eventData.scope_type);
  const scopeName = normalizeScopeValue(readScopeValue(eventData, "name") ?? eventData.scope_name);
  const legacyScopeId = normalizeScopeValue(readScopeValue(eventData, "id") ?? eventData.scope_id);
  const explicitAgentId = normalizeScopeValue(eventData.agent_id);
  const explicitSwarmId = normalizeScopeValue(eventData.swarm_id);
  const scopeId =
    scopeType === "agent"
      ? (explicitAgentId ?? legacyScopeId)
      : scopeType === "swarm"
        ? (explicitSwarmId ?? legacyScopeId)
        : legacyScopeId;

  const memoryScopeKey = resolveMemoryScopeKey(phase);
  // Each reevaluate cycle (and each `@depends_on_reevaluate` trigger pair) gets
  // its own scope key so successive chips render as separate inline markers
  // rather than overwriting each other. Without this every reevaluate cycle
  // would collide with the root scope and be replaced by the next `evaluating`
  // / `synthesizing` chip that fires after the re-plan completes.
  const reevaluateScopeKey =
    phase === "reevaluate_accrued"
      ? `__reevaluate:${reevaluate?.cycle ?? "x"}:${reevaluate?.triggerTool ?? ""}->${reevaluate?.targetTool ?? ""}__`
      : null;
  const persistentScopeKey = memoryScopeKey ?? reevaluateScopeKey;
  const scopeKey = persistentScopeKey ?? buildEnrichmentScopeKey(scopeType, scopeId, scopeName);
  const incomingScopePriority = resolveProcessingScopePriority(scopeType);

  const tracker = ctx.enrichmentTracker;

  if (!persistentScopeKey && tracker.shouldSkipPhase(scopeKey, phase)) return;
  if (tracker.isDuplicateEvent(scopeKey, phase, message)) return;
  if (!persistentScopeKey) tracker.recordPhaseRank(scopeKey, phase);

  if (phase === "reevaluate_accrued") {
    // Reset the currently-streaming bubble's content (in place) so the next
    // cycle's chunks populate it fresh. We deliberately do NOT create a new
    // bubble — the UI shows a single continuous assistant message that
    // updates as each cycle re-synthesises.
    resetStreamingAssistantContent(ctx);
  }

  if (!persistentScopeKey) {
    if (
      ctx.getProcessingScopeKey() === null ||
      scopeKey === ctx.getProcessingScopeKey() ||
      incomingScopePriority > ctx.getProcessingScopePriority()
    ) {
      ctx.setProcessingScopeKey(scopeKey);
      ctx.setProcessingScopePriority(incomingScopePriority);
    }

    // Update the bottom chip from the owning scope, OR from any scope
    // whose phase is more advanced.  This handles swarms where the
    // swarm scope emits "planning_actions" but only child agents
    // emit the later "executing_actions" / "synthesizing" phases.
    const currentPhaseRank = KNOWN_ENRICHMENT_PHASE_ORDER[ctx.getCurrentPhase() ?? ""] ?? -1;
    const incomingPhaseRank = KNOWN_ENRICHMENT_PHASE_ORDER[phase] ?? -1;

    if (scopeKey === ctx.getProcessingScopeKey() || incomingPhaseRank > currentPhaseRank) {
      ctx.setCurrentPhase(phase);
      ctx.setCurrentPhaseMessage(message);
    }
  }

  const chipData: PhaseChipData = {
    phase,
    message,
    timestamp: new Date().toISOString(),
  };
  if (scopeId) chipData.scopeId = scopeId;
  if (scopeName) chipData.scopeName = scopeName;
  if (scopeType) chipData.scopeType = scopeType;
  if (memory) chipData.memory = memory;
  if (redaction) chipData.redaction = redaction;
  if (reevaluate) chipData.reevaluate = reevaluate;

  const chipResult = tracker.applyPhaseChip(scopeKey, chipData, ctx.getChatFlowItems());
  ctx.setChatFlowItems(chipResult.chatFlowItems);

  if (phase === "memory_skill_extracted" && memory?.skills) {
    ctx.setExtractedSkills([...ctx.getExtractedSkills(), ...memory.skills]);
  }
  if (phase === "memory_insight_extracted" && memory?.insights) {
    ctx.setExtractedInsights([...ctx.getExtractedInsights(), ...memory.insights]);
  }
  if (phase === "memory_retrieved" && memory) {
    ctx.setRetrievedMemoryContext({
      hitCount: memory.hitCount ?? 0,
      skillHits: memory.skillCount ?? 0,
      insightHits: memory.insightCount ?? 0,
      resourceCount: memory.resourceCount ?? 0,
      vectorHits: memory.vectorHits ?? 0,
      keywordHits: memory.keywordHits ?? 0,
      graphHits: memory.graphHits ?? 0,
      latencyMs: memory.latencyMs ?? 0,
      skills: memory.skills,
      insights: memory.insights,
    });
  }

  if (
    phase === "memory_indexed" ||
    phase === "memory_skill_extracted" ||
    phase === "memory_insight_extracted"
  ) {
    ctx.showMemoryIndexedToast(message, memory);
  }
}
