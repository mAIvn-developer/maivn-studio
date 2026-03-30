import type { Demo, DemoDetails } from "../types";

import { API_BASE } from "./shared";

export async function fetchDemos(): Promise<Demo[]> {
  const res = await fetch(`${API_BASE}/demos`);
  if (!res.ok) throw new Error("Failed to fetch demos");
  const data = await res.json();
  return data.demos;
}

export async function fetchDemosByCategory(): Promise<Record<string, Demo[]>> {
  const res = await fetch(`${API_BASE}/demos`);
  if (!res.ok) throw new Error("Failed to fetch demos");
  const data = await res.json();
  const byCategory: Record<string, Demo[]> = {};

  for (const demo of data.demos as Demo[]) {
    if (!byCategory[demo.category]) {
      byCategory[demo.category] = [];
    }
    byCategory[demo.category].push(demo);
  }

  return byCategory;
}

export async function fetchDemo(id: string): Promise<DemoDetails> {
  const res = await fetch(`${API_BASE}/demos/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch demo ${id}`);
  const data = await res.json();

  return {
    ...data.demo,
    variants: data.variants,
    agents: [],
    swarms: [],
    tools: [],
    prompts: [],
    privateDataSchema: [],
  } as DemoDetails;
}

export async function fetchDemoFullDetails(id: string, variant?: string): Promise<DemoDetails> {
  const params = new URLSearchParams();
  if (variant) {
    params.set("variant", variant);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/demos/${id}/details${suffix}`);
  if (!res.ok) throw new Error(`Failed to fetch demo details ${id}`);
  return res.json();
}
