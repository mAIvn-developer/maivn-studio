import type { RepoScanItem, RepoScanSelection } from "../types";

import { API_BASE } from "./shared";

export async function scanRepo(): Promise<RepoScanItem[]> {
  const res = await fetch(`${API_BASE}/discovery/scan`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to scan repo");
  const data = await res.json();
  return data.items as RepoScanItem[];
}

export async function applyRepoSelection(selections: RepoScanSelection[]): Promise<number> {
  const res = await fetch(`${API_BASE}/discovery/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selections }),
  });
  if (!res.ok) throw new Error("Failed to apply selections");
  const data = await res.json();
  return data.added as number;
}
