import { describe, expect, it } from "vitest";

import type { PromptInfo } from "$lib/types";

import { getDefaultPromptContent, shouldReplaceComposerDraft } from "./prompt-sync";

function makePrompt(content: string, overrides: Partial<PromptInfo> = {}): PromptInfo {
  return {
    id: overrides.id ?? "prompt-1",
    name: overrides.name ?? "Prompt",
    content,
    description: overrides.description ?? "",
    is_default: overrides.is_default ?? false,
    source: overrides.source ?? "module",
    structured_output: overrides.structured_output,
    message_type: overrides.message_type,
    variant: overrides.variant,
  };
}

describe("getDefaultPromptContent", () => {
  it("returns the explicitly default prompt content", () => {
    const prompts = [
      makePrompt("First"),
      makePrompt("Second", { id: "prompt-2", is_default: true }),
    ];

    expect(getDefaultPromptContent(prompts)).toBe("Second");
  });

  it("falls back to the first prompt when no default is marked", () => {
    const prompts = [makePrompt("First"), makePrompt("Second", { id: "prompt-2" })];

    expect(getDefaultPromptContent(prompts)).toBe("First");
  });

  it("returns null when no prompts exist", () => {
    expect(getDefaultPromptContent([])).toBeNull();
  });
});

describe("shouldReplaceComposerDraft", () => {
  const prompts = [
    makePrompt("Default prompt", { is_default: true }),
    makePrompt("Secondary prompt", { id: "prompt-2" }),
  ];

  it("returns true for an empty draft", () => {
    expect(shouldReplaceComposerDraft("", prompts)).toBe(true);
  });

  it("returns true when the draft matches a known prompt", () => {
    expect(shouldReplaceComposerDraft("  Secondary prompt  ", prompts)).toBe(true);
  });

  it("returns false for a custom draft", () => {
    expect(shouldReplaceComposerDraft("Investigate a custom scenario", prompts)).toBe(false);
  });
});
