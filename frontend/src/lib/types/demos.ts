import type {
  InvocationConfig,
  InvocationOrchestrationConfig,
  InvocationSystemToolsConfig,
} from "./config";
import type { InvocationMemoryConfig } from "./memory";
import type { PrivateDataField } from "./config";

// MARK: Demo Types

export interface DemoVariant {
  args: string[];
  description: string;
  private_data?: Record<string, string | number | boolean>;
}

export interface Demo {
  id: string;
  name: string;
  description: string;
  module: string;
  category: string;
  tags: string[];
  variants: Record<string, DemoVariant>;
  source?: "configured" | "discovered";
}

export interface DemoDetails extends Demo {
  agents: AgentInfo[];
  swarms: SwarmInfo[];
  tools: ToolInfo[];
  prompts: PromptInfo[];
  privateDataSchema: PrivateDataField[];
  privateDataDefaults?: Record<string, string | number | boolean>;
  defaultInvocation?: Partial<InvocationConfig>;
  runtime_tool_count?: number;
}

// MARK: Dependency Info

export interface DependencyInfo {
  name: string;
  dependency_type: string;
  arg_name: string;
  data_key?: string;
  tool_id?: string;
  agent_id?: string;
  prompt?: string;
  input_type?: string;
}

// MARK: Agent & Swarm Info

export interface AgentInfo {
  name: string;
  description: string;
  system_prompt?: string;
  tags: string[];
  memory_config?: InvocationMemoryConfig;
  system_tools_config?: InvocationSystemToolsConfig;
  orchestration_config?: InvocationOrchestrationConfig;
  private_data?: Record<string, unknown>;
  tool_count: number;
  runtime_tool_count: number;
  timeout?: number;
  max_results?: number;
  use_as_final_output: boolean;
  included_nested_synthesis: boolean | "auto";
  allow_private_in_system_tools: boolean;
  hook_execution_mode: string;
  has_before_hook: boolean;
  has_after_hook: boolean;
  mcp_server_names: string[];
  private_data_keys: string[];
  is_swarm_member: boolean;
  swarm?: string;
}

export interface SwarmInfo {
  name: string;
  description: string;
  system_prompt?: string;
  tags: string[];
  memory_config?: InvocationMemoryConfig;
  system_tools_config?: InvocationSystemToolsConfig;
  orchestration_config?: InvocationOrchestrationConfig;
  allow_private_in_system_tools: boolean;
  private_data?: Record<string, unknown>;
  agent_count: number;
  agent_names: string[];
  tool_count: number;
  runtime_tool_count: number;
  private_data_keys: string[];
}

// MARK: Tool & Prompt Info

export interface ToolInfo {
  name: string;
  description: string;
  agent: string;
  tool_type: string;
  final_tool: boolean;
  always_execute: boolean;
  tags: string[];
  dependencies: DependencyInfo[];
  args_schema?: Record<string, unknown>;
}

export interface PromptInfo {
  id: string;
  name: string;
  content: string;
  description: string;
  is_default: boolean;
  source: string;
  structured_output?: string; // Tool name for structured output
  message_type?: string; // Auto-select message type (human, redacted)
  variant?: string; // Auto-select variant when prompt is chosen
}

// MARK: Repo Discovery Types

export interface RepoScanItem {
  id: string;
  name: string;
  description: string;
  module: string;
  category: string;
  tags: string[];
  file_path: string;
  discovery_path: string;
  agents: string[];
  swarms: string[];
}

export interface RepoScanSelection {
  file_path: string;
  discovery_path: string;
}
