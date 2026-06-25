import { describe, expect, it } from "vitest";

import type { ToolCard as ToolCardType } from "$lib/types";

import { buildScopeGroups } from "./exchange-scope-groups";

function makeCard(overrides: Partial<ToolCardType> & Pick<ToolCardType, "toolId">): ToolCardType {
  return {
    toolName: overrides.toolName ?? overrides.toolId,
    toolType: "func",
    status: "completed",
    args: {},
    startedAt: "2026-05-08T03:00:00Z",
    isStreaming: false,
    isSystemTool: false,
    ...overrides,
  };
}

describe("buildScopeGroups", () => {
  it("returns one NestedAgent per agent invocation when the same agent runs twice in a swarm", () => {
    // Supervisor_loop redeploys `coding_agent` twice. The server emits two
    // distinct swarm-action tool cards (different tool_ids) plus nested tool
    // cards inside each. The previous implementation grouped by agentName so
    // every nested tool from both runs collapsed into one card. The new
    // implementation gives each invocation its own card.
    const cards: ToolCardType[] = [
      makeCard({
        toolId: "swarm_tool_coding_agent_AAAA",
        toolName: "coding_agent",
        toolType: "agent",
        agentName: "coding_agent",
        swarmName: "creator_swarm",
        startedAt: "2026-05-08T03:00:00Z",
      }),
      makeCard({
        toolId: "tool_read_1",
        toolName: "read_file",
        agentName: "coding_agent",
        swarmName: "creator_swarm",
        startedAt: "2026-05-08T03:00:01Z",
      }),
      makeCard({
        toolId: "swarm_tool_coding_agent_BBBB",
        toolName: "coding_agent",
        toolType: "agent",
        agentName: "coding_agent",
        swarmName: "creator_swarm",
        startedAt: "2026-05-08T03:00:10Z",
      }),
      makeCard({
        toolId: "tool_edit_1",
        toolName: "edit_file",
        agentName: "coding_agent",
        swarmName: "creator_swarm",
        startedAt: "2026-05-08T03:00:11Z",
      }),
    ];

    const groups = buildScopeGroups(cards);

    expect(groups).toHaveLength(1);
    const swarmGroup = groups[0];
    expect(swarmGroup.type).toBe("swarm");
    expect(swarmGroup.nestedAgents).toHaveLength(2);

    const [firstInvocation, secondInvocation] = swarmGroup.nestedAgents;

    // Each invocation has its own unique invocationId (the agent card's tool_id).
    expect(firstInvocation.invocationId).toBe("swarm_tool_coding_agent_AAAA");
    expect(secondInvocation.invocationId).toBe("swarm_tool_coding_agent_BBBB");

    // Both share the agentName but render as separate cards in the UI.
    expect(firstInvocation.agentName).toBe("coding_agent");
    expect(secondInvocation.agentName).toBe("coding_agent");

    // Nested tools are routed by the most recent open invocation, so read_file
    // belongs to invocation #1 and edit_file to invocation #2 — not merged.
    const firstNested = firstInvocation.tools.map((t) => t.toolId);
    const secondNested = secondInvocation.tools.map((t) => t.toolId);
    expect(firstNested).toContain("tool_read_1");
    expect(firstNested).not.toContain("tool_edit_1");
    expect(secondNested).toContain("tool_edit_1");
    expect(secondNested).not.toContain("tool_read_1");
  });

  it("emits one ScopeGroup per standalone agent invocation when the same agent runs twice", () => {
    // Same logic for non-swarm contexts: each agent tool card is its own
    // ScopeGroup keyed by invocationId.
    const cards: ToolCardType[] = [
      makeCard({
        toolId: "agent_tool_X1",
        toolName: "writer",
        toolType: "agent",
        agentName: "writer",
        startedAt: "2026-05-08T03:00:00Z",
      }),
      makeCard({
        toolId: "agent_tool_X2",
        toolName: "writer",
        toolType: "agent",
        agentName: "writer",
        startedAt: "2026-05-08T03:00:10Z",
      }),
    ];

    const groups = buildScopeGroups(cards);

    expect(groups).toHaveLength(2);
    expect(groups.every((g) => g.type === "agent")).toBe(true);
    expect(groups[0].invocationId).toBe("agent_tool_X1");
    expect(groups[1].invocationId).toBe("agent_tool_X2");
  });

  it("attributes a nested tool to the most recent open invocation when two agents alternate", () => {
    // Two different agents in a swarm, each invoked once. Nested tools must
    // route to their owning invocation by the (swarm, agentName) key.
    const cards: ToolCardType[] = [
      makeCard({
        toolId: "swarm_tool_alpha_1",
        toolName: "alpha",
        toolType: "agent",
        agentName: "alpha",
        swarmName: "creator_swarm",
      }),
      makeCard({
        toolId: "swarm_tool_beta_1",
        toolName: "beta",
        toolType: "agent",
        agentName: "beta",
        swarmName: "creator_swarm",
      }),
      makeCard({
        toolId: "tool_alpha_nested",
        toolName: "read_file",
        agentName: "alpha",
        swarmName: "creator_swarm",
      }),
      makeCard({
        toolId: "tool_beta_nested",
        toolName: "edit_file",
        agentName: "beta",
        swarmName: "creator_swarm",
      }),
    ];

    const groups = buildScopeGroups(cards);

    expect(groups).toHaveLength(1);
    const swarmGroup = groups[0];
    expect(swarmGroup.nestedAgents).toHaveLength(2);

    const alphaScope = swarmGroup.nestedAgents.find((n) => n.agentName === "alpha");
    const betaScope = swarmGroup.nestedAgents.find((n) => n.agentName === "beta");
    expect(alphaScope?.tools.map((t) => t.toolId)).toContain("tool_alpha_nested");
    expect(alphaScope?.tools.map((t) => t.toolId)).not.toContain("tool_beta_nested");
    expect(betaScope?.tools.map((t) => t.toolId)).toContain("tool_beta_nested");
    expect(betaScope?.tools.map((t) => t.toolId)).not.toContain("tool_alpha_nested");
  });

  it("collapses tool_event + agent_assignment to one NestedAgent when both already share a card", () => {
    // The studio's tool-events.ts and agent-assignment-events.ts merge the
    // tool_event (id="swarm_tool_<agent>_<rand>") and agent_assignment
    // (id="<action_uuid>") for the same action into a single agent-typed
    // card via a lifecycle-gated by-agentName fallback. By the time
    // buildScopeGroups runs there is exactly ONE agent-typed card per
    // action — so this test pins the post-merge invariant: one
    // NestedAgent per swarm action regardless of which event source
    // arrived first.
    const cards: ToolCardType[] = [
      makeCard({
        toolId: "swarm_tool_coding_agent_only",
        toolName: "coding_agent",
        toolType: "agent",
        agentName: "coding_agent",
        swarmName: "creator_swarm",
      }),
      makeCard({
        toolId: "tool_read_file",
        toolName: "read_file",
        agentName: "coding_agent",
        swarmName: "creator_swarm",
      }),
    ];

    const groups = buildScopeGroups(cards);

    expect(groups).toHaveLength(1);
    expect(groups[0].nestedAgents).toHaveLength(1);
    expect(groups[0].nestedAgents[0].invocationId).toBe("swarm_tool_coding_agent_only");
  });

  it("renders a standalone agent's tools even when no toolType=agent anchor card exists", () => {
    // Standalone (non-swarm) runs of a single agent never get a
    // tool_event with toolType="agent" — those only fire for swarm
    // dispatches. The first iteration of buildScopeGroups dropped these
    // tools because they had no anchor card to attach to. The fix
    // synthesizes an InvocationScope keyed by agentName so the agent's
    // tool calls remain visible.
    const cards: ToolCardType[] = [
      makeCard({
        toolId: "tool_hardware_scan",
        toolName: "hardware_scanner",
        toolType: "func",
        agentName: "Diagnostics Agent",
        // no swarmName — this is a standalone agent run
      }),
      makeCard({
        toolId: "tool_run_diagnostics",
        toolName: "run_diagnostics",
        toolType: "func",
        agentName: "Diagnostics Agent",
      }),
      makeCard({
        toolId: "tool_check_firmware",
        toolName: "check_firmware",
        toolType: "func",
        agentName: "Diagnostics Agent",
      }),
    ];

    const groups = buildScopeGroups(cards);

    expect(groups).toHaveLength(1);
    const standalone = groups[0];
    expect(standalone.type).toBe("agent");
    expect(standalone.name).toBe("Diagnostics Agent");
    // Synthetic invocationId is keyed by agent name to keep the rendering
    // stable across re-renders.
    expect(standalone.invocationId).toBe("agent:Diagnostics Agent");
    const toolIds = standalone.tools.map((t) => t.toolId).sort();
    expect(toolIds).toEqual(["tool_check_firmware", "tool_hardware_scan", "tool_run_diagnostics"]);
  });

  it("groups root standalone system tools without exposing the root agent name", () => {
    const cards: ToolCardType[] = [
      makeCard({
        toolId: "system-tool-repl",
        toolName: "repl",
        toolType: "system",
        agentName: "REPL Demo Agent",
        isSystemTool: true,
      }),
    ];

    const groups = buildScopeGroups(cards);

    expect(groups).toHaveLength(1);
    expect(groups[0].type).toBe("system");
    expect(groups[0].name).toBe("System tools");
    expect(groups[0].invocationId).toBe("system:tools");
    expect(groups[0].tools.map((tool) => tool.toolId)).toEqual(["system-tool-repl"]);
  });

  it("returns an empty array for no tool cards", () => {
    expect(buildScopeGroups([])).toEqual([]);
  });

  it("keeps swarm-root tools (no agentName) in the swarm group's tools", () => {
    const cards: ToolCardType[] = [
      makeCard({
        toolId: "swarm_root_progress",
        toolName: "progress",
        swarmName: "creator_swarm",
      }),
    ];

    const groups = buildScopeGroups(cards);
    expect(groups).toHaveLength(1);
    expect(groups[0].type).toBe("swarm");
    expect(groups[0].tools.map((t) => t.toolId)).toContain("swarm_root_progress");
  });

  it("nests agent-owned tools under the only swarm when tool events omit swarmName", () => {
    const cards: ToolCardType[] = [
      makeCard({
        toolId: "report",
        toolName: "generate_research_report",
        toolType: "model",
        agentName: "Research Coordinator",
        swarmName: "Research Swarm",
      }),
      makeCard({
        toolId: "fetch",
        toolName: "fetch_data",
        toolType: "func",
        agentName: "Research Coordinator",
      }),
      makeCard({
        toolId: "analyze",
        toolName: "analyze_dataset",
        toolType: "func",
        agentName: "Data Analyzer",
      }),
    ];

    const groups = buildScopeGroups(cards);

    expect(groups).toHaveLength(1);
    expect(groups[0].type).toBe("swarm");
    expect(groups[0].name).toBe("Research Swarm");
    expect(groups[0].tools).toEqual([]);
    expect(
      groups[0].nestedAgents.map((agent) => ({
        agentName: agent.agentName,
        toolNames: agent.tools.map((tool) => tool.toolName),
      })),
    ).toEqual([
      {
        agentName: "Research Coordinator",
        toolNames: ["generate_research_report", "fetch_data"],
      },
      {
        agentName: "Data Analyzer",
        toolNames: ["analyze_dataset"],
      },
    ]);
  });

  it("merges an inferred swarm agent scope when its real agent card arrives later", () => {
    const cards: ToolCardType[] = [
      makeCard({
        toolId: "fetch",
        toolName: "fetch_data",
        toolType: "func",
        agentName: "Research Coordinator",
      }),
      makeCard({
        toolId: "research-coordinator-agent",
        toolName: "Research Coordinator",
        toolType: "agent",
        agentName: "Research Coordinator",
        swarmName: "Research Swarm",
      }),
      makeCard({
        toolId: "report",
        toolName: "generate_research_report",
        toolType: "model",
        agentName: "Research Coordinator",
        swarmName: "Research Swarm",
      }),
      makeCard({
        toolId: "analyze",
        toolName: "analyze_dataset",
        toolType: "func",
        agentName: "Data Analyzer",
      }),
    ];

    const groups = buildScopeGroups(cards);

    expect(groups).toHaveLength(1);
    expect(groups[0].nestedAgents.map((agent) => agent.agentName)).toEqual([
      "Research Coordinator",
      "Data Analyzer",
    ]);

    const researchCoordinator = groups[0].nestedAgents.find(
      (agent) => agent.agentName === "Research Coordinator",
    );
    expect(researchCoordinator?.tools.map((tool) => tool.toolName)).toEqual([
      "fetch_data",
      "Research Coordinator",
      "generate_research_report",
    ]);
  });
});
