import type { components } from "@/lib/api/generated/schema";

export type Agent = components["schemas"]["AgentResponse"];
export type AgentVersion = components["schemas"]["AgentVersionResponse"];
export type CreateAgentRequest = components["schemas"]["CreateAgentRequest"];

export type PublishAgentInput = {
  agentId: string;
};
