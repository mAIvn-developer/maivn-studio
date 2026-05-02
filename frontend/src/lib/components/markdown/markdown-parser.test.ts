import { describe, expect, it } from "vitest";

import { parseMarkdown } from "./markdown-parser";

describe("parseMarkdown links", () => {
  it("renders safe absolute links", () => {
    const html = parseMarkdown("[docs](https://developer.maivn.io/docs?section=studio&view=chat)");

    expect(html).toContain(
      '<a href="https://developer.maivn.io/docs?section=studio&amp;view=chat"',
    );
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
  });

  it("renders safe relative links", () => {
    const html = parseMarkdown("[config](./docs/getting-started.md)");

    expect(html).toContain('<a href="./docs/getting-started.md"');
  });

  it("drops unsafe javascript links to text", () => {
    const html = parseMarkdown("[click me](javascript:alert(1))");

    expect(html).toContain("click me");
    expect(html).not.toContain("<a ");
    expect(html).not.toContain("javascript:");
  });

  it("drops quoted hrefs that could escape the attribute", () => {
    const html = parseMarkdown('[click me](" onclick="alert(1))');

    expect(html).toContain("click me");
    expect(html).not.toContain("onclick");
    expect(html).not.toContain("<a ");
  });
});
