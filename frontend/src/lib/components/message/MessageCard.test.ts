import { render } from "svelte/server";
import { describe, expect, it } from "vitest";

import type { Message } from "$lib/types";

import MessageCard from "./MessageCard.svelte";

function makeAssistantMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "assistant-1",
    role: "assistant",
    messageType: "ai",
    content: "Streaming response",
    timestamp: "2026-06-17T12:00:00.000Z",
    ...overrides,
  };
}

describe("MessageCard", () => {
  it("marks assistant markdown as streaming while chunks are still arriving", () => {
    const { body } = render(MessageCard, {
      props: {
        message: makeAssistantMessage({
          metadata: {
            isStreaming: true,
          },
        }),
      },
    });

    expect(body).toMatch(/class="[^"]*\bmarkdown-content\b[^"]*\bstreaming\b[^"]*"/);
    expect(body).toMatch(/class="[^"]*\bcursor\b[^"]*"/);
  });
});
