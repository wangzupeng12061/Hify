import type { components } from "@/lib/api/generated/schema";

export type CreateToolRequest = components["schemas"]["CreateToolRequest"];
export type Tool = components["schemas"]["ToolResponse"];

export type GetToolInput = {
  toolId: string;
};
