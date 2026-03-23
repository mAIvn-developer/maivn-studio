import { describe, expect, it } from "vitest";

import {
  detectInputType,
  extractChoices,
  getBooleanChoices,
  getConfirmationChoices,
  analyzePrompt,
} from "./interruptDetection";

// MARK: detectInputType

describe("detectInputType", () => {
  describe("password detection", () => {
    it("detects password prompts", () => {
      expect(detectInputType("Enter your password")).toBe("password");
      expect(detectInputType("Please provide your secret")).toBe("password");
      expect(detectInputType("API key required")).toBe("password");
      expect(detectInputType("Enter your token")).toBe("password");
      expect(detectInputType("Enter your PIN")).toBe("password");
    });

    it("is case insensitive", () => {
      expect(detectInputType("ENTER YOUR PASSWORD")).toBe("password");
      expect(detectInputType("Api Key")).toBe("password");
    });
  });

  describe("email detection", () => {
    it("detects email prompts", () => {
      expect(detectInputType("Enter your email")).toBe("email");
      expect(detectInputType("What is your e-mail address?")).toBe("email");
      expect(detectInputType("Provide your email address")).toBe("email");
    });
  });

  describe("boolean detection", () => {
    it("detects yes/no prompts", () => {
      expect(detectInputType("Do you agree? (yes/no)")).toBe("boolean");
      expect(detectInputType("Continue? (y/n)")).toBe("boolean");
      expect(detectInputType("Is this correct? (true/false)")).toBe("boolean");
      expect(detectInputType("Do you want to proceed? yes or no")).toBe("boolean");
      expect(detectInputType("Is it ready? true or false")).toBe("boolean");
    });
  });

  describe("confirmation detection", () => {
    it("detects confirmation prompts", () => {
      expect(detectInputType("Please confirm your action")).toBe("confirmation");
      expect(detectInputType("Do you want to proceed with the deletion?")).toBe("confirmation");
      expect(detectInputType("Would you like to continue?")).toBe("confirmation");
      expect(detectInputType("Are you sure about this?")).toBe("confirmation");
    });
  });

  describe("number detection", () => {
    it("detects number prompts", () => {
      expect(detectInputType("Enter a number between 1 and 10")).toBe("number");
      expect(detectInputType("How many items do you need?")).toBe("number");
      expect(detectInputType("What is the quantity?")).toBe("number");
      expect(detectInputType("Enter the amount")).toBe("number");
      expect(detectInputType("What is your age?")).toBe("number");
      expect(detectInputType("What is the price?")).toBe("number");
      expect(detectInputType("Enter the cost")).toBe("number");
    });
  });

  describe("choice detection", () => {
    it("detects numbered choice prompts", () => {
      const prompt = "Choose an option:\n1. First option\n2. Second option\n3. Third option";
      expect(detectInputType(prompt)).toBe("choice");
    });

    it("detects lettered choice prompts", () => {
      const prompt = "Select one:\na) Option A\nb) Option B";
      expect(detectInputType(prompt)).toBe("choice");
    });

    it("requires at least 2 choices", () => {
      const prompt = "Note:\n1. Single option only";
      expect(detectInputType(prompt)).toBe("text"); // Only 1 choice = text
    });
  });

  describe("text fallback", () => {
    it("returns text for generic prompts", () => {
      expect(detectInputType("What is your name?")).toBe("text");
      expect(detectInputType("Enter a description")).toBe("text");
      expect(detectInputType("Tell me about yourself")).toBe("text");
    });
  });

  describe("priority ordering", () => {
    it("password takes priority over email", () => {
      // Both "password" and "email" could match, but password is checked first
      expect(detectInputType("Enter your email password")).toBe("password");
    });

    it("password takes priority over number", () => {
      expect(detectInputType("Enter the password amount")).toBe("password");
    });

    it("email takes priority over boolean", () => {
      expect(detectInputType("Email (yes/no)")).toBe("email");
    });

    it("boolean takes priority over confirmation", () => {
      expect(detectInputType("Do you want to proceed? (yes/no)")).toBe("boolean");
    });
  });
});

// MARK: extractChoices

describe("extractChoices", () => {
  it("extracts numbered choices with period separator", () => {
    const choices = extractChoices("1. Red\n2. Blue\n3. Green");
    expect(choices).toEqual([
      { value: "1", label: "Red" },
      { value: "2", label: "Blue" },
      { value: "3", label: "Green" },
    ]);
  });

  it("extracts numbered choices with parenthesis separator", () => {
    const choices = extractChoices("1) Option A\n2) Option B");
    expect(choices).toEqual([
      { value: "1", label: "Option A" },
      { value: "2", label: "Option B" },
    ]);
  });

  it("extracts numbered choices with colon separator", () => {
    const choices = extractChoices("1: First\n2: Second");
    expect(choices).toEqual([
      { value: "1", label: "First" },
      { value: "2", label: "Second" },
    ]);
  });

  it("extracts lettered choices", () => {
    const choices = extractChoices("a) Alpha\nb) Beta\nc) Gamma");
    expect(choices).toEqual([
      { value: "a", label: "Alpha" },
      { value: "b", label: "Beta" },
      { value: "c", label: "Gamma" },
    ]);
  });

  it("normalizes uppercase letters to lowercase", () => {
    const choices = extractChoices("A. Option A\nB. Option B");
    expect(choices).toEqual([
      { value: "a", label: "Option A" },
      { value: "b", label: "Option B" },
    ]);
  });

  it("handles mixed question and choices", () => {
    const prompt = "Pick a color:\n1. Red\n2. Blue";
    const choices = extractChoices(prompt);
    // "Pick a color:" doesn't match numbered/lettered pattern
    expect(choices).toEqual([
      { value: "1", label: "Red" },
      { value: "2", label: "Blue" },
    ]);
  });

  it("returns empty array for text without choices", () => {
    expect(extractChoices("Just a simple question")).toEqual([]);
    expect(extractChoices("")).toEqual([]);
  });

  it("trims whitespace from labels", () => {
    const choices = extractChoices("1.  Padded option  \n2.  Another  ");
    expect(choices[0].label).toBe("Padded option");
    expect(choices[1].label).toBe("Another");
  });

  it("handles leading whitespace on lines", () => {
    const choices = extractChoices("  1. Indented\n  2. Also indented");
    expect(choices).toHaveLength(2);
    expect(choices[0].label).toBe("Indented");
  });
});

// MARK: getBooleanChoices

describe("getBooleanChoices", () => {
  it("returns Yes/No choices", () => {
    const choices = getBooleanChoices();
    expect(choices).toEqual([
      { value: "yes", label: "Yes" },
      { value: "no", label: "No" },
    ]);
  });
});

// MARK: getConfirmationChoices

describe("getConfirmationChoices", () => {
  it("returns Confirm/Cancel choices", () => {
    const choices = getConfirmationChoices();
    expect(choices).toEqual([
      { value: "yes", label: "Confirm" },
      { value: "no", label: "Cancel" },
    ]);
  });
});

// MARK: analyzePrompt

describe("analyzePrompt", () => {
  it("analyzes a boolean prompt and strips indicator text", () => {
    const result = analyzePrompt("Do you agree? (yes/no)");
    expect(result.inputType).toBe("boolean");
    expect(result.choices).toEqual(getBooleanChoices());
    expect(result.cleanPrompt).toBe("Do you agree?");
  });

  it("analyzes a y/n prompt and strips indicator text", () => {
    const result = analyzePrompt("Continue? (y/n)");
    expect(result.inputType).toBe("boolean");
    expect(result.cleanPrompt).toBe("Continue?");
  });

  it("analyzes a true/false prompt and strips indicator text", () => {
    const result = analyzePrompt("Enabled? (true/false)");
    expect(result.inputType).toBe("boolean");
    expect(result.cleanPrompt).toBe("Enabled?");
  });

  it("analyzes a confirmation prompt", () => {
    const result = analyzePrompt("Please confirm the deletion");
    expect(result.inputType).toBe("confirmation");
    expect(result.choices).toEqual(getConfirmationChoices());
    expect(result.cleanPrompt).toBe("Please confirm the deletion");
  });

  it("analyzes a choice prompt and extracts question part", () => {
    const result = analyzePrompt("Pick a color:\n1. Red\n2. Blue\n3. Green");
    expect(result.inputType).toBe("choice");
    expect(result.choices).toHaveLength(3);
    expect(result.cleanPrompt).toBe("Pick a color:");
  });

  it("analyzes a text prompt with no modifications", () => {
    const result = analyzePrompt("What is your name?");
    expect(result.inputType).toBe("text");
    expect(result.choices).toEqual([]);
    expect(result.cleanPrompt).toBe("What is your name?");
  });

  it("analyzes a password prompt", () => {
    const result = analyzePrompt("Enter your password");
    expect(result.inputType).toBe("password");
    expect(result.choices).toEqual([]);
    expect(result.cleanPrompt).toBe("Enter your password");
  });

  it("analyzes an email prompt", () => {
    const result = analyzePrompt("Enter your email address");
    expect(result.inputType).toBe("email");
    expect(result.choices).toEqual([]);
    expect(result.cleanPrompt).toBe("Enter your email address");
  });

  it("analyzes a number prompt", () => {
    const result = analyzePrompt("How many items?");
    expect(result.inputType).toBe("number");
    expect(result.choices).toEqual([]);
    expect(result.cleanPrompt).toBe("How many items?");
  });

  it("handles choice prompt where all lines are options (no question)", () => {
    const result = analyzePrompt("1. Option A\n2. Option B");
    expect(result.inputType).toBe("choice");
    expect(result.choices).toHaveLength(2);
    // cleanPrompt falls back to original when no non-option lines
    expect(result.cleanPrompt).toBe("1. Option A\n2. Option B");
  });
});
