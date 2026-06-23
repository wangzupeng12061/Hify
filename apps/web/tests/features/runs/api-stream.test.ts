import { describe, expect, it } from "vitest";

import { executeRunStream } from "@/features/runs/api";

describe("executeRunStream", () => {
  it("posts to the run stream endpoint and emits typed run events", async () => {
    const events: unknown[] = [];
    const fetchMock = async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(input).toBe("/api/runs/run-1/execute-stream");
      expect(init?.method).toBe("POST");
      expect(init?.headers).toEqual({
        Accept: "text/event-stream",
      });

      return new Response(
        createTextStream(
          `id: 2
event: output.text_delta
data: ${JSON.stringify(createRunEventResponse())}

`,
        ),
        {
          headers: {
            "content-type": "text/event-stream",
          },
          status: 200,
        },
      );
    };

    await executeRunStream({
      fetch: fetchMock as typeof fetch,
      onEvent: (event) => events.push(event),
      runId: "run-1",
    });

    expect(events).toEqual([createRunEventResponse()]);
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

function createRunEventResponse() {
  return {
    created_at: "2026-06-23T00:00:00Z",
    event_type: "output.text_delta",
    id: "event-2",
    payload: {
      text: "Hello",
    },
    run_id: "run-1",
    sequence_number: 2,
    team_id: "team-1",
  };
}
