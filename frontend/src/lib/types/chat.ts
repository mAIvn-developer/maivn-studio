import type { Message } from "./messages";
import type { ExecutionStatus, TokenUsage } from "./session";
import type { InterruptData } from "./interrupts";
import type {
  ExtractedSkillSummary,
  ExtractedInsightSummary,
  MemoryActivityMode,
  MemoryActivitySource,
  MemoryActivityStatus,
  MemoryLevel,
  MemoryPersistenceMode,
} from "./memory";

// MARK: Chat Flow Types

export type ChatFlowItemType =
  | "message"
  | "tool_card"
  | "interrupt_card"
  | "phase_chip"
  | "batch_result";

export interface MemoryActivityData {
  // `mode`, `source`, and `status` are open-enum unions (see
  // `MemoryActivityMode`/`MemoryActivitySource`/`MemoryActivityStatus` in
  // `./memory`): each lists the documented-known server vocabulary for
  // autocomplete while staying assignable from any `string`, because these
  // values arrive as opaque dict entries forwarded verbatim from the maivn
  // memory enrichment builders and the server may emit others. `memoryLevel`/
  // `policyMode` mirror the canonical `maivn_shared` Literal unions; see
  // `coerceMemoryActivityData` for the wire-boundary narrowing (the open enums
  // need none — they accept any trimmed string).
  mode?: MemoryActivityMode;
  source?: MemoryActivitySource;
  status?: MemoryActivityStatus;
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
  memoryLevel?: MemoryLevel;
  policyMode?: MemoryPersistenceMode;
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

/**
 * Attribution for a `reevaluate_accrued` chip. `source="dependency"` means a
 * `@depends_on_reevaluate` boundary forced the re-plan (the server synthesised
 * it); `source="llm"` means the LLM itself asked to re-plan. The chip should
 * make this distinction visible so users can tell deterministic enforcement
 * from model-driven cycles.
 */
export interface ReevaluateChipData {
  source: "dependency" | "llm";
  triggerTool?: string;
  targetTool?: string;
  cycle?: number;
  collectedCount?: number;
}

export interface PhaseChipData {
  phase: string;
  message: string;
  timestamp: string;
  memory?: MemoryActivityData;
  redaction?: RedactionActivityData;
  reevaluate?: ReevaluateChipData;
  // Scope routing (set when session belongs to a swarm or swarm agent)
  scopeId?: string; // Agent ID or Swarm name
  scopeName?: string; // Display name
  scopeType?: "agent" | "swarm"; // Determines which scope card to route to
}

// MARK: Chat Flow Item

/**
 * What triggered this item to enter the flow. Default `"user"` covers the
 * normal case (the developer typing in the composer). `"schedule"` marks
 * fires that came from a cron schedule so the renderer can apply a badge
 * and a distinct border. The server is expected to populate this on
 * messages whose session was created by a scheduled fire — until that
 * lands, the field stays unset and the UI degrades to the user origin.
 */
export type ChatFlowOrigin = "user" | "schedule";

/**
 * Fields shared by every {@link ChatFlowItem} variant. The discriminant
 * (`type`) and its correlated `data` payload live on the per-variant
 * interfaces below; everything here is identical across variants.
 */
interface ChatFlowItemBase {
  id: string;
  timestamp: string;
  /** Optional — defaults to "user". Set to "schedule" for cron-triggered items. */
  origin?: ChatFlowOrigin;
  /** Optional — fire ID from the schedule that triggered this item, if any. */
  scheduleFireId?: string;
}

export interface MessageFlowItem extends ChatFlowItemBase {
  type: "message";
  data: Message;
}

export interface ToolCardFlowItem extends ChatFlowItemBase {
  type: "tool_card";
  data: ToolCard;
}

export interface InterruptFlowItem extends ChatFlowItemBase {
  type: "interrupt_card";
  data: InterruptData;
}

export interface PhaseChipFlowItem extends ChatFlowItemBase {
  type: "phase_chip";
  data: PhaseChipData;
}

export interface BatchResultFlowItem extends ChatFlowItemBase {
  type: "batch_result";
  data: BatchResult;
}

/**
 * Discriminated union over `type`. Narrowing on `item.type` correlates the
 * `data` payload to its concrete shape, removing the need to cast `data`.
 */
export type ChatFlowItem =
  | MessageFlowItem
  | ToolCardFlowItem
  | InterruptFlowItem
  | PhaseChipFlowItem
  | BatchResultFlowItem;

// MARK: Batch Result Types

export type BatchResultStatus = "running" | "completed" | "failed";
export type BatchResultItemStatus = "pending" | "completed" | "failed";

export interface BatchResultItem {
  index: number;
  label?: string;
  input: string;
  status: BatchResultItemStatus;
  variant?: string;
  model?: string;
  reasoning?: string;
  responses?: string[];
  response?: string;
  result?: unknown;
  error?: string;
  duration_ms?: number;
  token_usage?: TokenUsage;
}

export interface BatchResult {
  batchId: string;
  mode: "batch" | "abatch";
  status: BatchResultStatus;
  itemCount: number;
  maxConcurrency?: number;
  asyncMode: boolean;
  startedAt: string;
  completedAt?: string;
  duration_ms?: number;
  token_usage?: TokenUsage;
  error?: string;
  items: BatchResultItem[];
}

// MARK: Hook Firing

/**
 * One firing of a developer-registered scope or tool hook callback,
 * emitted by the SDK as a ``hook_fired`` event.
 *
 * Rendered as a persistent header (``stage === "before"``) or footer
 * (``stage === "after"``) on the matching tool card or scope card.
 */
export type HookSource = "tool" | "scope" | "swarm";

export interface HookFiring {
  name: string;
  stage: "before" | "after";
  status: "completed" | "failed";
  /** Which on-screen card the firing attaches to. */
  targetType: "tool" | "agent" | "swarm";
  targetId?: string;
  targetName?: string;
  /**
   * Which level defined the hook (``"tool"`` / ``"scope"`` / ``"swarm"``).
   * Lets the UI label pills even when multiple sources hook the same target.
   * Optional for backward compatibility with older SDKs.
   */
  source?: HookSource;
  error?: string;
  elapsedMs?: number;
  timestamp: string;
}

// MARK: Tool Card Types

export type ToolCardStatus = ExecutionStatus;
export type ToolType = "func" | "method" | "model" | "mcp" | "agent" | "system";

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
  /** Persistent hook-firing markers — rendered as header (before) / footer (after) on the card. */
  hookFirings?: HookFiring[];
}
