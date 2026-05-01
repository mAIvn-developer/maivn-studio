import type {
  AgentInfo,
  App,
  AppVariant,
  InvocationMemoryConfig,
  InvocationOrchestrationConfig,
  InvocationSystemToolsConfig,
  SwarmInfo,
} from "../types";

import { API_BASE } from "./shared";

export async function updateApp(
  appId: string,
  updates: {
    name?: string;
    description?: string;
    category?: string;
    tags?: string[];
    variants?: Record<string, AppVariant>;
    private_data?: Record<string, string | number | boolean>;
  },
): Promise<App> {
  const res = await fetch(`${API_BASE}/apps/${appId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update app ${appId}`);
  const data = await res.json();
  return data.app;
}

export async function updateAgent(
  appId: string,
  agentName: string,
  updates: {
    description?: string;
    system_prompt?: string;
    tags?: string[];
    memory_config?: InvocationMemoryConfig;
    system_tools_config?: InvocationSystemToolsConfig;
    orchestration_config?: InvocationOrchestrationConfig;
    timeout?: number;
    max_results?: number;
    included_nested_synthesis?: boolean | "auto";
    allow_private_in_system_tools?: boolean;
    private_data?: Record<string, unknown>;
  },
): Promise<AgentInfo> {
  const res = await fetch(`${API_BASE}/apps/${appId}/agents/${encodeURIComponent(agentName)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update agent ${agentName}`);
  return res.json();
}

export async function updateSwarm(
  appId: string,
  swarmName: string,
  updates: {
    description?: string;
    system_prompt?: string;
    tags?: string[];
    memory_config?: InvocationMemoryConfig;
    system_tools_config?: InvocationSystemToolsConfig;
    orchestration_config?: InvocationOrchestrationConfig;
    allow_private_in_system_tools?: boolean;
    private_data?: Record<string, unknown>;
  },
): Promise<SwarmInfo> {
  const res = await fetch(`${API_BASE}/apps/${appId}/swarms/${encodeURIComponent(swarmName)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update swarm ${swarmName}`);
  return res.json();
}
