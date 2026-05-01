import type { App, AppDetails } from "../types";

import { API_BASE } from "./shared";

export async function fetchApps(): Promise<App[]> {
  const res = await fetch(`${API_BASE}/apps`);
  if (!res.ok) throw new Error("Failed to fetch apps");
  const data = await res.json();
  return data.apps;
}

export async function fetchAppsByCategory(): Promise<Record<string, App[]>> {
  const res = await fetch(`${API_BASE}/apps`);
  if (!res.ok) throw new Error("Failed to fetch apps");
  const data = await res.json();
  const byCategory: Record<string, App[]> = {};

  for (const app of data.apps as App[]) {
    if (!byCategory[app.category]) {
      byCategory[app.category] = [];
    }
    byCategory[app.category].push(app);
  }

  return byCategory;
}

export async function fetchApp(id: string): Promise<AppDetails> {
  const res = await fetch(`${API_BASE}/apps/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch app ${id}`);
  const data = await res.json();

  return {
    ...data.app,
    variants: data.variants,
    agents: [],
    swarms: [],
    tools: [],
    prompts: [],
    privateDataSchema: [],
  } as AppDetails;
}

export async function fetchAppFullDetails(id: string, variant?: string): Promise<AppDetails> {
  const params = new URLSearchParams();
  if (variant) {
    params.set("variant", variant);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/apps/${id}/details${suffix}`);
  if (!res.ok) throw new Error(`Failed to fetch app details ${id}`);
  return res.json();
}
