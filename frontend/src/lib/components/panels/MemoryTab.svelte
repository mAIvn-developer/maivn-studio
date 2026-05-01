<script lang="ts">
  import { ChevronDown, Zap, Lightbulb, Search, Share2 } from "lucide-svelte";
  import Badge from "../ui/Badge.svelte";
  import type {
    ExtractedSkillSummary,
    ExtractedInsightSummary,
    RetrievedMemoryContext,
  } from "$lib/types";

  interface Props {
    extractedSkills?: ExtractedSkillSummary[];
    extractedInsights?: ExtractedInsightSummary[];
    retrievedMemoryContext?: RetrievedMemoryContext | null;
  }

  let {
    extractedSkills = [],
    extractedInsights = [],
    retrievedMemoryContext = null,
  }: Props = $props();

  type SectionKey = "retrieved" | "skills" | "insights";

  let sectionOpen = $state<Record<SectionKey, boolean>>({
    retrieved: true,
    skills: true,
    insights: true,
  });

  let expandedSkills = $state<Set<number>>(new Set());
  let expandedInsights = $state<Set<number>>(new Set());

  // Merge retrieved skills/insights with extracted ones, deduplicated by name/content.
  const allSkills = $derived.by(() => {
    const seen = new Set<string>();
    const merged: ExtractedSkillSummary[] = [];
    // Retrieved skills first (from memory retrieval)
    for (const skill of retrievedMemoryContext?.skills ?? []) {
      if (!seen.has(skill.name)) {
        seen.add(skill.name);
        merged.push(skill);
      }
    }
    // Then extracted skills (from extraction events)
    for (const skill of extractedSkills) {
      if (!seen.has(skill.name)) {
        seen.add(skill.name);
        merged.push(skill);
      }
    }
    return merged;
  });

  const allInsights = $derived.by(() => {
    const seen = new Set<string>();
    const merged: ExtractedInsightSummary[] = [];
    for (const insight of retrievedMemoryContext?.insights ?? []) {
      if (!seen.has(insight.content)) {
        seen.add(insight.content);
        merged.push(insight);
      }
    }
    for (const insight of extractedInsights) {
      if (!seen.has(insight.content)) {
        seen.add(insight.content);
        merged.push(insight);
      }
    }
    return merged;
  });

  function toggleSection(section: SectionKey) {
    sectionOpen = { ...sectionOpen, [section]: !sectionOpen[section] };
  }

  function toggleSkill(index: number) {
    const next = new Set(expandedSkills);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    expandedSkills = next;
  }

  function toggleInsight(index: number) {
    const next = new Set(expandedInsights);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    expandedInsights = next;
  }

  function insightTypeColor(type: string): string {
    switch (type) {
      case "warning":
        return "var(--color-warning)";
      case "failure_pattern":
        return "var(--color-error)";
      case "optimization":
        return "var(--color-secondary)";
      default:
        return "var(--color-secondary)";
    }
  }

  function insightTypeLabel(type: string): string {
    switch (type) {
      case "failure_pattern":
        return "failure";
      default:
        return type;
    }
  }

  function confidencePercent(value: number): string {
    return `${Math.round(value * 100)}%`;
  }

  let hasContent = $derived(
    allSkills.length > 0 || allInsights.length > 0 || retrievedMemoryContext !== null,
  );
</script>

<div class="h-full overflow-y-auto overflow-x-hidden">
  {#if !hasContent}
    <div class="flex flex-col items-center justify-center p-8 text-center">
      <p class="text-sm text-[var(--color-text-tertiary)]">No memory activity yet.</p>
      <p class="text-xs text-[var(--color-text-tertiary)] mt-1">
        Enable memory in Config and run a session.
      </p>
    </div>
  {:else}
    <!-- Retrieved Context -->
    {#if retrievedMemoryContext}
      <section class="memory-section">
        <button
          type="button"
          class="section-toggle"
          aria-expanded={sectionOpen.retrieved}
          onclick={() => toggleSection("retrieved")}
        >
          <div class="section-copy">
            <span class="section-title">
              <Search size={13} class="inline-block mr-1 opacity-70" />
              Retrieved Context
            </span>
            <span class="section-subtitle">
              {retrievedMemoryContext.hitCount} hits in {retrievedMemoryContext.latencyMs}ms
            </span>
          </div>
          <ChevronDown
            size={16}
            class="section-chevron {sectionOpen.retrieved ? 'rotate-180' : ''}"
          />
        </button>
        {#if sectionOpen.retrieved}
          <div class="section-body animate-in">
            <div class="stat-grid">
              <div class="stat-cell">
                <span class="stat-value">{retrievedMemoryContext.hitCount}</span>
                <span class="stat-label">Hits</span>
              </div>
              <div class="stat-cell">
                <span class="stat-value">{retrievedMemoryContext.skillHits}</span>
                <span class="stat-label">Skills</span>
              </div>
              <div class="stat-cell">
                <span class="stat-value">{retrievedMemoryContext.insightHits}</span>
                <span class="stat-label">Insights</span>
              </div>
              <div class="stat-cell">
                <span class="stat-value">{retrievedMemoryContext.resourceCount}</span>
                <span class="stat-label">Resources</span>
              </div>
              <div class="stat-cell">
                <span class="stat-value">{retrievedMemoryContext.vectorHits}</span>
                <span class="stat-label">Vectors</span>
              </div>
              <div class="stat-cell">
                <span class="stat-value">{retrievedMemoryContext.keywordHits}</span>
                <span class="stat-label">Keywords</span>
              </div>
              <div class="stat-cell">
                <span class="stat-value">{retrievedMemoryContext.graphHits}</span>
                <span class="stat-label">Graph</span>
              </div>
            </div>
          </div>
        {/if}
      </section>
    {/if}

    <!-- Skills -->
    <section class="memory-section">
      <button
        type="button"
        class="section-toggle"
        aria-expanded={sectionOpen.skills}
        onclick={() => toggleSection("skills")}
      >
        <div class="section-copy">
          <span class="section-title">
            <Zap size={13} class="inline-block mr-1 opacity-70" />
            Skills
          </span>
          {#if allSkills.length > 0}
            <span class="section-subtitle">{allSkills.length} available</span>
          {:else}
            <span class="section-subtitle">None yet</span>
          {/if}
        </div>
        <div class="flex items-center gap-1.5">
          {#if allSkills.length > 0}
            <Badge variant="tertiary" pill>{allSkills.length}</Badge>
          {/if}
          <ChevronDown size={16} class="section-chevron {sectionOpen.skills ? 'rotate-180' : ''}" />
        </div>
      </button>
      {#if sectionOpen.skills}
        <div class="section-body animate-in">
          {#if allSkills.length === 0}
            <p class="empty-text">No skills available yet.</p>
          {:else}
            <div class="card-list">
              {#each allSkills as skill, idx}
                <button type="button" class="memory-card" onclick={() => toggleSkill(idx)}>
                  <div class="card-header">
                    <span class="card-name">{skill.name}</span>
                    {#if skill.confidence > 0}
                      <span class="card-badge" style="color: var(--color-secondary)">
                        {confidencePercent(skill.confidence)}
                      </span>
                    {/if}
                  </div>
                  {#if expandedSkills.has(idx)}
                    <div class="card-body">
                      {#if skill.description}
                        <p class="card-description">{skill.description}</p>
                      {/if}
                      <div class="card-meta">
                        <Share2 size={11} class="opacity-50" />
                        <span>{skill.sharingScope}</span>
                      </div>
                    </div>
                  {/if}
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </section>

    <!-- Insights -->
    <section class="memory-section">
      <button
        type="button"
        class="section-toggle"
        aria-expanded={sectionOpen.insights}
        onclick={() => toggleSection("insights")}
      >
        <div class="section-copy">
          <span class="section-title">
            <Lightbulb size={13} class="inline-block mr-1 opacity-70" />
            Insights
          </span>
          {#if allInsights.length > 0}
            <span class="section-subtitle">{allInsights.length} available</span>
          {:else}
            <span class="section-subtitle">None yet</span>
          {/if}
        </div>
        <div class="flex items-center gap-1.5">
          {#if allInsights.length > 0}
            <Badge variant="secondary" pill>{allInsights.length}</Badge>
          {/if}
          <ChevronDown
            size={16}
            class="section-chevron {sectionOpen.insights ? 'rotate-180' : ''}"
          />
        </div>
      </button>
      {#if sectionOpen.insights}
        <div class="section-body animate-in">
          {#if allInsights.length === 0}
            <p class="empty-text">No insights available yet.</p>
          {:else}
            <div class="card-list">
              {#each allInsights as insight, idx}
                <button type="button" class="memory-card" onclick={() => toggleInsight(idx)}>
                  <div class="card-header">
                    <span
                      class="type-chip"
                      style="background: color-mix(in srgb, {insightTypeColor(
                        insight.insightType,
                      )} 18%, transparent); color: {insightTypeColor(insight.insightType)}"
                    >
                      {insightTypeLabel(insight.insightType)}
                    </span>
                    {#if insight.relevanceScore > 0}
                      <span class="card-badge" style="color: var(--color-text-tertiary)">
                        {confidencePercent(insight.relevanceScore)}
                      </span>
                    {/if}
                  </div>
                  {#if expandedInsights.has(idx)}
                    <div class="card-body">
                      <p class="card-description">{insight.content}</p>
                      <div class="card-meta">
                        <Share2 size={11} class="opacity-50" />
                        <span>{insight.sharingScope}</span>
                      </div>
                    </div>
                  {:else}
                    <p class="card-preview">{insight.content}</p>
                  {/if}
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </section>
  {/if}
</div>

<style>
  .memory-section {
    border-bottom: 1px solid var(--color-outline-variant);
  }

  .section-toggle {
    width: 100%;
    border: 0;
    background: transparent;
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    text-align: left;
    cursor: pointer;
    transition: background-color var(--transition-fast);
  }

  .section-toggle:hover {
    background: color-mix(in srgb, var(--color-bg-secondary) 72%, transparent);
  }

  .section-copy {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
  }

  .section-title {
    font-size: 0.8125rem;
    line-height: 1.2;
    font-weight: 600;
    color: var(--color-text);
    display: flex;
    align-items: center;
  }

  .section-subtitle {
    font-size: 0.6875rem;
    line-height: 1.25;
    color: var(--color-text-tertiary);
  }

  :global(.section-chevron) {
    flex-shrink: 0;
    color: var(--color-text-tertiary);
    transition:
      transform var(--transition-fast),
      color var(--transition-fast);
  }

  .section-body {
    padding: 0 1rem 0.75rem;
  }

  .empty-text {
    font-size: 0.75rem;
    color: var(--color-text-tertiary);
  }

  .stat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.5rem;
  }

  .stat-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.1rem;
    padding: 0.375rem;
    border-radius: var(--radius-md);
    background: var(--color-bg-secondary);
  }

  .stat-value {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }

  .stat-label {
    font-size: 0.625rem;
    color: var(--color-text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .card-list {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .memory-card {
    width: 100%;
    text-align: left;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    padding: 0.5rem 0.625rem;
    background: var(--color-bg-secondary);
    cursor: pointer;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast);
  }

  .memory-card:hover {
    background: var(--color-bg-tertiary);
    border-color: var(--color-outline);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .card-name {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }

  .card-badge {
    font-size: 0.6875rem;
    font-weight: 500;
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
  }

  .card-body {
    margin-top: 0.375rem;
  }

  .card-description {
    font-size: 0.6875rem;
    line-height: 1.4;
    color: var(--color-text-secondary);
  }

  .card-preview {
    font-size: 0.6875rem;
    line-height: 1.3;
    color: var(--color-text-tertiary);
    margin-top: 0.25rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .card-meta {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin-top: 0.375rem;
    font-size: 0.625rem;
    color: var(--color-text-tertiary);
  }

  .type-chip {
    font-size: 0.625rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0.125rem 0.375rem;
    border-radius: var(--radius-sm);
  }
</style>
