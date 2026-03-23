import type {
  ChatFlowItem,
  ExtractedInsightSummary,
  ExtractedSkillSummary,
  MemoryActivityData,
  PhaseChipData,
  RetrievedMemoryContext,
} from "$lib/types";
import { resolveEnrichmentDisplayMessage, resolveMemoryScopeKey } from "../utils/enrichmentTracker";
import type { EnrichmentTracker } from "../utils/enrichmentTracker";

interface CreateEnrichmentRuntimeParams {
  enrichmentTracker: EnrichmentTracker;
  getChatFlowItems: () => ChatFlowItem[];
  setChatFlowItems: (items: ChatFlowItem[]) => void;
  setCurrentPhase: (v: string | null) => void;
  setCurrentPhaseMessage: (v: string | null) => void;
  setProcessingScopeKey: (v: string | null) => void;
  setProcessingScopePriority: (v: number) => void;
  setExtractedSkills: (v: ExtractedSkillSummary[]) => void;
  setExtractedInsights: (v: ExtractedInsightSummary[]) => void;
  setRetrievedMemoryContext: (v: RetrievedMemoryContext | null) => void;
  setMemoryIndexedToast: (
    v: {
      message: string;
      timestamp: string;
      details?: MemoryActivityData;
    } | null,
  ) => void;
  getMemoryIndexedToastTimer: () => ReturnType<typeof setTimeout> | null;
  setMemoryIndexedToastTimer: (timer: ReturnType<typeof setTimeout> | null) => void;
}

export function createEnrichmentRuntime(params: CreateEnrichmentRuntimeParams) {
  function resetEnrichmentPhaseTracking() {
    params.setCurrentPhase(null);
    params.setCurrentPhaseMessage(null);
    params.setProcessingScopeKey(null);
    params.setProcessingScopePriority(-1);
    params.enrichmentTracker.reset();
  }

  function finalizeActiveExecutionPhaseChips(terminalPhase: "complete" | "failed") {
    const trackedChipIds = new Set(params.enrichmentTracker.phaseChipItemIdByScope.values());
    if (trackedChipIds.size === 0) {
      return;
    }

    const timestamp = new Date().toISOString();
    const terminalMessage = resolveEnrichmentDisplayMessage(terminalPhase, undefined);

    params.setChatFlowItems(
      params.getChatFlowItems().map((item) => {
        if (!trackedChipIds.has(item.id) || item.type !== "phase_chip") {
          return item;
        }

        const chipData = item.data as PhaseChipData;
        if (resolveMemoryScopeKey(chipData.phase) !== null) {
          return item;
        }

        return {
          ...item,
          timestamp,
          data: {
            ...chipData,
            phase: terminalPhase,
            message: terminalMessage,
            timestamp,
          },
        };
      }),
    );
  }

  function resetEnrichmentTracking() {
    resetEnrichmentPhaseTracking();
    params.setExtractedSkills([]);
    params.setExtractedInsights([]);
    params.setRetrievedMemoryContext(null);
  }

  function clearMemoryIndexedToastTimer() {
    const timer = params.getMemoryIndexedToastTimer();
    if (timer !== null) {
      clearTimeout(timer);
      params.setMemoryIndexedToastTimer(null);
    }
  }

  function showMemoryIndexedToast(message: string, details?: MemoryActivityData) {
    params.setMemoryIndexedToast({
      message,
      timestamp: new Date().toISOString(),
      details,
    });
    clearMemoryIndexedToastTimer();
    params.setMemoryIndexedToastTimer(
      setTimeout(() => {
        params.setMemoryIndexedToast(null);
        params.setMemoryIndexedToastTimer(null);
      }, 5000),
    );
  }

  return {
    resetEnrichmentPhaseTracking,
    finalizeActiveExecutionPhaseChips,
    resetEnrichmentTracking,
    clearMemoryIndexedToastTimer,
    showMemoryIndexedToast,
  };
}
