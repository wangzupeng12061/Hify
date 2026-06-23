import { createApiError } from "@/lib/api/errors";

import { HifySseDecoder, type HifySseMessage } from "./decoder";

export type StreamHifySseRequest = {
  fetch?: typeof fetch;
  method?: "GET" | "POST";
  onMessage: (message: HifySseMessage) => void;
  signal?: AbortSignal;
  url: string;
};

export async function streamHifySse(request: StreamHifySseRequest): Promise<void> {
  const fetchImplementation = request.fetch ?? fetch;
  const response = await fetchImplementation(request.url, {
    credentials: "same-origin",
    headers: {
      Accept: "text/event-stream",
    },
    method: request.method ?? "GET",
    signal: request.signal,
  });

  if (!response.ok) {
    throw createApiError({
      error: await readErrorResponse(response),
      response,
    });
  }

  if (!response.body) {
    throw createApiError({
      error: null,
      response,
    });
  }

  await readSseBody(response.body, request.onMessage);
}

async function readSseBody(
  body: ReadableStream<Uint8Array>,
  onMessage: (message: HifySseMessage) => void,
): Promise<void> {
  const reader = body.getReader();
  const textDecoder = new TextDecoder();
  const sseDecoder = new HifySseDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      const messages = sseDecoder.push(textDecoder.decode(value, { stream: true }));
      messages.forEach(onMessage);
    }

    const finalMessages = [
      ...sseDecoder.push(textDecoder.decode()),
      ...sseDecoder.close(),
    ];
    finalMessages.forEach(onMessage);
  } finally {
    reader.releaseLock();
  }
}

async function readErrorResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  const text = await response.text();
  return text ? { detail: { code: "api.request_failed", message: text, metadata: null } } : null;
}
