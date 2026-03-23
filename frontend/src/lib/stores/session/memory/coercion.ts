import type {
  ExtractedInsightSummary,
  ExtractedSkillSummary,
  MemoryActivityData,
  RedactionActivityData,
} from "$lib/types";

// MARK: Coercion Helpers

export function normalizeNonNegativeNumber(value: unknown): number | undefined {
  let parsed: number | undefined;
  if (typeof value === "number" && Number.isFinite(value)) {
    parsed = value;
  } else if (typeof value === "string" && value.trim()) {
    parsed = Number(value);
  }

  if (parsed === undefined || !Number.isFinite(parsed)) {
    return undefined;
  }
  if (!Number.isInteger(parsed) || parsed < 0) {
    return undefined;
  }
  return parsed;
}

export function coerceSkillSummaries(value: unknown): ExtractedSkillSummary[] {
  if (!Array.isArray(value)) return [];
  const result: ExtractedSkillSummary[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") continue;
    const s = item as Record<string, unknown>;
    if (typeof s.name !== "string" || !s.name.trim()) continue;
    result.push({
      name: s.name.trim(),
      description: typeof s.description === "string" ? s.description.trim() : "",
      confidence: typeof s.confidence === "number" ? s.confidence : 0,
      sharingScope: typeof s.sharing_scope === "string" ? s.sharing_scope.trim() : "project",
    });
  }
  return result;
}

export function coerceInsightSummaries(value: unknown): ExtractedInsightSummary[] {
  if (!Array.isArray(value)) return [];
  const result: ExtractedInsightSummary[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") continue;
    const i = item as Record<string, unknown>;
    if (typeof i.content !== "string" || !i.content.trim()) continue;
    result.push({
      insightType: typeof i.insight_type === "string" ? i.insight_type.trim() : "lesson",
      content: i.content.trim(),
      relevanceScore: typeof i.relevance_score === "number" ? i.relevance_score : 0,
      sharingScope: typeof i.sharing_scope === "string" ? i.sharing_scope.trim() : "agent",
    });
  }
  return result;
}

export function coerceMemoryActivityData(value: unknown): MemoryActivityData | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const details: MemoryActivityData = {};

  if (typeof payload.mode === "string" && payload.mode.trim()) {
    details.mode = payload.mode.trim();
  }
  if (typeof payload.source === "string" && payload.source.trim()) {
    details.source = payload.source.trim();
  }
  if (typeof payload.status === "string" && payload.status.trim()) {
    details.status = payload.status.trim();
  }
  if (typeof payload.memory_level === "string" && payload.memory_level.trim()) {
    details.memoryLevel = payload.memory_level.trim();
  }
  if (typeof payload.policy_mode === "string" && payload.policy_mode.trim()) {
    details.policyMode = payload.policy_mode.trim();
  }

  const hitCount = normalizeNonNegativeNumber(payload.hit_count);
  if (hitCount !== undefined) details.hitCount = hitCount;

  const vectorHits = normalizeNonNegativeNumber(payload.vector_hits);
  if (vectorHits !== undefined) details.vectorHits = vectorHits;

  const keywordHits = normalizeNonNegativeNumber(payload.keyword_hits);
  if (keywordHits !== undefined) details.keywordHits = keywordHits;

  const graphHits = normalizeNonNegativeNumber(payload.graph_hits);
  if (graphHits !== undefined) details.graphHits = graphHits;

  const skillCount = normalizeNonNegativeNumber(payload.skill_count);
  if (skillCount !== undefined) details.skillCount = skillCount;

  const insightCount = normalizeNonNegativeNumber(payload.insight_count);
  if (insightCount !== undefined) details.insightCount = insightCount;

  const resourceCount = normalizeNonNegativeNumber(payload.resource_count);
  if (resourceCount !== undefined) details.resourceCount = resourceCount;

  const vectorRows = normalizeNonNegativeNumber(payload.vector_rows);
  if (vectorRows !== undefined) details.vectorRows = vectorRows;

  const graphEdges = normalizeNonNegativeNumber(payload.graph_edges);
  if (graphEdges !== undefined) details.graphEdges = graphEdges;

  const traceEventCount = normalizeNonNegativeNumber(payload.trace_event_count);
  if (traceEventCount !== undefined) details.traceEventCount = traceEventCount;

  const latencyMs = normalizeNonNegativeNumber(payload.latency_ms);
  if (latencyMs !== undefined) details.latencyMs = latencyMs;

  const registeredCount = normalizeNonNegativeNumber(payload.registered_count);
  if (registeredCount !== undefined) details.registeredCount = registeredCount;

  const reusedCount = normalizeNonNegativeNumber(payload.reused_count);
  if (reusedCount !== undefined) details.reusedCount = reusedCount;

  const skippedCount = normalizeNonNegativeNumber(payload.skipped_count);
  if (skippedCount !== undefined) details.skippedCount = skippedCount;

  const totalBytes = normalizeNonNegativeNumber(payload.total_bytes);
  if (totalBytes !== undefined) details.totalBytes = totalBytes;

  const dedupReusedCount = normalizeNonNegativeNumber(payload.dedup_reused_count);
  if (dedupReusedCount !== undefined) details.dedupReusedCount = dedupReusedCount;

  const versionSupersededCount = normalizeNonNegativeNumber(payload.version_superseded_count);
  if (versionSupersededCount !== undefined) {
    details.versionSupersededCount = versionSupersededCount;
  }

  const discoveryCount = normalizeNonNegativeNumber(payload.discovery_count);
  if (discoveryCount !== undefined) details.discoveryCount = discoveryCount;

  const selectedCount = normalizeNonNegativeNumber(payload.selected_count);
  if (selectedCount !== undefined) details.selectedCount = selectedCount;

  const chunkCount = normalizeNonNegativeNumber(payload.chunk_count);
  if (chunkCount !== undefined) details.chunkCount = chunkCount;

  const requestedMaxResources = normalizeNonNegativeNumber(payload.requested_max_resources);
  if (requestedMaxResources !== undefined) {
    details.requestedMaxResources = requestedMaxResources;
  }

  const requiredTagCount = normalizeNonNegativeNumber(payload.required_tag_count);
  if (requiredTagCount !== undefined) details.requiredTagCount = requiredTagCount;

  if (typeof payload.requested_resource_id === "string" && payload.requested_resource_id.trim()) {
    details.requestedResourceId = payload.requested_resource_id.trim();
  }

  if (typeof payload.full_extraction === "boolean") {
    details.fullExtraction = payload.full_extraction;
  }

  if (Array.isArray(payload.resource_ids)) {
    const ids = payload.resource_ids
      .filter((item): item is string => typeof item === "string")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
    if (ids.length > 0) details.resourceIds = ids;
  }

  if (Array.isArray(payload.superseded_resource_ids)) {
    const ids = payload.superseded_resource_ids
      .filter((item): item is string => typeof item === "string")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
    if (ids.length > 0) details.supersededResourceIds = ids;
  }

  const extractedCount = normalizeNonNegativeNumber(payload.extracted_count);
  if (extractedCount !== undefined) details.extractedCount = extractedCount;

  const persistedCount = normalizeNonNegativeNumber(payload.persisted_count);
  if (persistedCount !== undefined) details.persistedCount = persistedCount;

  const skills = coerceSkillSummaries(payload.skills);
  if (skills.length > 0) details.skills = skills;

  const insights = coerceInsightSummaries(payload.insights);
  if (insights.length > 0) details.insights = insights;

  return Object.keys(details).length > 0 ? details : undefined;
}

export function coerceRedactionActivityData(value: unknown): RedactionActivityData | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return undefined;
  }

  const payload = value as Record<string, unknown>;
  const details: RedactionActivityData = {};

  if (Array.isArray(payload.inserted_keys)) {
    const insertedKeys = payload.inserted_keys
      .filter((item): item is string => typeof item === "string")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
    if (insertedKeys.length > 0) details.insertedKeys = insertedKeys;
  }

  if (
    payload.added_private_data &&
    typeof payload.added_private_data === "object" &&
    !Array.isArray(payload.added_private_data)
  ) {
    details.addedPrivateData = payload.added_private_data as Record<string, unknown>;
  }

  if (
    payload.merged_private_data &&
    typeof payload.merged_private_data === "object" &&
    !Array.isArray(payload.merged_private_data)
  ) {
    details.mergedPrivateData = payload.merged_private_data as Record<string, unknown>;
  }

  const redactedMessageCount = normalizeNonNegativeNumber(payload.redacted_message_count);
  if (redactedMessageCount !== undefined) details.redactedMessageCount = redactedMessageCount;

  const redactedValueCount = normalizeNonNegativeNumber(payload.redacted_value_count);
  if (redactedValueCount !== undefined) details.redactedValueCount = redactedValueCount;

  if (Array.isArray(payload.matched_known_pii_values)) {
    const matchedKnownPiiValues = payload.matched_known_pii_values
      .filter((item): item is string => typeof item === "string")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
    if (matchedKnownPiiValues.length > 0) details.matchedKnownPiiValues = matchedKnownPiiValues;
  }

  if (Array.isArray(payload.unmatched_known_pii_values)) {
    const unmatchedKnownPiiValues = payload.unmatched_known_pii_values
      .filter((item): item is string => typeof item === "string")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
    if (unmatchedKnownPiiValues.length > 0) {
      details.unmatchedKnownPiiValues = unmatchedKnownPiiValues;
    }
  }

  return Object.keys(details).length > 0 ? details : undefined;
}
