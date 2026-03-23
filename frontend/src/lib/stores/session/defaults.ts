import type { ChatFlowFilters, InterruptStyle, InvocationConfig } from "$lib/types";

export function createDefaultFilters(): ChatFlowFilters {
  return {
    itemType: "all",
    toolStatus: "all",
    expandAllCards: false,
    showToolArgs: true,
    richResultDisplay: true,
    showStructuredOutput: false,
    showSessionDetails: false,
  };
}

export function createDefaultInvocationConfig(): InvocationConfig {
  return {
    force_final_tool: false,
    stream_response: true,
    status_messages: false,
  };
}

export function loadInterruptStyle(): InterruptStyle {
  if (typeof window === "undefined") return "inline";

  const stored = localStorage.getItem("interruptStyle");
  if (stored && ["inline", "modal", "drawer", "floating", "hybrid"].includes(stored)) {
    return stored as InterruptStyle;
  }

  return "inline";
}
