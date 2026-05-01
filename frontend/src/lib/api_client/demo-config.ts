import type {
  AgentInfo,
  Demo,
  DemoVariant,
  InvocationMemoryConfig,
  InvocationOrchestrationConfig,
  InvocationSystemToolsConfig,
  SwarmInfo,
} from "../types";

import { API_BASE } from "./shared";

export async function updateDemo(
  demoId: string,
  updates: {
    name?: string;
    description?: string;
    category?: string;
    tags?: string[];
    variants?: Record<string, DemoVariant>;
    private_data?: Record<string, string | number | boolean>;
  },
): Promise<Demo> {
  const res = await fetch(`${API_BASE}/demos/${demoId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update demo ${demoId}`);
  const data = await res.json();
  return data.demo;
}

export async function updateAgent(
  demoId: string,
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
  const res = await fetch(`${API_BASE}/demos/${demoId}/agents/${encodeURIComponent(agentName)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update agent ${agentName}`);
  return res.json();
}

export async function updateSwarm(
  demoId: string,
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
  const res = await fetch(`${API_BASE}/demos/${demoId}/swarms/${encodeURIComponent(swarmName)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update swarm ${swarmName}`);
  return res.json();
}
