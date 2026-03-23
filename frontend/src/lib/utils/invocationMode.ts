import type { InvocationConfig, InvocationMode } from "$lib/types";

export function getInvocationMode(
  config: InvocationConfig | undefined,
  structuredOutputEnabled = false,
): InvocationMode {
  if (structuredOutputEnabled) {
    return "invoke";
  }
  return config?.stream_response === false ? "invoke" : "stream";
}

export function applyInvocationMode(
  config: InvocationConfig,
  mode: InvocationMode,
): InvocationConfig {
  if (mode === "invoke") {
    return {
      ...config,
      stream_response: false,
      status_messages: false,
    };
  }

  return {
    ...config,
    stream_response: true,
  };
}
