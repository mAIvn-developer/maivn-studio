/**
 * Utility functions for detecting interrupt input types from prompts.
 */

import type { InterruptChoice, InterruptInputType } from "$lib/types";

// MARK: Detection Patterns

// Boolean patterns (yes/no style)
const BOOLEAN_PATTERNS = [
  /\(yes\/no\)/i,
  /\(y\/n\)/i,
  /\(true\/false\)/i,
  /yes or no/i,
  /true or false/i,
];

// Confirmation patterns (proceed/confirm style)
const CONFIRMATION_PATTERNS = [
  /\bconfirm\b/i,
  /\bproceed\b/i,
  /\bcontinue\b/i,
  /are you sure/i,
  /do you want to/i,
  /would you like to/i,
];

// Number patterns
const NUMBER_PATTERNS = [
  /enter a number/i,
  /enter the number/i,
  /how many/i,
  /\bamount\b/i,
  /\bcount\b/i,
  /\bquantity\b/i,
  /\bage\b/i,
  /\bprice\b/i,
  /\bcost\b/i,
];

// Email patterns
const EMAIL_PATTERNS = [/\bemail\b/i, /\be-mail\b/i, /email address/i];

// Password/secret patterns
const PASSWORD_PATTERNS = [
  /\bpassword\b/i,
  /\bsecret\b/i,
  /\bapi.?key\b/i,
  /\btoken\b/i,
  /\bpin\b/i,
];

// MARK: Detection Functions

/**
 * Detect the input type from a prompt string.
 */
export function detectInputType(prompt: string): InterruptInputType {
  const normalizedPrompt = prompt.trim();

  // Check for password/secret first (highest priority)
  if (PASSWORD_PATTERNS.some((p) => p.test(normalizedPrompt))) {
    return "password";
  }

  // Check for email
  if (EMAIL_PATTERNS.some((p) => p.test(normalizedPrompt))) {
    return "email";
  }

  // Check for explicit boolean (yes/no)
  if (BOOLEAN_PATTERNS.some((p) => p.test(normalizedPrompt))) {
    return "boolean";
  }

  // Check for confirmation
  if (CONFIRMATION_PATTERNS.some((p) => p.test(normalizedPrompt))) {
    return "confirmation";
  }

  // Check for number
  if (NUMBER_PATTERNS.some((p) => p.test(normalizedPrompt))) {
    return "number";
  }

  // Check for choices (numbered or lettered options)
  const choices = extractChoices(normalizedPrompt);
  if (choices.length >= 2) {
    return "choice";
  }

  // Default to text
  return "text";
}

/**
 * Extract choices from a prompt that contains numbered or lettered options.
 * Examples:
 *   "1. Option A\n2. Option B\n3. Option C"
 *   "a) First choice\nb) Second choice"
 */
export function extractChoices(prompt: string): InterruptChoice[] {
  const choices: InterruptChoice[] = [];
  const lines = prompt.split("\n");

  // Pattern for numbered options: "1. Option" or "1) Option" or "1: Option"
  const numberedPattern = /^\s*(\d+)[.):\s]+(.+)$/;
  // Pattern for lettered options: "a. Option" or "a) Option" or "A. Option"
  const letteredPattern = /^\s*([a-zA-Z])[.):\s]+(.+)$/;

  for (const line of lines) {
    const numberedMatch = line.match(numberedPattern);
    if (numberedMatch) {
      choices.push({
        value: numberedMatch[1],
        label: numberedMatch[2].trim(),
      });
      continue;
    }

    const letteredMatch = line.match(letteredPattern);
    if (letteredMatch) {
      choices.push({
        value: letteredMatch[1].toLowerCase(),
        label: letteredMatch[2].trim(),
      });
    }
  }

  return choices;
}

/**
 * Get display-friendly choices for boolean input.
 */
export function getBooleanChoices(): InterruptChoice[] {
  return [
    { value: "yes", label: "Yes" },
    { value: "no", label: "No" },
  ];
}

/**
 * Get display-friendly choices for confirmation input.
 */
export function getConfirmationChoices(): InterruptChoice[] {
  return [
    { value: "yes", label: "Confirm" },
    { value: "no", label: "Cancel" },
  ];
}

/**
 * Analyze a prompt and return the detected type and any extracted choices.
 */
export function analyzePrompt(prompt: string): {
  inputType: InterruptInputType;
  choices: InterruptChoice[];
  cleanPrompt: string;
} {
  const inputType = detectInputType(prompt);
  let choices: InterruptChoice[] = [];
  let cleanPrompt = prompt;

  switch (inputType) {
    case "boolean":
      choices = getBooleanChoices();
      // Remove the (yes/no) etc. from the prompt
      cleanPrompt = prompt
        .replace(/\s*\(yes\/no\)/gi, "")
        .replace(/\s*\(y\/n\)/gi, "")
        .replace(/\s*\(true\/false\)/gi, "")
        .trim();
      break;

    case "confirmation":
      choices = getConfirmationChoices();
      break;

    case "choice": {
      choices = extractChoices(prompt);
      // Extract just the question part (before the options)
      const lines = prompt.split("\n");
      const questionLines: string[] = [];
      for (const line of lines) {
        if (/^\s*[\da-zA-Z][.):\s]/.test(line)) {
          break;
        }
        questionLines.push(line);
      }
      cleanPrompt = questionLines.join("\n").trim() || prompt;
      break;
    }

    default:
      cleanPrompt = prompt;
  }

  return { inputType, choices, cleanPrompt };
}
