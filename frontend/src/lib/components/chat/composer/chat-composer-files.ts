export function extractFilesFromInputEvent(event: Event): File[] {
  const target = event.target as HTMLInputElement;
  return target.files ? Array.from(target.files) : [];
}

export function resetFileInputValue(event: Event): void {
  const target = event.target as HTMLInputElement;
  target.value = "";
}

export function extractFilesFromClipboardEvent(event: ClipboardEvent): File[] {
  const items = event.clipboardData?.items;
  if (!items || items.length === 0) return [];

  const files: File[] = [];
  for (const item of Array.from(items)) {
    if (item.kind !== "file") continue;
    const file = item.getAsFile();
    if (file) files.push(file);
  }

  return files;
}

export function shouldIgnoreDragLeave(event: DragEvent): boolean {
  const relatedTarget = event.relatedTarget as Node | null;
  const currentTarget = event.currentTarget as Node | null;
  return !!(relatedTarget && currentTarget && currentTarget.contains(relatedTarget));
}

export function extractFilesFromDropEvent(event: DragEvent): File[] {
  return event.dataTransfer?.files ? Array.from(event.dataTransfer.files) : [];
}
