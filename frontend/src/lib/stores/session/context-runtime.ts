import type { InvocationConfig, MemoryActivityData, MemoryConfig } from "$lib/types";

import type { SessionStoreContext } from "./types";

interface CreateSessionContextRuntimeParams {
  batcher: SessionStoreContext["batcher"];
  enrichmentTracker: SessionStoreContext["enrichmentTracker"];
  interruptManager: SessionStoreContext["interruptManager"];
  assistantIdToToolId: SessionStoreContext["assistantIdToToolId"];
  pendingAssistantChunks: SessionStoreContext["pendingAssistantChunks"];
  assistantSnapshots: SessionStoreContext["assistantSnapshots"];
  getInvocationConfig: () => InvocationConfig;
  setInvocationConfig: (config: InvocationConfig) => void;
  getMemoryConfig: () => MemoryConfig;
  getMemoryConfigBase: () => InvocationConfig["memory_config"] | undefined;
  flushPendingStreams: () => void;
  showMemoryIndexedToast: (message: string, details?: MemoryActivityData) => void;
  resetEnrichmentPhaseTracking: () => void;
  finalizeActiveExecutionPhaseChips: (terminalPhase: "complete" | "failed") => void;
}

export function createSessionContextRuntime(params: CreateSessionContextRuntimeParams) {
  return {
    batcher: params.batcher,
    enrichmentTracker: params.enrichmentTracker,
    interruptManager: params.interruptManager,
    assistantIdToToolId: params.assistantIdToToolId,
    pendingAssistantChunks: params.pendingAssistantChunks,
    assistantSnapshots: params.assistantSnapshots,
    getInvocationConfig: params.getInvocationConfig,
    setInvocationConfig: params.setInvocationConfig,
    getMemoryConfig: params.getMemoryConfig,
    getMemoryConfigBase: params.getMemoryConfigBase,
    flushPendingStreams: params.flushPendingStreams,
    showMemoryIndexedToast: params.showMemoryIndexedToast,
    resetEnrichmentPhaseTracking: params.resetEnrichmentPhaseTracking,
    finalizeActiveExecutionPhaseChips: params.finalizeActiveExecutionPhaseChips,
  };
}
