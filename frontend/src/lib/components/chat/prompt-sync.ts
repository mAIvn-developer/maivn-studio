import type { PromptInfo } from "$lib/types";

function normalizePromptContent(value: string | null | undefined): string {
  return value?.trim() ?? "";
}

export function getDefaultPromptContent(prompts: PromptInfo[]): string | null {
  const defaultPrompt = prompts.find((prompt) => prompt.is_default) ?? prompts[0];
  if (!defaultPrompt) {
    return null;
  }

  const content = normalizePromptContent(defaultPrompt.content);
  return content || null;
}

export function shouldReplaceComposerDraft(inputValue: string, prompts: PromptInfo[]): boolean {
  const currentDraft = normalizePromptContent(inputValue);
  if (!currentDraft) {
    return true;
  }

  return prompts.some((prompt) => normalizePromptContent(prompt.content) === currentDraft);
}
