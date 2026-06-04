import { describe, expect, it } from "vitest";

import type { ChatFlowItem, InterruptData, InterruptRequiredEvent, Message } from "$lib/types";
import { InterruptManager } from "./interruptManager";

// MARK: Helpers

function makeEvent(overrides: Partial<InterruptRequiredEvent> = {}): InterruptRequiredEvent {
  return {
    checkpoint_id: "cp-1",
    interrupt_id: "int-1",
    prompt: "Enter a value",
    data_key: "user_input",
    arg_name: "value",
    tool_name: "ask_user",
    assignment_id: "assign-1",
    assignment_index: 0,
    interrupt_number: 1,
    total_interrupts: 1,
    timestamp: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

function interruptDataOf(item: ChatFlowItem): InterruptData {
  if (item.type !== "interrupt_card") {
    throw new Error(`expected interrupt_card item, got ${item.type}`);
  }
  return item.data;
}

// MARK: InterruptManager

describe("InterruptManager", () => {
  describe("handleRequired", () => {
    it("creates InterruptData from a backend event", () => {
      const mgr = new InterruptManager();
      const event = makeEvent({ interrupt_id: "int-100", prompt: "What is your name?" });

      const { interruptData } = mgr.handleRequired(event, []);

      expect(interruptData.cardId).toBeTruthy();
      expect(interruptData.interruptId).toBe("int-100");
      expect(interruptData.checkpointId).toBe("cp-1");
      expect(interruptData.toolName).toBe("ask_user");
      expect(interruptData.prompt).toBe("What is your name?");
      expect(interruptData.status).toBe("waiting");
      expect(interruptData.dataKey).toBe("user_input");
      expect(interruptData.assignmentId).toBe("assign-1");
      expect(interruptData.interruptNumber).toBe(1);
      expect(interruptData.totalInterrupts).toBe(1);
      expect(interruptData.turnSequence).toBe(0);
    });

    it("stores the interrupt in the cards Map", () => {
      const mgr = new InterruptManager();
      mgr.handleRequired(makeEvent({ interrupt_id: "int-1" }), []);

      expect(mgr.cards.has("int-1")).toBe(true);
      expect(mgr.cards.get("int-1")?.status).toBe("waiting");
    });

    it("appends an interrupt_card to chatFlowItems", () => {
      const mgr = new InterruptManager();
      const existing: ChatFlowItem[] = [
        {
          id: "msg-1",
          type: "message",
          timestamp: "2024-01-01T00:00:00Z",
          data: {
            id: "msg-1",
            role: "assistant",
            messageType: "ai",
            content: "Hi",
            timestamp: "2024-01-01T00:00:00Z",
          } satisfies Message,
        },
      ];

      const { chatFlowItems } = mgr.handleRequired(makeEvent(), existing);

      expect(chatFlowItems).toHaveLength(2);
      expect(chatFlowItems[0].type).toBe("message");
      expect(chatFlowItems[1].type).toBe("interrupt_card");
    });

    it("does not mutate the original chatFlowItems array", () => {
      const mgr = new InterruptManager();
      const original: ChatFlowItem[] = [];

      mgr.handleRequired(makeEvent(), original);

      expect(original).toHaveLength(0);
    });

    it("maps backend input_type to InterruptData", () => {
      const mgr = new InterruptManager();
      const event = makeEvent({ input_type: "boolean" });

      const { interruptData } = mgr.handleRequired(event, []);

      expect(interruptData.inputType).toBe("boolean");
    });

    it("maps backend choices to InterruptChoice format", () => {
      const mgr = new InterruptManager();
      const event = makeEvent({ choices: ["option_a", "option_b", "option_c"] });

      const { interruptData } = mgr.handleRequired(event, []);

      expect(interruptData.choices).toEqual([
        { value: "option_a", label: "option_a" },
        { value: "option_b", label: "option_b" },
        { value: "option_c", label: "option_c" },
      ]);
    });

    it("handles events without input_type or choices", () => {
      const mgr = new InterruptManager();
      const event = makeEvent(); // no input_type or choices

      const { interruptData } = mgr.handleRequired(event, []);

      expect(interruptData.inputType).toBeUndefined();
      expect(interruptData.choices).toBeUndefined();
    });

    it("stores independent copies in cards Map and chatFlowItems", () => {
      const mgr = new InterruptManager();
      const { interruptData, chatFlowItems } = mgr.handleRequired(
        makeEvent({ interrupt_id: "int-1" }),
        [],
      );

      // Mutate the returned interruptData
      interruptData.status = "completed";

      // Cards map and chatFlowItems should still be "waiting"
      expect(mgr.cards.get("int-1")?.status).toBe("waiting");
      expect(interruptDataOf(chatFlowItems[0]).status).toBe("waiting");
    });

    it("updates an existing interrupt_card when the same interrupt is replayed", () => {
      const mgr = new InterruptManager();
      const first = mgr.handleRequired(makeEvent({ interrupt_id: "int-1" }), []);

      const second = mgr.handleRequired(
        makeEvent({
          interrupt_id: "int-1",
          prompt: "Updated prompt",
          timestamp: "2024-01-01T00:01:00Z",
        }),
        first.chatFlowItems,
      );

      expect(second.chatFlowItems).toHaveLength(1);
      const card = interruptDataOf(second.chatFlowItems[0]);
      expect(card.cardId).toBe(first.interruptData.cardId);
      expect(card.interruptId).toBe("int-1");
      expect(card.prompt).toBe("Updated prompt");
      expect(second.chatFlowItems[0].timestamp).toBe("2024-01-01T00:01:00Z");
    });

    it("appends a new interrupt card when the same interrupt id appears on a later turn", () => {
      const mgr = new InterruptManager();
      mgr.beginTurn();

      const first = mgr.handleRequired(
        makeEvent({
          interrupt_id: "int-1",
          prompt: "What is your favorite color?",
          timestamp: "2024-01-01T00:00:00Z",
        }),
        [],
      );
      const completed = mgr.updateStatus(
        "int-1",
        { status: "completed", submittedValue: "red" },
        first.chatFlowItems,
      );

      mgr.beginTurn();
      const second = mgr.handleRequired(
        makeEvent({
          interrupt_id: "int-1",
          prompt: "What is your favorite color now?",
          timestamp: "2024-01-01T00:05:00Z",
        }),
        completed.chatFlowItems,
      );

      expect(second.chatFlowItems).toHaveLength(2);
      const firstCard = interruptDataOf(second.chatFlowItems[0]);
      const secondCard = interruptDataOf(second.chatFlowItems[1]);
      expect(firstCard.cardId).not.toBe(secondCard.cardId);
      expect(firstCard.status).toBe("completed");
      expect(secondCard.status).toBe("waiting");
      expect(secondCard.turnSequence).toBe(2);
      expect(mgr.cards.get("int-1")?.cardId).toBe(secondCard.cardId);
    });
  });

  describe("updateStatus", () => {
    it("patches an existing interrupt and syncs to chatFlowItems", () => {
      const mgr = new InterruptManager();
      const { chatFlowItems } = mgr.handleRequired(makeEvent({ interrupt_id: "int-1" }), []);

      const result = mgr.updateStatus(
        "int-1",
        { status: "submitting", submittedValue: "hello" },
        chatFlowItems,
      );

      // Cards map updated
      expect(result.cards.get("int-1")?.status).toBe("submitting");
      expect(result.cards.get("int-1")?.submittedValue).toBe("hello");

      // ChatFlowItems updated
      const card = interruptDataOf(result.chatFlowItems[0]);
      expect(card.status).toBe("submitting");
      expect(card.submittedValue).toBe("hello");
    });

    it("returns unchanged data for non-existent interrupt ID", () => {
      const mgr = new InterruptManager();
      const items: ChatFlowItem[] = [];

      const result = mgr.updateStatus("nonexistent", { status: "completed" }, items);

      expect(result.chatFlowItems).toEqual(items);
      expect(result.cards.size).toBe(0);
    });

    it("returns a new Map instance for reactivity", () => {
      const mgr = new InterruptManager();
      const { chatFlowItems } = mgr.handleRequired(makeEvent({ interrupt_id: "int-1" }), []);

      const result = mgr.updateStatus("int-1", { status: "completed" }, chatFlowItems);

      // Should be a different Map instance (for Svelte reactivity)
      expect(result.cards).not.toBe(mgr.cards);
    });
  });

  describe("getPending", () => {
    it("returns only interrupts with status 'waiting'", () => {
      const mgr = new InterruptManager();
      mgr.handleRequired(makeEvent({ interrupt_id: "int-1" }), []);
      mgr.handleRequired(makeEvent({ interrupt_id: "int-2" }), []);

      // Mark one as completed
      mgr.cards.set("int-1", { ...mgr.cards.get("int-1")!, status: "completed" });

      const pending = mgr.getPending();

      expect(pending).toHaveLength(1);
      expect(pending[0].interruptId).toBe("int-2");
    });

    it("returns empty array when no pending interrupts exist", () => {
      const mgr = new InterruptManager();
      expect(mgr.getPending()).toEqual([]);
    });
  });

  describe("getAll", () => {
    it("returns all interrupts regardless of status", () => {
      const mgr = new InterruptManager();
      mgr.handleRequired(makeEvent({ interrupt_id: "int-1" }), []);
      mgr.handleRequired(makeEvent({ interrupt_id: "int-2" }), []);
      mgr.cards.set("int-1", { ...mgr.cards.get("int-1")!, status: "completed" });

      const all = mgr.getAll();

      expect(all).toHaveLength(2);
    });

    it("returns empty array when no interrupts registered", () => {
      const mgr = new InterruptManager();
      expect(mgr.getAll()).toEqual([]);
    });
  });

  describe("reset", () => {
    it("clears all interrupt cards", () => {
      const mgr = new InterruptManager();
      mgr.handleRequired(makeEvent({ interrupt_id: "int-1" }), []);
      mgr.handleRequired(makeEvent({ interrupt_id: "int-2" }), []);

      mgr.reset();

      expect(mgr.cards.size).toBe(0);
      expect(mgr.getPending()).toEqual([]);
      expect(mgr.getAll()).toEqual([]);
    });
  });
});
