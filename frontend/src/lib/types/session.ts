// MARK: Execution Status

/**
 * Lifecycle status shared by tool/agent execution surfaces. Single source for
 * the `pending → executing → completed | failed` progression used by
 * `ToolCardStatus`, `ToolEvent.status`, and scope-group status rendering.
 */
export type ExecutionStatus = "pending" | "executing" | "completed" | "failed";

// MARK: Session Types

export interface Session {
  session_id: string;
  app_id: string;
  app_name: string;
  thread_id: string;
  variant: string | null;
  status: SessionStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  message_count: number;
  can_send_message: boolean;
  can_stage_message: boolean;
  queued_message_count: number;
  is_active: boolean;
  error: string | null;
}

export type SessionStatus =
  | "created"
  | "running"
  | "ready"
  | "waiting_input"
  | "completed"
  | "failed"
  | "cancelled";

// MARK: Event Types

export interface UIEvent {
  id: string;
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface ToolEvent {
  tool_name: string;
  tool_id: string;
  status: ExecutionStatus;
  args: Record<string, unknown>;
  result?: unknown;
  error?: string;
}

// MARK: Token Usage

export interface TokenUsage {
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  reasoning_tokens: number;
}

// MARK: Session Complete Event

// SessionCompleteEvent is emitted when an SDK invocation (session) completes
export interface SessionCompleteEvent {
  session_id: string;
  session_number: number; // Number of sessions in this thread
  responses: string[];
  can_continue: boolean;
  result?: unknown;
  duration_ms?: number;
  token_usage?: TokenUsage;
}

// MARK: Event Summary

export interface EventSummary {
  totalTools: number;
  pendingTools: number;
  executingTools: number;
  completedTools: number;
  failedTools: number;
  totalAgents: number;
  pendingAgents: number;
  executingAgents: number;
  completedAgents: number;
  failedAgents: number;
  totalMessages: number;
}
