import type {
  InterruptStyle,
  InvocationConfig,
  MemoryConfig,
  SendableMessageType,
} from "$lib/types";

import type { SessionStoreContext } from "../types";

interface CreateSessionActionBindingsParams {
  ctx: SessionStoreContext;
  getEventSource: () => EventSource | null;
  setEventSource: (eventSource: EventSource | null) => void;
  clearMemoryIndexedToastTimer: () => void;
  getMessageType: () => SendableMessageType;
  getPrivateData: () => Record<string, unknown>;
  setPrivateData: (data: Record<string, unknown>) => void;
  getMemoryConfig: () => MemoryConfig;
  setMemoryConfig: (config: MemoryConfig) => void;
  getMemoryConfigBase: () => InvocationConfig["memory_config"] | undefined;
  setMemoryConfigBase: (config: InvocationConfig["memory_config"] | undefined) => void;
  getInvocationConfig: () => InvocationConfig;
  setInvocationConfig: (config: InvocationConfig) => void;
  resetEnrichmentTracking: () => void;
  setInterruptStyle: (style: InterruptStyle) => void;
}

export function createSessionActionBindings(params: CreateSessionActionBindingsParams) {
  return {
    ctx: params.ctx,
    getEventSource: params.getEventSource,
    setEventSource: params.setEventSource,
    clearMemoryIndexedToastTimer: params.clearMemoryIndexedToastTimer,
    getMessageType: params.getMessageType,
    getPrivateData: params.getPrivateData,
    setPrivateData: params.setPrivateData,
    getMemoryConfig: params.getMemoryConfig,
    setMemoryConfig: params.setMemoryConfig,
    getMemoryConfigBase: params.getMemoryConfigBase,
    setMemoryConfigBase: params.setMemoryConfigBase,
    getInvocationConfig: params.getInvocationConfig,
    setInvocationConfig: params.setInvocationConfig,
    resetEnrichmentTracking: params.resetEnrichmentTracking,
    setInterruptStyle: params.setInterruptStyle,
  };
}
