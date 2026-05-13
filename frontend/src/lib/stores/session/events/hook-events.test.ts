import { describe, expect, test } from "vitest";

import type { HookFiring, ToolCard } from "$lib/types";
import { handleHookFired } from "./hook-events";

// MARK: Fake Context

function createCtx(initialCards: Map<string, ToolCard> = new Map()) {
  let toolCards = initialCards;
  let scopeHookFirings = new Map<string, HookFiring[]>();

  return {
    ctx: {
      getToolCards: () => toolCards,
      setToolCards: (cards: Map<string, ToolCard>) => {
        toolCards = cards;
      },
      getScopeHookFirings: () => scopeHookFirings,
      setScopeHookFirings: (firings: Map<string, HookFiring[]>) => {
        scopeHookFirings = firings;
      },
    },
    getToolCards: () => toolCards,
    getScopeHookFirings: () => scopeHookFirings,
  };
}

function baseToolCard(toolId: string): ToolCard {
  return {
    toolId,
    toolName: "my_tool",
    toolType: "func",
    status: "executing",
    args: {},
    startedAt: new Date().toISOString(),
    isStreaming: false,
    isSystemTool: false,
  };
}

// MARK: Tool Hook Routing

describe("handleHookFired - tool target", () => {
  test("appends to ToolCard.hookFirings when target_id matches a tool card", () => {
    const card = baseToolCard("evt-1");
    const { ctx, getToolCards } = createCtx(new Map([["evt-1", card]]));

    handleHookFired(ctx as never, {
      name: "audit_log",
      stage: "before",
      status: "completed",
      target_type: "tool",
      target_id: "evt-1",
      target_name: "my_tool",
      elapsed_ms: 2,
    });

    const updated = getToolCards().get("evt-1")!;
    expect(updated.hookFirings).toHaveLength(1);
    expect(updated.hookFirings![0]).toMatchObject({
      name: "audit_log",
      stage: "before",
      status: "completed",
      targetType: "tool",
      targetId: "evt-1",
      elapsedMs: 2,
    });
  });

  test("accumulates multiple firings on the same tool card", () => {
    const card = baseToolCard("evt-2");
    const { ctx, getToolCards } = createCtx(new Map([["evt-2", card]]));

    handleHookFired(ctx as never, {
      name: "hook_a",
      stage: "before",
      status: "completed",
      target_type: "tool",
      target_id: "evt-2",
    });
    handleHookFired(ctx as never, {
      name: "hook_b",
      stage: "after",
      status: "failed",
      target_type: "tool",
      target_id: "evt-2",
      error: "boom",
    });

    const updated = getToolCards().get("evt-2")!;
    expect(updated.hookFirings).toHaveLength(2);
    expect(updated.hookFirings![1].error).toBe("boom");
    expect(updated.hookFirings![1].status).toBe("failed");
  });

  test("drops the event when the target tool card doesn't exist", () => {
    const { ctx, getToolCards } = createCtx();

    handleHookFired(ctx as never, {
      name: "ghost",
      stage: "before",
      status: "completed",
      target_type: "tool",
      target_id: "evt-missing",
    });

    expect(getToolCards().size).toBe(0);
  });

  test("descriptor under 'hook' key is also read", () => {
    const card = baseToolCard("evt-3");
    const { ctx, getToolCards } = createCtx(new Map([["evt-3", card]]));

    handleHookFired(ctx as never, {
      hook: {
        name: "via_descriptor",
        stage: "before",
        status: "completed",
        target_type: "tool",
        target_id: "evt-3",
      },
    });

    const updated = getToolCards().get("evt-3")!;
    expect(updated.hookFirings).toHaveLength(1);
    expect(updated.hookFirings![0].name).toBe("via_descriptor");
  });
});

// MARK: Scope Hook Routing

describe("handleHookFired - scope target", () => {
  test("appends agent hooks to scopeHookFirings keyed by `agent:<id>`", () => {
    const { ctx, getScopeHookFirings } = createCtx();

    handleHookFired(ctx as never, {
      name: "swarm_setup",
      stage: "before",
      status: "completed",
      target_type: "agent",
      target_id: "agent-42",
      target_name: "MyAgent",
    });

    const firings = getScopeHookFirings().get("agent:agent-42")!;
    expect(firings).toHaveLength(1);
    expect(firings[0].targetType).toBe("agent");
    expect(firings[0].targetName).toBe("MyAgent");
  });

  test("falls back to target_name when target_id is missing", () => {
    const { ctx, getScopeHookFirings } = createCtx();

    handleHookFired(ctx as never, {
      name: "swarm_hook",
      stage: "after",
      status: "completed",
      target_type: "swarm",
      target_name: "MySwarm",
    });

    expect(getScopeHookFirings().get("swarm:MySwarm")).toHaveLength(1);
  });

  test("drops the event when both target_id and target_name are missing", () => {
    const { ctx, getScopeHookFirings } = createCtx();

    handleHookFired(ctx as never, {
      name: "stranded",
      stage: "before",
      status: "completed",
      target_type: "agent",
    });

    expect(getScopeHookFirings().size).toBe(0);
  });
});

// MARK: Validation

describe("handleHookFired - validation", () => {
  test("drops event when required fields are missing", () => {
    const { ctx, getToolCards, getScopeHookFirings } = createCtx();

    // Missing stage
    handleHookFired(ctx as never, {
      name: "x",
      status: "completed",
      target_type: "agent",
      target_id: "id",
    });
    // Missing status
    handleHookFired(ctx as never, {
      name: "x",
      stage: "before",
      target_type: "agent",
      target_id: "id",
    });
    // Bad target_type
    handleHookFired(ctx as never, {
      name: "x",
      stage: "before",
      status: "completed",
      target_type: "session",
      target_id: "id",
    });
    // Bad stage
    handleHookFired(ctx as never, {
      name: "x",
      stage: "during",
      status: "completed",
      target_type: "agent",
      target_id: "id",
    });

    expect(getToolCards().size).toBe(0);
    expect(getScopeHookFirings().size).toBe(0);
  });

  test("status falls back to 'completed' for unknown values", () => {
    const card = baseToolCard("evt-9");
    const { ctx, getToolCards } = createCtx(new Map([["evt-9", card]]));

    handleHookFired(ctx as never, {
      name: "x",
      stage: "before",
      status: "weird-value",
      target_type: "tool",
      target_id: "evt-9",
    });

    const firings = getToolCards().get("evt-9")!.hookFirings!;
    expect(firings[0].status).toBe("completed");
  });
});
