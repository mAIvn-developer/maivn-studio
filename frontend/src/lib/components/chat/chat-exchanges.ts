import type { ChatFlowItem, InterruptData, Message, PhaseChipData, ToolCard } from "$lib/types";

export interface Exchange {
  humanMessage: Message;
  toolCards: ToolCard[];
  interruptCards: InterruptData[];
  phaseChips: PhaseChipData[];
  statusMessages: Message[];
  aiMessage: Message | null;
}

export function buildExchanges(chatFlowItems: ChatFlowItem[]): Exchange[] {
  const result: Exchange[] = [];
  let currentExchange: Exchange | null = null;

  for (const item of chatFlowItems) {
    if (item.type === "message") {
      const message = item.data as Message;

      if (message.messageType === "status") {
        if (currentExchange) {
          currentExchange.statusMessages.push(message);
        }
      } else if (message.role === "user") {
        if (currentExchange) {
          result.push(currentExchange);
        }
        currentExchange = {
          humanMessage: message,
          toolCards: [],
          interruptCards: [],
          phaseChips: [],
          statusMessages: [],
          aiMessage: null,
        };
      } else if (message.role === "assistant") {
        if (currentExchange) {
          currentExchange.aiMessage = message;
          result.push(currentExchange);
          currentExchange = null;
        } else {
          result.push({
            humanMessage: {
              id: crypto.randomUUID(),
              role: "user",
              messageType: "human",
              content: "",
              timestamp: message.timestamp,
            },
            toolCards: [],
            interruptCards: [],
            phaseChips: [],
            statusMessages: [],
            aiMessage: message,
          });
        }
      }
    } else if (item.type === "tool_card") {
      const toolCard = item.data as ToolCard;
      const target = currentExchange ?? result[result.length - 1];
      if (target) {
        target.toolCards.push(toolCard);
      }
    } else if (item.type === "interrupt_card") {
      const interruptCard = item.data as InterruptData;
      const target = currentExchange ?? result[result.length - 1];
      if (target) {
        target.interruptCards.push(interruptCard);
      }
    } else if (item.type === "phase_chip") {
      const phaseChip = item.data as PhaseChipData;
      const target = currentExchange ?? result[result.length - 1];
      if (target) {
        target.phaseChips.push(phaseChip);
      }
    }
  }

  if (currentExchange) {
    result.push(currentExchange);
  }

  return result;
}
