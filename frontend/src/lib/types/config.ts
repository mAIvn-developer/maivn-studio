import type { InvocationMemoryConfig } from "./memory";
import type { MessageType } from "./messages";

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
  demoId: string;
  messageType: MessageType;
  createdAt: string;
}

// MARK: Filter/Control Types

export type ChatFlowFilter = "all" | "messages" | "tools";
export type ToolStatusFilter = "all" | "pending" | "executing" | "completed" | "failed";

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

export interface InvocationConfig {
  model?: ModelTier;
  reasoning?: ReasoningLevel;
  force_final_tool: boolean;
  stream_response?: boolean;
  status_messages?: boolean;
  targeted_tools?: string[];
  metadata?: Record<string, unknown>;
  memory_config?: InvocationMemoryConfig;
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
}

// MARK: Structured Output Types

export interface StructuredOutputConfig {
  enabled: boolean;
  schema?: StructuredOutputSchema;
  selectedTool?: string; // Tool name to use as model for output
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
