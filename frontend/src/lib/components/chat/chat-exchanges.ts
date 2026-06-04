import type {
  BatchResult,
  ChatFlowItem,
  ChatFlowOrigin,
  InterruptData,
  Message,
  PhaseChipData,
  ToolCard,
} from "$lib/types";

export interface Exchange {
  humanMessage: Message;
  toolCards: ToolCard[];
  interruptCards: InterruptData[];
  phaseChips: PhaseChipData[];
  statusMessages: Message[];
  batchResults: BatchResult[];
  aiMessage: Message | null;
  /**
   * Origin of the human message that opened this exchange. Defaults to
   * `"user"`. When the exchange came from a scheduled fire, the chat panel
   * applies a "Scheduled" badge + tertiary border on the relevant cards.
   */
  origin?: ChatFlowOrigin;
  /** Fire ID from the schedule that triggered this exchange, when applicable. */
  scheduleFireId?: string;
}

function emptyExchange(humanMessage: Message, item?: ChatFlowItem): Exchange {
  return {
    humanMessage,
    toolCards: [],
    interruptCards: [],
    phaseChips: [],
    statusMessages: [],
    batchResults: [],
    aiMessage: null,
    origin: item?.origin,
    scheduleFireId: item?.scheduleFireId,
  };
}

export function buildExchanges(chatFlowItems: ChatFlowItem[]): Exchange[] {
  const result: Exchange[] = [];
  let currentExchange: Exchange | null = null;

  for (const item of chatFlowItems) {
    if (item.type === "message") {
      const message = item.data;

      if (message.messageType === "status") {
        if (currentExchange) {
          currentExchange.statusMessages.push(message);
        }
      } else if (message.role === "user") {
        if (currentExchange) {
          result.push(currentExchange);
        }
        currentExchange = emptyExchange(message, item);
      } else if (message.role === "assistant") {
        if (currentExchange) {
          currentExchange.aiMessage = message;
          // If the assistant message was the cron-triggered one (only the
          // user-side message carries origin in most cases, but not always),
          // promote the origin to the exchange.
          if (item.origin && !currentExchange.origin) {
            currentExchange.origin = item.origin;
            currentExchange.scheduleFireId = item.scheduleFireId;
          }
          result.push(currentExchange);
          currentExchange = null;
        } else {
          const synthesized = emptyExchange(
            {
              id: crypto.randomUUID(),
              role: "user",
              messageType: "human",
              content: "",
              timestamp: message.timestamp,
            },
            item,
          );
          synthesized.aiMessage = message;
          result.push(synthesized);
        }
      }
    } else if (item.type === "tool_card") {
      const toolCard = item.data;
      const target = currentExchange ?? result[result.length - 1];
      if (target) {
        target.toolCards.push(toolCard);
      }
    } else if (item.type === "interrupt_card") {
      const interruptCard = item.data;
      const target = currentExchange ?? result[result.length - 1];
      if (target) {
        target.interruptCards.push(interruptCard);
      }
    } else if (item.type === "phase_chip") {
      const phaseChip = item.data;
      const target = currentExchange ?? result[result.length - 1];
      if (target) {
        target.phaseChips.push(phaseChip);
      }
    } else if (item.type === "batch_result") {
      const batchResult = item.data;
      const target = currentExchange ?? result[result.length - 1];
      if (target) {
        target.batchResults.push(batchResult);
      }
    }
  }

  if (currentExchange) {
    result.push(currentExchange);
  }

  return result;
}
