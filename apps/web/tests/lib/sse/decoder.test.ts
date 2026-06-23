import { describe, expect, it } from "vitest";

import { HifySseDecoder } from "@/lib/sse";

describe("HifySseDecoder", () => {
  it("decodes event id, type, and JSON data across chunks", () => {
    const decoder = new HifySseDecoder();

    const firstMessages = decoder.push('id: 1\nevent: output.text_delta\ndata: {"text":"Hel');
    const secondMessages = decoder.push('lo"}\n\n');

    expect(firstMessages).toEqual([]);
    expect(secondMessages).toEqual([
      {
        data: '{"text":"Hello"}',
        event: "output.text_delta",
        id: "1",
      },
    ]);
  });

  it("ignores heartbeat comments and joins multiline data", () => {
    const decoder = new HifySseDecoder();

    const messages = decoder.push(": heartbeat\n\nevent: diagnostic\ndata: first\ndata: second\n\n");

    expect(messages).toEqual([
      {
        data: "first\nsecond",
        event: "diagnostic",
        id: null,
      },
    ]);
  });
});
