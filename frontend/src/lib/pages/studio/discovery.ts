import type { RepoScanItem, RepoScanSelection } from "$lib/types";

export function selectionKey(item: RepoScanItem): string {
  return `${item.discovery_path}::${item.file_path}`;
}

export function toggleSelection(current: Set<string>, key: string): Set<string> {
  const next = new Set(current);
  if (next.has(key)) {
    next.delete(key);
  } else {
    next.add(key);
  }
  return next;
}

export function selectAllSelections(items: RepoScanItem[]): Set<string> {
  return new Set(items.map(selectionKey));
}

export function clearSelections(): Set<string> {
  return new Set();
}

export function buildRepoSelections(
  items: RepoScanItem[],
  selected: Set<string>,
): RepoScanSelection[] {
  return items
    .filter((item) => selected.has(selectionKey(item)))
    .map((item) => ({ file_path: item.file_path, discovery_path: item.discovery_path }));
}
