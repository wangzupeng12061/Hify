export class HifySseProtocolError extends Error {
  readonly code = "sse.protocol_error";

  constructor(message: string, options: { cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = "HifySseProtocolError";
  }
}
