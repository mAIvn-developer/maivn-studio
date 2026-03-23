import { buildInvocationMemoryConfig, buildStoreMemoryConfig } from "$lib/scopeMemory";
import type { InvocationMemoryConfig, MemoryConfig, PrivateDataField } from "$lib/types";

type EditableScopeItem = {
  name: string;
  tags?: string[];
  memory_config?: InvocationMemoryConfig;
  private_data?: Record<string, unknown>;
  private_data_keys?: string[];
};

type EditMap<T extends EditableScopeItem> = Record<string, Partial<T>>;

export function toggleExpandedItem(current: Set<string>, name: string): Set<string> {
  const next = new Set(current);
  if (next.has(name)) {
    next.delete(name);
  } else {
    next.add(name);
  }
  return next;
}

export function getItemEdit<T extends EditableScopeItem>(
  edits: EditMap<T>,
  itemName: string,
): Partial<T> {
  return edits[itemName] ?? {};
}

export function setItemEdit<T extends EditableScopeItem>(
  edits: EditMap<T>,
  itemName: string,
  field: string,
  value: unknown,
): EditMap<T> {
  return {
    ...edits,
    [itemName]: { ...getItemEdit(edits, itemName), [field]: value } as Partial<T>,
  };
}

export function discardItemEdit<T extends EditableScopeItem>(
  edits: EditMap<T>,
  itemName: string,
): EditMap<T> {
  const { [itemName]: _, ...rest } = edits;
  return rest;
}

export function hasItemChanges<T extends EditableScopeItem>(
  edits: EditMap<T>,
  itemName: string,
): boolean {
  return Object.keys(getItemEdit(edits, itemName)).length > 0;
}

export function getItemEditValue<T extends EditableScopeItem, K extends keyof T>(
  edits: EditMap<T>,
  item: T,
  field: K,
): T[K] {
  const edit = getItemEdit(edits, item.name);
  return (field in edit ? edit[field] : item[field]) as T[K];
}

export function getItemEditTags<T extends EditableScopeItem>(edits: EditMap<T>, item: T): string {
  const edit = getItemEdit(edits, item.name);
  const tags = "tags" in edit ? (edit.tags as string[] | undefined) : item.tags;
  return (tags ?? []).join(", ");
}

export function parseTagInput(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export function getItemScopeMemoryConfig<T extends EditableScopeItem>(
  edits: EditMap<T>,
  item: T,
): MemoryConfig {
  const edit = getItemEdit(edits, item.name);
  const current = ("memory_config" in edit ? edit.memory_config : item.memory_config) as
    | InvocationMemoryConfig
    | undefined;
  return buildStoreMemoryConfig(current);
}

export function buildItemScopeMemoryEdit<T extends EditableScopeItem>(
  edits: EditMap<T>,
  item: T,
  config: MemoryConfig,
): InvocationMemoryConfig {
  const edit = getItemEdit(edits, item.name);
  const current = ("memory_config" in edit ? edit.memory_config : item.memory_config) as
    | InvocationMemoryConfig
    | undefined;
  return buildInvocationMemoryConfig(config, current);
}

export function getItemPrivateDataValues<T extends EditableScopeItem>(
  edits: EditMap<T>,
  item: T,
): Record<string, unknown> {
  const edit = getItemEdit(edits, item.name);
  const current = ("private_data" in edit ? edit.private_data : item.private_data) as
    | Record<string, unknown>
    | undefined;
  return current ?? {};
}

export function buildItemPrivateDataSchema<T extends EditableScopeItem>(
  item: T,
  values: Record<string, unknown>,
): PrivateDataField[] {
  const keys = Array.from(new Set([...(item.private_data_keys ?? []), ...Object.keys(values)]));
  return keys.sort().map((key) => {
    const value = values[key];
    const type =
      typeof value === "boolean" ? "boolean" : typeof value === "number" ? "number" : "string";
    return {
      key,
      label: key,
      type,
      required: false,
    };
  });
}
