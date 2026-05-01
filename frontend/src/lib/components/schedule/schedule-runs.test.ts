import { describe, expect, it } from "vitest";

import type { ChatFlowItem, Message } from "$lib/types";
import type { ScheduleRunSummary } from "$lib/api_client/schedules";

import { buildScheduleRuns, deriveRunStatus } from "./schedule-runs";

function makeRecord(overrides: Partial<ScheduleRunSummary>): ScheduleRunSummary {
  return {
    fire_id: overrides.fire_id ?? "fire-1",
    scheduled_at: overrides.scheduled_at ?? "2026-04-30T14:00:00.000Z",
    fired_at: overrides.fired_at ?? null,
    finished_at: overrides.finished_at ?? null,
    status: overrides.status ?? "success",
    attempt: overrides.attempt ?? 1,
    jitter_offset_seconds: overrides.jitter_offset_seconds ?? 0,
    error: overrides.error ?? null,
    event_session_id: overrides.event_session_id ?? null,
  };
}

function makeMessage(content: string, fireId?: string): ChatFlowItem {
  const message: Message = {
    id: `msg-${content}`,
    role: "user",
    messageType: "human",
    content,
    timestamp: "2026-04-30T14:00:30.000Z",
  };
  return {
    id: `flow-${content}`,
    type: "message",
    timestamp: message.timestamp,
    data: message,
    origin: fireId ? "schedule" : undefined,
    scheduleFireId: fireId,
  };
}

describe("buildScheduleRuns", () => {
  it("orders runs oldest-first by scheduled_at", () => {
    const history = [
      makeRecord({ fire_id: "newer", scheduled_at: "2026-04-30T14:01:00.000Z" }),
      makeRecord({ fire_id: "older", scheduled_at: "2026-04-30T14:00:00.000Z" }),
    ];

    const runs = buildScheduleRuns(history, []);

    expect(runs.map((r) => r.fireId)).toEqual(["older", "newer"]);
  });

  it("attaches chat-flow items to the run with matching fire id", () => {
    const history = [makeRecord({ fire_id: "fire-1" })];
    const items = [makeMessage("hello", "fire-1"), makeMessage("untagged")];

    const runs = buildScheduleRuns(history, items);

    expect(runs).toHaveLength(1);
    expect(runs[0].fireId).toBe("fire-1");
    expect(runs[0].exchanges).toHaveLength(1);
    expect(runs[0].exchanges[0].humanMessage.content).toBe("hello");
  });

  it("creates a synthetic run when items arrive before the history record", () => {
    const items = [makeMessage("racing", "fire-late")];

    const runs = buildScheduleRuns([], items);

    expect(runs).toHaveLength(1);
    expect(runs[0].summary).toBeNull();
    expect(runs[0].exchanges[0].humanMessage.content).toBe("racing");
  });
});

describe("deriveRunStatus", () => {
  it("returns 'running' when fired_at is set but finished_at is missing", () => {
    const run = {
      fireId: "f",
      sortedAt: "2026-04-30T14:00:00Z",
      exchanges: [],
      summary: makeRecord({
        fire_id: "f",
        fired_at: "2026-04-30T14:00:01.000Z",
        finished_at: null,
        status: "running",
      }),
    };
    expect(deriveRunStatus(run)).toBe("running");
  });

  it("normalizes terminal status strings to ok / failed / skipped", () => {
    const cases: Array<[string, "ok" | "failed" | "skipped"]> = [
      ["succeeded", "ok"],
      ["success", "ok"],
      ["ok", "ok"],
      ["failed", "failed"],
      ["error", "failed"],
      ["skipped", "skipped"],
      ["skipped_overlap", "skipped"],
      ["skipped_jitter", "skipped"],
      ["skipped_misfire", "skipped"],
    ];

    for (const [status, expected] of cases) {
      const run = {
        fireId: "f",
        sortedAt: "x",
        exchanges: [],
        summary: makeRecord({ status }),
      };
      expect(deriveRunStatus(run), `status=${status}`).toBe(expected);
    }
  });
});
