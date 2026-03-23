import type { MessageAttachmentPayload } from "$lib/types";

export interface PendingAttachment {
  id: string;
  file: File;
  name: string;
  mimeType: string;
  size: number;
}

export function formatAttachmentSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function dedupeAndAppendFiles(
  currentAttachments: PendingAttachment[],
  files: File[],
): PendingAttachment[] {
  const existingKeys = new Set(
    currentAttachments.map((attachment) =>
      [
        attachment.name,
        attachment.size.toString(),
        attachment.file.lastModified.toString(),
        attachment.mimeType,
      ].join(":"),
    ),
  );

  const next = [...currentAttachments];
  for (const file of files) {
    const key = [file.name, file.size.toString(), file.lastModified.toString(), file.type].join(
      ":",
    );
    if (existingKeys.has(key)) continue;
    existingKeys.add(key);
    next.push({
      id: crypto.randomUUID(),
      file,
      name: file.name || "attachment.bin",
      mimeType: file.type || "application/octet-stream",
      size: file.size,
    });
  }

  return next;
}

export function removePendingAttachment(
  currentAttachments: PendingAttachment[],
  attachmentId: string,
): PendingAttachment[] {
  return currentAttachments.filter((attachment) => attachment.id !== attachmentId);
}

function clearAttachments(): PendingAttachment[] {
  return [];
}

export function clearPendingAttachments(): PendingAttachment[] {
  return clearAttachments();
}

async function fileToAttachmentPayload(file: File): Promise<MessageAttachmentPayload> {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(new Error(`Failed to read attachment: ${file.name}`));
    reader.readAsDataURL(file);
  });
  const commaIndex = dataUrl.indexOf(",");
  if (commaIndex < 0) {
    throw new Error(`Attachment encoding failed: ${file.name}`);
  }
  return {
    name: file.name || "attachment.bin",
    mime_type: file.type || "application/octet-stream",
    content_base64: dataUrl.slice(commaIndex + 1),
  };
}

export async function buildAttachmentPayloads(
  pendingAttachments: PendingAttachment[],
): Promise<MessageAttachmentPayload[] | undefined> {
  if (pendingAttachments.length === 0) return undefined;
  const payloads = await Promise.all(
    pendingAttachments.map((attachment) => fileToAttachmentPayload(attachment.file)),
  );
  return payloads.length > 0 ? payloads : undefined;
}
