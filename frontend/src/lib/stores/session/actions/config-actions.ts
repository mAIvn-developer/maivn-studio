import type { InterruptStyle, InvocationConfig, MemoryConfig } from "$lib/types";

import { buildStoreMemoryConfig } from "../memory";

export function createSetInvocationConfig(
  setInvocationConfigDirect: (config: InvocationConfig) => void,
  getInvocationConfig: () => InvocationConfig,
  setMemoryConfigBase: (v: InvocationConfig["memory_config"] | undefined) => void,
  setMemoryConfig: (config: MemoryConfig) => void,
) {
  return function setInvocationConfig(config: InvocationConfig) {
    const hasMemoryConfig = "memory_config" in config;

    if (hasMemoryConfig) {
      setMemoryConfigBase(config.memory_config);
      setMemoryConfig(buildStoreMemoryConfig(config.memory_config));
    }

    const { memory_config: _memoryConfig, ...nextConfig } = config;
    if (hasMemoryConfig && !("stream_response" in nextConfig)) {
      setInvocationConfigDirect({
        ...nextConfig,
        stream_response: getInvocationConfig().stream_response,
      });
      return;
    }

    setInvocationConfigDirect(nextConfig);
  };
}

export function createSetInterruptStyle(setInterruptStyleDirect: (style: InterruptStyle) => void) {
  return function setInterruptStyle(style: InterruptStyle) {
    setInterruptStyleDirect(style);
    if (typeof window !== "undefined") {
      localStorage.setItem("interruptStyle", style);
    }
  };
}
