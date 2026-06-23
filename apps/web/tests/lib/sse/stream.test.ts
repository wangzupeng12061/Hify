import { describe, expect, it } from "vitest";

import { streamHifySse } from "@/lib/sse";

describe("streamHifySse", () => {
  it("streams decoded SSE messages from a fetch response", async () => {
    const messages: unknown[] = [];
    const fetchMock = async () =>
      new Response(createTextStream('id: 1\nevent: run.started\ndata: {"ok":true}\n\n'), {
        headers: {
          "content-type": "text/event-stream",
        },
        status: 200,
      });

    await streamHifySse({
      fetch: fetchMock as typeof fetch,
      method: "POST",
      onMessage: (message) => messages.push(message),
      url: "/api/runs/run-1/execute-stream",
    });

    expect(messages).toEqual([
      {
        data: '{"ok":true}',
        event: "run.started",
        id: "1",
      },
    ]);
  });

  it("translates non-ok API responses into HifyApiError", async () => {
    const fetchMock = async () =>
      new Response(
        JSON.stringify({
          detail: {
            code: "RUN_NOT_FOUND",
            message: "run was not found",
            metadata: null,
          },
        }),
        {
          headers: {
            "content-type": "application/json",
          },
          status: 404,
        },
      );

    await expect(
      streamHifySse({
        fetch: fetchMock as typeof fetch,
        onMessage: () => undefined,
        url: "/api/runs/run-1/execute-stream",
      }),
    ).rejects.toMatchObject({
      code: "RUN_NOT_FOUND",
      message: "run was not found",
      status: 404,
    });
  });
});

function createTextStream(value: string): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(value));
      controller.close();
    },
  });
}
