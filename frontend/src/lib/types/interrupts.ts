// MARK: Interrupt Status & Style

export type InterruptCardStatus = "waiting" | "submitting" | "completed" | "cancelled";
export type InterruptStyle = "inline" | "modal" | "drawer" | "floating" | "hybrid";

// MARK: Input Types

// Input type detection for smart interrupt UI
export type InterruptInputType =
  | "text" // Default text input
  | "boolean" // Yes/No buttons
  | "confirmation" // Confirm/Cancel buttons
  | "choice" // Multiple choice options
  | "number" // Numeric input
  | "email" // Email input
  | "password"; // Password/secret input

export interface InterruptChoice {
  value: string;
  label: string;
}

// MARK: Interrupt Data

export interface InterruptData {
  cardId: string;
  interruptId: string;
  checkpointId: string;
  toolName: string;
  prompt: string;
  dataKey: string;
  assignmentId: string;
  status: InterruptCardStatus;
  submittedValue?: string;
  timestamp: string;
  interruptNumber: number;
  totalInterrupts: number;
  turnSequence: number;
  // Auto-detected or specified input type
  inputType?: InterruptInputType;
  // Choices for choice input type
  choices?: InterruptChoice[];
}

export interface InterruptRequiredEvent {
  checkpoint_id: string;
  interrupt_id: string;
  prompt: string;
  data_key: string;
  arg_name: string;
  tool_name: string;
  assignment_id: string;
  assignment_index: number;
  interrupt_number: number;
  total_interrupts: number;
  timestamp: string;
  // Backend-provided input type (from Literal type detection or explicit)
  input_type?: string;
  // Backend-provided choices (from Literal type values)
  choices?: string[];
}
