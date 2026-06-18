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
import type { EnrichmentTracker } from "../utils/enrichmentTracker";
import type { InterruptManager } from "../utils/interruptManager";
import type { ToolCardBatcher } from "../utils/toolCardBatcher";

// MARK: Accumulated Stats

// Tracks aggregated stats across all SDK invocations (sessions) in the thread
export interface AccumulatedStats {
  totalDurationMs: number;
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  reasoningTokens: number;
  cacheReadTokens: number;
  cacheCreationTokens: number;
  sessionCount: number; // Number of SDK invocations in this thread
}

// MARK: Session Store Context

/**
 * Mutable context object passed to helper modules so they can read/write
 * reactive state owned by index.svelte.ts without needing runes themselves.
 *
 * Every field mirrors a $state variable declared in the index file.
 * The index file populates getters/setters that proxy to the real $state.
 */
export interface SessionStoreContext {
  // State accessors
  getSession: () => import("$lib/types").Session | null;
  setSession: (s: import("$lib/types").Session | null) => void;
  getChatFlowItems: () => ChatFlowItem[];
  setChatFlowItems: (items: ChatFlowItem[]) => void;
  getToolCards: () => Map<string, ToolCard>;
  setToolCards: (cards: Map<string, ToolCard>) => void;
  // Hook firings keyed by `${target_type}:${target_id_or_name}` — populated
  // by ``handleHookFired`` for scope-level (agent/swarm) hooks. Tool hooks
  // attach to ``ToolCard.hookFirings`` directly.
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

  // Enrichment phase state
  getCurrentPhase: () => string | null;
  setCurrentPhase: (v: string | null) => void;
  getCurrentPhaseMessage: () => string | null;
  setCurrentPhaseMessage: (v: string | null) => void;
  getProcessingScopeKey: () => string | null;
  setProcessingScopeKey: (v: string | null) => void;
  getProcessingScopePriority: () => number;
  setProcessingScopePriority: (v: number) => void;

  // Memory state
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

  // Utility instances
  batcher: ToolCardBatcher;
  enrichmentTracker: EnrichmentTracker;
  interruptManager: InterruptManager;
  assistantIdToToolId: Map<string, string>;
  pendingAssistantChunks: Map<string, string>;
  assistantSnapshots: Map<string, string>;
  statusMessageItemIds: Map<string, string>;

  // Invocation state
  getInvocationConfig: () => InvocationConfig;
  setInvocationConfig: (v: InvocationConfig) => void;
  getMemoryConfig: () => MemoryConfig;
  getMemoryConfigBase: () => InvocationConfig["memory_config"] | undefined;

  // Helpers provided by index
  flushPendingStreams: () => void;
  showMemoryIndexedToast: (message: string, details?: MemoryActivityData) => void;
  resetEnrichmentPhaseTracking: () => void;
  finalizeActiveExecutionPhaseChips: (terminalPhase: "complete" | "failed") => void;
}
