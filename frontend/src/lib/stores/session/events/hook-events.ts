import type { HookFiring, ToolCard } from "$lib/types";

import type { SessionStoreContext } from "../types";
import { asRecord } from "./event-utils";

function normalizeScalar(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

// MARK: Hook Firing Handler

/**
 * Route a normalized ``hook_fired`` event onto the matching card.
 *
 * - ``target_type === "tool"``: append to the ``ToolCard.hookFirings`` of
 *   the card whose ``toolId`` matches ``target_id`` (the per-invocation
 *   event id supplied by the SDK).
 * - ``target_type === "agent" | "swarm"``: append to the context-level
 *   ``scopeHookFirings`` map keyed by ``${target_type}:${target_id_or_name}``
 *   so the matching ``ScopeGroupCard`` can render the firing as a
 *   persistent header / footer marker.
 *
 * Invalid or incomplete events are silently dropped to keep the UI
 * resilient to schema drift.
 */
export function handleHookFired(ctx: SessionStoreContext, eventData: Record<string, unknown>) {
  const firing = readHookFiring(eventData);
  if (!firing) return;

  if (firing.targetType === "tool") {
    appendToToolCard(ctx, firing);
    return;
  }

  appendToScope(ctx, firing);
}

// MARK: Parsing

function readHookFiring(eventData: Record<string, unknown>): HookFiring | null {
  const descriptor = asRecord(eventData.hook);

  const name = normalizeScalar(descriptor?.name ?? eventData.name);
  const stageRaw = normalizeScalar(descriptor?.stage ?? eventData.stage);
  const statusRaw = normalizeScalar(descriptor?.status ?? eventData.status);
  const targetTypeRaw = normalizeScalar(descriptor?.target_type ?? eventData.target_type);

  if (!name || !stageRaw || !statusRaw || !targetTypeRaw) return null;

  const stage = stageRaw === "before" ? "before" : stageRaw === "after" ? "after" : null;
  if (!stage) return null;

  const status = statusRaw === "failed" ? "failed" : "completed";

  const targetType =
    targetTypeRaw === "tool"
      ? "tool"
      : targetTypeRaw === "agent"
        ? "agent"
        : targetTypeRaw === "swarm"
          ? "swarm"
          : null;
  if (!targetType) return null;

  const targetId = normalizeScalar(descriptor?.target_id ?? eventData.target_id) ?? undefined;
  const targetName = normalizeScalar(descriptor?.target_name ?? eventData.target_name) ?? undefined;
  const error = normalizeScalar(descriptor?.error ?? eventData.error) ?? undefined;
  const elapsedRaw = descriptor?.elapsed_ms ?? eventData.elapsed_ms;
  const elapsedMs =
    typeof elapsedRaw === "number" && Number.isFinite(elapsedRaw) ? elapsedRaw : undefined;

  return {
    name,
    stage,
    status,
    targetType,
    targetId,
    targetName,
    error,
    elapsedMs,
    timestamp: new Date().toISOString(),
  };
}

// MARK: Tool Card Append

function appendToToolCard(ctx: SessionStoreContext, firing: HookFiring) {
  const key = firing.targetId;
  if (!key) return;

  const toolCards = ctx.getToolCards();
  const card = toolCards.get(key);
  if (!card) return;

  const next: ToolCard = {
    ...card,
    hookFirings: [...(card.hookFirings ?? []), firing],
  };
  const nextCards = new Map(toolCards);
  nextCards.set(key, next);
  ctx.setToolCards(nextCards);
}

// MARK: Scope Append

function appendToScope(ctx: SessionStoreContext, firing: HookFiring) {
  const key = scopeKey(firing);
  if (!key) return;

  const firings = ctx.getScopeHookFirings();
  const existing = firings.get(key) ?? [];
  const next = new Map(firings);
  next.set(key, [...existing, firing]);
  ctx.setScopeHookFirings(next);
}

function scopeKey(firing: HookFiring): string | null {
  const identifier = firing.targetId ?? firing.targetName;
  if (!identifier) return null;
  return `${firing.targetType}:${identifier}`;
}
