import { describe, expect, it } from "vitest";

import type { InvocationConfig } from "$lib/types";

import { applyInvocationMode, getInvocationMode } from "./invocationMode";

describe("getInvocationMode", () => {
  it("defaults to stream when stream_response is missing", () => {
    expect(getInvocationMode({ force_final_tool: false })).toBe("stream");
  });

  it("returns invoke when stream_response is false", () => {
    expect(getInvocationMode({ force_final_tool: false, stream_response: false })).toBe("invoke");
  });

  it("forces invoke when structured output is enabled", () => {
    expect(getInvocationMode({ force_final_tool: false, stream_response: true }, true)).toBe(
      "invoke",
    );
  });
});

describe("applyInvocationMode", () => {
  it("maps stream mode to stream_response true", () => {
    const config: InvocationConfig = {
      force_final_tool: false,
      stream_response: false,
      status_messages: false,
    };

    expect(applyInvocationMode(config, "stream")).toEqual({
      force_final_tool: false,
      stream_response: true,
      status_messages: false,
    });
  });

  it("maps invoke mode to stream_response false and clears status messages", () => {
    const config: InvocationConfig = {
      force_final_tool: true,
      stream_response: true,
      status_messages: true,
    };

    expect(applyInvocationMode(config, "invoke")).toEqual({
      force_final_tool: true,
      stream_response: false,
      status_messages: false,
    });
  });
});
