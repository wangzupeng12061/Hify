import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type {
  ActorContext,
  AddTeamMemberInput,
  CreateTeamRequest,
  CreateUserRequest,
  Membership,
  Team,
  User,
} from "./types";

export async function getCurrentUser(): Promise<ActorContext> {
  return unwrapApiResponse(await hifyApiClient.GET("/identity/me"));
}

export async function createUser(request: CreateUserRequest): Promise<User> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/identity/users", {
      body: request,
    }),
  );
}

export async function createTeam(request: CreateTeamRequest): Promise<Team> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/identity/teams", {
      body: request,
    }),
  );
}

export async function addTeamMember(request: AddTeamMemberInput): Promise<Membership> {
  const { teamId, ...body } = request;

  return unwrapApiResponse(
    await hifyApiClient.POST("/identity/teams/{team_id}/members", {
      body,
      params: {
        path: {
          team_id: teamId,
        },
      },
    }),
  );
}
