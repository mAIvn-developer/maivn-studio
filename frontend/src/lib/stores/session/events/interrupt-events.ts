import type { InterruptRequiredEvent } from "$lib/types";

import { asRecord } from "./event-utils";
import type { SessionStoreContext } from "../types";

export function handleInterruptRequired(
  ctx: SessionStoreContext,
  eventData: InterruptRequiredEvent,
) {
  const interruptData = asRecord((eventData as unknown as Record<string, unknown>).interrupt);
  const normalizedEventData = {
    ...eventData,
    interrupt_id: (interruptData?.id as string | undefined) ?? eventData.interrupt_id,
    checkpoint_id: (interruptData?.checkpoint_id as string | undefined) ?? eventData.checkpoint_id,
    data_key: (interruptData?.data_key as string | undefined) ?? eventData.data_key,
    prompt: (interruptData?.prompt as string | undefined) ?? eventData.prompt,
    tool_name: (interruptData?.tool_name as string | undefined) ?? eventData.tool_name,
    arg_name: (interruptData?.arg_name as string | undefined) ?? eventData.arg_name,
    assignment_id: (interruptData?.assignment_id as string | undefined) ?? eventData.assignment_id,
    interrupt_number: (interruptData?.number as number | undefined) ?? eventData.interrupt_number,
    total_interrupts: (interruptData?.total as number | undefined) ?? eventData.total_interrupts,
    input_type: (interruptData?.input_type as string | undefined) ?? eventData.input_type,
    choices: (interruptData?.choices as string[] | undefined) ?? eventData.choices,
  } satisfies InterruptRequiredEvent;
  const result = ctx.interruptManager.handleRequired(normalizedEventData, ctx.getChatFlowItems());
  ctx.setChatFlowItems(result.chatFlowItems);
  ctx.setInterruptCards(new Map(ctx.interruptManager.cards));

  const session = ctx.getSession();
  if (session) {
    ctx.setSession({ ...session, status: "waiting_input" });
  }
  ctx.setLoading(false);
}
