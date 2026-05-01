import { fetchAppFullDetails, fetchApps, fetchAppsByCategory } from "$lib/api_client/apps";
import type { App, AppDetails } from "$lib/types";

// Reactive state using Svelte 5 runes
let apps = $state<App[]>([]);
let byCategory = $state<Record<string, App[]>>({});
let selectedApp = $state<AppDetails | null>(null);
let selectedAppId = $state<string | null>(null);
let loading = $state(false);
let error = $state<string | null>(null);
let connecting = $state(false);
let retryTimer: ReturnType<typeof setTimeout> | null = null;
let appRequestToken = 0;

function isNetworkError(e: unknown): boolean {
  if (e instanceof TypeError && e.message.includes("fetch")) return true;
  if (e instanceof Error && e.message.includes("Failed to fetch")) return true;
  return false;
}

export function useApps() {
  async function loadApps(retryCount = 0) {
    loading = true;
    error = null;
    connecting = retryCount > 0;
    try {
      const [appList, categories] = await Promise.all([fetchApps(), fetchAppsByCategory()]);
      apps = appList;
      byCategory = categories;
      connecting = false;
    } catch (e) {
      // Auto-retry on network errors (backend starting up)
      if (isNetworkError(e) && retryCount < 10) {
        connecting = true;
        error = null;
        retryTimer = setTimeout(() => loadApps(retryCount + 1), 1500);
        return;
      }
      connecting = false;
      error = e instanceof Error ? e.message : "Failed to load apps";
    } finally {
      if (!connecting) loading = false;
    }
  }

  async function selectApp(id: string, variant?: string) {
    loading = true;
    error = null;
    selectedAppId = id;
    const requestToken = ++appRequestToken;
    if (selectedApp?.id !== id) {
      selectedApp = null;
    }
    try {
      const loaded = await fetchAppFullDetails(id, variant);
      if (requestToken !== appRequestToken) {
        return;
      }
      selectedApp = loaded;
    } catch (e) {
      if (requestToken !== appRequestToken) {
        return;
      }
      error = e instanceof Error ? e.message : "Failed to load app details";
    } finally {
      if (requestToken === appRequestToken) {
        loading = false;
      }
    }
  }

  function clearSelection() {
    appRequestToken += 1;
    selectedAppId = null;
    selectedApp = null;
  }

  function stopRetry() {
    if (retryTimer) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    connecting = false;
  }

  return {
    get apps() {
      return apps;
    },
    get byCategory() {
      return byCategory;
    },
    get selectedApp() {
      return selectedApp;
    },
    get selectedAppId() {
      return selectedAppId;
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
    loadApps,
    selectApp,
    clearSelection,
    stopRetry,
  };
}
