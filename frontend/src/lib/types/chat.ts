import type { Message } from "./messages";
import type { InterruptData } from "./interrupts";
import type { ExtractedSkillSummary, ExtractedInsightSummary } from "./memory";

// MARK: Chat Flow Types

export type ChatFlowItemType = "message" | "tool_card" | "interrupt_card" | "phase_chip";

export interface MemoryActivityData {
  mode?: string;
  source?: string;
  status?: string;
  hitCount?: number;
  vectorHits?: number;
  keywordHits?: number;
  graphHits?: number;
  skillCount?: number;
  insightCount?: number;
  resourceCount?: number;
  vectorRows?: number;
  graphEdges?: number;
  traceEventCount?: number;
  latencyMs?: number;
  memoryLevel?: string;
  policyMode?: string;
  registeredCount?: number;
  reusedCount?: number;
  skippedCount?: number;
  totalBytes?: number;
  dedupReusedCount?: number;
  versionSupersededCount?: number;
  discoveryCount?: number;
  selectedCount?: number;
  chunkCount?: number;
  requestedResourceId?: string;
  requestedMaxResources?: number;
  requiredTagCount?: number;
  fullExtraction?: boolean;
  resourceIds?: string[];
  supersededResourceIds?: string[];
  extractedCount?: number;
  persistedCount?: number;
  skills?: ExtractedSkillSummary[];
  insights?: ExtractedInsightSummary[];
}

export interface RedactionActivityData {
  insertedKeys?: string[];
  addedPrivateData?: Record<string, unknown>;
  mergedPrivateData?: Record<string, unknown>;
  redactedMessageCount?: number;
  redactedValueCount?: number;
  matchedKnownPiiValues?: string[];
  unmatchedKnownPiiValues?: string[];
}

// MARK: Phase Chip

export interface PhaseChipData {
  phase: string;
  message: string;
  timestamp: string;
  memory?: MemoryActivityData;
  redaction?: RedactionActivityData;
  // Scope routing (set when session belongs to a swarm or swarm agent)
  scopeId?: string; // Agent ID or Swarm name
  scopeName?: string; // Display name
  scopeType?: "agent" | "swarm"; // Determines which scope card to route to
}

// MARK: Chat Flow Item

export interface ChatFlowItem {
  id: string;
  type: ChatFlowItemType;
  timestamp: string;
  data: Message | ToolCard | InterruptData | PhaseChipData;
}

// MARK: Tool Card Types

export type ToolCardStatus = "pending" | "executing" | "completed" | "failed";
export type ToolType = "func" | "model" | "mcp" | "agent" | "system";

export interface ToolCard {
  toolId: string;
  toolName: string;
  toolType: ToolType;
  status: ToolCardStatus;
  args: Record<string, unknown>;
  result?: unknown;
  error?: string;
  startedAt: string;
  completedAt?: string;
  isStreaming: boolean;
  streamContent?: string;
  isSystemTool: boolean;
  agentName?: string;
  swarmName?: string;
}
