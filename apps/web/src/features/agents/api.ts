import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type { Agent, AgentVersion, CreateAgentRequest, PublishAgentInput } from "./types";

export async function listAgents(): Promise<Agent[]> {
  return unwrapApiResponse(await hifyApiClient.GET("/agents"));
}

export async function createAgent(request: CreateAgentRequest): Promise<Agent> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/agents", {
      body: request,
    }),
  );
}

export async function publishAgent(request: PublishAgentInput): Promise<AgentVersion> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/agents/{agent_id}/publish", {
      params: {
        path: {
          agent_id: request.agentId,
        },
      },
    }),
  );
}
