import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchApp, fetchAppFullDetails, fetchApps, fetchAppsByCategory } from "./apps";

// MARK: Helpers

function mockFetchOk(data: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data)),
      clone: () => ({
        text: () => Promise.resolve(JSON.stringify(data)),
      }),
    }),
  );
}

function mockFetchError(status: number, body?: Record<string, unknown>): void {
  const bodyStr = JSON.stringify(body ?? {});
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      json: () => (body ? Promise.resolve(body) : Promise.reject(new Error("no json"))),
      text: () => Promise.resolve(bodyStr),
      clone: () => ({
        text: () => Promise.resolve(bodyStr),
      }),
    }),
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// MARK: Apps API

describe("fetchApps", () => {
  it("returns list of apps", async () => {
    const apps = [{ id: "d1", name: "App 1" }];
    mockFetchOk({ apps });

    const result = await fetchApps();
    expect(result).toEqual(apps);
    expect(fetch).toHaveBeenCalledWith("/api/apps");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchApps()).rejects.toThrow("Failed to fetch apps");
  });
});

describe("fetchAppsByCategory", () => {
  it("groups apps by category", async () => {
    const apps = [
      { id: "d1", name: "App 1", category: "core" },
      { id: "d2", name: "App 2", category: "core" },
      { id: "d3", name: "App 3", category: "advanced" },
    ];
    mockFetchOk({ apps });

    const result = await fetchAppsByCategory();
    expect(result).toEqual({
      core: [apps[0], apps[1]],
      advanced: [apps[2]],
    });
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchAppsByCategory()).rejects.toThrow("Failed to fetch apps");
  });
});

describe("fetchApp", () => {
  it("merges app and variants into AppDetails", async () => {
    const app = { id: "d1", name: "App 1" };
    const variants = [{ args: [], description: "default" }];
    mockFetchOk({ app, variants });

    const result = await fetchApp("d1");
    expect(result.id).toBe("d1");
    expect(result.variants).toEqual(variants);
    expect(result.agents).toEqual([]);
    expect(result.tools).toEqual([]);
  });

  it("throws on non-ok response", async () => {
    mockFetchError(404);
    await expect(fetchApp("d1")).rejects.toThrow("Failed to fetch app d1");
  });
});

describe("fetchAppFullDetails", () => {
  it("returns full app details", async () => {
    const details = { id: "d1", name: "App 1", agents: [], tools: [] };
    mockFetchOk(details);

    const result = await fetchAppFullDetails("d1");
    expect(result).toEqual(details);
    expect(fetch).toHaveBeenCalledWith("/api/apps/d1/details");
  });

  it("passes the selected variant in the details query string", async () => {
    const details = { id: "d1", name: "App 1", agents: [], tools: [] };
    mockFetchOk(details);

    await fetchAppFullDetails("d1", "with-private-data");

    expect(fetch).toHaveBeenCalledWith("/api/apps/d1/details?variant=with-private-data");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchAppFullDetails("d1")).rejects.toThrow("Failed to fetch app details d1");
  });
});
