export interface StructuredDiffColumn {
  id: string;
  label: string;
  value: unknown;
}

export interface StructuredDiffCell {
  missing: boolean;
  changed: boolean;
  value: unknown;
  displayValue: string;
}

export interface StructuredDiffRow {
  path: string;
  changed: boolean;
  cells: StructuredDiffCell[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeForCompare(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeForCompare(item));
  }

  if (isRecord(value)) {
    return Object.fromEntries(
      Object.entries(value)
        .toSorted(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, normalizeForCompare(item)]),
    );
  }

  return value;
}

function canonicalize(value: unknown): string {
  try {
    return JSON.stringify(normalizeForCompare(value));
  } catch {
    return String(value);
  }
}

export function formatDiffValue(value: unknown): string {
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function appendPath(parent: string, key: string): string {
  return parent ? `${parent}.${key}` : key;
}

function appendArrayPath(parent: string, index: number): string {
  return `${parent || "value"}[${index}]`;
}

export function flattenStructuredValue(value: unknown): Map<string, unknown> {
  const flattened = new Map<string, unknown>();

  function visit(current: unknown, path: string): void {
    if (Array.isArray(current)) {
      if (current.length === 0) {
        flattened.set(path || "value", current);
        return;
      }
      current.forEach((item, index) => visit(item, appendArrayPath(path, index)));
      return;
    }

    if (isRecord(current)) {
      const entries = Object.entries(current);
      if (entries.length === 0) {
        flattened.set(path || "value", current);
        return;
      }
      for (const [key, item] of entries) {
        visit(item, appendPath(path, key));
      }
      return;
    }

    flattened.set(path || "value", current);
  }

  visit(value, "");
  return flattened;
}

export function buildStructuredDiff(columns: StructuredDiffColumn[]): StructuredDiffRow[] {
  const flattenedColumns = columns.map((column) => flattenStructuredValue(column.value));
  const paths = Array.from(
    flattenedColumns.reduce((acc, flattened) => {
      for (const path of flattened.keys()) {
        acc.add(path);
      }
      return acc;
    }, new Set<string>()),
  ).toSorted((left, right) => left.localeCompare(right));

  return paths.map((path) => {
    const rawValues = flattenedColumns.map((flattened) => flattened.get(path));
    const presentValues = rawValues.filter((value) => value !== undefined);
    const uniqueValues = new Set(presentValues.map((value) => canonicalize(value)));
    const changed = presentValues.length !== columns.length || uniqueValues.size > 1;

    return {
      path,
      changed,
      cells: rawValues.map((value) => ({
        missing: value === undefined,
        changed,
        value,
        displayValue: value === undefined ? "Missing" : formatDiffValue(value),
      })),
    };
  });
}
