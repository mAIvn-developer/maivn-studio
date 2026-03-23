/**
 * Keyboard shortcut registry system.
 * Manages global keyboard shortcuts with modifier key support.
 */

// MARK: Types

export interface ShortcutAction {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  label: string;
  shortcutDisplay: string;
  action: () => void;
}

// MARK: Registry

const shortcuts: ShortcutAction[] = [];

/**
 * Register a keyboard shortcut. Returns an unregister function.
 */
export function registerShortcut(shortcut: ShortcutAction): () => void {
  shortcuts.push(shortcut);

  return () => {
    const index = shortcuts.indexOf(shortcut);
    if (index !== -1) {
      shortcuts.splice(index, 1);
    }
  };
}

/**
 * Get all currently registered shortcuts (for display in command palette).
 */
export function getRegisteredShortcuts(): ShortcutAction[] {
  return [...shortcuts];
}

// MARK: Global Handler

/**
 * Check whether the event target is an editable element (input, textarea, contenteditable).
 */
function isEditableTarget(event: KeyboardEvent): boolean {
  const target = event.target as HTMLElement | null;
  if (!target) return false;

  const tagName = target.tagName.toLowerCase();
  if (tagName === "input" || tagName === "textarea") return true;
  if (target.isContentEditable) return true;

  return false;
}

/**
 * Global keydown handler. Attach this to the window keydown event.
 *
 * When the target is an editable element, only Escape shortcuts are handled.
 * Supports Ctrl (Windows) and Cmd (Mac) via metaKey || ctrlKey check.
 */
export function handleGlobalKeydown(event: KeyboardEvent): void {
  const inEditable = isEditableTarget(event);

  for (const shortcut of shortcuts) {
    // Key match (case-insensitive for letters)
    const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();
    if (!keyMatch) continue;

    // Modifier match: support both Ctrl (Windows) and Cmd (Mac)
    const ctrlRequired = shortcut.ctrl ?? false;
    const ctrlPressed = event.metaKey || event.ctrlKey;
    if (ctrlRequired !== ctrlPressed) continue;

    const shiftRequired = shortcut.shift ?? false;
    if (shiftRequired !== event.shiftKey) continue;

    // Inside editable elements, only allow Escape
    if (inEditable && shortcut.key.toLowerCase() !== "escape") continue;

    event.preventDefault();
    shortcut.action();
    return;
  }
}
