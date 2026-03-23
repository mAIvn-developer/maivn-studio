import { submitInterrupt as submitInterruptRequest } from "$lib/api_client/sessions";

import { applyInterruptStatusUpdate } from "./action-helpers";
import type { SessionStoreContext } from "../types";

export function createHandleSubmitInterrupt(
  ctx: SessionStoreContext,
  reconnectEventStream?: (sessionId: string) => void,
) {
  return async function handleSubmitInterrupt(interruptId: string, value: string) {
    const interrupt = ctx.interruptManager.cards.get(interruptId);
    if (!interrupt || !ctx.getSession()) return;

    applyInterruptStatusUpdate(ctx, interruptId, { status: "submitting" });

    try {
      const session = ctx.getSession()!;
      const updatedSession = await submitInterruptRequest(
        session.session_id,
        interrupt.interruptId,
        interrupt.dataKey,
        value,
      );

      applyInterruptStatusUpdate(ctx, interruptId, {
        status: "completed",
        submittedValue: value,
      });

      const shouldForceRunning =
        session.status === "waiting_input" &&
        updatedSession.is_active &&
        updatedSession.status !== "running";
      const nextSession = shouldForceRunning
        ? {
            ...updatedSession,
            status: "running" as const,
            can_send_message: false,
            can_stage_message: true,
          }
        : updatedSession;

      ctx.setSession(nextSession);

      if (nextSession.is_active) {
        ctx.setLoading(true);
        reconnectEventStream?.(nextSession.session_id);
      }
    } catch (e) {
      applyInterruptStatusUpdate(ctx, interruptId, { status: "waiting" });
      ctx.setError(e instanceof Error ? e.message : "Failed to submit interrupt");
    }
  };
}

export function createHandleCancelInterrupt(
  ctx: SessionStoreContext,
  cancelFn: () => Promise<void>,
) {
  return function handleCancelInterrupt(interruptId: string) {
    applyInterruptStatusUpdate(ctx, interruptId, { status: "cancelled" });
    cancelFn();
  };
}
