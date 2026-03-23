// MARK: Memory Summary Types

export interface ExtractedSkillSummary {
  name: string;
  description: string;
  confidence: number;
  sharingScope: string;
}

export interface ExtractedInsightSummary {
  insightType: string;
  content: string;
  relevanceScore: number;
  sharingScope: string;
}

// MARK: Retrieved Memory Context

export interface RetrievedMemoryContext {
  hitCount: number;
  skillHits: number;
  insightHits: number;
  resourceCount: number;
  vectorHits: number;
  keywordHits: number;
  graphHits: number;
  latencyMs: number;
  skills?: ExtractedSkillSummary[];
  insights?: ExtractedInsightSummary[];
}

// MARK: Memory Config

export interface MemoryConfig {
  enabled: boolean;
  level: "none" | "glimpse" | "focus" | "clarity";
  summarizationEnabled: boolean;
  skillExtractionEnabled: boolean;
  insightExtractionEnabled: boolean;
  retrievalEnabled: boolean;
  persistenceMode: string;
}

// MARK: Invocation Memory Config

export interface InvocationMemoryRetrievalConfig {
  top_k?: number;
  candidate_limit?: number;
  skills_enabled?: boolean;
  insights_enabled?: boolean;
  resources_enabled?: boolean;
}

export interface InvocationMemorySkillExtractionConfig {
  enabled?: boolean;
  sharing_scope?: string;
  confidence_threshold?: number;
  max_count?: number;
}

export interface InvocationMemoryInsightExtractionConfig {
  enabled?: boolean;
  sharing_scope?: string;
  max_count?: number;
  min_relevance_score?: number;
}

export interface InvocationMemoryConfig {
  enabled?: boolean;
  level?: string;
  summarization_enabled?: boolean;
  persistence_mode?: string;
  retrieval?: InvocationMemoryRetrievalConfig;
  skill_extraction?: InvocationMemorySkillExtractionConfig;
  insight_extraction?: InvocationMemoryInsightExtractionConfig;
}
