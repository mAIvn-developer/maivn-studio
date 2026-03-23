import type { InvocationConfig, MemoryConfig } from "$lib/types";

// MARK: Memory Config

export function createDefaultMemoryConfig(): MemoryConfig {
  return {
    enabled: false,
    level: "clarity",
    summarizationEnabled: true,
    skillExtractionEnabled: true,
    insightExtractionEnabled: true,
    retrievalEnabled: true,
    persistenceMode: "vector_plus_graph",
  };
}

export function normalizeMemoryLevel(value: unknown): MemoryConfig["level"] {
  if (value === "none" || value === "glimpse" || value === "focus" || value === "clarity") {
    return value;
  }
  return "clarity";
}

export function resolveRetrievalEnabled(
  config?: InvocationConfig["memory_config"],
): MemoryConfig["retrievalEnabled"] {
  const retrieval = config?.retrieval;
  if (!retrieval) {
    return true;
  }

  const flags = [
    retrieval.skills_enabled,
    retrieval.insights_enabled,
    retrieval.resources_enabled,
  ].filter((value): value is boolean => typeof value === "boolean");

  if (flags.length === 0) {
    return true;
  }

  return flags.some(Boolean);
}

export function buildStoreMemoryConfig(config?: InvocationConfig["memory_config"]): MemoryConfig {
  const defaults = createDefaultMemoryConfig();
  if (!config) {
    return defaults;
  }

  return {
    enabled: config.enabled ?? defaults.enabled,
    level: normalizeMemoryLevel(config.level),
    summarizationEnabled: config.summarization_enabled ?? defaults.summarizationEnabled,
    skillExtractionEnabled: config.skill_extraction?.enabled ?? defaults.skillExtractionEnabled,
    insightExtractionEnabled:
      config.insight_extraction?.enabled ?? defaults.insightExtractionEnabled,
    retrievalEnabled: resolveRetrievalEnabled(config),
    persistenceMode:
      typeof config.persistence_mode === "string" && config.persistence_mode.trim()
        ? config.persistence_mode
        : defaults.persistenceMode,
  };
}

export function buildInvocationMemoryConfig(
  config: MemoryConfig,
  baseConfig?: InvocationConfig["memory_config"],
): InvocationConfig["memory_config"] {
  const baseRetrieval = baseConfig?.retrieval;
  const baseResourcesEnabled = baseRetrieval?.resources_enabled;
  const hasExplicitRetrievalSignals =
    typeof baseRetrieval?.skills_enabled === "boolean" ||
    typeof baseRetrieval?.insights_enabled === "boolean" ||
    typeof baseResourcesEnabled === "boolean";

  if (!config.enabled) {
    return {
      ...(baseConfig ?? {}),
      enabled: false,
    };
  }

  return {
    ...(baseConfig ?? {}),
    enabled: true,
    level: config.level,
    summarization_enabled: config.summarizationEnabled,
    persistence_mode: config.persistenceMode,
    retrieval: config.retrievalEnabled
      ? hasExplicitRetrievalSignals
        ? {
            ...baseRetrieval,
            resources_enabled: baseResourcesEnabled,
          }
        : {
            ...baseRetrieval,
            skills_enabled: true,
            insights_enabled: true,
            resources_enabled: true,
          }
      : {
          ...baseRetrieval,
          skills_enabled: false,
          insights_enabled: false,
          resources_enabled: false,
        },
    skill_extraction: {
      ...(baseConfig?.skill_extraction ?? {}),
      enabled: config.skillExtractionEnabled,
    },
    insight_extraction: {
      ...(baseConfig?.insight_extraction ?? {}),
      enabled: config.insightExtractionEnabled,
    },
  };
}
