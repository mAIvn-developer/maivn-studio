import { describe, expect, it } from "vitest";

import { buildStructuredDiff, flattenStructuredValue } from "./batch-structured-diff";

describe("batch structured diff", () => {
  it("flattens nested objects and arrays into comparable paths", () => {
    const flattened = flattenStructuredValue({
      incident: { id: "BATCH-1", tags: ["api", "p1"] },
      count: 2,
    });

    expect(Object.fromEntries(flattened)).toEqual({
      "incident.id": "BATCH-1",
      "incident.tags[0]": "api",
      "incident.tags[1]": "p1",
      count: 2,
    });
  });

  it("marks equal fields as stable and changed fields as changed", () => {
    const rows = buildStructuredDiff([
      {
        id: "run-1",
        label: "Run 1",
        value: { incident_id: "BATCH-1", severity: "P1" },
      },
      {
        id: "run-2",
        label: "Run 2",
        value: { incident_id: "BATCH-1", severity: "P2" },
      },
    ]);

    expect(rows.find((row) => row.path === "incident_id")?.changed).toBe(false);
    expect(rows.find((row) => row.path === "severity")?.changed).toBe(true);
  });

  it("marks missing fields as changed", () => {
    const rows = buildStructuredDiff([
      {
        id: "run-1",
        label: "Run 1",
        value: { incident_id: "BATCH-1", owner: "API" },
      },
      {
        id: "run-2",
        label: "Run 2",
        value: { incident_id: "BATCH-1" },
      },
    ]);

    const owner = rows.find((row) => row.path === "owner");

    expect(owner?.changed).toBe(true);
    expect(owner?.cells[1].missing).toBe(true);
  });
});
