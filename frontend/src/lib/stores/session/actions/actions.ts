import { createSession, sendMessage } from "$lib/api_client/sessions";
import type {
  BatchInvocationConfig,
  InvocationConfig,
  MemoryConfig,
  MessageAttachmentPayload,
  SendableMessageType,
  StructuredOutputConfig,
} from "$lib/types";
import {
  appendUserMessageToChatFlow,
  buildEffectiveInvocationConfig,
  clearSessionRuntimeState,
} from "./action-helpers";
import type { SessionStoreContext } from "../types";

// MARK: Session Lifecycle

export function createStartSession(
  ctx: SessionStoreContext,
  getMessageType: () => SendableMessageType,
  getPrivateData: () => Record<string, unknown>,
  getMemoryConfig: () => MemoryConfig,
  getMemoryConfigBase: () => InvocationConfig["memory_config"] | undefined,
  getInvocationConfig: () => InvocationConfig,
  connectToEventStream: (sessionId: string) => void,
  resetEnrichmentTracking: () => void,
  clearMemoryIndexedToastTimer: () => void,
) {
  return async function startSession(
    appId: string,
    initialMessage: string,
    options?: {
      variant?: string;
      messageType?: SendableMessageType;
      attachments?: MessageAttachmentPayload[];
      systemMessage?: string;
      privateData?: Record<string, unknown>;
      structuredOutput?: StructuredOutputConfig;
      batch?: BatchInvocationConfig;
    },
  ) {
    ctx.setLoading(true);
    ctx.setError(null);
    clearSessionRuntimeState(ctx, resetEnrichmentTracking, clearMemoryIndexedToastTimer);
    ctx.interruptManager.reset();
    ctx.setInterruptCards(new Map());

    const msgType = options?.messageType ?? getMessageType();

    try {
      ctx.setChatFlowItems([]);
      appendUserMessageToChatFlow(ctx, initialMessage, msgType);

      const effectiveInvocation = buildEffectiveInvocationConfig(
        getInvocationConfig(),
        getMemoryConfig(),
        getMemoryConfigBase(),
      );

      // Create session
      const session = await createSession(appId, initialMessage, {
        variant: options?.variant,
        messageType: msgType,
        attachments: options?.attachments,
        privateData: options?.privateData ?? getPrivateData(),
        structuredOutput: options?.structuredOutput,
        systemMessage: options?.systemMessage,
        invocation: effectiveInvocation,
        batch: options?.batch,
      });

      ctx.setSession(session);

      // Connect to event stream
      // NOTE: loading stays true until session_end event is received
      if (!session) {
        throw new Error("Session creation failed");
      }
      connectToEventStream(session.session_id);
    } catch (e) {
      ctx.setError(e instanceof Error ? e.message : "Failed to start session");
      ctx.setSession(null);
      ctx.setLoading(false);
    }
  };
}

export function createSend(
  ctx: SessionStoreContext,
  getMessageType: () => SendableMessageType,
  getMemoryConfig: () => MemoryConfig,
  getMemoryConfigBase: () => InvocationConfig["memory_config"] | undefined,
  getInvocationConfig: () => InvocationConfig,
  clearMemoryIndexedToastTimer: () => void,
  reconnectEventStream?: (sessionId: string) => void,
) {
  return async function send(
    message: string,
    msgType?: SendableMessageType,
    structuredOutput?: StructuredOutputConfig,
    attachments?: MessageAttachmentPayload[],
    batch?: BatchInvocationConfig,
  ) {
    const session = ctx.getSession();
    if (!session || (!session.can_send_message && !session.can_stage_message)) {
      ctx.setError("Session not ready for messages");
      return;
    }

    const shouldQueueForNextTurn = !session.can_send_message && session.can_stage_message;

    if (!shouldQueueForNextTurn) {
      ctx.setLoading(true);
    }
    ctx.setError(null);
    if (!shouldQueueForNextTurn) {
      clearMemoryIndexedToastTimer();
      ctx.setMemoryIndexedToast(null);
    }

    const type = msgType ?? getMessageType();

    try {
      if (!shouldQueueForNextTurn) {
        ctx.resetEnrichmentPhaseTracking();
      }

      appendUserMessageToChatFlow(ctx, message, type, {
        queuedForNextTurn: shouldQueueForNextTurn,
      });

      const effectiveInvocation = buildEffectiveInvocationConfig(
        getInvocationConfig(),
        getMemoryConfig(),
        getMemoryConfigBase(),
      );
      const updatedSession = await sendMessage(
        session.session_id,
        message,
        type,
        structuredOutput,
        effectiveInvocation,
        attachments,
        batch,
      );
      ctx.setSession(updatedSession);

      // Ensure the SSE stream is alive for direct follow-up messages.
      // Between turns the original SSE connection may have gone stale
      // (browser timeout, proxy drop, etc.).  Reconnecting replays any
      // events already buffered in the bridge's history so the frontend
      // never misses an interrupt or tool event.
      if (!shouldQueueForNextTurn && reconnectEventStream) {
        reconnectEventStream(session.session_id);
      }
    } catch (e) {
      ctx.setError(e instanceof Error ? e.message : "Failed to send message");
      if (!shouldQueueForNextTurn) {
        ctx.setLoading(false);
      }
    }
  };
}
