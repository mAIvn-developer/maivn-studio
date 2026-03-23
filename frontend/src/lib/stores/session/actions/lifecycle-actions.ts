import { cancelSession, endSession } from "$lib/api_client/sessions";
import type { InvocationConfig, MemoryConfig } from "$lib/types";

import { clearSessionRuntimeState, markActiveToolCardsCancelled } from "./action-helpers";
import { createDefaultInvocationConfig } from "../defaults";
import { createDefaultMemoryConfig } from "../memory";
import type { SessionStoreContext } from "../types";

export function createEnd(ctx: SessionStoreContext, disconnect: () => void) {
  return async function end() {
    if (!ctx.getSession()) return;

    try {
      await endSession(ctx.getSession()!.session_id);
      disconnect();
    } catch (e) {
      ctx.setError(e instanceof Error ? e.message : "Failed to end session");
    }
  };
}

export function createCancel(ctx: SessionStoreContext, disconnect: () => void) {
  return async function cancel() {
    const session = ctx.getSession();
    if (!session) return;

    try {
      await cancelSession(session.session_id);
      markActiveToolCardsCancelled(ctx);
      ctx.setLoading(false);
      ctx.resetEnrichmentPhaseTracking();
      if (ctx.getSession()) {
        ctx.setSession({
          ...ctx.getSession()!,
          status: "cancelled",
          can_send_message: false,
          can_stage_message: false,
          queued_message_count: 0,
          is_active: false,
        });
      }
      disconnect();
    } catch (e) {
      ctx.setError(e instanceof Error ? e.message : "Failed to cancel execution");
      ctx.setLoading(false);
    }
  };
}

export function createReset(
  ctx: SessionStoreContext,
  disconnect: () => void,
  resetEnrichmentTracking: () => void,
  clearMemoryIndexedToastTimer: () => void,
  setPrivateData: (data: Record<string, unknown>) => void,
  setInvocationConfigDirect: (config: InvocationConfig) => void,
  setMemoryConfigBase: (v: InvocationConfig["memory_config"] | undefined) => void,
  setMemoryConfig: (config: MemoryConfig) => void,
) {
  return function reset() {
    disconnect();
    ctx.setSession(null);
    clearSessionRuntimeState(ctx, resetEnrichmentTracking, clearMemoryIndexedToastTimer);
    ctx.setInterruptCards(new Map());
    ctx.interruptManager.reset();
    ctx.setError(null);
    ctx.setLoading(false);
    setPrivateData({});
    setInvocationConfigDirect(createDefaultInvocationConfig());
    setMemoryConfigBase(undefined);
    setMemoryConfig(createDefaultMemoryConfig());
  };
}
