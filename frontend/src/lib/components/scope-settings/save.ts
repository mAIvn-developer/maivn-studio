type NamedScopeItem = {
  name: string;
};

type ScopeEditMap<T extends NamedScopeItem> = Record<string, Partial<T>>;

interface SaveScopeItemChangesParams<T extends NamedScopeItem> {
  itemName: string;
  edit: Partial<T>;
  edits: ScopeEditMap<T>;
  setEdits: (edits: ScopeEditMap<T>) => void;
  saving: Record<string, boolean>;
  setSaving: (saving: Record<string, boolean>) => void;
  saveErrors: Record<string, string>;
  setSaveErrors: (saveErrors: Record<string, string>) => void;
  editingName: string | null;
  setEditingName: (name: string | null) => void;
  onUpdated?: () => void;
  persist: (edit: Partial<T>) => Promise<void>;
}

export async function saveScopeItemChanges<T extends NamedScopeItem>(
  params: SaveScopeItemChangesParams<T>,
) {
  if (Object.keys(params.edit).length === 0) return;

  params.setSaving({ ...params.saving, [params.itemName]: true });
  params.setSaveErrors({ ...params.saveErrors, [params.itemName]: "" });

  try {
    await params.persist(params.edit);

    const { [params.itemName]: _, ...rest } = params.edits;
    params.setEdits(rest);
    params.onUpdated?.();

    if (params.editingName === params.itemName) {
      params.setEditingName(null);
    }
  } catch (e) {
    params.setSaveErrors({
      ...params.saveErrors,
      [params.itemName]: e instanceof Error ? e.message : "Failed to save",
    });
  } finally {
    params.setSaving({ ...params.saving, [params.itemName]: false });
  }
}
