import type {
  ChatFlowItem,
  InterruptData,
  MemoryActivityData,
  Session,
  ToolCard,
  UIEvent,
} from "$lib/types";

interface CreateSessionStateAccessorsParams {
  getSession: () => Session | null;
  setSession: (session: Session | null) => void;
  getChatFlowItems: () => ChatFlowItem[];
  setChatFlowItems: (items: ChatFlowItem[]) => void;
  getToolCards: () => Map<string, ToolCard>;
  setToolCards: (cards: Map<string, ToolCard>) => void;
  getEvents: () => UIEvent[];
  setEvents: (events: UIEvent[]) => void;
  getLoading: () => boolean;
  setLoading: (loading: boolean) => void;
  getError: () => string | null;
  setError: (error: string | null) => void;
  getRootAssistantId: () => string | null;
  setRootAssistantId: (assistantId: string | null) => void;
  getStreamingAssistantItemId: () => string | null;
  setStreamingAssistantItemId: (assistantItemId: string | null) => void;
  getInterruptCards: () => Map<string, InterruptData>;
  setInterruptCards: (cards: Map<string, InterruptData>) => void;
  getCurrentPhase: () => string | null;
  setCurrentPhase: (phase: string | null) => void;
  getCurrentPhaseMessage: () => string | null;
  setCurrentPhaseMessage: (message: string | null) => void;
  getProcessingScopeKey: () => string | null;
  setProcessingScopeKey: (scopeKey: string | null) => void;
  getProcessingScopePriority: () => number;
  setProcessingScopePriority: (priority: number) => void;
  getExtractedSkills: () => import("$lib/types").ExtractedSkillSummary[];
  setExtractedSkills: (skills: import("$lib/types").ExtractedSkillSummary[]) => void;
  getExtractedInsights: () => import("$lib/types").ExtractedInsightSummary[];
  setExtractedInsights: (insights: import("$lib/types").ExtractedInsightSummary[]) => void;
  getRetrievedMemoryContext: () => import("$lib/types").RetrievedMemoryContext | null;
  setRetrievedMemoryContext: (context: import("$lib/types").RetrievedMemoryContext | null) => void;
  getMemoryIndexedToast: () => {
    message: string;
    timestamp: string;
    details?: MemoryActivityData;
  } | null;
  setMemoryIndexedToast: (
    toast: {
      message: string;
      timestamp: string;
      details?: MemoryActivityData;
    } | null,
  ) => void;
}

export function createSessionStateAccessors(params: CreateSessionStateAccessorsParams) {
  return {
    getSession: params.getSession,
    setSession: params.setSession,
    getChatFlowItems: params.getChatFlowItems,
    setChatFlowItems: params.setChatFlowItems,
    getToolCards: params.getToolCards,
    setToolCards: params.setToolCards,
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
  };
}
