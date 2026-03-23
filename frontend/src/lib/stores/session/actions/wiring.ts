import type {
  InterruptStyle,
  InvocationConfig,
  MemoryConfig,
  SendableMessageType,
} from "$lib/types";

import { createSend, createStartSession } from "./actions";
import { createSetInterruptStyle, createSetInvocationConfig } from "./config-actions";
import { createConnectToEventStream, createDisconnect } from "./connection-actions";
import { processEvent, shouldDisconnectAfterEvent } from "../events/events";
import { createHandleCancelInterrupt, createHandleSubmitInterrupt } from "./interrupt-actions";
import { createCancel, createEnd, createReset } from "./lifecycle-actions";
import type { SessionStoreContext } from "../types";

interface CreateSessionStoreActionsParams {
  ctx: SessionStoreContext;
  getEventSource: () => EventSource | null;
  setEventSource: (es: EventSource | null) => void;
  clearMemoryIndexedToastTimer: () => void;
  getMessageType: () => SendableMessageType;
  getPrivateData: () => Record<string, unknown>;
  setPrivateData: (data: Record<string, unknown>) => void;
  getMemoryConfig: () => MemoryConfig;
  setMemoryConfig: (config: MemoryConfig) => void;
  getMemoryConfigBase: () => InvocationConfig["memory_config"] | undefined;
  setMemoryConfigBase: (v: InvocationConfig["memory_config"] | undefined) => void;
  getInvocationConfig: () => InvocationConfig;
  setInvocationConfig: (config: InvocationConfig) => void;
  resetEnrichmentTracking: () => void;
  setInterruptStyle: (style: InterruptStyle) => void;
}

export function createSessionStoreActions(params: CreateSessionStoreActionsParams) {
  const disconnect = createDisconnect(
    params.ctx,
    params.getEventSource,
    params.setEventSource,
    params.clearMemoryIndexedToastTimer,
  );

  function handleEvent(type: string, data: unknown) {
    processEvent(params.ctx, type, data);
    if (shouldDisconnectAfterEvent(type)) {
      disconnect();
    }
  }

  const connectToEventStream = createConnectToEventStream(
    params.ctx,
    disconnect,
    handleEvent,
    params.getEventSource,
    params.setEventSource,
  );

  const startSession = createStartSession(
    params.ctx,
    params.getMessageType,
    params.getPrivateData,
    params.getMemoryConfig,
    params.getMemoryConfigBase,
    params.getInvocationConfig,
    connectToEventStream,
    params.resetEnrichmentTracking,
    params.clearMemoryIndexedToastTimer,
  );

  const send = createSend(
    params.ctx,
    params.getMessageType,
    params.getMemoryConfig,
    params.getMemoryConfigBase,
    params.getInvocationConfig,
    params.clearMemoryIndexedToastTimer,
    connectToEventStream,
  );

  const end = createEnd(params.ctx, disconnect);
  const cancel = createCancel(params.ctx, disconnect);

  const reset = createReset(
    params.ctx,
    disconnect,
    params.resetEnrichmentTracking,
    params.clearMemoryIndexedToastTimer,
    params.setPrivateData,
    params.setInvocationConfig,
    params.setMemoryConfigBase,
    params.setMemoryConfig,
  );

  const submitInterrupt = createHandleSubmitInterrupt(params.ctx, connectToEventStream);
  const cancelInterrupt = createHandleCancelInterrupt(params.ctx, cancel);

  const setInvocationConfigAction = createSetInvocationConfig(
    params.setInvocationConfig,
    params.getInvocationConfig,
    params.setMemoryConfigBase,
    params.setMemoryConfig,
  );

  const setInterruptStyleAction = createSetInterruptStyle(params.setInterruptStyle);

  return {
    startSession,
    send,
    end,
    cancel,
    reset,
    submitInterrupt,
    cancelInterrupt,
    setInvocationConfigAction,
    setInterruptStyleAction,
  };
}
