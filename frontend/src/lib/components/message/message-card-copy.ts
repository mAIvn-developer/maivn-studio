import { copyToClipboard } from "$lib/utils/clipboard";

function formatStructuredOutputForCopy(structuredOutput: unknown): string {
  return typeof structuredOutput === "string"
    ? structuredOutput
    : JSON.stringify(structuredOutput, null, 2);
}

export async function copyMessageCardContent(content: string): Promise<boolean> {
  return copyToClipboard(content);
}

export async function copyMessageCardStructuredOutput(structuredOutput: unknown): Promise<boolean> {
  return copyToClipboard(formatStructuredOutputForCopy(structuredOutput));
}
