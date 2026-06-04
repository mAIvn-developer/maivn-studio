// MARK: Memory Vocabularies

/**
 * Memory recall depth. Mirrors the canonical backend union
 * `MemoryLevel` in `maivn_shared.domain.entities.memory_config`
 * (`Literal["none", "glimpse", "focus", "clarity"]`). The server normalizes
 * the wire value to lowercase before emitting it.
 */
export type MemoryLevel = "none" | "glimpse" | "focus" | "clarity";

/**
 * Memory persistence ceiling / policy mode. Mirrors the canonical backend
 * union `MemoryPersistenceMode` in
 * `maivn_shared.domain.entities.memory_config`
 * (`Literal["persist_none", "vector_only", "vector_plus_graph"]`).
 */
export type MemoryPersistenceMode = "persist_none" | "vector_only" | "vector_plus_graph";

// MARK: Memory Activity Vocabularies

/**
 * Memory-activity `mode` for an enrichment chip. The union below is the
 * documented-known set emitted by the maivn-server memory enrichment builders;
 * it is intentionally OPEN (`string & {}`) because these values arrive as
 * opaque dict entries forwarded verbatim through the SDK bridge and studio's
 * reporter passthrough, so the server may add modes the UI has not enumerated.
 *
 * Known values (with source):
 * - `retrieve`, `summarize`, `index` —
 *   `build_retrieval_memory_details` / `build_summary_memory_details` /
 *   `build_index_memory_details` in
 *   `services/maivn-server/.../session/memory/enrichment.py`.
 * - `extract_skills`, `extract_insights` —
 *   `services/maivn-server/.../session/execution_helpers/extraction/operations.py`.
 * - `resource_registration` —
 *   `build_resource_lifecycle_details` in
 *   `services/maivn-server/.../session/memory/resources/core.py`.
 * - `resource_extract` —
 *   `extraction_details` in
 *   `services/maivn-server/.../system_tools/functions/resource_extract_tool.py`.
 */
export type MemoryActivityMode =
  | "retrieve"
  | "summarize"
  | "index"
  | "extract_skills"
  | "extract_insights"
  | "resource_registration"
  | "resource_extract"
  | (string & {});

/**
 * Memory-activity `source` (attribution for resource-registration chips). The
 * union is the documented-known set and is intentionally OPEN (`string & {}`)
 * for the same wire-passthrough reason as {@link MemoryActivityMode}.
 *
 * Known values (with source): `message_attachments`, `bound_resources` —
 * `emit_resource_registration_events` callers in
 * `services/maivn-server/.../api/session_service/builder.py`, threaded into the
 * memory dict by `build_resource_lifecycle_details`.
 */
export type MemoryActivitySource = "message_attachments" | "bound_resources" | (string & {});

/**
 * Memory-activity `status` (resource-extract / RLM outcome). The union is the
 * documented-known set and is intentionally OPEN (`string & {}`): the backend
 * status vocabulary is large and shared across resource-extract result rows and
 * enrichment chips, so a closed Literal would be unsound for forwarded values.
 *
 * Known values (with source): `found`, `partial`, `not_found`, `error` —
 * `derive_resource_result_status` and the `emit_memory_enrichment_event`
 * call sites in
 * `services/maivn-server/.../system_tools/functions/resource_extract_tool.py`;
 * `inline_available` — `inline_available_result` /
 * `results.py` in the same `resource_extraction/` package.
 */
export type MemoryActivityStatus =
  | "found"
  | "partial"
  | "not_found"
  | "error"
  | "inline_available"
  | (string & {});

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
  level: MemoryLevel;
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
