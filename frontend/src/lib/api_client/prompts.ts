import type { MessageType, SavedPrompt } from "../types";

import { API_BASE } from "./shared";

export async function fetchSavedPrompts(demoId?: string): Promise<SavedPrompt[]> {
  const url = demoId ? `${API_BASE}/prompts?demo_id=${demoId}` : `${API_BASE}/prompts`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch saved prompts");
  return res.json();
}

export async function savePrompt(prompt: {
  name: string;
  content: string;
  description?: string;
  demoId: string;
  messageType?: MessageType;
}): Promise<SavedPrompt> {
  const res = await fetch(`${API_BASE}/prompts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: prompt.name,
      content: prompt.content,
      description: prompt.description ?? "",
      demo_id: prompt.demoId,
      message_type: prompt.messageType ?? "human",
    }),
  });
  if (!res.ok) throw new Error("Failed to save prompt");
  return res.json();
}

export async function deletePrompt(promptId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/prompts/${promptId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete prompt");
}
