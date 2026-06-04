import type {
  ChatFlowFilters,
  MemoryConfig,
  Message,
  MessageFlowItem,
  SendableMessageType,
} from "$lib/types";

import { computeAccumulatedStats, computeEventSummary, filterChatFlowItems } from "./tools";

interface CreateSessionStoreApiParams {
  getSession: () => import("$lib/types").Session | null;
  getChatFlowItems: () => import("$lib/types").ChatFlowItem[];
  getToolCards: () => Map<string, import("$lib/types").ToolCard>;
  getScopeHookFirings: () => Map<string, import("$lib/types").HookFiring[]>;
  getEvents: () => import("$lib/types").UIEvent[];
  getLoading: () => boolean;
  getError: () => string | null;
  getEventSource: () => EventSource | null;
  getMessageType: () => SendableMessageType;
  getPrivateData: () => Record<string, unknown>;
  getFilters: () => ChatFlowFilters;
  getInvocationConfig: () => import("$lib/types").InvocationConfig;
  getCurrentPhase: () => string | null;
  getCurrentPhaseMessage: () => string | null;
  getMemoryIndexedToast: () => {
    message: string;
    timestamp: string;
    details?: import("$lib/types").MemoryActivityData;
  } | null;
  getExtractedSkills: () => import("$lib/types").ExtractedSkillSummary[];
  getExtractedInsights: () => import("$lib/types").ExtractedInsightSummary[];
  getRetrievedMemoryContext: () => import("$lib/types").RetrievedMemoryContext | null;
  getMemoryConfig: () => MemoryConfig;
  getInterruptStyle: () => import("$lib/types").InterruptStyle;
  getInterruptCards: () => Map<string, import("$lib/types").InterruptData>;
  getPendingInterrupts: () => import("$lib/types").InterruptData[];
  getAllInterrupts: () => import("$lib/types").InterruptData[];
  startSession: (
    appId: string,
    initialMessage: string,
    options?: {
      variant?: string;
      messageType?: SendableMessageType;
      attachments?: import("$lib/types").MessageAttachmentPayload[];
      systemMessage?: string;
      privateData?: Record<string, unknown>;
      structuredOutput?: import("$lib/types").StructuredOutputConfig;
      batch?: import("$lib/types").BatchInvocationConfig;
    },
  ) => Promise<void>;
  send: (
    message: string,
    messageType?: SendableMessageType,
    structuredOutput?: import("$lib/types").StructuredOutputConfig,
    attachments?: import("$lib/types").MessageAttachmentPayload[],
    batch?: import("$lib/types").BatchInvocationConfig,
  ) => Promise<void>;
  end: () => Promise<void>;
  cancel: () => Promise<void>;
  reset: () => void;
  setMessageType: (type: SendableMessageType) => void;
  setPrivateData: (data: Record<string, unknown>) => void;
  setFilters: (newFilters: Partial<ChatFlowFilters>) => void;
  setInvocationConfig: (config: import("$lib/types").InvocationConfig) => void;
  clearError: () => void;
  submitInterrupt: (interruptId: string, value: string) => Promise<void>;
  cancelInterrupt: (interruptId: string) => void;
  setInterruptStyle: (style: import("$lib/types").InterruptStyle) => void;
  setMemoryConfig: (config: MemoryConfig) => void;
}

function getMessages(chatFlowItems: import("$lib/types").ChatFlowItem[]): Message[] {
  return chatFlowItems
    .filter((item): item is MessageFlowItem => item.type === "message")
    .map((item) => item.data);
}

export function createSessionStoreApi(params: CreateSessionStoreApiParams) {
  return {
    get session() {
      return params.getSession();
    },
    get hasActiveSession() {
      return params.getSession()?.is_active ?? false;
    },
    get chatFlowItems() {
      return params.getChatFlowItems();
    },
    get filteredChatFlowItems() {
      return filterChatFlowItems(params.getChatFlowItems(), params.getFilters());
    },
    get toolCards() {
      return params.getToolCards();
    },
    get scopeHookFirings() {
      return params.getScopeHookFirings();
    },
    get messages() {
      return getMessages(params.getChatFlowItems());
    },
    get events() {
      return params.getEvents();
    },
    get eventSummary() {
      return computeEventSummary(params.getChatFlowItems());
    },
    get accumulatedStats() {
      return computeAccumulatedStats(params.getChatFlowItems());
    },
    get loading() {
      return params.getLoading();
    },
    get canStageNext() {
      return params.getSession()?.can_stage_message ?? false;
    },
    get queuedMessageCount() {
      return params.getSession()?.queued_message_count ?? 0;
    },
    get error() {
      return params.getError();
    },
    get isConnected() {
      return params.getEventSource() !== null;
    },
    get messageType() {
      return params.getMessageType();
    },
    get privateData() {
      return params.getPrivateData();
    },
    get filters() {
      return params.getFilters();
    },
    get invocationConfig() {
      return params.getInvocationConfig();
    },
    get currentPhase() {
      return params.getCurrentPhase();
    },
    get currentPhaseMessage() {
      return params.getCurrentPhaseMessage();
    },
    get memoryIndexedToast() {
      return params.getMemoryIndexedToast();
    },
    get extractedSkills() {
      return params.getExtractedSkills();
    },
    get extractedInsights() {
      return params.getExtractedInsights();
    },
    get retrievedMemoryContext() {
      return params.getRetrievedMemoryContext();
    },
    get memoryConfig() {
      return params.getMemoryConfig();
    },
    get interruptStyle() {
      return params.getInterruptStyle();
    },
    get interruptCards() {
      return params.getInterruptCards();
    },
    get pendingInterrupts() {
      return params.getPendingInterrupts();
    },
    get allInterrupts() {
      return params.getAllInterrupts();
    },
    startSession: params.startSession,
    send: params.send,
    end: params.end,
    cancel: params.cancel,
    reset: params.reset,
    setMessageType: params.setMessageType,
    setPrivateData: params.setPrivateData,
    setFilters: params.setFilters,
    setInvocationConfig: params.setInvocationConfig,
    clearError: params.clearError,
    submitInterrupt: params.submitInterrupt,
    cancelInterrupt: params.cancelInterrupt,
    setInterruptStyle: params.setInterruptStyle,
    setMemoryConfig: params.setMemoryConfig,
  };
}
