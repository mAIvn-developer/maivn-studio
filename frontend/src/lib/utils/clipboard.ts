/**
 * Clipboard utility with reactive copied state.
 * Extracted from MessageCard and ExchangeContainer.
 */

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
