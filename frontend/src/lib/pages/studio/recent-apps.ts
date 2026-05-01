import type { App } from "$lib/types";

export const RECENT_APPS_KEY = "maivn-studio-recent-apps";

export function loadRecentApps(): App[] {
  try {
    const stored = localStorage.getItem(RECENT_APPS_KEY);
    if (stored) {
      return JSON.parse(stored) as App[];
    }
  } catch {
    return [];
  }

  return [];
}

export function saveRecentApps(apps: App[]): void {
  try {
    localStorage.setItem(RECENT_APPS_KEY, JSON.stringify(apps));
  } catch {
    return;
  }
}

export function updateRecentApps(existing: App[], app: App): App[] {
  const filtered = existing.filter((item) => item.id !== app.id);
  filtered.unshift(app);
  if (filtered.length > 5) {
    filtered.length = 5;
  }
  saveRecentApps(filtered);
  return filtered;
}

export function getCollapsedAppLabel(name: string): string {
  const normalized = name.replace(/[_-]+/g, " ").trim();
  if (!normalized) return "?";
  const parts = normalized.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}
