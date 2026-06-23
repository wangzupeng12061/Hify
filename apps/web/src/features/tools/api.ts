import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type { CreateToolRequest, GetToolInput, Tool } from "./types";

export async function createTool(request: CreateToolRequest): Promise<Tool> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/tools", {
      body: request,
    }),
  );
}

export async function listTools(): Promise<Tool[]> {
  return unwrapApiResponse(await hifyApiClient.GET("/tools"));
}

export async function getTool(request: GetToolInput): Promise<Tool> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/tools/{tool_id}", {
      params: {
        path: {
          tool_id: request.toolId,
        },
      },
    }),
  );
}
