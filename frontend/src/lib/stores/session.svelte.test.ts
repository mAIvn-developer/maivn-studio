import { describe, expect, it } from "vitest";

import type { ChatFlowItem, Message, ToolCard } from "$lib/types";
import {
  coerceMemoryActivityData,
  computeAccumulatedStats,
  computeEventSummary,
  filterChatFlowItems,
  normalizeNonNegativeNumber,
} from "./session/index.svelte";

// MARK: Helpers

function makeToolFlowItem(overrides: Partial<ToolCard> = {}): ChatFlowItem {
  const card: ToolCard = {
    toolId: "tool-1",
    toolName: "test_tool",
    toolType: "func",
    status: "executing",
    args: {},
    startedAt: "2024-01-01T00:00:00Z",
    isStreaming: false,
    isSystemTool: false,
    ...overrides,
  };
  return {
    id: `flow-${card.toolId}`,
    type: "tool_card",
    timestamp: card.startedAt,
    data: card,
  };
}

function makeMessageFlowItem(overrides: Partial<Message> = {}): ChatFlowItem {
  const msg: Message = {
    id: "msg-1",
    role: "assistant",
    messageType: "ai",
    content: "Hello",
    timestamp: "2024-01-01T00:00:00Z",
    ...overrides,
  };
  return {
    id: msg.id,
    type: "message",
    timestamp: msg.timestamp,
    data: msg,
  };
}

// MARK: computeEventSummary

describe("computeEventSummary", () => {
  it("returns zero counts for empty array", () => {
    const summary = computeEventSummary([]);
    expect(summary).toEqual({
      totalTools: 0,
      pendingTools: 0,
      executingTools: 0,
      completedTools: 0,
      failedTools: 0,
      totalAgents: 0,
      pendingAgents: 0,
      executingAgents: 0,
      completedAgents: 0,
      failedAgents: 0,
      totalMessages: 0,
    });
  });

  it("counts messages", () => {
    const items = [makeMessageFlowItem(), makeMessageFlowItem({ id: "msg-2" })];
    expect(computeEventSummary(items).totalMessages).toBe(2);
  });

  it("counts tools by status", () => {
    const items = [
      makeToolFlowItem({ toolId: "t1", status: "pending" }),
      makeToolFlowItem({ toolId: "t2", status: "executing" }),
      makeToolFlowItem({ toolId: "t3", status: "completed" }),
      makeToolFlowItem({ toolId: "t4", status: "failed" }),
    ];
    const summary = computeEventSummary(items);
    expect(summary.pendingTools).toBe(1);
    expect(summary.executingTools).toBe(1);
    expect(summary.completedTools).toBe(1);
    expect(summary.failedTools).toBe(1);
    expect(summary.totalTools).toBe(4);
  });

  it("counts agents separately from tools", () => {
    const items = [
      makeToolFlowItem({
        toolId: "a1",
        toolType: "agent",
        toolName: "Agent One",
        status: "pending",
      }),
      makeToolFlowItem({
        toolId: "a2",
        toolType: "agent",
        toolName: "Agent Two",
        status: "executing",
      }),
      makeToolFlowItem({
        toolId: "a3",
        toolType: "agent",
        toolName: "Agent Three",
        status: "completed",
      }),
      makeToolFlowItem({
        toolId: "a4",
        toolType: "agent",
        toolName: "Agent Four",
        status: "failed",
      }),
      makeToolFlowItem({ toolId: "t1", toolType: "func", status: "completed" }),
    ];
    const summary = computeEventSummary(items);
    expect(summary.totalAgents).toBe(4);
    expect(summary.pendingAgents).toBe(1);
    expect(summary.executingAgents).toBe(1);
    expect(summary.completedAgents).toBe(1);
    expect(summary.failedAgents).toBe(1);
    expect(summary.totalTools).toBe(1);
    expect(summary.completedTools).toBe(1);
  });

  it("counts mixed items correctly", () => {
    const items = [
      makeMessageFlowItem(),
      makeToolFlowItem({ toolId: "t1", status: "completed" }),
      makeToolFlowItem({ toolId: "a1", toolType: "agent", status: "executing" }),
      makeMessageFlowItem({ id: "msg-2" }),
    ];
    const summary = computeEventSummary(items);
    expect(summary.totalMessages).toBe(2);
    expect(summary.totalTools).toBe(1);
    expect(summary.totalAgents).toBe(1);
  });

  it("counts nested logical agents from owned tool cards", () => {
    const items = [
      makeToolFlowItem({
        toolId: "t1",
        toolType: "func",
        status: "completed",
        agentName: "Research Coordinator",
        swarmName: "Research Swarm",
      }),
      makeToolFlowItem({
        toolId: "t2",
        toolType: "model",
        status: "completed",
        agentName: "Research Coordinator",
        swarmName: "Research Swarm",
      }),
      makeToolFlowItem({
        toolId: "t3",
        toolType: "func",
        status: "completed",
        agentName: "Data Analyzer",
        swarmName: "Research Swarm",
      }),
    ];

    const summary = computeEventSummary(items);
    expect(summary.totalTools).toBe(3);
    expect(summary.completedTools).toBe(3);
    expect(summary.totalAgents).toBe(2);
    expect(summary.completedAgents).toBe(2);
  });

  it("does not double-count agent groups when control and owned tools coexist", () => {
    const items = [
      makeToolFlowItem({
        toolId: "agent-1",
        toolType: "agent",
        toolName: "Research Coordinator",
        status: "completed",
        agentName: "Research Coordinator",
        swarmName: "Research Swarm",
      }),
      makeToolFlowItem({
        toolId: "t1",
        toolType: "func",
        status: "completed",
        agentName: "Research Coordinator",
        swarmName: "Research Swarm",
      }),
    ];

    const summary = computeEventSummary(items);
    expect(summary.totalTools).toBe(1);
    expect(summary.completedTools).toBe(1);
    expect(summary.totalAgents).toBe(1);
    expect(summary.completedAgents).toBe(1);
  });

  it("ignores non-tool non-message items", () => {
    const items: ChatFlowItem[] = [
      {
        id: "phase-1",
        type: "phase_chip",
        timestamp: "2024-01-01T00:00:00Z",
        data: { phase: "planning", message: "Planning...", timestamp: "2024-01-01T00:00:00Z" },
      },
      makeMessageFlowItem(),
    ];
    const summary = computeEventSummary(items);
    expect(summary.totalMessages).toBe(1);
    expect(summary.totalTools).toBe(0);
  });
});

// MARK: filterChatFlowItems

describe("filterChatFlowItems", () => {
  const defaultFilters = {
    itemType: "all" as const,
    toolStatus: "all" as const,
    expandAllCards: false,
    showToolArgs: false,
    richResultDisplay: false,
    showStructuredOutput: false,
    showSessionDetails: false,
  };

  const mixedItems = [
    makeMessageFlowItem(),
    makeToolFlowItem({ toolId: "t1", status: "completed" }),
    makeToolFlowItem({ toolId: "t2", status: "failed" }),
  ];

  it("returns all items with default filters", () => {
    const result = filterChatFlowItems(mixedItems, defaultFilters);
    expect(result).toHaveLength(3);
  });

  it("filters to messages only", () => {
    const result = filterChatFlowItems(mixedItems, {
      ...defaultFilters,
      itemType: "messages",
    });
    expect(result).toHaveLength(1);
    expect(result[0].type).toBe("message");
  });

  it("filters to tools only", () => {
    const result = filterChatFlowItems(mixedItems, {
      ...defaultFilters,
      itemType: "tools",
    });
    expect(result).toHaveLength(2);
    expect(result.every((i) => i.type === "tool_card")).toBe(true);
  });

  it("filters tools by status", () => {
    const result = filterChatFlowItems(mixedItems, {
      ...defaultFilters,
      toolStatus: "completed",
    });
    // Messages pass (not tool_card), plus only "completed" tools
    expect(result).toHaveLength(2);
    const toolItems = result.filter((i) => i.type === "tool_card");
    expect(toolItems).toHaveLength(1);
    expect((toolItems[0].data as ToolCard).status).toBe("completed");
  });

  it("combines itemType and toolStatus filters", () => {
    const result = filterChatFlowItems(mixedItems, {
      ...defaultFilters,
      itemType: "tools",
      toolStatus: "failed",
    });
    expect(result).toHaveLength(1);
    expect((result[0].data as ToolCard).status).toBe("failed");
  });

  it("returns empty array when no items match", () => {
    const result = filterChatFlowItems(mixedItems, {
      ...defaultFilters,
      itemType: "tools",
      toolStatus: "pending",
    });
    expect(result).toHaveLength(0);
  });

  it("returns empty array for empty input", () => {
    const result = filterChatFlowItems([], defaultFilters);
    expect(result).toHaveLength(0);
  });
});

// MARK: computeAccumulatedStats

describe("computeAccumulatedStats", () => {
  it("returns zero stats for empty array", () => {
    const stats = computeAccumulatedStats([]);
    expect(stats).toEqual({
      totalDurationMs: 0,
      totalTokens: 0,
      inputTokens: 0,
      outputTokens: 0,
      reasoningTokens: 0,
      cacheReadTokens: 0,
      cacheCreationTokens: 0,
      sessionCount: 0,
    });
  });

  it("ignores user messages", () => {
    const items = [makeMessageFlowItem({ role: "user" })];
    const stats = computeAccumulatedStats(items);
    expect(stats.sessionCount).toBe(0);
  });

  it("ignores assistant messages without sessionDetails", () => {
    const items = [makeMessageFlowItem({ role: "assistant" })];
    const stats = computeAccumulatedStats(items);
    expect(stats.sessionCount).toBe(0);
  });

  it("counts sessions from assistant messages with sessionDetails", () => {
    const items = [
      makeMessageFlowItem({
        role: "assistant",
        sessionDetails: { duration_ms: 500 },
      }),
    ];
    const stats = computeAccumulatedStats(items);
    expect(stats.sessionCount).toBe(1);
    expect(stats.totalDurationMs).toBe(500);
  });

  it("accumulates token usage across multiple sessions", () => {
    const items = [
      makeMessageFlowItem({
        id: "msg-1",
        role: "assistant",
        sessionDetails: {
          duration_ms: 100,
          token_usage: {
            total_tokens: 50,
            input_tokens: 20,
            output_tokens: 25,
            reasoning_tokens: 5,
            cache_read_tokens: 3,
            cache_creation_tokens: 2,
          },
        },
      }),
      makeMessageFlowItem({
        id: "msg-2",
        role: "assistant",
        sessionDetails: {
          duration_ms: 200,
          token_usage: {
            total_tokens: 100,
            input_tokens: 40,
            output_tokens: 50,
            reasoning_tokens: 10,
            cache_read_tokens: 7,
            cache_creation_tokens: 3,
          },
        },
      }),
    ];
    const stats = computeAccumulatedStats(items);
    expect(stats.sessionCount).toBe(2);
    expect(stats.totalDurationMs).toBe(300);
    expect(stats.totalTokens).toBe(150);
    expect(stats.inputTokens).toBe(60);
    expect(stats.outputTokens).toBe(75);
    expect(stats.reasoningTokens).toBe(15);
    expect(stats.cacheReadTokens).toBe(10);
    expect(stats.cacheCreationTokens).toBe(5);
  });

  it("handles sessionDetails with duration but no token_usage", () => {
    const items = [
      makeMessageFlowItem({
        role: "assistant",
        sessionDetails: { duration_ms: 750 },
      }),
    ];
    const stats = computeAccumulatedStats(items);
    expect(stats.sessionCount).toBe(1);
    expect(stats.totalDurationMs).toBe(750);
    expect(stats.totalTokens).toBe(0);
  });

  it("ignores tool_card items", () => {
    const items = [
      makeToolFlowItem({ toolId: "t1" }),
      makeMessageFlowItem({
        role: "assistant",
        sessionDetails: { duration_ms: 100 },
      }),
    ];
    const stats = computeAccumulatedStats(items);
    expect(stats.sessionCount).toBe(1);
  });
});

// MARK: normalizeNonNegativeNumber

describe("normalizeNonNegativeNumber", () => {
  it("accepts zero", () => {
    expect(normalizeNonNegativeNumber(0)).toBe(0);
  });

  it("accepts positive integers", () => {
    expect(normalizeNonNegativeNumber(1)).toBe(1);
    expect(normalizeNonNegativeNumber(42)).toBe(42);
    expect(normalizeNonNegativeNumber(1000)).toBe(1000);
  });

  it("coerces string integers", () => {
    expect(normalizeNonNegativeNumber("0")).toBe(0);
    expect(normalizeNonNegativeNumber("5")).toBe(5);
    expect(normalizeNonNegativeNumber("100")).toBe(100);
  });

  it("rejects negative numbers", () => {
    expect(normalizeNonNegativeNumber(-1)).toBeUndefined();
    expect(normalizeNonNegativeNumber(-100)).toBeUndefined();
  });

  it("rejects fractional numbers", () => {
    expect(normalizeNonNegativeNumber(1.25)).toBeUndefined();
    expect(normalizeNonNegativeNumber(0.5)).toBeUndefined();
  });

  it("rejects NaN", () => {
    expect(normalizeNonNegativeNumber(NaN)).toBeUndefined();
  });

  it("rejects Infinity", () => {
    expect(normalizeNonNegativeNumber(Infinity)).toBeUndefined();
    expect(normalizeNonNegativeNumber(-Infinity)).toBeUndefined();
  });

  it("rejects non-numeric types", () => {
    expect(normalizeNonNegativeNumber(null)).toBeUndefined();
    expect(normalizeNonNegativeNumber(undefined)).toBeUndefined();
    expect(normalizeNonNegativeNumber(true)).toBeUndefined();
    expect(normalizeNonNegativeNumber({})).toBeUndefined();
    expect(normalizeNonNegativeNumber([])).toBeUndefined();
  });

  it("rejects non-numeric strings", () => {
    expect(normalizeNonNegativeNumber("abc")).toBeUndefined();
    expect(normalizeNonNegativeNumber("")).toBeUndefined();
    expect(normalizeNonNegativeNumber("  ")).toBeUndefined();
  });

  it("rejects string floats", () => {
    expect(normalizeNonNegativeNumber("1.5")).toBeUndefined();
  });
});

// MARK: coerceMemoryActivityData

describe("coerceMemoryActivityData", () => {
  describe("basic validation", () => {
    it("returns undefined for null", () => {
      expect(coerceMemoryActivityData(null)).toBeUndefined();
    });

    it("returns undefined for undefined", () => {
      expect(coerceMemoryActivityData(undefined)).toBeUndefined();
    });

    it("returns undefined for arrays", () => {
      expect(coerceMemoryActivityData([1, 2, 3])).toBeUndefined();
    });

    it("returns undefined for non-objects", () => {
      expect(coerceMemoryActivityData("string")).toBeUndefined();
      expect(coerceMemoryActivityData(42)).toBeUndefined();
      expect(coerceMemoryActivityData(true)).toBeUndefined();
    });

    it("returns undefined for empty object (no recognized fields)", () => {
      expect(coerceMemoryActivityData({})).toBeUndefined();
    });
  });

  describe("string fields", () => {
    it("coerces mode, source, status fields", () => {
      const details = coerceMemoryActivityData({
        mode: "extract_skills",
        source: "execution_trace",
        status: "success",
      });

      expect(details).toMatchObject({
        mode: "extract_skills",
        source: "execution_trace",
        status: "success",
      });
    });

    it("trims whitespace from string fields", () => {
      const details = coerceMemoryActivityData({
        mode: "  retrieve  ",
        memory_level: "  high  ",
        policy_mode: "  strict  ",
      });

      expect(details).toMatchObject({
        mode: "retrieve",
        memoryLevel: "high",
        policyMode: "strict",
      });
    });

    it("ignores empty or whitespace-only string fields", () => {
      const details = coerceMemoryActivityData({
        mode: "valid",
        source: "",
        status: "   ",
      });

      expect(details).toEqual({ mode: "valid" });
    });
  });

  describe("numeric fields", () => {
    it("preserves explicit zero metrics", () => {
      const details = coerceMemoryActivityData({
        hit_count: 0,
        vector_hits: "0",
        keyword_hits: 0,
        graph_hits: 0,
        skill_count: 0,
        insight_count: 0,
        resource_count: 0,
        vector_rows: 0,
        graph_edges: "0",
        trace_event_count: 0,
        latency_ms: 0,
      });

      expect(details).toEqual({
        hitCount: 0,
        vectorHits: 0,
        keywordHits: 0,
        graphHits: 0,
        skillCount: 0,
        insightCount: 0,
        resourceCount: 0,
        vectorRows: 0,
        graphEdges: 0,
        traceEventCount: 0,
        latencyMs: 0,
      });
    });

    it("ignores invalid numeric values", () => {
      const details = coerceMemoryActivityData({
        mode: "test",
        hit_count: -1,
        vector_hits: 1.5,
        latency_ms: "abc",
      });

      expect(details).toEqual({ mode: "test" });
    });
  });

  describe("resource lifecycle fields", () => {
    it("coerces resource lifecycle metrics and IDs", () => {
      const details = coerceMemoryActivityData({
        registered_count: 2,
        reused_count: 1,
        skipped_count: 0,
        total_bytes: 4096,
        dedup_reused_count: 1,
        version_superseded_count: 1,
        discovery_count: 4,
        selected_count: 2,
        chunk_count: 7,
        requested_resource_id: "doc-123",
        requested_max_resources: 3,
        required_tag_count: 2,
        full_extraction: true,
        resource_ids: ["doc-123", "doc-456"],
        superseded_resource_ids: ["doc-old"],
      });

      expect(details).toMatchObject({
        registeredCount: 2,
        reusedCount: 1,
        skippedCount: 0,
        totalBytes: 4096,
        dedupReusedCount: 1,
        versionSupersededCount: 1,
        discoveryCount: 4,
        selectedCount: 2,
        chunkCount: 7,
        requestedResourceId: "doc-123",
        requestedMaxResources: 3,
        requiredTagCount: 2,
        fullExtraction: true,
        resourceIds: ["doc-123", "doc-456"],
        supersededResourceIds: ["doc-old"],
      });
    });

    it("filters non-string items from resource_ids arrays", () => {
      const details = coerceMemoryActivityData({
        resource_ids: ["valid", 123, null, "another", ""],
      });

      expect(details?.resourceIds).toEqual(["valid", "another"]);
    });

    it("ignores empty resource_ids arrays after filtering", () => {
      const details = coerceMemoryActivityData({
        mode: "test",
        resource_ids: [123, null, ""],
      });

      expect(details?.resourceIds).toBeUndefined();
    });

    it("handles full_extraction boolean", () => {
      expect(coerceMemoryActivityData({ full_extraction: true })?.fullExtraction).toBe(true);
      expect(coerceMemoryActivityData({ full_extraction: false })?.fullExtraction).toBe(false);
    });

    it("ignores non-boolean full_extraction", () => {
      const details = coerceMemoryActivityData({
        mode: "test",
        full_extraction: "true",
      });

      expect(details?.fullExtraction).toBeUndefined();
    });
  });

  describe("extraction count fields", () => {
    it("coerces extracted_count and persisted_count", () => {
      const details = coerceMemoryActivityData({
        extracted_count: 5,
        persisted_count: 3,
      });

      expect(details).toMatchObject({
        extractedCount: 5,
        persistedCount: 3,
      });
    });

    it("coerces string values for extraction counts", () => {
      const details = coerceMemoryActivityData({
        extracted_count: "2",
        persisted_count: "1",
      });

      expect(details).toMatchObject({
        extractedCount: 2,
        persistedCount: 1,
      });
    });
  });

  describe("skill summaries", () => {
    it("coerces valid skill summaries from snake_case backend format", () => {
      const details = coerceMemoryActivityData({
        skills: [
          {
            name: "Data Analysis",
            description: "Analyze datasets",
            confidence: 0.95,
            sharing_scope: "project",
          },
          {
            name: "Report Generation",
            description: "Generate reports",
            confidence: 0.8,
            sharing_scope: "organization",
          },
        ],
      });

      expect(details?.skills).toEqual([
        {
          name: "Data Analysis",
          description: "Analyze datasets",
          confidence: 0.95,
          sharingScope: "project",
        },
        {
          name: "Report Generation",
          description: "Generate reports",
          confidence: 0.8,
          sharingScope: "organization",
        },
      ]);
    });

    it("skips skills without a valid name", () => {
      const details = coerceMemoryActivityData({
        mode: "extract_skills",
        skills: [
          { name: "Valid Skill", description: "test", confidence: 0.9, sharing_scope: "project" },
          { name: "", description: "missing name", confidence: 0.5, sharing_scope: "project" },
          { name: "   ", description: "whitespace name", confidence: 0.5, sharing_scope: "agent" },
          { description: "no name field", confidence: 0.5, sharing_scope: "agent" },
          null,
          42,
        ],
      });

      expect(details?.skills).toHaveLength(1);
      expect(details?.skills?.[0].name).toBe("Valid Skill");
    });

    it("applies defaults for missing optional skill fields", () => {
      const details = coerceMemoryActivityData({
        skills: [{ name: "Minimal Skill" }],
      });

      expect(details?.skills?.[0]).toEqual({
        name: "Minimal Skill",
        description: "",
        confidence: 0,
        sharingScope: "project",
      });
    });

    it("trims whitespace from skill string fields", () => {
      const details = coerceMemoryActivityData({
        skills: [
          {
            name: "  Padded Name  ",
            description: "  Padded Desc  ",
            confidence: 0.9,
            sharing_scope: "  project  ",
          },
        ],
      });

      expect(details?.skills?.[0].name).toBe("Padded Name");
      expect(details?.skills?.[0].description).toBe("Padded Desc");
      expect(details?.skills?.[0].sharingScope).toBe("project");
    });

    it("omits skills key when input is not an array", () => {
      const details = coerceMemoryActivityData({
        mode: "test",
        skills: "not an array",
      });

      expect(details?.skills).toBeUndefined();
    });

    it("omits skills key when all items are invalid", () => {
      const details = coerceMemoryActivityData({
        mode: "test",
        skills: [null, { name: "" }, 42],
      });

      expect(details?.skills).toBeUndefined();
    });
  });

  describe("insight summaries", () => {
    it("coerces valid insight summaries from snake_case backend format", () => {
      const details = coerceMemoryActivityData({
        insights: [
          {
            insight_type: "lesson",
            content: "Always validate inputs",
            relevance_score: 0.9,
            sharing_scope: "agent",
          },
          {
            insight_type: "warning",
            content: "Rate limits may apply",
            relevance_score: 0.7,
            sharing_scope: "project",
          },
        ],
      });

      expect(details?.insights).toEqual([
        {
          insightType: "lesson",
          content: "Always validate inputs",
          relevanceScore: 0.9,
          sharingScope: "agent",
        },
        {
          insightType: "warning",
          content: "Rate limits may apply",
          relevanceScore: 0.7,
          sharingScope: "project",
        },
      ]);
    });

    it("skips insights without valid content", () => {
      const details = coerceMemoryActivityData({
        mode: "extract_insights",
        insights: [
          {
            insight_type: "lesson",
            content: "Valid",
            relevance_score: 0.9,
            sharing_scope: "agent",
          },
          { insight_type: "lesson", content: "", relevance_score: 0.5, sharing_scope: "agent" },
          { insight_type: "lesson", content: "   ", relevance_score: 0.5, sharing_scope: "agent" },
          { insight_type: "lesson", sharing_scope: "agent" },
          null,
          "string",
        ],
      });

      expect(details?.insights).toHaveLength(1);
      expect(details?.insights?.[0].content).toBe("Valid");
    });

    it("applies defaults for missing optional insight fields", () => {
      const details = coerceMemoryActivityData({
        insights: [{ content: "Minimal insight" }],
      });

      expect(details?.insights?.[0]).toEqual({
        insightType: "lesson",
        content: "Minimal insight",
        relevanceScore: 0,
        sharingScope: "agent",
      });
    });

    it("trims whitespace from insight string fields", () => {
      const details = coerceMemoryActivityData({
        insights: [
          {
            insight_type: "  warning  ",
            content: "  Padded Content  ",
            relevance_score: 0.8,
            sharing_scope: "  project  ",
          },
        ],
      });

      expect(details?.insights?.[0].insightType).toBe("warning");
      expect(details?.insights?.[0].content).toBe("Padded Content");
      expect(details?.insights?.[0].sharingScope).toBe("project");
    });

    it("omits insights key when input is not an array", () => {
      const details = coerceMemoryActivityData({
        mode: "test",
        insights: "not an array",
      });

      expect(details?.insights).toBeUndefined();
    });

    it("omits insights key when all items are invalid", () => {
      const details = coerceMemoryActivityData({
        mode: "test",
        insights: [null, { content: "" }, 42],
      });

      expect(details?.insights).toBeUndefined();
    });
  });

  describe("combined payload", () => {
    it("coerces a full extraction completion payload", () => {
      const details = coerceMemoryActivityData({
        mode: "extract_skills",
        extracted_count: 3,
        persisted_count: 2,
        latency_ms: 1500,
        skills: [
          {
            name: "Skill A",
            description: "First skill",
            confidence: 0.95,
            sharing_scope: "project",
          },
          {
            name: "Skill B",
            description: "Second skill",
            confidence: 0.8,
            sharing_scope: "organization",
          },
        ],
      });

      expect(details).toMatchObject({
        mode: "extract_skills",
        extractedCount: 3,
        persistedCount: 2,
        latencyMs: 1500,
      });
      expect(details?.skills).toHaveLength(2);
    });

    it("coerces a retrieval context payload", () => {
      const details = coerceMemoryActivityData({
        mode: "retrieve",
        hit_count: 5,
        vector_hits: 3,
        keyword_hits: 1,
        graph_hits: 1,
        skill_count: 2,
        insight_count: 3,
        latency_ms: 250,
      });

      expect(details).toMatchObject({
        mode: "retrieve",
        hitCount: 5,
        vectorHits: 3,
        keywordHits: 1,
        graphHits: 1,
        skillCount: 2,
        insightCount: 3,
        latencyMs: 250,
      });
    });
  });
});
