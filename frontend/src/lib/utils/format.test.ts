import { describe, expect, it } from "vitest";

import {
  formatDuration,
  formatTokens,
  formatValue,
  isValueTruncated,
  formatTime,
  formatTimeWithSeconds,
} from "./format";

// MARK: formatDuration

describe("formatDuration", () => {
  it("formats sub-minute durations as seconds", () => {
    expect(formatDuration(0)).toBe("0.0s");
    expect(formatDuration(500)).toBe("0.5s");
    expect(formatDuration(1234)).toBe("1.2s");
    expect(formatDuration(59999)).toBe("60.0s");
  });

  it("formats durations >= 60s as minutes and seconds", () => {
    expect(formatDuration(60000)).toBe("1m 0.0s");
    expect(formatDuration(90000)).toBe("1m 30.0s");
    expect(formatDuration(125500)).toBe("2m 5.5s");
  });

  it("handles large durations", () => {
    expect(formatDuration(600000)).toBe("10m 0.0s");
    expect(formatDuration(3661000)).toBe("61m 1.0s");
  });
});

// MARK: formatTokens

describe("formatTokens", () => {
  it("formats numbers with locale-appropriate separators", () => {
    expect(formatTokens(0)).toBe("0");
    expect(formatTokens(999)).toBe("999");
    // 1000+ should have commas (in en-US locale)
    const result = formatTokens(1000);
    expect(result).toMatch(/1.?000/);
  });

  it("formats large numbers", () => {
    const result = formatTokens(1234567);
    expect(result).toMatch(/1.?234.?567/);
  });
});

// MARK: formatValue

describe("formatValue", () => {
  it("returns 'null' for null and undefined", () => {
    expect(formatValue(null)).toBe("null");
    expect(formatValue(undefined)).toBe("null");
  });

  it("returns short strings unchanged", () => {
    expect(formatValue("hello")).toBe("hello");
    expect(formatValue("short string")).toBe("short string");
  });

  it("truncates strings longer than 200 chars by default", () => {
    const longStr = "a".repeat(250);
    const result = formatValue(longStr);
    expect(result).toHaveLength(203); // 200 + "..."
    expect(result.endsWith("...")).toBe(true);
  });

  it("does not truncate when truncate=false", () => {
    const longStr = "a".repeat(250);
    const result = formatValue(longStr, false);
    expect(result).toHaveLength(250);
  });

  it("formats objects as pretty JSON", () => {
    expect(formatValue({ key: "value" })).toContain('"key"');
  });

  it("truncates JSON longer than 400 chars", () => {
    const obj = { data: "x".repeat(500) };
    const result = formatValue(obj);
    expect(result.endsWith("...")).toBe(true);
    expect(result.length).toBeLessThanOrEqual(403);
  });

  it("does not truncate JSON when truncate=false", () => {
    const obj = { data: "x".repeat(500) };
    const result = formatValue(obj, false);
    expect(result.endsWith("...")).toBe(false);
  });

  it("formats numbers as JSON", () => {
    expect(formatValue(42)).toBe("42");
  });

  it("formats booleans as JSON", () => {
    expect(formatValue(true)).toBe("true");
    expect(formatValue(false)).toBe("false");
  });

  it("formats arrays as JSON", () => {
    const result = formatValue([1, 2, 3]);
    expect(result).toContain("1");
    expect(result).toContain("2");
    expect(result).toContain("3");
  });
});

// MARK: isValueTruncated

describe("isValueTruncated", () => {
  it("returns false for null and undefined", () => {
    expect(isValueTruncated(null)).toBe(false);
    expect(isValueTruncated(undefined)).toBe(false);
  });

  it("returns false for short strings", () => {
    expect(isValueTruncated("short")).toBe(false);
    expect(isValueTruncated("a".repeat(200))).toBe(false);
  });

  it("returns true for strings longer than 200 chars", () => {
    expect(isValueTruncated("a".repeat(201))).toBe(true);
  });

  it("returns false for small objects", () => {
    expect(isValueTruncated({ key: "value" })).toBe(false);
  });

  it("returns true for large objects whose JSON exceeds 400 chars", () => {
    expect(isValueTruncated({ data: "x".repeat(500) })).toBe(true);
  });
});

// MARK: formatTime

describe("formatTime", () => {
  it("returns a formatted time string", () => {
    const result = formatTime("2024-06-15T14:30:00Z");
    // Should contain hours and minutes (format depends on locale)
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("handles ISO timestamps with milliseconds", () => {
    const result = formatTime("2024-06-15T14:30:45.123Z");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });
});

// MARK: formatTimeWithSeconds

describe("formatTimeWithSeconds", () => {
  it("returns a formatted time string with seconds", () => {
    const result = formatTimeWithSeconds("2024-06-15T14:30:45Z");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("produces a longer string than formatTime (includes seconds)", () => {
    const ts = "2024-06-15T14:30:45Z";
    const withSec = formatTimeWithSeconds(ts);
    const withoutSec = formatTime(ts);
    // formatTimeWithSeconds should be at least as long (includes seconds portion)
    expect(withSec.length).toBeGreaterThanOrEqual(withoutSec.length);
  });
});
