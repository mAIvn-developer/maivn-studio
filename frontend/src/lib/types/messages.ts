import type { TokenUsage } from "./session";

// MARK: Message Types

export type MessageType = "human" | "ai" | "system" | "tool" | "status" | "redacted";
export type SendableMessageType = "human" | "redacted";

export interface MessageAttachmentPayload {
  name?: string;
  mime_type?: string;
  content_base64?: string;
  source_url?: string;
  sharing_scope?: string;
  binding_type?: string;
  source_type?: string;
  description?: string;
  tags?: string[];
}

// MARK: Message

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  messageType: MessageType;
  content: string;
  timestamp: string;
  metadata?: MessageMetadata;
  structuredResult?: unknown; // Structured output result from session_complete
  sessionDetails?: SessionDetails; // Stats from SDK invocation (duration, tokens)
}

export interface MessageMetadata {
  toolCallId?: string;
  toolName?: string;
  isStreaming?: boolean;
  queuedForNextTurn?: boolean;
}

// MARK: Session Details

// SessionDetails contains stats from a single SDK invocation (session)
export interface SessionDetails {
  duration_ms?: number;
  token_usage?: TokenUsage;
}
