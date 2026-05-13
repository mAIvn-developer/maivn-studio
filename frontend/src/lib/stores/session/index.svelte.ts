import type {
  ChatFlowFilters,
  ChatFlowItem,
  InterruptData,
  InterruptStyle,
  InvocationConfig,
  MemoryActivityData,
  MemoryConfig,
  SendableMessageType,
  Session,
  ToolCard,
  UIEvent,
} from "$lib/types";
import { EnrichmentTracker } from "../utils/enrichmentTracker";
import { InterruptManager } from "../utils/interruptManager";
import { ToolCardBatcher } from "../utils/toolCardBatcher";

import { createSessionActionBindings } from "./actions/action-bindings";
import { createSessionApiGetters } from "./api-getters";
import { createSessionBatcherRuntime } from "./batcher-runtime";
import { createSessionStoreContext } from "./context";
import { createSessionContextRuntime } from "./context-runtime";
import {
  createDefaultFilters,
  createDefaultInvocationConfig,
  loadInterruptStyle,
} from "./defaults";
import { createEnrichmentRuntime } from "./enrichment-runtime";
import { createSessionLocalActions } from "./actions/local-actions";
import { createDefaultMemoryConfig } from "./memory";
import { createSessionStateAccessors } from "./state-accessors";
import { createSessionStoreApi } from "./store-api";
import type { SessionStoreContext } from "./types";
import { createSessionStoreActions } from "./actions/wiring";

// Re-export pure functions used by tests and other consumers
export {
  coerceMemoryActivityData,
  coerceRedactionActivityData,
  normalizeNonNegativeNumber,
} from "./memory";
export { computeAccumulatedStats, computeEventSummary, filterChatFlowItems } from "./tools";
export type { AccumulatedStats } from "./types";

// MARK: State

let session = $state<Session | null>(null);
let chatFlowItems = $state<ChatFlowItem[]>([]);
let toolCards = $state<Map<string, ToolCard>>(new Map());
// Scope-level hook firings keyed by `${target_type}:${target_id_or_name}`.
// Tool hooks attach to their owning ToolCard.hookFirings; this map holds
// the Agent/Swarm firings that the ScopeGroupCard renders as
// header/footer markers.
let scopeHookFirings = $state<Map<string, import("$lib/types").HookFiring[]>>(new Map());
let events = $state<UIEvent[]>([]);
let loading = $state(false);
let error = $state<string | null>(null);
let eventSource = $state<EventSource | null>(null);
let messageType = $state<SendableMessageType>("human");
let privateData = $state<Record<string, unknown>>({});
let filters = $state<ChatFlowFilters>(createDefaultFilters());
let invocationConfig = $state<InvocationConfig>(createDefaultInvocationConfig());

// MARK: Interrupt State

let interruptStyle = $state<InterruptStyle>(loadInterruptStyle());
let interruptCards = $state<Map<string, InterruptData>>(new Map());

// MARK: Utility Instances

const batcher = new ToolCardBatcher();
const enrichmentTracker = new EnrichmentTracker();
const interruptManager = new InterruptManager();

let rootAssistantId = $state<string | null>(null);
let streamingAssistantItemId = $state<string | null>(null);
const assistantIdToToolId = new Map<string, string>();
const pendingAssistantChunks = new Map<string, string>();
const assistantSnapshots = new Map<string, string>();

// MARK: Enrichment Phase State

let currentPhase = $state<string | null>(null);
let currentPhaseMessage = $state<string | null>(null);
let processingScopeKey = $state<string | null>(null);
let processingScopePriority = $state<number>(-1);
let memoryIndexedToast = $state<{
  message: string;
  timestamp: string;
  details?: MemoryActivityData;
} | null>(null);
let memoryIndexedToastTimer: ReturnType<typeof setTimeout> | null = null;

// MARK: Memory State

let extractedSkills = $state<import("$lib/types").ExtractedSkillSummary[]>([]);
let extractedInsights = $state<import("$lib/types").ExtractedInsightSummary[]>([]);
let retrievedMemoryContext = $state<import("$lib/types").RetrievedMemoryContext | null>(null);
let memoryConfigBase = $state<InvocationConfig["memory_config"] | undefined>(undefined);
let memoryConfig = $state<MemoryConfig>(createDefaultMemoryConfig());

// MARK: Enrichment Helpers

const {
  resetEnrichmentPhaseTracking,
  finalizeActiveExecutionPhaseChips,
  resetEnrichmentTracking,
  clearMemoryIndexedToastTimer,
  showMemoryIndexedToast,
} = createEnrichmentRuntime({
  enrichmentTracker,
  getChatFlowItems: () => chatFlowItems,
  setChatFlowItems: (items) => {
    chatFlowItems = items;
  },
  setCurrentPhase: (v) => {
    currentPhase = v;
  },
  setCurrentPhaseMessage: (v) => {
    currentPhaseMessage = v;
  },
  setProcessingScopeKey: (v) => {
    processingScopeKey = v;
  },
  setProcessingScopePriority: (v) => {
    processingScopePriority = v;
  },
  setExtractedSkills: (v) => {
    extractedSkills = v;
  },
  setExtractedInsights: (v) => {
    extractedInsights = v;
  },
  setRetrievedMemoryContext: (v) => {
    retrievedMemoryContext = v;
  },
  setMemoryIndexedToast: (v) => {
    memoryIndexedToast = v;
  },
  getMemoryIndexedToastTimer: () => memoryIndexedToastTimer,
  setMemoryIndexedToastTimer: (timer) => {
    memoryIndexedToastTimer = timer;
  },
});

// MARK: Batcher Wiring

const { flushPendingStreams } = createSessionBatcherRuntime({
  batcher,
  getToolCards: () => toolCards,
  setToolCards: (cards) => {
    toolCards = cards;
  },
  getChatFlowItems: () => chatFlowItems,
  setChatFlowItems: (items) => {
    chatFlowItems = items;
  },
});

// MARK: Store Context

const ctx: SessionStoreContext = createSessionStoreContext({
  ...createSessionStateAccessors({
    getSession: () => session,
    setSession: (s) => {
      session = s;
    },
    getChatFlowItems: () => chatFlowItems,
    setChatFlowItems: (items) => {
      chatFlowItems = items;
    },
    getToolCards: () => toolCards,
    setToolCards: (cards) => {
      toolCards = cards;
    },
    getScopeHookFirings: () => scopeHookFirings,
    setScopeHookFirings: (firings) => {
      scopeHookFirings = firings;
    },
    getEvents: () => events,
    setEvents: (e) => {
      events = e;
    },
    getLoading: () => loading,
    setLoading: (v) => {
      loading = v;
    },
    getError: () => error,
    setError: (v) => {
      error = v;
    },
    getRootAssistantId: () => rootAssistantId,
    setRootAssistantId: (v) => {
      rootAssistantId = v;
    },
    getStreamingAssistantItemId: () => streamingAssistantItemId,
    setStreamingAssistantItemId: (v) => {
      streamingAssistantItemId = v;
    },
    getInterruptCards: () => interruptCards,
    setInterruptCards: (cards) => {
      interruptCards = cards;
    },
    getCurrentPhase: () => currentPhase,
    setCurrentPhase: (v) => {
      currentPhase = v;
    },
    getCurrentPhaseMessage: () => currentPhaseMessage,
    setCurrentPhaseMessage: (v) => {
      currentPhaseMessage = v;
    },
    getProcessingScopeKey: () => processingScopeKey,
    setProcessingScopeKey: (v) => {
      processingScopeKey = v;
    },
    getProcessingScopePriority: () => processingScopePriority,
    setProcessingScopePriority: (v) => {
      processingScopePriority = v;
    },
    getExtractedSkills: () => extractedSkills,
    setExtractedSkills: (v) => {
      extractedSkills = v;
    },
    getExtractedInsights: () => extractedInsights,
    setExtractedInsights: (v) => {
      extractedInsights = v;
    },
    getRetrievedMemoryContext: () => retrievedMemoryContext,
    setRetrievedMemoryContext: (v) => {
      retrievedMemoryContext = v;
    },
    getMemoryIndexedToast: () => memoryIndexedToast,
    setMemoryIndexedToast: (v) => {
      memoryIndexedToast = v;
    },
  }),
  ...createSessionContextRuntime({
    batcher,
    enrichmentTracker,
    interruptManager,
    assistantIdToToolId,
    pendingAssistantChunks,
    assistantSnapshots,
    getInvocationConfig: () => invocationConfig,
    setInvocationConfig: (v) => {
      invocationConfig = v;
    },
    getMemoryConfig: () => memoryConfig,
    getMemoryConfigBase: () => memoryConfigBase,
    flushPendingStreams,
    showMemoryIndexedToast,
    resetEnrichmentPhaseTracking,
    finalizeActiveExecutionPhaseChips,
  }),
});

// MARK: Session Management

export function useSession() {
  const {
    startSession,
    send,
    end,
    cancel,
    reset,
    submitInterrupt,
    cancelInterrupt,
    setInvocationConfigAction,
    setInterruptStyleAction,
  } = createSessionStoreActions({
    ...createSessionActionBindings({
      ctx,
      getEventSource: () => eventSource,
      setEventSource: (es) => {
        eventSource = es;
      },
      clearMemoryIndexedToastTimer,
      getMessageType: () => messageType,
      getPrivateData: () => privateData,
      setPrivateData: (data) => {
        privateData = data;
      },
      getMemoryConfig: () => memoryConfig,
      setMemoryConfig: (config) => {
        memoryConfig = config;
      },
      getMemoryConfigBase: () => memoryConfigBase,
      setMemoryConfigBase: (v) => {
        memoryConfigBase = v;
      },
      getInvocationConfig: () => invocationConfig,
      setInvocationConfig: (config) => {
        invocationConfig = config;
      },
      resetEnrichmentTracking,
      setInterruptStyle: (style) => {
        interruptStyle = style;
      },
    }),
  });

  const {
    setMessageType,
    setPrivateData,
    setFilters,
    clearError,
    setMemoryConfigAction,
    getPendingInterrupts,
    getAllInterrupts,
  } = createSessionLocalActions({
    setMessageTypeState: (type) => {
      messageType = type;
    },
    setPrivateDataState: (data) => {
      privateData = data;
    },
    getFilters: () => filters,
    setFiltersState: (nextFilters) => {
      filters = nextFilters;
    },
    setErrorState: (nextError) => {
      error = nextError;
    },
    setMemoryConfigState: (config) => {
      memoryConfig = config;
    },
    getPendingInterrupts: () => interruptManager.getPending(),
    getAllInterrupts: () => interruptManager.getAll(),
  });

  return createSessionStoreApi({
    ...createSessionApiGetters({
      getSession: () => session,
      getChatFlowItems: () => chatFlowItems,
      getToolCards: () => toolCards,
      getScopeHookFirings: () => scopeHookFirings,
      getEvents: () => events,
      getLoading: () => loading,
      getError: () => error,
      getEventSource: () => eventSource,
      getMessageType: () => messageType,
      getPrivateData: () => privateData,
      getFilters: () => filters,
      getInvocationConfig: () => invocationConfig,
      getCurrentPhase: () => currentPhase,
      getCurrentPhaseMessage: () => currentPhaseMessage,
      getMemoryIndexedToast: () => memoryIndexedToast,
      getExtractedSkills: () => extractedSkills,
      getExtractedInsights: () => extractedInsights,
      getRetrievedMemoryContext: () => retrievedMemoryContext,
      getMemoryConfig: () => memoryConfig,
      getInterruptStyle: () => interruptStyle,
      getInterruptCards: () => interruptCards,
    }),
    getPendingInterrupts,
    getAllInterrupts,
    startSession,
    send,
    end,
    cancel,
    reset,
    setMessageType,
    setPrivateData,
    setFilters,
    setInvocationConfig: setInvocationConfigAction,
    clearError,
    submitInterrupt,
    cancelInterrupt,
    setInterruptStyle: setInterruptStyleAction,
    setMemoryConfig: setMemoryConfigAction,
  });
}
