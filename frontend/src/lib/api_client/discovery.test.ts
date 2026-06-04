import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RepoScanSelection } from "../types";

import { applyRepoSelection, scanRepo } from "./discovery";

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

// MARK: Repo Discovery API

describe("scanRepo", () => {
  it("returns scan items", async () => {
    const items = [{ path: "src/main.py", type: "file" }];
    mockFetchOk({ items });

    const result = await scanRepo();
    expect(result).toEqual(items);
    expect(fetch).toHaveBeenCalledWith("/api/discovery/scan", { method: "POST" });
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(scanRepo()).rejects.toThrow("Failed to scan repo");
  });
});

describe("applyRepoSelection", () => {
  it("returns number of added items", async () => {
    mockFetchOk({ added: 3 });

    const selections: RepoScanSelection[] = [{ file_path: "a", discovery_path: "a" }];
    const result = await applyRepoSelection(selections);
    expect(result).toBe(3);
    expect(fetch).toHaveBeenCalledWith(
      "/api/discovery/apply",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(applyRepoSelection([])).rejects.toThrow("Failed to apply selections");
  });
});
