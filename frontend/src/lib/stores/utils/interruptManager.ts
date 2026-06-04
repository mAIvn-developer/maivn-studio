import type {
  ChatFlowItem,
  InterruptData,
  InterruptInputType,
  InterruptRequiredEvent,
} from "$lib/types";

// MARK: InterruptManager

/**
 * Single source of truth for interrupt state.
 *
 * Consolidates the `interruptCards` Map management and the mirrored
 * chatFlowItems updates into one module. The caller passes the current
 * chatFlowItems array and receives the updated version back, so Svelte 5
 * reactive assignments remain in the .svelte.ts file.
 */
export class InterruptManager {
  readonly cards = new Map<string, InterruptData>();
  private _currentTurnSequence = 0;

  beginTurn(): number {
    this._currentTurnSequence += 1;
    return this._currentTurnSequence;
  }

  /**
   * Convert a raw backend InterruptRequiredEvent into an InterruptData
   * and register it. Returns `{ interruptData, chatFlowItems }` with
   * the new interrupt appended to the chat flow.
   */
  handleRequired(
    eventData: InterruptRequiredEvent,
    chatFlowItems: ChatFlowItem[],
  ): { interruptData: InterruptData; chatFlowItems: ChatFlowItem[] } {
    const existingInterrupt = this.cards.get(eventData.interrupt_id);
    const isReplayForCurrentTurn =
      existingInterrupt !== undefined &&
      existingInterrupt.turnSequence === this._currentTurnSequence;

    // Convert backend input_type to frontend InterruptInputType if provided
    const backendInputType = eventData.input_type as InterruptInputType | undefined;

    // Convert backend choices array to InterruptChoice format if provided
    const backendChoices = eventData.choices?.map((value) => ({
      value,
      label: value,
    }));

    const interruptData: InterruptData = {
      cardId:
        existingInterrupt?.cardId && isReplayForCurrentTurn
          ? existingInterrupt.cardId
          : crypto.randomUUID(),
      interruptId: eventData.interrupt_id,
      checkpointId: eventData.checkpoint_id,
      toolName: eventData.tool_name,
      prompt: eventData.prompt,
      dataKey: eventData.data_key,
      assignmentId: eventData.assignment_id,
      status: "waiting",
      timestamp: eventData.timestamp,
      interruptNumber: eventData.interrupt_number,
      totalInterrupts: eventData.total_interrupts,
      turnSequence: this._currentTurnSequence,
      // Use backend-provided type/choices if available (from Literal type detection)
      inputType: backendInputType,
      choices: backendChoices,
    };

    const nextInterrupt: InterruptData = {
      ...(isReplayForCurrentTurn ? existingInterrupt : {}),
      ...interruptData,
      status: "waiting",
      submittedValue: undefined,
    };

    // Store a copy in the cards Map
    this.cards.set(nextInterrupt.interruptId, { ...nextInterrupt });

    const hasExistingCard = chatFlowItems.some(
      (item) => item.type === "interrupt_card" && item.data.cardId === nextInterrupt.cardId,
    );

    if (hasExistingCard) {
      const updatedItems = chatFlowItems.map((item) => {
        if (item.type !== "interrupt_card") {
          return item;
        }
        const data = item.data;
        if (data.cardId !== nextInterrupt.cardId) {
          return item;
        }
        return { ...item, timestamp: nextInterrupt.timestamp, data: { ...nextInterrupt } };
      });

      return { interruptData: nextInterrupt, chatFlowItems: updatedItems };
    }

    // Append a separate copy to chatFlowItems
    const updatedItems: ChatFlowItem[] = [
      ...chatFlowItems,
      {
        id: crypto.randomUUID(),
        type: "interrupt_card" as const,
        timestamp: nextInterrupt.timestamp,
        data: { ...nextInterrupt },
      },
    ];

    return { interruptData: nextInterrupt, chatFlowItems: updatedItems };
  }

  /**
   * Update an interrupt's status and sync it into chatFlowItems.
   * Returns the updated chatFlowItems array and a shallow copy of
   * the cards Map (for Svelte reactivity triggers).
   */
  updateStatus(
    interruptId: string,
    patch: Partial<InterruptData>,
    chatFlowItems: ChatFlowItem[],
  ): { cards: Map<string, InterruptData>; chatFlowItems: ChatFlowItem[] } {
    const interrupt = this.cards.get(interruptId);
    if (!interrupt) {
      return { cards: new Map(this.cards), chatFlowItems };
    }

    const updated: InterruptData = { ...interrupt, ...patch };
    this.cards.set(interruptId, updated);

    const updatedItems = chatFlowItems.map((item) => {
      if (item.type === "interrupt_card") {
        const data = item.data;
        if (data.cardId === updated.cardId) {
          return { ...item, data: updated };
        }
      }
      return item;
    });

    return { cards: new Map(this.cards), chatFlowItems: updatedItems };
  }

  /** Get all interrupts currently in "waiting" status. */
  getPending(): InterruptData[] {
    return Array.from(this.cards.values()).filter((i) => i.status === "waiting");
  }

  /** Get all interrupts regardless of status. */
  getAll(): InterruptData[] {
    return Array.from(this.cards.values());
  }

  /** Clear all interrupt state. */
  reset(): void {
    this.cards.clear();
    this._currentTurnSequence = 0;
  }
}
