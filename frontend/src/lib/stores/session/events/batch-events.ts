import type { BatchResult, BatchResultItem, BatchResultStatus } from "$lib/types";

import type { SessionStoreContext } from "../types";

// MARK: Helpers

function readString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function readNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function readBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function readMode(value: unknown): "batch" | "abatch" {
  return value === "batch" ? "batch" : "abatch";
}

function readStatus(value: unknown, fallback: BatchResultStatus): BatchResultStatus {
  return value === "completed" || value === "failed" || value === "running" ? value : fallback;
}

function readItems(value: unknown): BatchResultItem[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item, fallbackIndex): BatchResultItem | null => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const record = item as Record<string, unknown>;
      const index = readNumber(record.index) ?? fallbackIndex;
      const status =
        record.status === "completed" || record.status === "failed" ? record.status : "pending";
      const normalized: BatchResultItem = {
        index,
        label: readString(record.label),
        input: readString(record.input) ?? "",
        status,
        variant: readString(record.variant),
        model: readString(record.model),
        reasoning: readString(record.reasoning),
      };
      if (Array.isArray(record.responses)) {
        normalized.responses = record.responses.filter(
          (response): response is string => typeof response === "string",
        );
      }
      normalized.response = readString(record.response);
      normalized.result = record.result;
      normalized.error = readString(record.error);
      normalized.duration_ms = readNumber(record.duration_ms);
      normalized.token_usage = record.token_usage as BatchResultItem["token_usage"];
      return normalized;
    })
    .filter((item): item is BatchResultItem => item !== null);
}

function updateBatchResult(
  ctx: SessionStoreContext,
  batchId: string,
  updater: (current: BatchResult | null) => BatchResult,
) {
  let found = false;
  const nextItems = ctx.getChatFlowItems().map((item) => {
    if (item.type !== "batch_result") {
      return item;
    }
    const current = item.data as BatchResult;
    if (current.batchId !== batchId) {
      return item;
    }
    found = true;
    return {
      ...item,
      data: updater(current),
    };
  });

  if (found) {
    ctx.setChatFlowItems(nextItems);
    return;
  }

  ctx.setChatFlowItems([
    ...nextItems,
    {
      id: crypto.randomUUID(),
      type: "batch_result",
      timestamp: new Date().toISOString(),
      data: updater(null),
    },
  ]);
}

function buildPendingItems(inputs: unknown): BatchResultItem[] {
  if (!Array.isArray(inputs)) {
    return [];
  }
  return inputs
    .map((input, index) => ({
      index,
      input: readString(input) ?? "",
      status: "pending" as const,
    }))
    .filter((item) => item.input);
}

function buildPendingItemsFromRows(rows: unknown): BatchResultItem[] {
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows
    .map((row, fallbackIndex): BatchResultItem | null => {
      if (!row || typeof row !== "object") {
        return null;
      }
      const record = row as Record<string, unknown>;
      const input = readString(record.input) ?? readString(record.message) ?? "";
      if (!input) {
        return null;
      }
      return {
        index: readNumber(record.index) ?? fallbackIndex,
        label: readString(record.label),
        input,
        status: "pending" as const,
        variant: readString(record.variant),
        model: readString(record.model),
        reasoning: readString(record.reasoning),
      };
    })
    .filter((item): item is BatchResultItem => item !== null);
}

// MARK: Event Handlers

export function handleBatchStart(ctx: SessionStoreContext, eventData: Record<string, unknown>) {
  const batchId = readString(eventData.batch_id);
  if (!batchId) {
    return;
  }

  const itemCount = readNumber(eventData.item_count) ?? 0;
  const pendingItems = buildPendingItemsFromRows(eventData.items);
  const fallbackPendingItems = buildPendingItems(eventData.inputs);

  updateBatchResult(ctx, batchId, () => ({
    batchId,
    mode: readMode(eventData.mode),
    status: "running",
    itemCount,
    maxConcurrency: readNumber(eventData.max_concurrency),
    asyncMode: readBoolean(eventData.async_mode, true),
    startedAt: new Date().toISOString(),
    items:
      pendingItems.length > 0
        ? pendingItems
        : fallbackPendingItems.length > 0
          ? fallbackPendingItems
          : Array.from({ length: itemCount }, (_, index) => ({
              index,
              input: "",
              status: "pending" as const,
            })),
  }));
}

export function handleBatchItemComplete(
  ctx: SessionStoreContext,
  eventData: Record<string, unknown>,
) {
  const batchId = readString(eventData.batch_id);
  const index = readNumber(eventData.index);
  if (!batchId || index === undefined) {
    return;
  }

  updateBatchResult(ctx, batchId, (current) => {
    const base =
      current ??
      ({
        batchId,
        mode: readMode(eventData.mode),
        status: "running",
        itemCount: index + 1,
        asyncMode: readBoolean(eventData.async_mode, true),
        startedAt: new Date().toISOString(),
        items: [],
      } satisfies BatchResult);

    const nextItem = readItems([eventData])[0] ?? {
      index,
      input: readString(eventData.input) ?? "",
      status: eventData.status === "failed" ? ("failed" as const) : ("completed" as const),
      error: readString(eventData.error),
    };
    const nextItems = [...base.items];
    nextItems[index] = nextItem;

    return {
      ...base,
      itemCount: Math.max(base.itemCount, nextItems.length),
      items: nextItems,
    };
  });
}

export function handleBatchComplete(ctx: SessionStoreContext, eventData: Record<string, unknown>) {
  const batchId = readString(eventData.batch_id);
  if (!batchId) {
    return;
  }

  const completedItems = readItems(eventData.items);

  updateBatchResult(ctx, batchId, (current) => {
    const itemCount =
      readNumber(eventData.item_count) ?? current?.itemCount ?? completedItems.length;
    return {
      batchId,
      mode: readMode(eventData.mode ?? current?.mode),
      status: readStatus(eventData.status, "completed"),
      itemCount,
      maxConcurrency: readNumber(eventData.max_concurrency) ?? current?.maxConcurrency,
      asyncMode: readBoolean(eventData.async_mode, current?.asyncMode ?? true),
      startedAt: current?.startedAt ?? new Date().toISOString(),
      completedAt: new Date().toISOString(),
      duration_ms: readNumber(eventData.duration_ms),
      token_usage: eventData.token_usage as BatchResult["token_usage"],
      error: readString(eventData.error),
      items:
        completedItems.length > 0
          ? completedItems
          : (current?.items.map((item) => ({
              ...item,
              status: eventData.status === "failed" ? "failed" : item.status,
              error: eventData.status === "failed" ? readString(eventData.error) : item.error,
            })) ?? []),
    };
  });
}
