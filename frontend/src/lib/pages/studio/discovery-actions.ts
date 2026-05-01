import { applyRepoSelection, scanRepo } from "$lib/api_client/discovery";
import {
  buildRepoSelections,
  clearSelections,
  selectAllSelections,
  toggleSelection,
} from "$lib/pages/studio/discovery";
import type { RepoScanItem, RepoScanSelection } from "$lib/types";

interface CreateDiscoveryActionsParams {
  getDiscoveryItems: () => RepoScanItem[];
  setDiscoveryItems: (items: RepoScanItem[]) => void;
  getDiscoverySelections: () => Set<string>;
  setDiscoverySelections: (selections: Set<string>) => void;
  setDiscoveryOpen: (open: boolean) => void;
  setDiscoveryLoading: (loading: boolean) => void;
  getDiscoveryError: () => string | null;
  setDiscoveryError: (error: string | null) => void;
  reloadApps: () => Promise<void>;
}

export function createDiscoveryActions(params: CreateDiscoveryActionsParams) {
  async function openDiscovery() {
    params.setDiscoveryOpen(true);
    await rescanDiscovery();
  }

  async function rescanDiscovery() {
    params.setDiscoveryLoading(true);
    params.setDiscoveryError(null);
    try {
      params.setDiscoveryItems(await scanRepo());
      params.setDiscoverySelections(new Set());
    } catch (e) {
      params.setDiscoveryError(e instanceof Error ? e.message : "Failed to scan repo");
    } finally {
      params.setDiscoveryLoading(false);
    }
  }

  function toggleDiscoverySelection(key: string) {
    params.setDiscoverySelections(toggleSelection(params.getDiscoverySelections(), key));
  }

  function selectAllDiscoveries() {
    params.setDiscoverySelections(selectAllSelections(params.getDiscoveryItems()));
  }

  function clearDiscoverySelections() {
    params.setDiscoverySelections(clearSelections());
  }

  async function applyDiscoverySelections() {
    const selections: RepoScanSelection[] = buildRepoSelections(
      params.getDiscoveryItems(),
      params.getDiscoverySelections(),
    );

    if (selections.length === 0) return;

    try {
      await applyRepoSelection(selections);
      params.setDiscoveryOpen(false);
      params.setDiscoverySelections(new Set());
      await params.reloadApps();
    } catch (e) {
      params.setDiscoveryError(e instanceof Error ? e.message : "Failed to apply selections");
    }
  }

  return {
    openDiscovery,
    rescanDiscovery,
    toggleDiscoverySelection,
    selectAllDiscoveries,
    clearDiscoverySelections,
    applyDiscoverySelections,
  };
}
