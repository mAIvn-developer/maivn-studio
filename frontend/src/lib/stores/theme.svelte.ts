// MARK: - Types

export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

// MARK: - Constants

const STORAGE_KEY = "maivn-theme-preference";

// MARK: - Helpers

function isThemePreference(value: string | null | undefined): value is ThemePreference {
  return value === "system" || value === "light" || value === "dark";
}

function resolveTheme(preference: ThemePreference, systemDark: boolean): ResolvedTheme {
  if (preference === "system") return systemDark ? "dark" : "light";
  return preference;
}

function readPreference(): ThemePreference {
  if (typeof localStorage === "undefined") return "system";
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (isThemePreference(stored)) return stored;
  } catch {
    // ignore
  }
  return "system";
}

function applyTheme(preference: ThemePreference, persist: boolean): ResolvedTheme {
  if (typeof document === "undefined" || typeof window === "undefined") return "dark";
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const resolved = resolveTheme(preference, systemDark);
  const root = document.documentElement;
  root.dataset.themePreference = preference;
  root.dataset.theme = resolved;
  if (persist) {
    try {
      localStorage.setItem(STORAGE_KEY, preference);
    } catch {
      // ignore
    }
  }
  return resolved;
}

// MARK: - Store

class ThemeStore {
  preference = $state<ThemePreference>("system");
  resolved = $state<ResolvedTheme>("dark");

  init() {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    const initialPreference = isThemePreference(root.dataset.themePreference ?? null)
      ? (root.dataset.themePreference as ThemePreference)
      : readPreference();
    this.preference = initialPreference;
    this.resolved = applyTheme(initialPreference, false);

    if (typeof window !== "undefined") {
      const media = window.matchMedia("(prefers-color-scheme: dark)");
      const onChange = () => {
        if (this.preference === "system") {
          this.resolved = applyTheme("system", false);
        }
      };
      if (typeof media.addEventListener === "function") {
        media.addEventListener("change", onChange);
      } else {
        media.addListener(onChange);
      }
    }
  }

  set(next: ThemePreference) {
    this.preference = next;
    this.resolved = applyTheme(next, true);
  }
}

export const theme = new ThemeStore();
