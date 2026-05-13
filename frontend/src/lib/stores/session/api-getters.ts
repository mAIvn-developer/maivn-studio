import type {
  ChatFlowFilters,
  ChatFlowItem,
  ExtractedInsightSummary,
  ExtractedSkillSummary,
  HookFiring,
  InterruptData,
  InterruptStyle,
  InvocationConfig,
  MemoryActivityData,
  MemoryConfig,
  RetrievedMemoryContext,
  Session,
  ToolCard,
  UIEvent,
} from "$lib/types";

interface CreateSessionApiGettersParams {
  getSession: () => Session | null;
  getChatFlowItems: () => ChatFlowItem[];
  getToolCards: () => Map<string, ToolCard>;
  getScopeHookFirings: () => Map<string, HookFiring[]>;
  getEvents: () => UIEvent[];
  getLoading: () => boolean;
  getError: () => string | null;
  getEventSource: () => EventSource | null;
  getMessageType: () => import("$lib/types").SendableMessageType;
  getPrivateData: () => Record<string, unknown>;
  getFilters: () => ChatFlowFilters;
  getInvocationConfig: () => InvocationConfig;
  getCurrentPhase: () => string | null;
  getCurrentPhaseMessage: () => string | null;
  getMemoryIndexedToast: () => {
    message: string;
    timestamp: string;
    details?: MemoryActivityData;
  } | null;
  getExtractedSkills: () => ExtractedSkillSummary[];
  getExtractedInsights: () => ExtractedInsightSummary[];
  getRetrievedMemoryContext: () => RetrievedMemoryContext | null;
  getMemoryConfig: () => MemoryConfig;
  getInterruptStyle: () => InterruptStyle;
  getInterruptCards: () => Map<string, InterruptData>;
}

export function createSessionApiGetters(params: CreateSessionApiGettersParams) {
  return {
    getSession: params.getSession,
    getChatFlowItems: params.getChatFlowItems,
    getToolCards: params.getToolCards,
    getScopeHookFirings: params.getScopeHookFirings,
    getEvents: params.getEvents,
    getLoading: params.getLoading,
    getError: params.getError,
    getEventSource: params.getEventSource,
    getMessageType: params.getMessageType,
    getPrivateData: params.getPrivateData,
    getFilters: params.getFilters,
    getInvocationConfig: params.getInvocationConfig,
    getCurrentPhase: params.getCurrentPhase,
    getCurrentPhaseMessage: params.getCurrentPhaseMessage,
    getMemoryIndexedToast: params.getMemoryIndexedToast,
    getExtractedSkills: params.getExtractedSkills,
    getExtractedInsights: params.getExtractedInsights,
    getRetrievedMemoryContext: params.getRetrievedMemoryContext,
    getMemoryConfig: params.getMemoryConfig,
    getInterruptStyle: params.getInterruptStyle,
    getInterruptCards: params.getInterruptCards,
  };
}
