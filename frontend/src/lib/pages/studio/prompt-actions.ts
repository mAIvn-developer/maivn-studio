import { fetchSavedPrompts, savePrompt } from "$lib/api_client/prompts";
import type { SavedPrompt } from "$lib/types";

interface CreatePromptActionsParams {
  getSelectedDemo: () => { id: string } | null;
  getMessageType: () => import("$lib/types").SendableMessageType;
  getSavedPrompts: () => SavedPrompt[];
  setSavedPrompts: (prompts: SavedPrompt[]) => void;
}

export function createPromptActions(params: CreatePromptActionsParams) {
  async function loadSavedPrompts(demoId: string) {
    try {
      params.setSavedPrompts(await fetchSavedPrompts(demoId));
    } catch (e) {
      console.error("Failed to load saved prompts:", e);
      params.setSavedPrompts([]);
    }
  }

  async function handleSavePrompt(content: string) {
    const selectedDemo = params.getSelectedDemo();
    if (!selectedDemo) return;

    const name = content.length > 30 ? `${content.substring(0, 30)}...` : content;
    try {
      const saved = await savePrompt({
        name,
        content,
        demoId: selectedDemo.id,
        messageType: params.getMessageType(),
      });
      params.setSavedPrompts([...params.getSavedPrompts(), saved]);
    } catch (e) {
      console.error("Failed to save prompt:", e);
    }
  }

  return {
    loadSavedPrompts,
    handleSavePrompt,
  };
}
