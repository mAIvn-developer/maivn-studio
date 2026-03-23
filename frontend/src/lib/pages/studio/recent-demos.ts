import type { Demo } from "$lib/types";

export const RECENT_DEMOS_KEY = "maivn-studio-recent-demos";

export function loadRecentDemos(): Demo[] {
  try {
    const stored = localStorage.getItem(RECENT_DEMOS_KEY);
    if (stored) {
      return JSON.parse(stored) as Demo[];
    }
  } catch {
    return [];
  }

  return [];
}

export function saveRecentDemos(demos: Demo[]): void {
  try {
    localStorage.setItem(RECENT_DEMOS_KEY, JSON.stringify(demos));
  } catch {
    return;
  }
}

export function updateRecentDemos(existing: Demo[], demo: Demo): Demo[] {
  const filtered = existing.filter((item) => item.id !== demo.id);
  filtered.unshift(demo);
  if (filtered.length > 5) {
    filtered.length = 5;
  }
  saveRecentDemos(filtered);
  return filtered;
}

export function getCollapsedDemoLabel(name: string): string {
  const normalized = name.replace(/[_-]+/g, " ").trim();
  if (!normalized) return "?";
  const parts = normalized.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}
