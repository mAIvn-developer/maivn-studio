import type { ChatFlowItem } from "$lib/types";
import type { ScheduleRunSummary } from "$lib/api_client/schedules";

import { buildExchanges, type Exchange } from "../chat/chat-exchanges";

// MARK: - Types

/**
 * Aggregated view of one scheduled fire — combines the scheduler's run record
 * (status, attempt, jitter, timing) with whatever chat-flow items the backend
 * has tagged with the same `scheduleFireId`. Chat content is optional: until
 * the server pipes per-fire events through to the SSE stream, the card
 * renders with metadata only.
 */
export interface ScheduleRun {
  fireId: string;
  /** Run record from the scheduler — present once the backend has acknowledged the fire. */
  summary: ScheduleRunSummary | null;
  /** Chat exchanges captured for this fire, if any. */
  exchanges: Exchange[];
  /** Earliest timestamp seen for this fire — used to sort runs chronologically. */
  sortedAt: string;
}

// MARK: - Builder

/**
 * Group history records and chat-flow items into per-fire runs, sorted oldest
 * first. Chat-flow items carry an optional `scheduleFireId`; items without one
 * are ignored here (they belong to the interactive chat).
 */
export function buildScheduleRuns(
  history: ScheduleRunSummary[],
  chatFlowItems: ChatFlowItem[],
): ScheduleRun[] {
  const runsByFireId = new Map<string, ScheduleRun>();

  for (const record of history) {
    runsByFireId.set(record.fire_id, {
      fireId: record.fire_id,
      summary: record,
      exchanges: [],
      sortedAt: record.scheduled_at,
    });
  }

  // Bucket items by fire ID so each run renders its own exchange list.
  const itemsByFireId = new Map<string, ChatFlowItem[]>();
  for (const item of chatFlowItems) {
    if (!item.scheduleFireId) continue;
    const bucket = itemsByFireId.get(item.scheduleFireId) ?? [];
    bucket.push(item);
    itemsByFireId.set(item.scheduleFireId, bucket);
  }

  for (const [fireId, items] of itemsByFireId) {
    const existing = runsByFireId.get(fireId);
    const exchanges = buildExchanges(items);
    if (existing) {
      existing.exchanges = exchanges;
      continue;
    }
    // Item arrived for a fire we haven't yet seen in history (e.g., events
    // racing ahead of the scheduler's record). Render it with whatever
    // timestamp the items carry.
    runsByFireId.set(fireId, {
      fireId,
      summary: null,
      exchanges,
      sortedAt: items[0]?.timestamp ?? new Date().toISOString(),
    });
  }

  return Array.from(runsByFireId.values()).sort(compareBySortedAt);
}

function compareBySortedAt(a: ScheduleRun, b: ScheduleRun): number {
  const aTime = Date.parse(a.sortedAt);
  const bTime = Date.parse(b.sortedAt);
  if (Number.isNaN(aTime) && Number.isNaN(bTime)) return 0;
  if (Number.isNaN(aTime)) return 1;
  if (Number.isNaN(bTime)) return -1;
  return aTime - bTime;
}

// MARK: - Run state derivation

export type ScheduleRunStatus = "running" | "ok" | "failed" | "skipped" | "pending";

export function deriveRunStatus(run: ScheduleRun): ScheduleRunStatus {
  const summary = run.summary;
  if (!summary) return "pending";
  const status = summary.status?.toLowerCase() ?? "";
  if (status === "succeeded" || status === "success" || status === "ok") return "ok";
  if (status === "failed" || status === "error") return "failed";
  if (status.startsWith("skipped") || status === "skip") return "skipped";
  if (summary.fired_at && !summary.finished_at) return "running";
  return "pending";
}
