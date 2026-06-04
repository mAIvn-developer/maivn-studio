import type { InvocationMemoryConfig } from "./memory";
import type { MessageType } from "./messages";
import type { ExecutionStatus } from "./session";

// MARK: Private Data Types

export interface PrivateDataField {
  key: string;
  label: string;
  type: "string" | "number" | "boolean";
  required: boolean;
  default_value?: string | number | boolean;
  description?: string;
}

// MARK: Saved Prompt Types

export interface SavedPrompt {
  id: string;
  name: string;
  content: string;
  description: string;
  appId: string;
  messageType: MessageType;
  createdAt: string;
}

// MARK: Filter/Control Types

export type ChatFlowFilter = "all" | "messages" | "tools";
export type ToolStatusFilter = "all" | ExecutionStatus;

export interface ChatFlowFilters {
  itemType: ChatFlowFilter;
  toolStatus: ToolStatusFilter;
  expandAllCards: boolean;
  showToolArgs: boolean;
  richResultDisplay: boolean;
  showStructuredOutput: boolean;
  showSessionDetails: boolean;
}

// MARK: Model & Invocation Config

export type ModelTier = "fast" | "balanced" | "max";
export type ReasoningLevel = "minimal" | "low" | "medium" | "high";
export type InvocationMode = "stream" | "invoke";

export interface InvocationSystemToolsConfig {
  allowed_tools?: string[];
  approved_compose_artifact_targets?: string[] | boolean;
  allow_private_data?: boolean;
  allow_private_data_placeholders?: boolean;
}

export interface InvocationOrchestrationConfig {
  allow_reevaluate_loop?: boolean;
  max_cycles?: number;
}

export interface InvocationConfig {
  model?: ModelTier;
  reasoning?: ReasoningLevel;
  force_final_tool: boolean;
  stream_response?: boolean;
  status_messages?: boolean;
  targeted_tools?: string[];
  /**
   * Caps how many semantic-search results the agent considers when picking a
   * tool. Maps to `SessionRequest.max_results` server-side. Useful for apps
   * with a long tool catalog where the default cap would either be too loose
   * (too many irrelevant tools surface) or too tight.
   */
  max_results?: number;
  /**
   * Suppresses PII redaction for approved spans. Maps to
   * `SessionRequest.pii_whitelist`. The shape is the SDK's `PIIWhitelist`:
   * keys are entity types, values are arrays of literal strings to allow
   * through unredacted. Studio surfaces this as a JSON textarea inside the
   * advanced disclosure since the schema is small and writes are rare.
   */
  pii_whitelist?: Record<string, string[]>;
  metadata?: Record<string, unknown>;
  memory_config?: InvocationMemoryConfig;
  system_tools_config?: InvocationSystemToolsConfig;
  orchestration_config?: InvocationOrchestrationConfig;
  allow_private_in_system_tools?: boolean;
}

export interface BatchInvocationConfig {
  enabled: boolean;
  messages?: string[];
  rows?: BatchInvocationRow[];
  max_concurrency?: number;
  async_mode?: boolean;
}

export interface BatchInvocationRow {
  id?: string;
  label?: string;
  message: string;
  variant?: string;
  model?: InvocationConfig["model"];
  reasoning?: InvocationConfig["reasoning"];
  system_message?: string;
  targeted_tools?: string[];
  /**
   * Per-row overrides. Mirror the SDK's `BatchInvocationRow` so a single row
   * can opt into a different orchestration shape than the rest of the batch.
   * Undefined falls back to the global invocation config.
   */
  force_final_tool?: boolean;
  stream_response?: boolean;
}

// MARK: Structured Output Types

export interface StructuredOutputConfig {
  enabled: boolean;
  schema?: StructuredOutputSchema;
  selectedTool?: string; // Tool name to use as model for output
  /**
   * Force a specific LLM model tier just for the structured-output pass,
   * independent of the agent's main `InvocationConfig.model`. Common usage:
   * keep `balanced` for the conversational turn but pin `max` here so the
   * schema fill is more reliable on long, deeply-nested structures.
   */
  model?: ModelTier;
}

export interface StructuredOutputSchema {
  name: string;
  description?: string;
  schema: Record<string, unknown>; // JSON Schema
}

export interface ModelToolOption {
  name: string;
  description?: string;
  schema?: Record<string, unknown>;
}
