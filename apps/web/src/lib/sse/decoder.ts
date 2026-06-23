export type HifySseMessage = {
  data: string;
  event: string;
  id: string | null;
};

export class HifySseDecoder {
  private buffer = "";
  private dataLines: string[] = [];
  private eventType = "";
  private lastEventId: string | null = null;

  push(chunk: string): HifySseMessage[] {
    const messages: HifySseMessage[] = [];
    this.buffer += chunk;

    while (true) {
      const lineEndIndex = this.findLineEndIndex();
      if (lineEndIndex === -1) {
        break;
      }

      const rawLine = this.buffer.slice(0, lineEndIndex);
      const nextIndex =
        this.buffer[lineEndIndex] === "\r" && this.buffer[lineEndIndex + 1] === "\n"
          ? lineEndIndex + 2
          : lineEndIndex + 1;
      this.buffer = this.buffer.slice(nextIndex);

      const message = this.processLine(rawLine);
      if (message) {
        messages.push(message);
      }
    }

    return messages;
  }

  close(): HifySseMessage[] {
    if (this.buffer === "") {
      return this.dispatch();
    }

    const message = this.processLine(this.buffer);
    this.buffer = "";
    return [...(message ? [message] : []), ...this.dispatch()];
  }

  private findLineEndIndex(): number {
    const carriageReturnIndex = this.buffer.indexOf("\r");
    const lineFeedIndex = this.buffer.indexOf("\n");

    if (carriageReturnIndex === -1) {
      return lineFeedIndex;
    }
    if (lineFeedIndex === -1) {
      return carriageReturnIndex;
    }
    return Math.min(carriageReturnIndex, lineFeedIndex);
  }

  private processLine(rawLine: string): HifySseMessage | null {
    const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;

    if (line === "") {
      return this.dispatch()[0] ?? null;
    }
    if (line.startsWith(":")) {
      return null;
    }

    const separatorIndex = line.indexOf(":");
    const field = separatorIndex === -1 ? line : line.slice(0, separatorIndex);
    const rawValue = separatorIndex === -1 ? "" : line.slice(separatorIndex + 1);
    const value = rawValue.startsWith(" ") ? rawValue.slice(1) : rawValue;

    if (field === "data") {
      this.dataLines.push(value);
    } else if (field === "event") {
      this.eventType = value;
    } else if (field === "id") {
      this.lastEventId = value;
    }

    return null;
  }

  private dispatch(): HifySseMessage[] {
    if (this.dataLines.length === 0) {
      this.eventType = "";
      return [];
    }

    const message: HifySseMessage = {
      data: this.dataLines.join("\n"),
      event: this.eventType || "message",
      id: this.lastEventId,
    };
    this.dataLines = [];
    this.eventType = "";
    return [message];
  }
}
