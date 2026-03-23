import { fetchDemoFullDetails, fetchDemos, fetchDemosByCategory } from "$lib/api_client/demos";
import type { Demo, DemoDetails } from "$lib/types";

// Reactive state using Svelte 5 runes
let demos = $state<Demo[]>([]);
let byCategory = $state<Record<string, Demo[]>>({});
let selectedDemo = $state<DemoDetails | null>(null);
let loading = $state(false);
let error = $state<string | null>(null);
let connecting = $state(false);
let retryTimer: ReturnType<typeof setTimeout> | null = null;

function isNetworkError(e: unknown): boolean {
  if (e instanceof TypeError && e.message.includes("fetch")) return true;
  if (e instanceof Error && e.message.includes("Failed to fetch")) return true;
  return false;
}

export function useDemos() {
  async function loadDemos(retryCount = 0) {
    loading = true;
    error = null;
    connecting = retryCount > 0;
    try {
      const [demoList, categories] = await Promise.all([fetchDemos(), fetchDemosByCategory()]);
      demos = demoList;
      byCategory = categories;
      connecting = false;
    } catch (e) {
      // Auto-retry on network errors (backend starting up)
      if (isNetworkError(e) && retryCount < 10) {
        connecting = true;
        error = null;
        retryTimer = setTimeout(() => loadDemos(retryCount + 1), 1500);
        return;
      }
      connecting = false;
      error = e instanceof Error ? e.message : "Failed to load demos";
    } finally {
      if (!connecting) loading = false;
    }
  }

  async function selectDemo(id: string) {
    loading = true;
    error = null;
    selectedDemo = null;
    try {
      selectedDemo = await fetchDemoFullDetails(id);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load demo details";
    } finally {
      loading = false;
    }
  }

  function clearSelection() {
    selectedDemo = null;
  }

  function stopRetry() {
    if (retryTimer) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    connecting = false;
  }

  return {
    get demos() {
      return demos;
    },
    get byCategory() {
      return byCategory;
    },
    get selectedDemo() {
      return selectedDemo;
    },
    get loading() {
      return loading;
    },
    get error() {
      return error;
    },
    get connecting() {
      return connecting;
    },
    loadDemos,
    selectDemo,
    clearSelection,
    stopRetry,
  };
}
