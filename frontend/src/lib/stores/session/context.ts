import type {
  ChatFlowItem,
  HookFiring,
  InterruptData,
  InvocationConfig,
  MemoryActivityData,
  MemoryConfig,
  ToolCard,
  UIEvent,
} from "$lib/types";

import type { SessionStoreContext } from "./types";

interface CreateSessionStoreContextParams {
  getSession: () => import("$lib/types").Session | null;
  setSession: (s: import("$lib/types").Session | null) => void;
  getChatFlowItems: () => ChatFlowItem[];
  setChatFlowItems: (items: ChatFlowItem[]) => void;
  getToolCards: () => Map<string, ToolCard>;
  setToolCards: (cards: Map<string, ToolCard>) => void;
  getScopeHookFirings: () => Map<string, HookFiring[]>;
  setScopeHookFirings: (firings: Map<string, HookFiring[]>) => void;
  getEvents: () => UIEvent[];
  setEvents: (events: UIEvent[]) => void;
  getLoading: () => boolean;
  setLoading: (v: boolean) => void;
  getError: () => string | null;
  setError: (v: string | null) => void;
  getRootAssistantId: () => string | null;
  setRootAssistantId: (v: string | null) => void;
  getStreamingAssistantItemId: () => string | null;
  setStreamingAssistantItemId: (v: string | null) => void;
  getInterruptCards: () => Map<string, InterruptData>;
  setInterruptCards: (cards: Map<string, InterruptData>) => void;
  getCurrentPhase: () => string | null;
  setCurrentPhase: (v: string | null) => void;
  getCurrentPhaseMessage: () => string | null;
  setCurrentPhaseMessage: (v: string | null) => void;
  getProcessingScopeKey: () => string | null;
  setProcessingScopeKey: (v: string | null) => void;
  getProcessingScopePriority: () => number;
  setProcessingScopePriority: (v: number) => void;
  getExtractedSkills: () => import("$lib/types").ExtractedSkillSummary[];
  setExtractedSkills: (v: import("$lib/types").ExtractedSkillSummary[]) => void;
  getExtractedInsights: () => import("$lib/types").ExtractedInsightSummary[];
  setExtractedInsights: (v: import("$lib/types").ExtractedInsightSummary[]) => void;
  getRetrievedMemoryContext: () => import("$lib/types").RetrievedMemoryContext | null;
  setRetrievedMemoryContext: (v: import("$lib/types").RetrievedMemoryContext | null) => void;
  getMemoryIndexedToast: () => {
    message: string;
    timestamp: string;
    details?: MemoryActivityData;
  } | null;
  setMemoryIndexedToast: (
    v: {
      message: string;
      timestamp: string;
      details?: MemoryActivityData;
    } | null,
  ) => void;
  batcher: SessionStoreContext["batcher"];
  enrichmentTracker: SessionStoreContext["enrichmentTracker"];
  interruptManager: SessionStoreContext["interruptManager"];
  assistantIdToToolId: SessionStoreContext["assistantIdToToolId"];
  pendingAssistantChunks: SessionStoreContext["pendingAssistantChunks"];
  assistantSnapshots: SessionStoreContext["assistantSnapshots"];
  statusMessageItemIds: SessionStoreContext["statusMessageItemIds"];
  getInvocationConfig: () => InvocationConfig;
  setInvocationConfig: (v: InvocationConfig) => void;
  getMemoryConfig: () => MemoryConfig;
  getMemoryConfigBase: () => InvocationConfig["memory_config"] | undefined;
  flushPendingStreams: () => void;
  showMemoryIndexedToast: (message: string, details?: MemoryActivityData) => void;
  resetEnrichmentPhaseTracking: () => void;
  finalizeActiveExecutionPhaseChips: (terminalPhase: "complete" | "failed") => void;
}

export function createSessionStoreContext(
  params: CreateSessionStoreContextParams,
): SessionStoreContext {
  return {
    getSession: params.getSession,
    setSession: params.setSession,
    getChatFlowItems: params.getChatFlowItems,
    setChatFlowItems: params.setChatFlowItems,
    getToolCards: params.getToolCards,
    setToolCards: params.setToolCards,
    getScopeHookFirings: params.getScopeHookFirings,
    setScopeHookFirings: params.setScopeHookFirings,
    getEvents: params.getEvents,
    setEvents: params.setEvents,
    getLoading: params.getLoading,
    setLoading: params.setLoading,
    getError: params.getError,
    setError: params.setError,
    getRootAssistantId: params.getRootAssistantId,
    setRootAssistantId: params.setRootAssistantId,
    getStreamingAssistantItemId: params.getStreamingAssistantItemId,
    setStreamingAssistantItemId: params.setStreamingAssistantItemId,
    getInterruptCards: params.getInterruptCards,
    setInterruptCards: params.setInterruptCards,
    getCurrentPhase: params.getCurrentPhase,
    setCurrentPhase: params.setCurrentPhase,
    getCurrentPhaseMessage: params.getCurrentPhaseMessage,
    setCurrentPhaseMessage: params.setCurrentPhaseMessage,
    getProcessingScopeKey: params.getProcessingScopeKey,
    setProcessingScopeKey: params.setProcessingScopeKey,
    getProcessingScopePriority: params.getProcessingScopePriority,
    setProcessingScopePriority: params.setProcessingScopePriority,
    getExtractedSkills: params.getExtractedSkills,
    setExtractedSkills: params.setExtractedSkills,
    getExtractedInsights: params.getExtractedInsights,
    setExtractedInsights: params.setExtractedInsights,
    getRetrievedMemoryContext: params.getRetrievedMemoryContext,
    setRetrievedMemoryContext: params.setRetrievedMemoryContext,
    getMemoryIndexedToast: params.getMemoryIndexedToast,
    setMemoryIndexedToast: params.setMemoryIndexedToast,
    batcher: params.batcher,
    enrichmentTracker: params.enrichmentTracker,
    interruptManager: params.interruptManager,
    assistantIdToToolId: params.assistantIdToToolId,
    pendingAssistantChunks: params.pendingAssistantChunks,
    assistantSnapshots: params.assistantSnapshots,
    statusMessageItemIds: params.statusMessageItemIds,
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
