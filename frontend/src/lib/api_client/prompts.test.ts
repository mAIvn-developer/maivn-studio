import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { deletePrompt, fetchSavedPrompts, savePrompt } from "./prompts";

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

// MARK: Prompts API

describe("fetchSavedPrompts", () => {
  it("fetches all prompts", async () => {
    const prompts = [{ id: "p1", name: "Prompt 1" }];
    mockFetchOk(prompts);

    const result = await fetchSavedPrompts();
    expect(result).toEqual(prompts);
    expect(fetch).toHaveBeenCalledWith("/api/prompts");
  });

  it("fetches prompts filtered by appId", async () => {
    mockFetchOk([]);

    await fetchSavedPrompts("d1");
    expect(fetch).toHaveBeenCalledWith("/api/prompts?app_id=d1");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(500);
    await expect(fetchSavedPrompts()).rejects.toThrow("Failed to fetch saved prompts");
  });
});

describe("savePrompt", () => {
  it("saves a prompt and returns it", async () => {
    const saved = { id: "p1", name: "My Prompt" };
    mockFetchOk(saved);

    const result = await savePrompt({
      name: "My Prompt",
      content: "Test content",
      appId: "d1",
    });
    expect(result).toEqual(saved);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.name).toBe("My Prompt");
    expect(body.content).toBe("Test content");
    expect(body.app_id).toBe("d1");
    expect(body.description).toBe("");
    expect(body.message_type).toBe("human");
  });

  it("sends optional description and messageType", async () => {
    mockFetchOk({ id: "p1" });

    await savePrompt({
      name: "Test",
      content: "Content",
      description: "A description",
      appId: "d1",
      messageType: "system",
    });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.description).toBe("A description");
    expect(body.message_type).toBe("system");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(savePrompt({ name: "Test", content: "C", appId: "d1" })).rejects.toThrow(
      "Failed to save prompt",
    );
  });
});

describe("deletePrompt", () => {
  it("sends DELETE request", async () => {
    mockFetchOk(undefined);

    await deletePrompt("p1");
    expect(fetch).toHaveBeenCalledWith("/api/prompts/p1", { method: "DELETE" });
  });

  it("throws on non-ok response", async () => {
    mockFetchError(404);
    await expect(deletePrompt("p1")).rejects.toThrow("Failed to delete prompt");
  });
});
