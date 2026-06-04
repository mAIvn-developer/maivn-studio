import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { updateAgent, updateApp, updateSwarm } from "./app-config";

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

// MARK: App Update API

describe("updateApp", () => {
  it("sends PATCH request with updates", async () => {
    mockFetchOk({ app: { id: "d1", name: "Updated" } });

    const result = await updateApp("d1", { name: "Updated" });
    expect(result).toEqual({ id: "d1", name: "Updated" });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/apps/d1");
    expect(call[1].method).toBe("PATCH");
    const body = JSON.parse(call[1].body);
    expect(body.name).toBe("Updated");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(updateApp("d1", {})).rejects.toThrow("Failed to update app d1");
  });
});

describe("updateAgent", () => {
  it("sends PATCH request with encoded agent name", async () => {
    const agent = { name: "Agent One", description: "Updated" };
    mockFetchOk(agent);

    const result = await updateAgent("d1", "Agent One", { description: "Updated" });
    expect(result).toEqual(agent);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/apps/d1/agents/Agent%20One");
    expect(call[1].method).toBe("PATCH");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(updateAgent("d1", "agent", {})).rejects.toThrow("Failed to update agent agent");
  });
});

describe("updateSwarm", () => {
  it("sends PATCH request with encoded swarm name", async () => {
    const swarm = { name: "My Swarm", description: "Updated" };
    mockFetchOk(swarm);

    const result = await updateSwarm("d1", "My Swarm", { description: "Updated" });
    expect(result).toEqual(swarm);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/apps/d1/swarms/My%20Swarm");
    expect(call[1].method).toBe("PATCH");
  });

  it("throws on non-ok response", async () => {
    mockFetchError(400);
    await expect(updateSwarm("d1", "swarm", {})).rejects.toThrow("Failed to update swarm swarm");
  });
});
