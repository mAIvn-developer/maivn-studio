import { describe, expect, it } from "vitest";

import {
  buildEnrichmentScopeKey,
  ENRICHMENT_PHASE_LABELS,
  EnrichmentTracker,
  KNOWN_ENRICHMENT_PHASE_ORDER,
  MEMORY_PHASE_SCOPE_MAP,
  normalizeScopeType,
  normalizeScopeValue,
  PERSISTENT_MEMORY_PHASES,
  PHASE_RESET_MARKERS,
  resolveEnrichmentDisplayMessage,
  resolveKnownPhaseRank,
  resolveMemoryScopeKey,
  resolveProcessingScopePriority,
  ROOT_ENRICHMENT_SCOPE_KEY,
} from "./enrichmentTracker";

// MARK: Constants

describe("constants", () => {
  it("ROOT_ENRICHMENT_SCOPE_KEY is a non-empty string", () => {
    expect(ROOT_ENRICHMENT_SCOPE_KEY).toBe("__root_scope__");
  });

  it("MEMORY_PHASE_SCOPE_MAP pairs extracting/extracted phases to shared scope keys", () => {
    // Extracting and extracted phases for the same operation share a scope
    expect(MEMORY_PHASE_SCOPE_MAP["memory_skill_extracting"]).toBe("__memory:extract_skills__");
    expect(MEMORY_PHASE_SCOPE_MAP["memory_skill_extracted"]).toBe("__memory:extract_skills__");

    expect(MEMORY_PHASE_SCOPE_MAP["memory_insight_extracting"]).toBe("__memory:extract_insights__");
    expect(MEMORY_PHASE_SCOPE_MAP["memory_insight_extracted"]).toBe("__memory:extract_insights__");

    expect(MEMORY_PHASE_SCOPE_MAP["memory_retrieving"]).toBe("__memory:retrieve__");
    expect(MEMORY_PHASE_SCOPE_MAP["memory_retrieved"]).toBe("__memory:retrieve__");

    expect(MEMORY_PHASE_SCOPE_MAP["memory_indexing"]).toBe("__memory:index__");
    expect(MEMORY_PHASE_SCOPE_MAP["memory_indexed"]).toBe("__memory:index__");
    expect(MEMORY_PHASE_SCOPE_MAP["memory_graph_extracting"]).toBe("__memory:index__");
  });

  it("PERSISTENT_MEMORY_PHASES contains all keys from MEMORY_PHASE_SCOPE_MAP", () => {
    for (const key of Object.keys(MEMORY_PHASE_SCOPE_MAP)) {
      expect(PERSISTENT_MEMORY_PHASES.has(key)).toBe(true);
    }
    expect(PERSISTENT_MEMORY_PHASES.size).toBe(Object.keys(MEMORY_PHASE_SCOPE_MAP).length);
  });

  it("KNOWN_ENRICHMENT_PHASE_ORDER assigns increasing ranks for execution phases", () => {
    expect(KNOWN_ENRICHMENT_PHASE_ORDER["evaluating"]).toBe(0);
    expect(KNOWN_ENRICHMENT_PHASE_ORDER["planning"]).toBe(1);
    expect(KNOWN_ENRICHMENT_PHASE_ORDER["synthesizing"]).toBe(7);
    expect(KNOWN_ENRICHMENT_PHASE_ORDER["complete"]).toBe(8);
    expect(KNOWN_ENRICHMENT_PHASE_ORDER["completed"]).toBe(8);
    expect(KNOWN_ENRICHMENT_PHASE_ORDER["failed"]).toBe(8);
  });

  it("PHASE_RESET_MARKERS are a subset of KNOWN_ENRICHMENT_PHASE_ORDER", () => {
    for (const marker of PHASE_RESET_MARKERS) {
      expect(KNOWN_ENRICHMENT_PHASE_ORDER[marker]).toBeDefined();
    }
  });

  it("ENRICHMENT_PHASE_LABELS has labels for memory extraction completion phases", () => {
    expect(ENRICHMENT_PHASE_LABELS["memory_skill_extracted"]).toContain("Skills extracted");
    expect(ENRICHMENT_PHASE_LABELS["memory_insight_extracted"]).toContain("Insights extracted");
  });

  it("ENRICHMENT_PHASE_LABELS has labels for all terminal phases", () => {
    expect(ENRICHMENT_PHASE_LABELS["complete"]).toBe("Complete");
    expect(ENRICHMENT_PHASE_LABELS["completed"]).toBe("Complete");
    expect(ENRICHMENT_PHASE_LABELS["failed"]).toBe("Failed");
  });
});

// MARK: resolveMemoryScopeKey

describe("resolveMemoryScopeKey", () => {
  it("returns scope key for known memory phases", () => {
    expect(resolveMemoryScopeKey("memory_skill_extracting")).toBe("__memory:extract_skills__");
    expect(resolveMemoryScopeKey("memory_retrieved")).toBe("__memory:retrieve__");
    expect(resolveMemoryScopeKey("memory_indexed")).toBe("__memory:index__");
  });

  it("returns null for execution phases", () => {
    expect(resolveMemoryScopeKey("evaluating")).toBeNull();
    expect(resolveMemoryScopeKey("planning")).toBeNull();
    expect(resolveMemoryScopeKey("synthesizing")).toBeNull();
    expect(resolveMemoryScopeKey("complete")).toBeNull();
  });

  it("handles whitespace and casing normalization", () => {
    expect(resolveMemoryScopeKey("  Memory_Skill_Extracting  ")).toBe("__memory:extract_skills__");
    expect(resolveMemoryScopeKey("MEMORY_INDEXED")).toBe("__memory:index__");
  });

  it("returns null for unknown phases", () => {
    expect(resolveMemoryScopeKey("unknown_phase")).toBeNull();
    expect(resolveMemoryScopeKey("")).toBeNull();
  });
});

// MARK: resolveKnownPhaseRank

describe("resolveKnownPhaseRank", () => {
  it("returns rank for known execution phases", () => {
    expect(resolveKnownPhaseRank("evaluating")).toBe(0);
    expect(resolveKnownPhaseRank("planning")).toBe(1);
    expect(resolveKnownPhaseRank("searching_tools")).toBe(2);
    expect(resolveKnownPhaseRank("complete")).toBe(8);
  });

  it("returns null for unknown phases", () => {
    expect(resolveKnownPhaseRank("memory_skill_extracting")).toBeNull();
    expect(resolveKnownPhaseRank("bogus")).toBeNull();
    expect(resolveKnownPhaseRank("")).toBeNull();
  });

  it("normalizes whitespace and casing", () => {
    expect(resolveKnownPhaseRank("  EVALUATING  ")).toBe(0);
    expect(resolveKnownPhaseRank("Complete")).toBe(8);
  });
});

// MARK: resolveEnrichmentDisplayMessage

describe("resolveEnrichmentDisplayMessage", () => {
  it("returns label for known phases", () => {
    expect(resolveEnrichmentDisplayMessage("evaluating", undefined)).toBe("Evaluating...");
    expect(resolveEnrichmentDisplayMessage("complete", undefined)).toBe("Complete");
    expect(resolveEnrichmentDisplayMessage("memory_skill_extracted", undefined)).toContain(
      "Skills extracted",
    );
  });

  it("falls back to explicit message when phase is unknown", () => {
    expect(resolveEnrichmentDisplayMessage("custom_phase", "Custom message")).toBe(
      "Custom message",
    );
  });

  it("falls back to raw phase when both label and message are missing", () => {
    expect(resolveEnrichmentDisplayMessage("custom_phase", undefined)).toBe("custom_phase");
  });

  it("prefers phase label over explicit message", () => {
    expect(resolveEnrichmentDisplayMessage("evaluating", "Some other message")).toBe(
      "Evaluating...",
    );
  });
});

// MARK: normalizeScopeValue

describe("normalizeScopeValue", () => {
  it("returns trimmed string for non-empty values", () => {
    expect(normalizeScopeValue("agent-1")).toBe("agent-1");
    expect(normalizeScopeValue("  spaced  ")).toBe("spaced");
  });

  it("returns undefined for empty or whitespace strings", () => {
    expect(normalizeScopeValue("")).toBeUndefined();
    expect(normalizeScopeValue("   ")).toBeUndefined();
  });

  it("returns undefined for non-string values", () => {
    expect(normalizeScopeValue(123)).toBeUndefined();
    expect(normalizeScopeValue(null)).toBeUndefined();
    expect(normalizeScopeValue(undefined)).toBeUndefined();
    expect(normalizeScopeValue({})).toBeUndefined();
  });
});

// MARK: normalizeScopeType

describe("normalizeScopeType", () => {
  it("returns 'agent' for agent input", () => {
    expect(normalizeScopeType("agent")).toBe("agent");
  });

  it("returns 'swarm' for swarm input", () => {
    expect(normalizeScopeType("swarm")).toBe("swarm");
  });

  it("returns undefined for anything else", () => {
    expect(normalizeScopeType("team")).toBeUndefined();
    expect(normalizeScopeType("")).toBeUndefined();
    expect(normalizeScopeType(null)).toBeUndefined();
    expect(normalizeScopeType(42)).toBeUndefined();
  });
});

// MARK: buildEnrichmentScopeKey

describe("buildEnrichmentScopeKey", () => {
  it("returns root scope key when no scope type", () => {
    expect(buildEnrichmentScopeKey(undefined, "id-1", "Name")).toBe(ROOT_ENRICHMENT_SCOPE_KEY);
  });

  it("builds key from scope type and id", () => {
    expect(buildEnrichmentScopeKey("agent", "agent-123", "My Agent")).toBe("agent:agent-123");
    expect(buildEnrichmentScopeKey("swarm", "swarm-456", "My Swarm")).toBe("swarm:swarm-456");
  });

  it("falls back to scope name when id is undefined", () => {
    expect(buildEnrichmentScopeKey("agent", undefined, "My Agent")).toBe("agent:My Agent");
  });

  it("falls back to 'unknown' when both id and name are undefined", () => {
    expect(buildEnrichmentScopeKey("agent", undefined, undefined)).toBe("agent:unknown");
  });
});

// MARK: resolveProcessingScopePriority

describe("resolveProcessingScopePriority", () => {
  it("unscoped (root) has highest priority", () => {
    expect(resolveProcessingScopePriority(undefined)).toBe(3);
  });

  it("swarm has medium priority", () => {
    expect(resolveProcessingScopePriority("swarm")).toBe(2);
  });

  it("agent has lowest priority", () => {
    expect(resolveProcessingScopePriority("agent")).toBe(1);
  });

  it("root > swarm > agent priority ordering", () => {
    const root = resolveProcessingScopePriority(undefined);
    const swarm = resolveProcessingScopePriority("swarm");
    const agent = resolveProcessingScopePriority("agent");
    expect(root).toBeGreaterThan(swarm);
    expect(swarm).toBeGreaterThan(agent);
  });
});

// MARK: EnrichmentTracker

describe("EnrichmentTracker", () => {
  it("initializes with empty maps", () => {
    const tracker = new EnrichmentTracker();
    expect(tracker.lastEnrichmentEventByScope.size).toBe(0);
    expect(tracker.phaseChipItemIdByScope.size).toBe(0);
    expect(tracker.highestKnownPhaseRankByScope.size).toBe(0);
  });

  describe("reset", () => {
    it("clears all tracking maps", () => {
      const tracker = new EnrichmentTracker();
      tracker.lastEnrichmentEventByScope.set("key", "val");
      tracker.phaseChipItemIdByScope.set("key", "id");
      tracker.highestKnownPhaseRankByScope.set("key", 5);

      tracker.reset();

      expect(tracker.lastEnrichmentEventByScope.size).toBe(0);
      expect(tracker.phaseChipItemIdByScope.size).toBe(0);
      expect(tracker.highestKnownPhaseRankByScope.size).toBe(0);
    });
  });

  describe("shouldSkipPhase", () => {
    it("does not skip when no previous rank exists", () => {
      const tracker = new EnrichmentTracker();
      expect(tracker.shouldSkipPhase("scope-1", "evaluating")).toBe(false);
    });

    it("does not skip when incoming rank is higher", () => {
      const tracker = new EnrichmentTracker();
      tracker.highestKnownPhaseRankByScope.set("scope-1", 2);
      expect(tracker.shouldSkipPhase("scope-1", "synthesizing")).toBe(false);
    });

    it("does not skip when incoming rank is equal", () => {
      const tracker = new EnrichmentTracker();
      tracker.highestKnownPhaseRankByScope.set("scope-1", 2);
      expect(tracker.shouldSkipPhase("scope-1", "searching_tools")).toBe(false);
    });

    it("skips when incoming rank is lower than current (stale regression)", () => {
      const tracker = new EnrichmentTracker();
      tracker.highestKnownPhaseRankByScope.set("scope-1", 7); // synthesizing
      // executing_actions (rank 6) is NOT a reset marker, so it should be skipped
      expect(tracker.shouldSkipPhase("scope-1", "executing_actions")).toBe(true);
    });

    it("does not skip phase reset markers even when rank is lower", () => {
      const tracker = new EnrichmentTracker();
      tracker.highestKnownPhaseRankByScope.set("scope-1", 7); // synthesizing
      // planning is a reset marker, so it should NOT be skipped
      expect(tracker.shouldSkipPhase("scope-1", "planning")).toBe(false);
      expect(tracker.shouldSkipPhase("scope-1", "evaluating")).toBe(false);
      expect(tracker.shouldSkipPhase("scope-1", "searching_tools")).toBe(false);
    });

    it("does not skip unknown phases", () => {
      const tracker = new EnrichmentTracker();
      tracker.highestKnownPhaseRankByScope.set("scope-1", 7);
      expect(tracker.shouldSkipPhase("scope-1", "custom_unknown")).toBe(false);
    });

    it("isolates scopes from each other", () => {
      const tracker = new EnrichmentTracker();
      tracker.highestKnownPhaseRankByScope.set("scope-A", 7);
      // scope-B has no rank, so nothing is skipped there
      expect(tracker.shouldSkipPhase("scope-B", "evaluating")).toBe(false);
    });
  });

  describe("isDuplicateEvent", () => {
    it("returns false for first event on a scope", () => {
      const tracker = new EnrichmentTracker();
      expect(tracker.isDuplicateEvent("scope-1", "evaluating", "Starting...")).toBe(false);
    });

    it("returns true for exact duplicate on same scope", () => {
      const tracker = new EnrichmentTracker();
      tracker.isDuplicateEvent("scope-1", "evaluating", "Starting...");
      expect(tracker.isDuplicateEvent("scope-1", "evaluating", "Starting...")).toBe(true);
    });

    it("returns false when phase changes", () => {
      const tracker = new EnrichmentTracker();
      tracker.isDuplicateEvent("scope-1", "evaluating", "Starting...");
      expect(tracker.isDuplicateEvent("scope-1", "planning", "Starting...")).toBe(false);
    });

    it("returns false when message changes", () => {
      const tracker = new EnrichmentTracker();
      tracker.isDuplicateEvent("scope-1", "evaluating", "Starting...");
      expect(tracker.isDuplicateEvent("scope-1", "evaluating", "Different message")).toBe(false);
    });

    it("isolates scopes from each other", () => {
      const tracker = new EnrichmentTracker();
      tracker.isDuplicateEvent("scope-A", "evaluating", "Starting...");
      // Same event on different scope is not a duplicate
      expect(tracker.isDuplicateEvent("scope-B", "evaluating", "Starting...")).toBe(false);
    });
  });

  describe("recordPhaseRank", () => {
    it("records rank for known phases", () => {
      const tracker = new EnrichmentTracker();
      tracker.recordPhaseRank("scope-1", "evaluating");
      expect(tracker.highestKnownPhaseRankByScope.get("scope-1")).toBe(0);

      tracker.recordPhaseRank("scope-1", "synthesizing");
      expect(tracker.highestKnownPhaseRankByScope.get("scope-1")).toBe(7);
    });

    it("does not record rank for unknown phases", () => {
      const tracker = new EnrichmentTracker();
      tracker.recordPhaseRank("scope-1", "memory_skill_extracting");
      expect(tracker.highestKnownPhaseRankByScope.has("scope-1")).toBe(false);
    });

    it("overwrites with lower rank (reset scenario)", () => {
      const tracker = new EnrichmentTracker();
      tracker.recordPhaseRank("scope-1", "synthesizing"); // 7
      tracker.recordPhaseRank("scope-1", "evaluating"); // 0
      expect(tracker.highestKnownPhaseRankByScope.get("scope-1")).toBe(0);
    });
  });

  describe("applyPhaseChip", () => {
    it("creates a new phase chip item when none exists for scope", () => {
      const tracker = new EnrichmentTracker();
      const chipData = {
        phase: "evaluating",
        message: "Evaluating...",
        timestamp: "2024-01-01T00:00:00Z",
      };

      const result = tracker.applyPhaseChip("scope-1", chipData, []);

      expect(result.created).toBe(true);
      expect(result.chatFlowItems).toHaveLength(1);
      expect(result.chatFlowItems[0].type).toBe("phase_chip");
      expect(result.chatFlowItems[0].data).toEqual(chipData);
      // Chip item ID should be tracked
      expect(tracker.phaseChipItemIdByScope.has("scope-1")).toBe(true);
    });

    it("updates existing phase chip item for same scope", () => {
      const tracker = new EnrichmentTracker();
      const chipData1 = {
        phase: "evaluating",
        message: "Evaluating...",
        timestamp: "2024-01-01T00:00:00Z",
      };
      const result1 = tracker.applyPhaseChip("scope-1", chipData1, []);

      const chipData2 = {
        phase: "planning",
        message: "Planning...",
        timestamp: "2024-01-01T00:01:00Z",
      };
      const result2 = tracker.applyPhaseChip("scope-1", chipData2, result1.chatFlowItems);

      expect(result2.created).toBe(false);
      expect(result2.chatFlowItems).toHaveLength(1);
      expect(result2.chatFlowItems[0].data).toEqual(chipData2);
    });

    it("creates separate chips for different scopes", () => {
      const tracker = new EnrichmentTracker();
      const chipA = {
        phase: "evaluating",
        message: "Evaluating...",
        timestamp: "2024-01-01T00:00:00Z",
      };
      const resultA = tracker.applyPhaseChip("scope-A", chipA, []);

      const chipB = {
        phase: "memory_skill_extracting",
        message: "Extracting skills...",
        timestamp: "2024-01-01T00:00:01Z",
      };
      const resultB = tracker.applyPhaseChip("scope-B", chipB, resultA.chatFlowItems);

      expect(resultB.created).toBe(true);
      expect(resultB.chatFlowItems).toHaveLength(2);
    });

    it("preserves other items when updating existing chip", () => {
      const tracker = new EnrichmentTracker();
      const existingItems = [
        {
          id: "msg-1",
          type: "message" as const,
          timestamp: "2024-01-01T00:00:00Z",
          data: {
            id: "msg-1",
            role: "assistant" as const,
            messageType: "ai" as const,
            content: "Hello",
            timestamp: "2024-01-01T00:00:00Z",
          },
        },
      ];

      const chipData1 = {
        phase: "evaluating",
        message: "Evaluating...",
        timestamp: "2024-01-01T00:00:01Z",
      };
      const result1 = tracker.applyPhaseChip("scope-1", chipData1, existingItems);
      expect(result1.chatFlowItems).toHaveLength(2);

      const chipData2 = {
        phase: "planning",
        message: "Planning...",
        timestamp: "2024-01-01T00:00:02Z",
      };
      const result2 = tracker.applyPhaseChip("scope-1", chipData2, result1.chatFlowItems);
      expect(result2.chatFlowItems).toHaveLength(2);
      expect(result2.chatFlowItems[0].type).toBe("message");
      expect(result2.chatFlowItems[1].data).toEqual(chipData2);
    });
  });
});
